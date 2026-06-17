# Skill-Gap Diagnosis Plan

Status: implemented as a deterministic CLI/core slice after fresh-context review of the plan. The
implementation still requires normal PR review before merge.

## Purpose

Add a deterministic, cited gap report from a learner's existing session artifacts. This is the standout
workflow for the submission because it composes shipped primitives instead of adding a new agent surface:
teach traces, quiz grades, review-queue events, retrieval, grounding, and typed redacted traces.

The promise: "After a teach/quiz session, the coach shows the learner the top gaps and a cited next-step
review plan." It must never grade mastery with an LLM.

## Inputs

- `session_id` or a short list of session IDs.
- Teach trace rows already written by `TraceWriter`.
- Quiz results and `QuizTraceRow` metadata when present.
- `review_queue.jsonl` events for refusals/escalations.

Inputs may contain local private text. The public output and trace must not.

## Deterministic Logic

1. Load local artifacts for the requested session IDs.
2. Group observations by topic hash / topic ID / citation ID where available.
3. Compute per-topic mastery signals from deterministic fields:
   - Quiz correctness and total attempts.
   - Teach profile `struggled[]` markers.
   - Refusal/escalation counts.
   - Evidence score and evidence band.
4. Rank gaps with a transparent score. Example seed formula:
   - incorrect quiz answer: +3
   - teach `struggled[]` marker: +2
   - refusal/escalation: +2
   - confirm-band evidence: +1
   - correct quiz answer: -2
5. For each ranked gap, call `Foundation.retrieve`.
6. Pass retrieved spans through `require_citeable_spans`.
7. If citeable spans exist, emit a cited "review next" item using only citation metadata and a compact
   deterministic review target.
8. If no citeable span exists, refuse that gap item with an escalation reason. Do not backfill from model
   priors.

## Output

The user-facing report contains:

- A ranked list of gaps.
- For each gap: why it was flagged, evidence band/score, cited next-step review target, and escalation
  status if no citeable corpus exists.
- A short "do next" plan ordered by the ranked gaps.

The machine trace uses a typed allow-list mirroring `QuizTraceRow`:

- `session_id`
- `topic_hash`
- `gap_id`
- `source_session_ids`
- `evidence_score`
- `evidence_band`
- `citation_ids`
- `quiz_correct`
- `quiz_total`
- `struggle_count`
- `refusal_count`
- `next_action`
- `escalated`
- `reason_code`

No raw topic text, learner answer, quiz prompt, option text, rationale, keywords, corpus span text, or raw
trace JSON may be serialized.

## New Files Only

- `src/genacademy_coach/skillgap_types.py`
- `src/genacademy_coach/skillgap_session.py`
- `scripts/run_skillgap_demo.py`
- `tests/test_skillgap_*.py`

No new dependencies. No web UI in this slice. No memory provider. No direct `langgraph.*` imports. No web
framework imports in core.

## Reuse

- `genacademy_coach.grounding.evidence_score`
- `genacademy_coach.grounding.evidence_band`
- `genacademy_coach.grounding.require_citeable_spans`
- `genacademy_coach.escalation.append_review_queue`
- Quiz trace typed allow-list pattern from `QuizTraceRow` and `QuizTraceWriter`
- Existing `Foundation.retrieve`

## Tests

- Ranking is deterministic for mixed quiz/struggle/refusal signals.
- Correct quiz answers reduce gap priority but do not erase later refusals.
- Gaps with no citeable spans refuse/escalate.
- Output trace rejects extra fields and contains only the allow-list.
- No raw learner text, raw topic, quiz prompt/options, expected answers, rationales, keywords, or corpus
  span text appears in serialized output.
- The CLI can run a fixture-backed demo in under 60 seconds without provider calls.
- Static guard remains clean: no direct `langgraph.*`; no web imports in core.

## Demo

The demo command should run locally:

```bash
uv run python scripts/run_skillgap_demo.py \
  --source-session-id demo-grounded-main-final-20260616
```

Expected demo beat:

1. Show that the learner struggled or missed a quiz item.
2. Show a ranked gap.
3. Show a cited next-step review target or a refusal/escalation if the gap cannot be cited.
4. Show the redacted trace row.

## Acceptance Criteria

- Builds only after plan review.
- No held-out `test` split use.
- No private corpus/eval/generated text committed.
- `uv run pytest -q`, `uv run ruff check .`, and `uv run python scripts/check_eval_leak.py` pass.
- A reviewer can explain the workflow in one sentence: deterministic gap ranking plus cited retrieval for
  the next step.
