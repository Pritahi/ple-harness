# An Agent Harness for Physical Engineering's Last Exam: Deliverable Discipline Under Brutal Resource Ceilings

## Summary

We built a model-agnostic agent harness (planner / worker / verifier) and drove it entirely on free-tier infrastructure: GitHub Actions runners as the sandbox and Google's AI Studio free tier as the model API. The harness's mechanics held up across every dev task we ran; the failures we met were almost all economic (per-request token ceilings, daily request caps, job time ceilings) and behavioral (agents that explore forever and never write the deliverable). We describe the failure taxonomy, the fixes that worked, and why the same harness on the declared Stage 2 model converts directly into rubric points.

## Harness design

The harness is a single-file Python asyncio service speaking the OpenAI chat API to any endpoint. Three roles run in separate conversations:

1. **Planner** (read-only tools): inspects the task and files, writes a plan ending with a `DELIVERABLES:` line naming the exact output files.
2. **Worker** (bash + file tools): executes the plan with a tool loop that shows the remaining time after every tool result.
3. **Verifier** (read-only): re-opens every deliverable, recomputes key numbers, runs runnable deliverables end-to-end, and sends a gap list back to the worker for fix rounds.

Resource-guard mechanisms, each added in response to an observed death:

- **TPM pacing**: a token-bucket pacer keeps request rate under the endpoint's per-minute cap; a per-model `MODEL_TPM` env sets it.
- **Context compaction**: at a configurable token budget the conversation is summarized and earlier turns dropped; oversized tool results are truncated; reasoning text is capped.
- **429 recovery**: compact-on-429 plus retry with backoff; `num_retries: 0` at the proxy so the harness keeps control of failure handling.
- **Deliverable-aware escalating nudge**: once a time share passes, every few tool results append a reminder until the planner-named deliverable files exist on disk, escalating in tone.
- **Short-task bypass**: tasks under 45 minutes skip planner and verifier; one worker gets the whole budget.
- **Time-margin discipline**: a final-summary margin guarantees the agent answers with a summary instead of being cut off mid-tool-call.

## Failure analysis: a taxonomy

Over 16 dev runs we observed four distinct failure classes, in increasing order of subtlety:

**Class 1 - model endpoint economics.** gemma-4-26b free tier has a 16k-token per-request ceiling (verified: a 27k-token request is rejected in 251 ms) and a 16k tokens/min rate; gemini-3.8-flash free tier allows only 20 requests/day. A direct consequence: flash cannot drive an agentic loop at all (our 60-minute flash run burned the daily quota in 7 calls and wedged on 429s), and the free judge cannot grade substantial deliverables because the grader's rubric prompts exceed 16k tokens. Quotas are per GCP project, so a second AI Studio project doubled our parallelism.

**Class 2 - harness configuration mismatch.** Our first flash run completed exactly 2 model calls in 10 minutes: the gemma-tuned TPM pacer (15k/min) throttled flash's large MCP-catalog prompts to one call per 3+ minutes. Environment presets must travel with the model, not the task.

**Class 3 - infrastructure ceilings.** GitHub-hosted runners kill jobs at 6 hours. Three full agent runs were lost because the 310-minute agent budget plus ~2.5 hours of task-environment setup and filesystem capture exceeded the 355-minute job timeout. Agent budgets must be sized per task class: light tasks fit 285 minutes, app-stack tasks (database-backed MCP servers) fit only ~120.

**Class 4 - agent behavior.** The most instructive failures. A 5-hour run explored a fire-test memo task and wrote zero deliverables: the single end-of-run reminder had washed out. The fix, an escalating reminder repeated until the first file write, moved the failure mode: the next run wrote 53 files, none of them the deliverable, because any write satisfied the nudge. The final form nudges until the planner-named deliverable paths exist. A 120-minute run on the backfeed task then produced a correct-format Word letter and the required OpenProject work package - the harness works.

## What the scores say

Dev-set scores on gemma-4-26b remain low: the backfeed letter, self-graded against the task's official 17-item rubric (the free judge cannot read it - Class 1), earns 8/61 (~0.13). Every earned point is mechanical: correct file, correct addressee, correct permit facts, correct responsibilities. Every missed point is engineering judgment: the records contain NFPA 70 code violations that should have blocked the energization date, and gemma at a 4k-token compacted context did not find them. This is the clean separation the harness was built for: mechanics earn the floor, model capability earns the rest. The Stage 2 declaration (google-cloud/claude-opus-5-5, currently the strongest model on the public leaderboard at 0.483 with a comparable harness) keeps every mechanism and drops only the gemma-specific crutches (context budget 150k, no TPM pacing).

## Cross-model generalizability

The harness speaks one OpenAI-compatible protocol and reads all model-specifics from environment variables; we ran it against gemma-4-26b and gemini-3.8-flash without code changes, and the submission declares claude-opus-5-5 with a different env block only. The two models we could run exhibited the same failure classes with different economics, which is itself the finding: for agentic workloads, quota shape (per-request, per-minute, per-day) matters as much as model quality, and a harness must treat endpoint economics as a first-class input.

## Efficiency and scaling

The entire development loop ran at zero cost: GitHub Actions public-repo runners (355-minute jobs, artifacts between jobs), two AI Studio free-tier keys (per-project quotas), and the benchmark's own grader for small candidates plus rubric self-grading for large ones. 600+ agent calls/day on one free key. The main scaling costs were the three runs lost to the job ceiling and the judge's inability to read large candidates; both are documented above with their fixes.

## What we would do with more time

Run the full 29-task dev set on the declared model ahead of Stage 2; add a mid-run verifier checkpoint at 50% time so wrong-track explorations get caught earlier; and teach the nudge to check deliverable *content* (not just existence) against the rubric's binary items.

## Figures

- Figure 1: harness architecture (planner / worker / verifier, proxy, task container with MCP servers).
- Figure 2: failure taxonomy timeline across 16 runs (class per failure, fix per class).
- Figure 3: run outcomes table (task, model, cap, steps, deliverables, official/self-graded score).