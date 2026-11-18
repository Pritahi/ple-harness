# An Agent Harness for Physical Engineering's Last Exam: Deliverable Discipline Under Brutal Resource Ceilings

## Summary

We built a model-agnostic agent harness (planner / worker / verifier) and developed it entirely on free-tier infrastructure: GitHub Actions runners as the sandbox and Google AI Studio free-tier models as drivers. Across 20 dev runs we hit ten distinct failure layers, each invisible until the previous one was fixed, and each fixed by a mechanism that is now part of the harness: quota death, missing deliverables, a scratch-write loophole, stub plans, early quitting, fix-loops, invalid formats, hollow containers, a gate catch-22, and an agent that explores for five hours and simply never writes. The last mechanism - deliverable salvage, where the harness assembles the deliverable itself from the run's own findings - closed the plumbing era: every run since has put a valid deliverable in front of the grader. Scores moved from 0.0 across eight consecutive runs to 0.1774, then 0.1935 once a stronger free driver and a structure-first planner lifted the content ceiling. Every mechanism is model-agnostic; the declared Stage 2 model keeps them all and drops only the free-tier crutches.

## Harness design

A single-file Python asyncio service speaks the OpenAI chat API to any endpoint. Three roles run in separate conversations:

1. **Planner** (read-only): inspects the task and files, reads any source document or procedure the deliverable must follow end-to-end, and emits a plan with a REQUIRED OUTLINE (section by section, with the determination each section must produce) and a final `DELIVERABLES:` line naming the exact output files.
2. **Worker** (bash + file tools): executes the plan; every tool result shows the minutes remaining.
3. **Verifier** (read-only): re-opens every deliverable, recomputes key numbers, runs runnable deliverables end-to-end, and sends a gap list back for fix rounds.

Resource guards, each added in response to an observed death: TPM pacing (token bucket per model), context compaction with oversized-tool-result truncation, compact-on-429 with backoff, short-task bypass (one worker for tasks under 45 minutes), and a time-margin discipline that guarantees a final summary instead of a mid-call cutoff.

## Failure analysis: the ten-layer taxonomy

The dev campaign's real product. Each layer below was the dominant failure only after every layer above it had a shipped fix.

1. **Quota death.** gemma-4-26b free tier: 16k tokens/minute and a 16k-token per-request ceiling (a 27k request 429s in 251 ms). gemini-3.8-flash free tier: 20 requests/day - an agent loop burns that in 7 calls. Fix: per-model env presets, a second AI Studio project for 2x parallelism, compaction budgets sized to the ceiling.
2. **No deliverable.** A 5-hour run explored a fire-test task and wrote nothing; the single end-of-run reminder washed out. Fix: an escalating nudge that repeats until the named deliverable exists on disk.
3. **Scratch-write loophole.** The next run wrote 53 files, none of them the deliverable - any write satisfied the nudge. Fix: nudge tracks the planner-named paths, not any write.
4. **Stub plan.** The planner named deliverables from the task text's first mention, not the required content. Fix: plan validation against the task's deliverable section.
5. **Early quit.** The agent declared done mid-task. Fix: finish-refusal - a finish without a valid deliverable is rejected with instructions (capped to avoid infinite loops).
6. **Fix-loop.** The agent edited the same analysis script for an hour, ignoring nudges. Fix: a force-write gate in the last 30% of time blocks every tool except bash/read/write/edit until the deliverable exists.
7. **Invalid format.** A ".docx" that was plain text with a renamed extension; the grader's renderer rejected it. Fix: deliverable validity checks - magic bytes for the declared type.
8. **Hollow container.** A structurally valid docx containing four words. Fix: word-floor validation (>=100 words in document.xml; >=2KB for other types).
9. **Gate catch-22.** The gate blocked the agent's own build scripts (`python3 create_memo.py` names no deliverable file). A gate that blocks the build path is worse than no gate. Fix: bash/read/write/edit are always allowed; the disk is re-checked for a valid deliverable after every bash call.
10. **Explore-forever.** With the gate open to bash, the agent burned the entire 285-minute budget on 19 analysis scripts, ignored 92 nudges, and finished with a final message promising a memo that never existed. Fix: **deliverable salvage** - in the last 15% of time, the harness itself assembles the deliverable: one model call turns the run's findings into clean document text (raw findings as fallback), a pure-Python renderer writes a real .docx/.pdf with no container installs, and the agent is told where the draft is so it can improve it. A raw-only retry fires at wrap-up.

After layer 10, the failure mode changed character. Runs 29-35 (gemini-3.1-flash-lite driver) produced self-authored, structurally valid deliverables in about an hour with no salvage at all - and scored on substance, not mechanics: a professional memo that concluded "screen FAILED" where the correct engineering call was advancement to a study agreement (0.0 despite perfect delivery), a valid cable-sizing zip whose 22 held-out answers were all wrong (0.0), a fire-test memo that earned format and mid-level points while missing deep domain inferences (0.0817), and a permission-to-operate memo on a heavy app-stack task that hit every mechanical item (correct file type, addressee, PE signature block) while making the wrong energization call. The outline planner lifted the same solar task class from 0.0 to 0.0909. Plumbing earns the right to be graded; judgment earns the points.

Every mechanism change was validated offline before a live dispatch: a scripted-model dry-run suite (five scenarios) simulates a fix-looping agent, an early-quitter, an invalid-format writer, and an explore-forever agent, and asserts the harness countermeasure fires. A mechanism that only ever gets validated by a 285-minute GPU run is a debugging loop measured in days; the dry-runs run in seconds.

## What the scores say

| Run | Task | Driver | Mechanism added | Score |
|-----|------|--------|-----------------|-------|
| 7-18 | various | gemma-4-26b | layers 1-8 | 0.0 x8 |
| 21 | footing-settlement | gemma-4-26b | validity floor | 0.1774 |
| 28 | engineers-estimate | gemma-4-26b | salvage (auto-written) | 0.0435 |
| 29 | solar-review | flash-lite | - | 0.0 (valid memo, wrong call) |
| 31 | footing-settlement | flash-lite | outline planner | 0.1935 |
| 33 | fire-test-memo | flash-lite | outline planner | 0.0817 |
| 34 | solar-supplemental-review | flash-lite | outline planner | 0.0909 |
| 35 | permission-to-operate-memo | flash-lite | - | 0.0682 |

run21's grade detail shows the pattern precisely: 11/62 points, every earned point mechanical (settlement derivation present, tolerance finding, CONDITIONAL disposition, basis items), every missed point a deep-discrepancy judgment call. The harness earns the floor; the model earns the rest. That is exactly the separation Stage 2 rewards: the declared model runs inside the same enforced discipline with a 150k context budget and no pacing crutches.

## Cross-model generalizability

The harness speaks one OpenAI-compatible protocol and reads every model-specific from the environment: model name, TPM, compaction budget, call gap, output ceiling. We ran it unchanged against gemma-4-26b, gemma-4-31b, and gemini-3.1-flash-lite (and attempted gemini-3.8-flash). The findings generalize in two directions. First, quota shape matters as much as model quality for agentic workloads: flash-lite's 1M-token context removed the 16k per-request ceiling that throttled every gemma run, and its free tier sustained agent-loop request rates (verified with a 25-call burst, zero 429s), cutting wall-clock per task from 5 hours to about 1. Second, the failure taxonomy is driver-independent: gemma and flash-lite failed through the same layers in the same order, differing only in economics and speed - which is why mechanisms built against one driver transferred to the other without modification. The submission declares one of the sponsored models for Stage 2; the dev drivers above are free-tier models used only to produce artifacts, as the rules allow. To be explicit: every dev score reported here was earned by a free-tier driver (gemma-4-26b, gemma-4-31b, or gemini-3.1-flash-lite), never by the declared model, which we cannot call on free infrastructure. Our CI kit-check likewise routes the declared model name to a gemma endpoint - a clearly labeled stand-in that exists only so the kit's connectivity probe can exercise the harness end-to-end; in Stage 2 the declared model is served by the competition infrastructure.

## Efficiency and scaling

Total development cost: zero. GitHub Actions public-repo runners (355-minute job ceiling - the binding constraint, sized into per-class agent budgets: 285 minutes for light tasks, ~120 for app-stack tasks with 2.5h environment overhead), two AI Studio free-tier projects for 2x parallelism, and the benchmark's own grader for scoring. The CI proxy (litellm) fronts the free keys and lets a declared sponsored alias be retargeted at any dev driver for comparison runs while submission.yaml keeps its sponsored declaration. Judge calls use a retry-hardened alias on the opposite key slot from any live agent. One lesson stands out for anyone scaling free-tier agent development: validate mechanisms offline. The five-scenario dry-run suite caught the gate catch-22 class of bug before it could burn a 5-hour run.

## What we would do with more time

Run the full 29-task dev set on the declared model; teach the verifier to check deliverable content against rubric-style binary items mid-run rather than at the end; and add a second salvage pass that re-derives findings from raw tool outputs when the agent's own summaries are thin.

## Figures

- Figure 1: harness architecture (planner / worker / verifier, CI proxy, task container with MCP servers).
- Figure 2: the ten-layer failure taxonomy, in the order each layer was exposed and fixed.
- Figure 3: dev-run scores across the campaign - plumbing fixes turn eight consecutive zeros into scored content; the outline planner and a stronger driver lift the ceiling.
