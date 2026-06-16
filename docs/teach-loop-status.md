# Teach Loop Status

Status: implemented, live-verified, and reviewed by Gemini + Claude.

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

## Review Notes

- Builder did not self-approve.
- Gemini fresh-context review: `APPROVE`; merge allowed.
- Claude fresh-context review: `APPROVE WITH REQUIRED FOLLOW-UP`; merge allowed.
- Claude required follow-up F1 fixed: removed invalid `"concise"` fallback strategy and added a
  literal-validity regression test.
- Claude non-blocking test-seam gaps F5 and F7 also covered with focused tests for
  `LangChainAgentPort.invoke` mapping and combined escalation idempotency.
