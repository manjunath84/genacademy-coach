# Teach Loop Status

Status: implemented and live-verified. Earlier teach-loop PRs were reviewed by Gemini/Claude; the
latest demo-readiness fallback still needs a fresh review before merge.

## Verification

- `uv run pytest -q` before implementation: `27 passed, 2 warnings`.
- `uv lock`: resolved 163 packages.
- `GENACADEMY_CHUNKER=section uv run python scripts/ingest_course_corpus.py`: `ingested 33 docs -> 1540 chunks into collection=coach_course`.
- `uv run pytest tests/test_teach_agent.py tests/test_teach_session.py -q`: `14 passed`.
- `uv run pytest tests/test_teach_tools.py tests/test_teach_session.py -q`: `15 passed`.
- `uv run pytest tests/test_eval_teach_loop.py -q`: `4 passed`.
- `uv run pytest tests/test_teach_session.py -q` after Claude follow-up fix: `17 passed`.
- `uv run ruff check src/genacademy_coach/teach_session.py tests/test_teach_session.py`: `All checks passed!`.
- `uv run ruff check ...` on touched files: `All checks passed!`.
- `uv run ruff check .` after Claude follow-up fix: `All checks passed!`.
- `uv run pytest -q` after Claude follow-up fix: `77 passed, 2 warnings`.
- `uv run python scripts/check_eval_leak.py` after Claude follow-up fix: passed; existing PDF extraction
  warnings were emitted.

## Live Nebius Demo

Command:

```bash
GENACADEMY_PROVIDER=nebius uv run python scripts/run_teach_demo.py \
  --topic "agent loop" \
  --style analogy \
  --track-lens code_heavy \
  --learner-answer "It is just one final answer without observing feedback."
```

Trace: `traces/bd596fa3b069.jsonl`

Trace summary:

- Turn 1: `drill`, strategy `short_drill`, evidence `0.682 confirm`, `faithfulness_ok=true`.
- Turn 2: `re_explain_differently`, strategy `contrastive_example`, evidence `0.682 confirm`, `faithfulness_ok=true`.
- Both turns cite retrieved course spans; no LLM self-confidence is present.

## Refusal Path

Command:

```bash
GENACADEMY_PROVIDER=nebius uv run python scripts/run_teach_demo.py \
  --topic "Gen Academy cafeteria menu" \
  --style concise \
  --track-lens low_code_no_code
```

Trace: `traces/1ac3236819de.jsonl`

Observed:

- Learner-visible response refused/escalated because no citeable course corpus was found.
- Trace shows `next_action=refuse_escalate`, evidence `0.0 stop`.
- `review_queue.jsonl` received one row for session `1ac3236819de`.

## Dev Eval

Command:

```bash
GENACADEMY_PROVIDER=nebius uv run python scripts/eval_teach_loop.py \
  --split dev \
  --limit 10 \
  --json-out eval/runs/teach-loop-dev.json
```

Result:

- Overall: `1/10` passed, `pass_rate=0.1`.
- Teachable subset: `1/1` passed, `teachable_pass_rate=1.0`.
- Safe refusals: `9`.
- Initial failure mode: scenarios `000` through `008` had post-filter `top_score=0.0`, were below the
  STOP threshold, and refused/escalated without leaking raw private question text.
- Follow-up retrieval triage: raw retrieval returned candidates for every dev scenario; the low-coverage
  symptom came from top cosine scores below the initial `0.60` STOP threshold, not from missing
  ingestion. The adapter preserves the globally top-scored candidate before thresholding; source-priority
  demotion remains a separate retrieval-quality signal. See `docs/teach-loop-retrieval-triage.md`.

## Calibrated Threshold Eval

Command:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/eval_teach_loop.py \
    --split dev \
    --limit 10 \
    --json-out eval/runs/teach-loop-dev-threshold-040.json
```

Result:

- Overall: `3/10` passed, `pass_rate=0.3`.
- Teachable subset: `3/8` passed, `teachable_pass_rate=0.375`.
- Safe refusals: `2`.
- Retrieval coverage: `8` scenarios with spans, `2` without spans.
- Remaining failure mode: recovered teachable scenarios now fail mostly on grading, strategy-change, and
  runtime-decision trace checks rather than retrieval coverage. See
  `docs/teach-loop-threshold-calibration.md`.

## Behavior-Hardened Dev Eval

Command:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/eval_teach_loop.py \
    --split dev \
    --limit 10 \
    --json-out eval/runs/teach-loop-dev-behavior-fixes.json
```

Result:

- Overall: `6/10` passed, `pass_rate=0.6`.
- Teachable subset: `6/8` passed, `teachable_pass_rate=0.75`.
- Safe refusals: `2`.
- Retrieval coverage: `8` scenarios with spans, `2` without spans.
- Diagnostic reason counts: `citation_ids_not_resolved=2`, `safe_low_retrieval_refusal=2`.
- The prior `grade_not_correct`, `missing_strategy_change`, and `missing_runtime_decision_trace`
  bottlenecks are cleared on this dev run.
- Remaining failure mode: two teachable scenarios reached `refuse_escalate` with no resolved final
  citation IDs. This is the next hardening target before a demo-ready MVP trace.

## Citation-Hardened Dev Eval

Command:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/eval_teach_loop.py \
    --split dev \
    --limit 10 \
    --json-out eval/runs/teach-loop-dev-citation-resolution.json
```

Result:

- Overall: `8/10` passed, `pass_rate=0.8`.
- Teachable subset: `8/8` passed, `teachable_pass_rate=1.0`.
- Safe refusals: `2`.
- Retrieval coverage: `8` scenarios with spans, `2` without spans.
- Diagnostic reason counts: `safe_low_retrieval_refusal=2`.
- There are no remaining teachable failures in this dev run; the two non-passing scenarios are safe
  low-retrieval refusals.

## Demo-Ready Runtime Trace

Grounded command:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_teach_demo.py \
    --session-id demo-grounded-harness-fallback-20260616 \
    --topic "agent harness" \
    --style analogy \
    --track-lens code_heavy \
    --learner-answer "It is just one prompt with no tool checks or feedback."
```

Trace: `traces/demo-grounded-harness-fallback-20260616.jsonl`

Redacted trace summary:

- Turn 1: `drill`, strategy `short_drill`, evidence `0.711 confirm`, `faithfulness_ok=true`,
  `retrieved_count=5`, tool calls include `retrieve_course_corpus` and `generate_check_item`.
- Turn 2: `re_explain_differently`, strategy `contrastive_example`, evidence `0.753 confirm`,
  `faithfulness_ok=true`, `retrieved_count=4`, tool calls include retrieval, grading, and profile update.
- This run demonstrates a grounded teach turn plus a learner-dependent strategy change after a wrong
  answer. The held-out `test` split was not used.
- Post-fallback dev eval remains `8/10` overall and `8/8` teachable with only
  `safe_low_retrieval_refusal=2` (`eval/runs/teach-loop-dev-demo-fallback.json`).

Refusal command:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_teach_demo.py \
    --session-id demo-refusal-20260616 \
    --topic "Gen Academy cafeteria menu" \
    --style concise \
    --track-lens low_code_no_code
```

Trace: `traces/demo-refusal-20260616.jsonl`

Redacted trace summary:

- Turn 1: `refuse_escalate`, strategy `refusal`, evidence `0.0 stop`, `faithfulness_ok=null`,
  `retrieved_count=0`, tool calls include retrieval and mentor escalation.
- `review_queue.jsonl` received exactly one row for the refusal session, preserving escalation
  idempotency even when the model attempted the escalation tool more than once.

## Review Notes

- Builder did not self-approve.
- Gemini fresh-context review: `APPROVE`; merge allowed.
- Claude fresh-context review: `APPROVE WITH REQUIRED FOLLOW-UP`; merge allowed.
- Claude required follow-up F1 fixed: removed invalid `"concise"` fallback strategy and added a
  literal-validity regression test.
- Claude non-blocking test-seam gaps F5 and F7 also covered with focused tests for
  `LangChainAgentPort.invoke` mapping and combined escalation idempotency.
