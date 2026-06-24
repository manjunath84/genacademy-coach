# Week 4 Eval Progress Handoff

Status: implementation and local eval progress as of 2026-06-24.

This note documents the current Week 4 evaluation state for the GenAcademy Coach teach-loop agent. It
combines two views:

- how the work maps to the Week 4 "Evaluate Your Agent" handout
- what the actual product problem, root cause, fixes, and remaining risks are

It is meant to help a future AI session or reviewer pick up the work without replaying chat history.

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
- p50 / p95 latency
- input/output/total tokens
- cost, currently `0.0` because pricing env vars are unset

The judge method is primarily deterministic Python. That fits the handout because these labels are
mostly machine-checkable. No LLM-as-judge is currently needed for the core score.

### Phase 2: LangSmith instrumentation

Status: partially complete.

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

Remaining handout gap:

- upload/version the dataset in LangSmith, or clearly document why the local harness is the source of
  truth
- include the LangSmith project/experiment link in the final submission if owner-approved
- confirm end-to-end LangSmith traces show LLM calls, tool calls, latency, and tokens

### Phase 3: Run eval and analyze failures

Status: complete locally.

Baseline provided for the 40-case golden run:

| Metric | Baseline |
|---|---:|
| Task completion | 36/38 = 94.7% |
| Teachable | 26/28 = 92.9% |
| Refusal precision / recall / F1 | 0.833 / 1.000 / 0.909 |
| Citation F1 | 0.444 |
| Tool F1 | 0.893 |
| Retrieval recall@5 | 1.000 |
| Latency p50 / p95 | 6843 / 11328 ms |
| Total tokens | 1,330,184 |
| Cost | 0.0, pricing env unset |

Failure analysis found two dominant product-level issues:

1. Correct learner answers did not always advance the session.
2. Citation misses were mostly check-span selection problems, not retrieval misses.

The key discovery: retrieval recall@5 was already 1.0, and in many citation failures the expected span
was retrieved. The agent often generated the check from a lower-value span, then faithfully cited that
span later. This means citation quality had to be improved through product/tool behavior, not scorer
changes.

### Phase 4: Improve and measure delta

Status: two useful improvements implemented and measured; one infra improvement implemented with
residual failures.

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
- the preferred span is the first retrieved `slide` or `handout` span, otherwise the first citeable span
- the system prompt tells the agent to prefer `preferred_for_check=true` and slide/handout rows when
  generating a check

Three-run measurement after this change:

| Run | Task completion | Teachable | Citation F1 | Refusal recall | Retrieval recall@5 |
|---|---:|---:|---:|---:|---:|
| `preferred-check-r1` | 37/39 | 27/29 | 0.500 | 1.000 | 1.000 |
| `preferred-check-r2` | 37/39 | 27/29 | 0.533 | 1.000 | 1.000 |
| `preferred-check-r3` | 38/40 | 28/30 | 0.483 | 1.000 | 1.000 |

Average citation F1 moved from about 0.394 in the prior `correct-advance` runs to about 0.506 in the
`preferred-check` runs. Task completion and adversarial refusal safety held.

Verdict: keep.

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

Stable remaining issues:

- `known_failure_001`: false refusal caused by below-threshold retrieval
- `edge_008`: recurring structured-output infra failure
- `happy_014`: intermittent refusal/infra behavior
- citation F1 improved but remains below the original aspirational pass bar

Submission/package gaps against the handout:

- LangSmith project link still needs to be produced or explicitly scoped out
- dataset upload/versioning in LangSmith is not yet proven
- final report and Loom walkthrough still need to be assembled
- cost remains `0.0` until model pricing env vars are set

## Latency/Loop Implementation Snapshot

Implemented on branch `codex/week4-latency-improvements`:

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

Local verification is complete. A new full 40-case remote golden eval has not been run after these
changes because the approval system blocked remote provider egress for non-cloud-safe golden rows.
Run the full eval only from an approved environment/path for that specific eval egress.

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

## Verification Commands Already Run

Focused and full checks after the implementation slices:

```bash
uv run pytest tests/test_teach_session.py -q
uv run pytest tests/test_teach_tools.py tests/test_teach_agent.py -q
uv run pytest -q
uv run ruff check .
uv run python scripts/check_eval_leak.py
```

Observed latest full-suite result:

- `299 passed, 4 warnings`
- Ruff clean
- leak check clean, with existing PDF extraction warnings

## Useful Eval Artifacts

Local ignored artifacts produced during this work:

- `eval/runs/golden-correct-advance-correct-advance-r1-20260624.json`
- `eval/runs/golden-correct-advance-correct-advance-r2-20260624.json`
- `eval/runs/golden-correct-advance-correct-advance-r3-20260624.json`
- `eval/runs/golden-preferred-check-preferred-check-r1-20260624.json`
- `eval/runs/golden-preferred-check-preferred-check-r2-20260624.json`
- `eval/runs/golden-preferred-check-preferred-check-r3-20260624.json`
- `eval/runs/golden-latency-loop-slide-cloudsafe-latency-loop-slide-cloudsafe-r1-20260624.json`

These artifacts are useful for report tables and failure analysis, but raw traces and generated tutor
prose must not be committed or publicly shared.

## Future Session Instructions

If another AI session continues this work:

1. Keep the two product fixes unless a fresh 3-run eval shows a regression.
2. Do not implement post-hoc citation anchoring without a stronger counterfactual.
3. Do not lower STOP threshold for `known_failure_001` without a separate calibration study.
4. Preserve guardrails: no scorer hacks, no frozen test split edits, no raw learner text or traces in
   committed artifacts.
5. The next highest-value work is submission packaging: final report, LangSmith project/experiment link,
   dataset version note, and Loom outline.
