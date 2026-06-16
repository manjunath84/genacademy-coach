# Teach Loop Agent Fresh Review Handoff

You are the required different-model / fresh-context reviewer for the GenAcademy Coach teach-loop
agent implementation. Review the current working tree on branch `teach-loop-agent`.

Do not modify files. Do not read or print `.env`, raw corpus files, raw `corpus/eval-questions/*`
contents, `eval/runs/*`, `traces/*`, or `review_queue.jsonl`. You may inspect source code, tests,
README/status docs, `.env_example`, `pyproject.toml`, and the approved plan.

## Review Inputs

- Constitution / guardrails: `AGENTS.md`
- Approved implementation plan: `docs/superpowers/plans/2026-06-15-teach-loop-agent.md`
- Status/evidence: `docs/teach-loop-status.md`
- Primary implementation files:
  - `src/genacademy_coach/settings.py`
  - `src/genacademy_coach/teach_types.py`
  - `src/genacademy_coach/grounding.py`
  - `src/genacademy_coach/check_items.py`
  - `src/genacademy_coach/teach_tools.py`
  - `src/genacademy_coach/teach_agent.py`
  - `src/genacademy_coach/teach_session.py`
  - `src/genacademy_coach/trace.py`
  - `src/genacademy_coach/escalation.py`
  - `src/genacademy_coach/eval_io.py`
  - `scripts/run_teach_demo.py`
  - `scripts/print_trace.py`
  - `scripts/eval_teach_loop.py`
  - `scripts/check_eval_leak.py`
  - related tests under `tests/test_*teach*`, `tests/test_grounding.py`,
    `tests/test_check_items.py`, `tests/test_trace_and_escalation.py`,
    `tests/test_guardrails.py`

## Specific Review Questions

1. Does the implementation preserve the guardrails in `AGENTS.md`?
   - grounded or refuse
   - no LLM self-rated confidence
   - citations captured from retrieval, not reconstructed
   - no direct `langgraph.*` import
   - pure core / thin view
   - Week-2 `genacademy-rag` reuse
   - held-out eval privacy and no raw private question leakage
2. Were the prior blockers resolved?
   - B1: no `confidence` field in model response; evidence score is computed from retrieval.
   - B2: `scripts/eval_teach_loop.py` runs the full teach loop, not retrieval only.
   - B3: wrong learner answers trigger `re_explain_differently` with changed strategy.
   - I1: `CoachSettings` dataclass field ordering is valid.
3. Review the implementation deltas from live verification:
   - `build_langchain_model` falls back to `Qwen/Qwen3-30B-A3B-Instruct-2507`.
   - `StaticAgentPort` exhaustion message is descriptive.
   - LangChain `ModelCallLimitMiddleware` / `ToolCallLimitMiddleware` bound runaway loops.
   - Escalation queue writes are idempotent per turn.
   - Eval trace files reset per scenario to avoid rerun contamination.
   - Incorrect-grade and correct-grade unfaithful model outputs recover with grounded retrieved-span
     fallbacks, while unsupported topics still refuse.
   - Eval reports `safe_refusals` and teachable-subset pass rate without printing raw question text.
4. Are the tests sufficient for the changed behavior? Identify missing tests or risky test gaps.
5. Is this ready to merge? If not, list blockers first.

## Verification Evidence From Builder

- `uv run ruff check .`: `All checks passed!`
- `uv run pytest -q`: `72 passed, 2 warnings`
- `uv run python scripts/check_eval_leak.py`: passed; existing PDF extraction warnings were emitted.
- Live teach demo trace `bd596fa3b069`: turn 1 `drill` with `faithfulness_ok=true`; turn 2
  `re_explain_differently`, changed strategy, `faithfulness_ok=true`.
- Live refusal trace `1ac3236819de`: `refuse_escalate`, evidence `0.0 stop`, one queue row.
- Live dev eval: overall `1/10`, teachable subset `1/1`, safe refusals `9`.

## Output Format

Return:

1. Verdict: `APPROVE`, `APPROVE WITH REQUIRED FOLLOW-UP`, or `REQUEST CHANGES`.
2. Findings first, ordered by severity, with file/line references.
3. Explicit assessment of whether merge is allowed under the project gates.
4. Any residual risks or follow-up recommendations.
