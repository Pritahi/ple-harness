"""Offline dry-run of the ple-harness deliverable salvage.

Simulates the run25/26 failure: the scripted model burns the whole budget
on scratch analysis scripts, ignores every nudge and the gate (bash stays
open), and never writes the named deliverable. Once time drops below
salvage_left the harness must assemble a valid deliverable from the run's
own findings by itself. No network, no quota.
"""
import asyncio
import json
import os
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MODEL", "google-cloud/gemma-4-26b")
os.environ.setdefault("MODEL_BASE_URL", "http://127.0.0.1:9/unused")
os.environ.setdefault("MODEL_KEY", "unused")

import serve  # noqa: E402
serve.FINISH_MARGIN_SEC = 30

SANDBOX = "/tmp/ple-harness-dryrun-fs"
os.makedirs(SANDBOX, exist_ok=True)

for _f in os.listdir(SANDBOX):
    os.remove(os.path.join(SANDBOX, _f))

DELIV = "Thelbridge_Verification_Memo_Item051_BlockC.docx"
TOTAL = 1000.0
FORCE_LEFT = 300.0
NUDGE_LEFT = 660.0
SALVAGE_LEFT = 150.0


class FakeSession:
    def __init__(self):
        self.workdir = "/filesystem"
        self.instruction = f"Do the engineering. Save it as {DELIV}."
        self.final_message = None
        self.left = [TOTAL]
        self.logs = []

    def time_left(self):
        return self.left[0]

    async def log(self, msg):
        self.logs.append(msg)
        print("  [log]", msg)


def local_bash(cmd, cwd=SANDBOX):
    cmd = cmd.replace("/filesystem", SANDBOX)
    try:
        out = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=50
        )
        return f"exit_code={out.returncode}\n{out.stdout}{out.stderr}"[:2000]
    except subprocess.TimeoutExpired:
        return "error: timeout"


def make_reply(calls=None, text=""):
    r = serve.Reply()
    r.text = text
    for i, (name, args) in enumerate(calls or []):
        r.calls[f"c{i}"] = {
            "id": f"c{i}",
            "name": name,
            "arguments": json.dumps(args),
            "extra": {},
            "function_extra": {},
        }
    return r


async def main():
    session = FakeSession()
    agent = serve.Agent(
        session,
        with_mcp=False,
        nudge_left=NUDGE_LEFT,
        force_left=FORCE_LEFT,
        salvage_left=SALVAGE_LEFT,
        deliverables=[DELIV],
        user_text=session.instruction,
    )
    agent.bash = lambda command, timeout_sec=120: _fake_bash(command)
    agent.read_file = lambda path, **kw: "file text"
    agent.edit_file = lambda **kw: "ok"

    async def fake_write_file(path, content="", append=False, **kw):
        # the salvage path writes /tmp helper files; the agent writes /filesystem
        target = path if path.startswith("/tmp/") else os.path.join(
            SANDBOX, path.replace("/filesystem/", "")
        )
        mode = "a" if append else "w"
        with open(target, mode) as f:
            f.write(content)
        return "ok"

    agent.write_file = fake_write_file

    async def _fake_bash(command, timeout_sec=120):
        return local_bash(command)

    # scripted model: only ever runs scratch analysis, then finishes
    script = [
        make_reply(
            calls=[("bash", {"command": "echo analyzing > /dev/null"})],
            text="Found loads: min 1100 kW, max 8526 kW, avg 4743 kW. " * 5,
        )
        for _ in range(30)
    ]
    script.append(make_reply(text="Done exploring."))
    turns = {"i": 0}

    async def fake_complete(**kw):
        i = turns["i"]
        turns["i"] += 1
        session.left[0] = max(0.0, TOTAL - 40 * (i + 1))
        print(f"-- turn {i}: left={session.left[0]} tool_choice={kw.get('tool_choice')}")
        if kw.get("tool_choice") == "none" and i < len(script):
            # the salvage call: return clean deliverable prose
            return make_reply(
                text="# Verification Memo\n\n"
                + ("Determination: settlement within tolerance, basis ALN-214 "
                   "load study. ") * 20
            )
        return script[min(i, len(script) - 1)]

    agent.complete = fake_complete
    result = await agent.run()

    path = os.path.join(SANDBOX, DELIV)
    on_disk = os.path.exists(path)
    print()
    print("salvage logs:", [l for l in session.logs if "salvage" in l])
    print("deliverable on disk:", on_disk)
    print("final:", (result or "")[:100])

    assert on_disk, "salvage never wrote the deliverable"
    with zipfile.ZipFile(path) as z:
        words = len(z.read("word/document.xml").decode().split())
    print("docx words:", words)
    assert words >= 100, "salvaged docx below the word floor"
    assert any("salvage deliverable written" in l for l in session.logs), \
        "no salvage log: " + str(session.logs)
    print("PASS: harness assembled a valid deliverable the agent never wrote")


asyncio.run(main())
