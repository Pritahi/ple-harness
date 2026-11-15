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
        with open(p, "a" if append else "w") as f:
            f.write(content)
        return "ok"

    agent.write_file = fake_write_file
    agent.read_file = lambda path, **kw: "file text"
    agent.edit_file = lambda **kw: "ok"

    # scripted model: burns turns on scratch bash, keeps scratching inside
    # the gate zone (left<300 from dispatch turn 8 on), finally writes
    script = [
        make_reply(text="Attempt 1: I cannot do this."),
        make_reply(text="Attempt 2: still cannot."),
        make_reply(text="Attempt 3: truly stuck, giving up."),
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
    print("refusals:", len(refusals))
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

    assert len(refusals) == 2, f"expected exactly 2 refusals, got {len(refusals)}"
    assert not on_disk
    assert "Attempt 3" in (result or ""), "third finish was not accepted"
    print("SCENARIO-3 PASS (refusal cap 2, no infinite loop)")


asyncio.run(main())
