# Week 4 Eval Progress Handoff

Status: implementation, local eval, and governance progress as of 2026-06-24.

This note documents the current Week 4 evaluation state for the GenAcademy Coach teach-loop agent. It
combines two views:

- how the work maps to the Week 4 "Evaluate Your Agent" handout
- what the actual product problem, root cause, fixes, and remaining risks are

It is meant to help a future AI session or reviewer pick up the work without replaying chat history.

## How To Read This Handoff

Use this document in three passes:

1. For the course handout/submission story, read `Handout Mapping`, then `Remaining Issues`, then
   `Future Session Instructions`.
2. For the learner-facing product story, read `User Perspective`, then the improvement summaries in
   `Phase 4`.
3. For the builder/debugging story, read `Builder Perspective`, `Root Cause`, `Important Negative
   Findings`, and `Latency/Loop Implementation Snapshot`.

The most important mental model: retrieval was usually finding useful evidence; the failures mostly came
from what the agent did after retrieval. The fixes therefore target session-boundary decisions, check-span
selection, and tool-loop observability rather than changing the scorer or weakening grounding thresholds.

## Change Map

| Change | User-visible problem | Builder-side fix | Evidence / current status |
|---|---|---|---|
| Structured-output retry | Occasional infra-style refusal or malformed agent response | Retry missing/invalid structured output once, with token usage accumulated | Implemented; no infra errors appeared in the three current-main full runs |
| Correct answer must advance | Learner could answer correctly and still be drilled/re-explained | `_enforce_grounding` forces `advance` when deterministic grade is correct and grounded evidence exists | Three historical runs improved task flow while refusal recall stayed `1.0` |
| Preferred check span | Citation could point to weaker note/transcript/glossary material | Mark `preferred_for_check`; guide agent toward slide/handout spans for check generation | Historical citation F1 improved from about `0.394` to about `0.506` |
| Latency attribution | Slow turns were hard to explain from a single total duration | Add redacted agent/tool timing, attempts, cache hits, case latency, and repeated-tool metrics | Implemented in PR #45; three full runs show turn p95 improved from `11328 ms` to `8275 ms` mean |
| Loop reduction | Repeated retrieval/check/escalation calls inflated latency and sometimes exhausted turns | Add LangChain tool-call caps plus same-turn retrieval/check reuse | Implemented in PR #45; full runs show no infra errors, but some high-latency tool loops remain |
| Slide-first hardening | Preferred source behavior could drift with source-priority changes | Choose first slide, then first handout, then first citeable span | Implemented in PR #45; three full runs show citation F1 mean `0.594` vs `0.444` baseline |
| LangSmith governance | Full eval needed private traces, but old docs only allowed cloud-safe tracing | AD-12 now permits owner-approved private seed/dev LangSmith eval traces with explicit CLI gate | Implemented in PR #46; three full runs completed locally under the private eval project |

## Handout Mapping

### Evaluation one-liner

We are measuring task completion, teachable completion, refusal precision/recall/F1, citation
precision/recall/F1, tool F1, retrieval recall@5, latency, tokens, and cost on the GenAcademy Coach
teach-loop agent using a 40-case golden dataset covering happy, edge, known-failure, and adversarial
cases, with mostly deterministic code-based evaluators. We compare baseline vs targeted improvements
and report measured deltas.

### Phase 1: Metrics and golden dataset

Status: mostly complete locally.

The handout asks for 30 to 50 labeled cases covering happy paths, edge cases, known failures, and
adversarial cases. The repo has a 40-case golden dataset in `eval/golden/golden_cases.jsonl`:

| Scenario type | Count |
|---|---:|
| Happy | 16 |
| Edge | 9 |
| Known failure | 5 |
| Adversarial | 10 |

The mix intentionally differs from the handout's suggested 50/30/15/5 because the project needs a
larger refusal/adversarial control set. Cases include expected behavior fields such as expected next
action, expected tools, expected citation span, refusal expectation, and expected check keywords.

Metrics currently emitted by the local harness:

- `task_completion`
- teachable pass rate
- refusal precision / recall / F1
- citation precision / recall / F1
- tool F1
- retrieval recall@5
- turn p50 / p95 latency and full-case p50 / p95 latency
- per-tool call counts and tool latencies
- agent attempts, retrieval cache hits, average tool calls per case, and max repeated tool count
- input/output/total tokens
- cost, currently `0.0` in the recorded artifacts because pricing env vars were unset

The judge method is primarily deterministic Python. That fits the handout because these labels are
mostly machine-checkable. No LLM-as-judge is currently needed for the core score.

### Phase 2: LangSmith instrumentation and governance

Status: governance complete; three full current-main LangSmith runs completed locally.

Local observability is strong:

- per-turn redacted trace files exist under `traces/`
- token and latency fields are captured
- eval rows include diagnostic fields:
  - `predicted_citation_ids`
  - `answered_check_id`
  - `post_final_check_id`
  - `boundary_grade_citation_id`
  - `anchor_present_in_final_retrieved`
  - `decision_source`
  - `refusal_reason_code`
  - `final_trace_path`

LangSmith egress protection was added in `scripts/run_golden_eval.py`: if LangSmith tracing is enabled,
the CLI requires the private project name and explicit egress approval. This protects private learner and
course material.

Governance status:

- PR #46, `docs: clarify Week 4 LangSmith eval egress`, is merged into `main` at merge commit
  `b2d506f7ae5759062fe97c9b0db71045b78deec3`.
- AD-12 now permits owner-approved private LangSmith upload of seed/dev golden eval traces plus
  cloud-safe controls, while the frozen `test` split remains local-only.
- RAGAS and LLM-judge evaluation remain cloud-safe-only unless a separate judge-egress decision is
  approved.
- The eval CLI preflight requires `LANGSMITH_PROJECT=genacademy-coach-week4-eval` and
  `GENACADEMY_LANGSMITH_EVAL_EGRESS_OK=true` before tracing.
- Public/committed artifacts remain redacted. Raw learner text, tutor prose, retrieved span text, and raw
  traces still must not be committed, screenshotted publicly, or posted.
- A cloud-safe-only LangSmith smoke run completed on June 24, 2026 against the private eval project.
- Three full current-main runs also completed locally under the same private project gate:
  `current-main-full-langsmith-r1`, `current-main-full-langsmith-r2`, and
  `current-main-full-langsmith-r3`.

Remaining handout gap:

- include the LangSmith project/experiment link in the final submission
- confirm the LangSmith UI shows the three expected full-run traces/experiments before recording
- record the upload command, experiment URL, and any retention reason in submission notes if traces are
  kept after the submission window

### Phase 3: Run eval and analyze failures

Status: complete locally, with three current-main full LangSmith runs measured on June 24, 2026.

Baseline provided for the 40-case golden run:

| Metric | Baseline |
|---|---:|
| Task completion | 36/38 = 94.7% |
| Teachable | 26/28 = 92.9% |
| Refusal precision / recall / F1 | 0.833 / 1.000 / 0.909 |
| Citation F1 | 0.444 |
| Tool F1 | 0.893 |
| Retrieval recall@5 | 1.000 |
| Turn latency p50 / p95 | 6843 / 11328 ms |
| Total tokens | 1,330,184 |
| Cost | 0.0, pricing env unset |

Failure analysis found two dominant product-level issues:

1. Correct learner answers did not always advance the session.
2. Citation misses were mostly check-span selection problems, not retrieval misses.

The key discovery: retrieval recall@5 was already 1.0, and in many citation failures the expected span
was retrieved. The agent often generated the check from a lower-value span, then faithfully cited that
span later. This means citation quality had to be improved through product/tool behavior, not scorer
changes.

Current-main three-run LangSmith measurement after PR #45 and PR #46:

| Metric | Run 1 | Run 2 | Run 3 | Mean |
|---|---:|---:|---:|---:|
| Task completion | 37/40 | 38/40 | 37/40 | 93.3% |
| Teachable | 27/30 | 28/30 | 27/30 | 91.1% |
| Refusal precision / recall / F1 | 0.769 / 1.000 / 0.870 | 0.833 / 1.000 / 0.909 | 0.769 / 1.000 / 0.870 | 0.791 / 1.000 / 0.883 |
| Citation F1 | 0.539 | 0.667 | 0.578 | 0.594 |
| Tool F1 | 0.911 | 0.902 | 0.887 | 0.900 |
| Retrieval recall@5 | 1.000 | 1.000 | 1.000 | 1.000 |
| Turn latency p50 / p95 | 4737 / 8102 ms | 4577 / 8356 ms | 4507 / 8368 ms | 4607 / 8275 ms |
| Case latency p50 / p95 | 13630 / 21374 ms | 14198 / 21962 ms | 13695 / 22547 ms | 13841 / 21961 ms |
| Total tokens | 1,310,309 | 1,380,538 | 1,211,862 | 1,300,903 |
| Cost | pricing unset | $0.147 | $0.130 | about $0.139 with pricing active |

Compared with the original baseline, the strongest measured wins are citation quality and turn latency:

- citation F1 improved from `0.444` to a three-run mean of `0.594`
- turn latency p50 improved from `6843 ms` to `4607 ms`
- turn latency p95 improved from `11328 ms` to `8275 ms`
- retrieval recall stayed at `1.000`
- refusal recall stayed at `1.000`

The remaining tradeoff is refusal precision/task completion: the current runs have no infra exclusions,
but two teachable cases now fail consistently by refusing even though retrieval recall@5 is true.

### Phase 4: Improve and measure delta

Status: product/instrumentation improvements are implemented and measured with three full current-main
LangSmith runs.

#### Improvement 1: structured-output retry

File: `src/genacademy_coach/teach_session.py`

The LangChain agent port now retries once when structured output is missing or invalid. Token usage is
accumulated across attempts. Attempts are capped at two total calls.

Result:

- reduced some structured-output noise
- did not fully eliminate recurring `edge_008` infra failures
- `happy_014` remains intermittent

#### Improvement 2: correct answer must advance

File: `src/genacademy_coach/teach_session.py`

Problem: after a deterministic correct grade, the agent sometimes chose `drill` or
`re_explain_differently`. From the learner's perspective this felt like the tutor ignored the correct
answer.

Fix: `_enforce_grounding` now forces `advance` when:

- the boundary answer grade is correct
- retrieved grounded evidence exists
- the agent chose a non-advancing teach action or tried to stop/refuse without valid citations

Three-run measurement after this change:

| Run | Task completion | Teachable | Citation F1 | Refusal recall | Retrieval recall@5 |
|---|---:|---:|---:|---:|---:|
| `correct-advance-r1` | 37/39 | 27/29 | 0.394 | 1.000 | 1.000 |
| `correct-advance-r2` | 37/38 | 27/28 | 0.350 | 1.000 | 1.000 |
| `correct-advance-r3` | 37/38 | 27/28 | 0.439 | 1.000 | 1.000 |

Verdict: keep. It reliably improves task flow and preserves refusal safety, but it does not solve
citation quality.

#### Improvement 3: preferred check span

Files:

- `src/genacademy_coach/teach_tools.py`
- `src/genacademy_coach/teach_agent.py`

Problem: the check span was agent-chosen, and the agent often selected glossary, note, or transcript
fallback spans even when a cleaner slide/handout span existed.

Fix:

- retrieval rows now include `preferred_for_check`
- the preferred span is the first retrieved `slide`, then the first `handout`, otherwise the first citeable
  span
- the system prompt tells the agent to prefer `preferred_for_check=true` and slide/handout rows when
  generating a check

Three-run historical measurement after the first preferred-check change, before the later PR #45
latency/loop hardening:

| Run | Task completion | Teachable | Citation F1 | Refusal recall | Retrieval recall@5 |
|---|---:|---:|---:|---:|---:|
| `preferred-check-r1` | 37/39 | 27/29 | 0.500 | 1.000 | 1.000 |
| `preferred-check-r2` | 37/39 | 27/29 | 0.533 | 1.000 | 1.000 |
| `preferred-check-r3` | 38/40 | 28/30 | 0.483 | 1.000 | 1.000 |

Average citation F1 moved from about 0.394 in the prior `correct-advance` runs to about 0.506 in the
`preferred-check` runs. Task completion and adversarial refusal safety held.

Verdict: keep.

#### Improvement 4: latency attribution, loop reduction, and slide-first hardening

Files:

- `src/genacademy_coach/teach_agent.py`
- `src/genacademy_coach/teach_tools.py`
- `src/genacademy_coach/teach_session.py`
- `src/genacademy_coach/eval_runner.py`
- `src/genacademy_coach/eval_metrics.py`
- `src/genacademy_coach/teach_types.py`

PR #45 merged these changes into `main`:

- redacted attribution for agent latency, attempts, retrieval cache hits, tool-call counts, and tool
  latencies
- explicit aggregate metrics for turn latency, case latency, tool counts, total tool time, repeated-tool
  loops, agent attempts, and retrieval cache hits
- LangChain tool-call caps for repeated retrieval, check generation, and mentor escalation
- same-turn retrieval/check reuse so repeated calls are cheap and visible rather than hidden
- slide-first preferred-check selection

Cloud-safe measurement after PR #45 shows refusal safety held, but it only covers adversarial controls:
`10/10` task completion, refusal precision/recall/F1 `1.0 / 1.0 / 1.0`, turn latency p50/p95
`2202.7 / 3718.0 ms`, case latency p50/p95 `4869.3 / 7109.4 ms`, average tool calls per case `4.8`.

Full current-main measurement after PR #45 shows the implementation should still be kept: citation F1 and
turn latency improved materially, retrieval recall and refusal recall held at `1.0`, and there were no
infra errors in the three measured runs. Task completion remains roughly in the baseline band, but stable
false refusals remain for `happy_014` and `known_failure_001`; `edge_002` failed in two of three runs.

Verdict: keep the implementation. Do not add more product changes before submission unless there is time
for a targeted false-refusal investigation plus another full eval.

## User Perspective

The learner-facing issue was not that the tutor had no course material. Most of the time retrieval was
finding useful material.

The bad user experience was more subtle:

- the learner could answer correctly, but the tutor might keep teaching instead of advancing
- citations could point to odd supporting material, such as transcript/glossary/note chunks, even when a
  clearer slide or handout was available
- a few teachable cases still refused because evidence fell below the grounding threshold

After the fixes:

- correct answers are much more consistently treated as progress
- the tutor is more likely to build checks from cleaner slide/handout spans
- repeated retrieval/check/escalation loops are now capped and instrumented, reducing hidden latency waste
- refusal safety still holds on adversarial controls

## Builder Perspective

The key internal sequence is:

1. `retrieve_course_corpus` retrieves citeable spans.
2. `generate_check_item_for_span` builds the active check from one citation ID.
3. `grade_understanding` deterministically grades the learner answer against that check.
4. the agent chooses `next_action`.
5. `_enforce_grounding` validates or overrides unsafe/unfaithful behavior.

The original diagnosis was too broad: citation F1 was low, but retrieval was not the main failure. The
agent could retrieve the expected span and still pick a different check span. Since the final answer
usually cited the check span, citation mismatches followed.

This is why the fix had to target span selection before check generation, not final citation rewriting.
The later latency work targets the same runtime boundary: make repeated tool calls cheap or capped, then
measure them explicitly instead of guessing from total turn duration.

## Root Cause

There were two root causes:

### Root cause 1: model decision could override deterministic grade

The deterministic grader knew the learner answer was correct, but the agent was still allowed to choose
`re_explain_differently` or `drill` if its output was grounded. That made the product behave as if the
learner had not succeeded.

The fix is now in the grounding gate: correct grade plus grounded evidence implies `advance`.

### Root cause 2: citation label was downstream of agent-chosen check span

The final citation often reflected the active check span, and the active check span was chosen by the
agent from retrieved rows. If the agent picked a lower-value span, the final citation was faithfully
wrong relative to the golden label.

The fix adds a preferred check-span signal to retrieval output and explicit prompt guidance.

### Root cause 3: agent/tool loops hid latency inside one turn

The earlier trace only exposed total turn duration. Slow cases could be caused by inference, repeated
retrieval, nested check generation, escalation loops, or structured-output retry, but the run artifact did
not separate those buckets.

The fix adds redacted per-tool counts/timing plus agent attempts and case latency, then caps/reuses repeat
calls inside a turn.

## Important Negative Findings

These are useful because they prevented scorer hacks.

### Do not blindly anchor final citations to `answered_check_id`

Counterfactual analysis showed mixed results:

- some rows improved
- repeat regressions appeared, including cases like `known_failure_003`, `edge_009`, and others
- the reason is that the check anchor itself can be wrong

So final citation anchoring is not safe as a primary fix.

### Do not lower the STOP threshold to rescue `known_failure_001`

For `known_failure_001`, the expected span is retrieved but below the calibrated 0.40 STOP threshold.
Lowering that threshold would likely improve that row, but it would violate the grounding guardrail and
increase the risk of teaching from weak evidence. Leave this alone unless a separate threshold
calibration pass proves it safe.

### Do not mix label audit with product improvement

Some citation misses may be semantically reasonable sibling chunks. A label audit may be valid later, but
it must be separate from product changes and reported as label-only movement. Do not change the scorer to
make product numbers look better.

## Remaining Issues

Stable remaining issues after the current-main full eval:

- `known_failure_001`: stable false refusal; expected span is retrieved, but the runtime still refuses
- `happy_014`: stable false refusal across all three current-main runs
- `edge_002`: false refusal in two of three current-main runs
- citation F1 improved but remains below the original aspirational pass bar
- `edge_008`: no infra failure appeared in the three current-main runs, but keep it on the watchlist
  because it was historically unstable

Submission/package gaps against the handout:

- LangSmith project/experiment link needs to be copied into the final submission
- dataset/version note should reference the committed golden manifest and the three run IDs
- final report and Loom walkthrough still need to be assembled
- r1 cost remains `0.0` because pricing env vars were unset; r2/r3 cost is active and should be used
  for the cost estimate

## Latency/Loop Implementation Snapshot

Merged into `main` via PR #45 (`codex/week4-latency-improvements`):

- Redacted latency attribution:
  - trace rows now carry `agent_latency_ms`, `agent_attempts`, `retrieval_cache_hits`,
    `tool_latencies_ms`, and `tool_call_counts`
  - golden rows now carry `case_latency_ms`, per-turn tool timing/count summaries, and per-case totals
  - aggregate metrics now distinguish legacy turn latency from explicit `turn_latency_*` and
    `case_latency_*`
  - repeated-tool metrics are computed from within-turn counts, so normal once-per-turn calls across
    multiple turns do not look like a single-turn loop
- Loop reduction:
  - LangChain middleware now caps repeated calls for `retrieve_course_corpus`,
    `generate_check_item_for_span`, and `escalate_to_mentor`
  - repeated same-turn retrieval reuses already-citeable spans instead of calling retrieval again
  - repeated check generation for the current citation returns the existing check without another
    provider call
- Preferred check selection:
  - `_preferred_check_citation_id` now chooses first slide, else first handout, else first citeable span

Local verification is complete. This Codex tenant could not run the full non-cloud-safe eval because its
external-egress policy rejected Nebius/LangSmith data transfer even after owner approval. The owner then
ran the approved full eval locally with the explicit AD-12 gate:

```bash
LANGSMITH_TRACING=true \
LANGSMITH_PROJECT=genacademy-coach-week4-eval \
GENACADEMY_LANGSMITH_EVAL_EGRESS_OK=true \
uv run python scripts/run_golden_eval.py \
  --tag current-main-full-langsmith \
  --run-id current-main-full-langsmith-r1
```

The same command was repeated for `current-main-full-langsmith-r2` and
`current-main-full-langsmith-r3`. All three used model
`Qwen/Qwen3-30B-A3B-Instruct-2507`.

Cloud-safe remote verification was run on June 24, 2026 using:

```bash
uv run python scripts/run_golden_eval.py --cloud-safe-only \
  --tag latency-loop-slide-cloudsafe \
  --run-id latency-loop-slide-cloudsafe-r1
```

Cloud-safe result summary:

- selected rows: `10`, all `negative_control`, all `cloud_safe=true`
- task completion: `10/10 = 100%`
- refusal precision/recall/F1: `1.0 / 1.0 / 1.0`
- turn latency p50/p95: `2202.7 ms / 3718.0 ms`
- case latency p50/p95: `4869.3 ms / 7109.4 ms`
- average tool calls per case: `4.8`
- max repeated tool count: `4`
- cost remains `0.0` because pricing env vars were unset

This is a useful refusal-safety and latency smoke signal, but it is not a replacement for the full
40-case golden eval because it contains no teachable rows and therefore does not test citation quality
or check-generation behavior.

A second cloud-safe run was completed with LangSmith tracing enabled:

```bash
LANGSMITH_TRACING=true \
LANGSMITH_PROJECT=genacademy-coach-week4-eval \
GENACADEMY_LANGSMITH_EVAL_EGRESS_OK=true \
uv run python scripts/run_golden_eval.py --cloud-safe-only \
  --tag current-main-cloudsafe-langsmith \
  --run-id current-main-cloudsafe-langsmith-r1
```

Cloud-safe LangSmith result summary:

- selected rows: `10`, all `negative_control`, all `cloud_safe=true`
- task completion: `10/10 = 100%`
- refusal precision/recall/F1: `1.0 / 1.0 / 1.0`
- turn latency p50/p95: `2804.8 ms / 4290.4 ms`
- case latency p50/p95: `6724.0 ms / 8268.8 ms`
- average tool calls per case: `4.8`
- max repeated tool count: `2`
- cost remains `0.0` because pricing env vars were unset

This validates the private LangSmith eval gate on safe rows only. It still does not prove teachable-path
task completion, citation quality, or full 40-case latency.

## Verification Commands Already Run

Focused and full checks after the implementation slices:

```bash
uv run pytest tests/test_teach_session.py -q
uv run pytest tests/test_teach_tools.py tests/test_teach_agent.py -q
uv run pytest -q
uv run ruff check .
uv run python scripts/check_eval_leak.py
```

Observed latest full-suite result after PR #46 review-response docs:

- `300 passed, 4 warnings`
- Ruff clean
- leak check clean, with existing PDF extraction warnings

## Useful Eval Artifacts

Local ignored artifacts produced during this work:

- `eval/runs/golden-baseline-20260624.json`
- `eval/runs/golden-correct-advance-correct-advance-r1-20260624.json`
- `eval/runs/golden-correct-advance-correct-advance-r2-20260624.json`
- `eval/runs/golden-correct-advance-correct-advance-r3-20260624.json`
- `eval/runs/golden-preferred-check-preferred-check-r1-20260624.json`
- `eval/runs/golden-preferred-check-preferred-check-r2-20260624.json`
- `eval/runs/golden-preferred-check-preferred-check-r3-20260624.json`
- `eval/runs/golden-latency-loop-slide-cloudsafe-latency-loop-slide-cloudsafe-r1-20260624.json`
- `eval/runs/golden-current-main-full-langsmith-current-main-full-langsmith-r1-20260624.json`
- `eval/runs/golden-current-main-full-langsmith-current-main-full-langsmith-r2-20260624.json`
- `eval/runs/golden-current-main-full-langsmith-current-main-full-langsmith-r3-20260624.json`

These artifacts are useful for report tables and failure analysis, but raw traces and generated tutor
prose must not be committed or publicly shared.

## Future Session Instructions

If another AI session continues this work:

1. Keep the product fixes and PR #45 observability/loop controls unless a fresh 3-run eval shows a
   regression.
2. Do not implement post-hoc citation anchoring without a stronger counterfactual.
3. Do not lower STOP threshold for `known_failure_001` without a separate calibration study.
4. Preserve guardrails: no scorer hacks, no frozen test split edits, no raw learner text or traces in
   committed artifacts.
5. The next highest-value work is submission packaging: LangSmith project/experiment link, dataset
   version note, final report, and Loom outline.
6. Do not start provider/model bakeoff work unless the submission has enough time left for provider
   governance plus three full eval runs per finalist.
7. Treat LLM-as-judge as an optional audit layer, not the pass/fail scorer. Keep deterministic golden
   metrics as the official result unless a separate judge-egress decision is approved and documented.
