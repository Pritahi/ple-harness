# ple-harness

An entry for the [PLE Harness Competition](https://ple-bench.com) (Kaggle:
"Google - Agent Harness on Physical-Engineering's Last Exam").

A planner + worker + verifier agent harness on `google-cloud/gemma-4-26b`,
built on the competition kit's `custom-openai` sample (streaming, context
compaction, task MCP tools, retry and context-limit recovery) with the
three-role loop and time budgeting of its `plan-verify` sample:

1. The planner explores the task's files read-only and writes a structured
   plan (each deliverable's path, format, method, and how to check it),
   wrapping up after PLAN_SHARE (10%) of the task time.
2. The worker executes the plan with bash/read/write/edit tools and the
   task's MCP tools, wrapping up when CHECK_SHARE (25%) of the time remains.
3. The verifier starts a fresh conversation (task + plan + worker summary
   only), re-opens every deliverable and checks it against the task. Gaps go
   back to the worker for up to two fix rounds.

Role shares are tunable via `PLAN_SHARE`, `CHECK_SHARE`, `MAX_FIX_ROUNDS` in
`env:`. No task-specific logic: the same loop runs for every task.
