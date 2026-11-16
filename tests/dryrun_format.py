"""Offline dry-run of the ple-harness force-write gate.

Simulates a gemma-style fix-loop: the scripted model only ever calls bash
with scratch commands. The gate must block those once time drops below
force_left, until the deliverable exists on disk. No network, no quota.
"""
import asyncio
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MODEL", "google-cloud/gemma-4-26b")
os.environ.setdefault("MODEL_BASE_URL", "http://127.0.0.1:9/unused")
os.environ.setdefault("MODEL_KEY", "unused")

import serve  # noqa: E402
serve.FINISH_MARGIN_SEC = 30  # keep the sim clock from tripping the time-up cutoff

SANDBOX = "/tmp/ple-harness-dryrun-fs"
os.makedirs(SANDBOX, exist_ok=True)

# a stale deliverable from a previous run would poison the assertions
for _f in os.listdir(SANDBOX):
    os.remove(os.path.join(SANDBOX, _f))

DELIV = "Thelbridge_Verification_Memo_Item051_BlockC.docx"
TOTAL = 1000.0
FORCE_LEFT = 300.0  # until(FORCE_SHARE=0.30) on a 1000s budget
NUDGE_LEFT = 660.0


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
        deliverables=[DELIV],
        user_text=session.instruction,
    )

    # local filesystem instead of the task container
    async def fake_bash(command, timeout_sec=120):
        return local_bash(command)
    agent.bash = fake_bash

    async def fake_write_file(path, content="", append=False, **kw):
        p = os.path.join(SANDBOX, path.replace("/filesystem/", ""))
        if path.endswith(".docx") and content.startswith("ZIP:"):
            content = content[4:]
            import zipfile
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("word/document.xml",
                           "<w:doc><w:t>" + content + "</w:t></w:doc>")
        else:
            with open(p, "a" if append else "w") as f:
                f.write(content)
        return "ok"

    agent.write_file = fake_write_file
    agent.read_file = lambda path, **kw: "file text"
    agent.edit_file = lambda **kw: "ok"

    # scripted model: burns turns on scratch bash, keeps scratching inside
    # the gate zone (left<300 from dispatch turn 8 on), finally writes
    script = [
        make_reply(calls=[("bash", {"command": "python3 fix.py"})]),
        # first write: plain text under a .docx name - must be REJECTED
        make_reply(calls=[("write_file", {"path": f"/filesystem/{DELIV}", "content": "just text"})]),
        # second write: a real zip with only 4 words - must be REJECTED (run22)
        make_reply(calls=[("write_file", {"path": f"/filesystem/{DELIV}", "content": "ZIP:four word memo only"})]),
        # third write: valid container + real word count - must be accepted
        make_reply(calls=[("write_file", {"path": f"/filesystem/{DELIV}", "content": "ZIP:" + "memo " * 150})]),
        make_reply(text="Done: memo written."),
    ]
    turns = {"i": 0}

    async def fake_complete(**kw):
        i = turns["i"]
        turns["i"] += 1
        # the clock burns 100s per model turn: gate zone from turn 8 on...
        # use 80s so the gate zone (<=300) starts at turn 9; tighten: 100
        session.left[0] = max(0.0, TOTAL - 40 * (i + 1))
        print(f"-- turn {i}: left={session.left[0]}")
        return script[min(i, len(script) - 1)]

    agent.complete = fake_complete
    result = await agent.run()

    refusals = [l for l in session.logs if "refused finish" in l]
    print("refusals:", refusals)
    blocked = [
        m for m in agent.messages
        if m.get("role") == "tool" and "BLOCKED" in str(m.get("content", ""))
    ]
    on_disk = os.path.exists(os.path.join(SANDBOX, DELIV))
    print()
    print("blocked tool results:", len(blocked))
    print("nudge logs:", [l for l in session.logs if l.startswith("nudge")])
    print("gate log:", [l for l in session.logs if "force-write gate" in l])
    print("deliverable on disk:", on_disk)
    print("final:", (result or "")[:120])

    rejects = [m for m in agent.messages if m.get("role")=="tool" and "cannot score it" in str(m.get("content",""))]
    assert len(rejects) == 2, f"expected 2 invalid-notes, got {len(rejects)}"
    reasons = " ".join(str(m.get("content")) for m in rejects)
    assert "plain text with a .docx name" in reasons, "run19 case missing"
    assert "only 4 words of memo text" in reasons, "run22 word-floor case missing"
    valid_logs = [l for l in session.logs if l.startswith("deliverable valid")]
    assert len(valid_logs) == 1, f"expected 1 valid-accept log, got {valid_logs}"
    assert len(refusals) == 0, f"no refusal expected once a valid file exists, got {refusals}"
    assert on_disk, "deliverable never landed after refusal"
    print("SCENARIO-4 PASS (invalid .docx rejected -> valid rebuild accepted)")


asyncio.run(main())
