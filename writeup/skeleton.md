# PLE Agent Harness — writeup skeleton (rubric-mapped, <2000 words, 3 figures)

## Rubric: Insight & Failure Analysis 25 | Engineering Reasoning 25 | Cross-Model Generalizability 15 | Efficiency & Scaling 20 | Clarity & Visuals 15

## 1. Summary (~100 words)
- Harness: planner / worker / verifier split; escalating deliverable nudge; TPM-paced calls; context compaction at 4k tokens.
- Dev results across 4 task classes (IFC script, cable sizing, fire memo, PTO memo) on gemma-4-26b + one flash cross-model run.

## 2. Harness design (Engineering Reasoning) (~400 words)
- Architecture diagram (FIGURE 1): planner -> worker loop (bash/read/write/edit tools) -> verifier with rubric checklist -> fix round.
- Token budget engineering: COMPACT_AT_TOKENS 4000, TOOL_RESULT_CHARS 3000, reasoning cap 4000 chars, compact-on-429, force_shrink, num_retries 0 (quota death fix).
- Deliverable discipline: escalating nudge until first file write (fixes \"explores forever, never writes\" = run8's 0/208).
- Verifier actually executes deliverables (fixes untested final rewrites).
- Time budgeting: AGENT_TIMEOUT_SEC, first-session rough-draft rule in system prompt.

## 3. Failure analysis (Insight) (~500 words)
- run7 data-hall-mep-routing 0.0: 5.1h perfect harness ops, model couldn't complete IFC script (capability-bound).
- run8 fire-test-validation-memo 0.0 (0/208 rubric pts): agent explored 5h, wrote NO .docx. Root cause: one-shot nudge washed out; fixed by escalating nudge (9d09f26).
- run9 lv-cable-sizing 0.0: graded clean, calculation task beyond 4k-context gemma.
- run10 PTO memo (old harness) vs run8: natural A/B for memo class.
- flashx1: 20 req/day free quota exhausted within minutes; agent wedged on 429s; time-cap patch didn't apply (sed miss) — failure of dev-loop, not harness; captured for analysis.
- Key insight: at 4k compacted context, failure modes are (a) capability ceiling, (b) time budgeting, (c) deliverable discipline — in that order of frequency.

## 4. Cross-model generalizability (Cross-Model, NEED >=2 models) (~250 words)
- gemma-4-26b (open, 16k TPM free) vs gemini-3.8-flash (20 req/day free).
- Leaderboard anchors: Opus 5.5 + Pi harness 0.483, Gemini 4 Argon 0.406, Flash 0.275, gpt-oss-120b 0.038.
- Harness is model-agnostic: OpenAI-compatible endpoint, per-model env presets (submission.yaml env block).
- Declared model for Stage 2: google-cloud/claude-opus-5-5 (env: COMPACT_AT_TOKENS 150000, no gemma crutches).

## 5. Efficiency & scaling (~350 words)
- Free-only dev loop: GitHub Actions public-repo runners as agent sandbox (6h cap, docker), two AI Studio keys for parallel quota (key_slot).
- MODEL_TPM pacer: 600+ calls without daily cap on gemma.
- Judge separation: JUDGE_MODEL via proxy alias, regrade workflow; never grade concurrent with agent (TPM contention).
- FIGURE 2: calls/tokens per run; compaction events timeline.
- FIGURE 3: score vs model vs task class table/heatmap (leaderboard anchors + own runs).

## 6. What we'd do with more time (~150 words)

## OPEN DATA NEEDED:
- [ ] run10 score (old harness memo) vs run8 — did task matter more than harness?
- [ ] run11 score (new harness, backfeed-energization-reply)
- [ ] flashx1 post-mortem: exact wedge point, 429 pattern, sed-miss cause
- [ ] final submission.yaml flip to claude-opus-5-5 + env retune
- [ ] 3 figures: architecture diagram, per-run telemetry table, score heatmap

## DATA FILLED Nov 14 night:

### flashx1 (flash, 10-min cap, gemma env): AgentTimeoutError at exactly 600.0s (cap works). Only 2 model calls: MODEL_TPM=15000 pacer throttled flash (flash prompts ~50k tokens with MCP catalog -> 3.3 min/call pacing). Judge: 429 (shared key). LESSON: env presets must be per-model.

### flashx2 (flash key2, 60-min cap, tuned env TPM 200k/gap 6s/compact 60k): 21 proxy connections, 7 real model calls in 60 min. egress.log pattern: 50KB-up requests -> 1415-byte responses (error bodies) with 550s retry waits. Flash free tier = 20 req/day hard cap; agent burned quota in ~7 calls incl retries, then 429-wedged until timeout. No deliverable. Judge (gemma, opposite key) still 429d -> root-caused gemma TPM: 3 concurrent 7.5k-token calls = third 429s (verified empirically on idle key). Fixed: judge alias num_retries 10.

### run10 (gemma key1, OLD harness, 310-min cap): GitHub job timeout-minutes 355 hit at 5h55m; agent cancelled before finalize; NO artifact. Setup+capture overhead for heavy MCP tasks (mysql/wiki/openproject/nextcloud stack) ~40+ min. LESSON: agent cap + overhead must fit in 355 min; cap now 285.

### run11 (gemma key2, NEW harness, 310-min cap): same job-timeout loss, no artifact. Doubly painful - first nudge-fix test lost. run12 redispatched at 285.

### Infra economics for writeup Efficiency section:
- gemma-4-26b free: 16k input TPM, no daily cap observed (1000+ calls/day), concurrent big calls 429 (TPM, recoverable w/ retries)
- gemini-3.8-flash free: 20 req/day hard cap -> agentic loops impossible (7 calls = day over)
- Quotas are per-GCP-project; 2 projects = 2x parallelism (key_slot)
- GitHub Actions: 355-min job ceiling; agent cap must leave ~60 min for heavy-task setup+capture

### run13 backfeed-energization-reply (gemma, nudge-fix harness 9d09f26, 120-min cap): SELF-GRADED 8/61 (~0.13)
- Deliverables: real .docx reply letter + OpenProject work package + coherent final message.
- Rubric hits (8 pts): correct filename (1), letter to Imogen Strathe (1), permit EP-25-0418 no-energize-before-approval (2), 07/24 inspection prerequisite (2), Tamsworth responsibility (2).
- Rubric misses (53 pts): ALL engineering-core items - the records contain NFPA 70-2023 code breaches (Type TC cable w/o raceway, Type USE above ground, enamel strut corrosion) that should BLOCK the 07/29 date; the letter wrongly confirmed the date. Pure model-capability gap.
- KEY WRITEUP POINT: harness got a weak model to a formatted, addressed, fact-grounded deliverable; the missing points are what a stronger declared model earns in Stage 2.

### Judge ceiling finding (Efficiency section):
- gemma-4-26b free tier rejects any single request >~16k tokens INSTANTLY (verified: 27k-token request 429s in 251ms). TPM is a per-request ceiling, not just per-minute.
- Consequence: free-tier gemma can only judge small deliverables; substantial rubric candidates perma-429. Dev loop uses self-grading for those; official grading unaffected (server-side).
- Grader retry backoff 15s/30s/60s/120s cannot fix per-request ceiling.

## run15/run16 (Nov 15) - stub-plan failure signature (both 0.0)
- Both light tasks, full 282-min runs, ended "done" with NO deliverable on disk.
- Root cause: planner emitted a stub plan ("follow this plan:" then truncated); DELIVERABLES line missing -> nudge fell back to any-write -> 21 scratch writes silenced it -> no reminders in 232 steps.
- Fix a1d2ec1: refuse finish while named deliverable unwritten (2 forced retries); fallback parse "Save it as X" from task text; bash-built deliverables count.
- Lesson for writeup: planner output validation matters as much as planner prompting; a single malformed line silently disabled the entire deliverable-enforcement subsystem.


## run17/run18 (Nov 15-16, harness a1d2ec1) - both 0.0, advisory-nudge insufficiency
- run17 trajectory: 163 exec + 71 MCP + 18 write_file calls over the full 285 min; every write was a scratch extraction script (read_settlement_calc.py rewritten 7x in the final hour). The agent hallucinated having written the memo (steps 200-211 searched the disk for it), then the clock ran out. Never an early quit, so the finish-refusal never engaged.
- Trajectories record raw tool results pre-mutation: harness-injected text (reminders, minutes-left) is invisible there. Instrumentation must be logged serve-side.
- a1d2ec1's bash deliverable heuristic false-positived on `find` commands mentioning the filename - replaced with on-disk verification.
- Fix ad1627c: force-write gate (last 30% of budget blocks any call that cannot produce the deliverable) + serve-side instrumentation logs. Offline dry-runs (tests/) validate gate/refusal/cap in seconds without quota.
- Lesson: advisory nudges lose to a model stuck in a fix-loop; late-run behavior needs hard gates, not text. Also: a small model's failure mode is not stopping, it is looping - budget enforcement has to assume the loop never exits on its own.

## run19/run20 (Nov 16, harness ad1627c) - gate works: 0.0 and 0.0435 (FIRST OFFICIAL NON-ZERO)
- Instrumentation confirmed the full chain fires: nudge 1 at 187 min left, escalating every ~6 tool results, force-write gate on in both runs.
- run19 (footing): memo file ON DISK at grading but plain text under a .docx name - judge could not open it, 0/62. Format failure, not absence.
- run20 (engineers-estimate): valid parseable memo, scored 2/46 = 0.0435 (addresses Callaway + correct date). Judge verdict: "placeholder" - existence achieved, content hollow.
- Fix 849777d: deliverable validity gate (>=2KB + magic bytes PK/%PDF; invalid writes rejected with rebuild note; finish-refusal now requires a VALID deliverable). dryrun_format.py added.
- Failure taxonomy now 8 deep: quota death -> no deliverable -> scratch-write loophole -> stub plan -> early quit -> ignored nudges/fix-loop -> invalid format -> placeholder content. Each layer exposed only after the previous one was fixed.
- Remaining gap is content quality = model capability. Dev-model scores are diagnostics; Stage 2 runs the declared strong model.

## run21/run22 (Nov 16, harness 849777d) - 0.1774 OFFICIAL + word-floor lesson
- run21 (footing) = 0.1774 (11/62): real engineering content scored (consolidation-settlement derivation +4, tolerance-exceeds finding +2, CONDITIONAL disposition +2, basis/tolerance/author items). Misses are deep-discrepancy judgment (founding-elevation conflict, Round 15 routing, date/LL/PI discrepancies) plus cheap heading-wording items a stronger model gets.
- run22 (solar) = 0.0/77: a REAL 36KB docx containing 4 words ("Bramwick Commons Solar Memo"). Container bytes proved nothing.
- Fix b6d6baa: word-floor for .docx (>=100 words in document.xml; size floor skips docx). dryrun_format now covers plain-text (run19), 4-word zip (run22), valid memo.
- Taxonomy layer 9: hollow-but-valid container. Content quality is now the binding constraint in both directions: gemma either can't extract the data (fix-loop) or pads to pass the gate.
- Score trajectory: 0,0,0,0,0,0,0,0 -> 0.0435 -> 0.1774 (official, gemma-dev). Threshold for Stage 2 prize eligibility is mean >= 0.138 across hidden tasks with the DECLARED model.

## run23/run24 (Nov 16, harness b6d6baa) - 0.0 / 0.0435: the gate's catch-22
- Both runs: gate on, nudge chains firing, but "deliverable valid" never logged. run24's memo existed with [TBD] placeholders (2/46 again); run23's never materialized (0/77).
- Root cause: in the gate zone bash was allowed only when the command NAMED the deliverable - 'python3 create_memo.py' was blocked, so the agent could not run the very script that builds the file. And the bash disk-check only ran for naming commands, so silently-built files went undetected.
- Fix 0fbfd64: gate blocks only tools that cannot produce a deliverable; disk re-check after every bash call; nudge cadence every 2nd result in gate zone. dryrun_gate rewritten to cover the unnamed-builder case.
- Lesson: enforcement mechanisms must be audited against the agent's actual build idioms; a gate that blocks the build path is worse than no gate.
