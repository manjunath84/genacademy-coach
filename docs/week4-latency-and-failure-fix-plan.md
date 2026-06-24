# Week 4 Latency and Remaining Failure Fix Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`
> (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce golden-eval latency and remaining infra/product failures without weakening grounded
teaching, refusal safety, or citation guardrails.

**Architecture:** Keep the current pure-core LangChain `create_agent` teach loop. First add redacted
latency attribution, then reduce repeated tool loops, then finish the small slide-first citation
preference hardening. Only after those product-side waste reducers are measured should we run a
governed model/provider bakeoff. Retrieval threshold changes are out of scope unless a separate
calibration study proves they are safe.

**Tech Stack:** Python, LangChain `create_agent`, OpenAI-compatible chat providers, local Chroma
retrieval through the Week-2 foundation adapter, existing 40-case golden eval.

**Current status:** Tasks 1, 3, and 4 are implemented and merged via PR #45. PR #46 merged the AD-12
governance path for owner-approved private LangSmith seed/dev eval traces. The current missing evidence
is a governed full 40-case eval on `main`; the cloud-safe smoke run only verifies the adversarial refusal
path.

---

## Current Diagnosis

Latency is worth improving, but retrieval is not the main bottleneck.

Evidence gathered on June 24, 2026:

- Existing eval traces store full turn latency in `TraceTurn.latency_ms`; aggregation reports p50/p95
  over individual turns, not full 3-turn case time.
- A local retrieval-only probe across the 40 golden queries showed retrieval after warmup around:
  - p50: 226 ms
  - p95: 258 ms
  - max: 385 ms
- Preferred-check golden runs show multi-second agent turns and much larger full-case times:
  - turn p50 usually about 7.5s to 9.5s
  - turn p95 usually about 15s to 21s
  - full 3-turn case p95 commonly about 39s to 53s
- Across preferred-check runs, case latency correlated strongly with output tokens and total tokens,
  and moderately with tool count.

Most likely bottlenecks:

- LLM inference in each LangChain agent turn.
- Repeated agent tool loops inside a single turn.
- Nested check generation: `generate_check_item_for_span` calls `provider.generate(...)`, which is
  another LLM call.
- Structured-output failures that trigger retries and then a safety refusal.

Current comparison baseline:

- Use a fresh full eval from the current `main` state before claiming final deltas. The old
  preferred-check runs are historical context because PR #45 added latency attribution, loop controls, and
  stricter slide-first selection afterward.
- Do not compare future deltas to the older `0.444` citation-F1 artifact except as historical context.
- Label latency metrics precisely:
  - turn p50/p95: one agent turn
  - case p50/p95: full golden case across its turns

Important code anchors:

- `src/genacademy_coach/teach_session.py`
  - `LangChainAgentPort.invoke` retries structured output once.
  - `CoachSession._invoke_agent` measures one total agent-turn timer.
  - `_enforce_grounding` contains the safety fallback paths.
- `src/genacademy_coach/teach_tools.py`
  - `retrieve_course_corpus` filters by STOP threshold.
  - `generate_check_item_for_span` calls the check generator.
  - `_preferred_check_citation_id` chooses first slide, then first handout, then fallback.
- `src/genacademy_coach/check_items.py`
  - `generate_check_item` calls the model through the Week-2 provider.
- `src/genacademy_coach/eval_metrics.py`
  - latency aggregates now distinguish turn p50/p95 from full-case p50/p95.

## Guardrails

Do not violate these while improving latency:

- Do not import web frameworks in `src/genacademy_coach/**`.
- Do not import `langgraph.*` directly.
- Do not touch or tune on the frozen `test` split.
- Do not commit raw learner text, raw tutor prose, raw retrieved span text, or raw traces.
- Do not lower the STOP threshold globally to rescue one case.
- Do not add scorer hacks, citation rewrites, or golden-label shortcuts.
- Keep all changes measurable through the existing 40-case golden eval.
- For LangSmith tracing, follow AD-12: seed/dev traces require the private eval project and explicit
  egress opt-in; the frozen `test` split stays local; RAGAS/LLM-judge remain cloud-safe-only unless a
  separate judge-egress decision is approved.

## Priority Plan

Task numbers are stable topic labels. The authoritative execution order is the checklist in
`Recommended Execution Sequence`.

### Task 1: Add Redacted Latency Attribution

**Purpose:** Prove exactly how much time is spent in retrieval, check generation, grading, escalation,
and the outer agent turn before optimizing behavior.

**Files:**

- Modify: `src/genacademy_coach/teach_types.py`
- Modify: `src/genacademy_coach/teach_tools.py`
- Modify: `src/genacademy_coach/teach_session.py`
- Modify: `src/genacademy_coach/eval_runner.py`
- Modify: `src/genacademy_coach/eval_metrics.py`
- Test: `tests/test_teach_tools.py`
- Test: `tests/test_teach_session.py`
- Test: `tests/test_eval_runner.py`
- Test: `tests/test_eval_metrics.py`

Implementation requirements:

- Add trace-safe numeric timing fields only. Suggested fields:
  - `tool_latencies_ms: dict[str, float]`
  - `tool_call_counts: dict[str, int]`
  - `agent_latency_ms: float`
  - `agent_attempts: int`
  - `retrieval_cache_hits: int`
  - `case_latency_ms: float` in eval output/aggregate scope
- Do not record tool arguments, learner text, retrieved span text, tutor text, or provider payloads.
- Time these tool buckets:
  - `retrieve_course_corpus`
  - `generate_check_item`
  - `grade_understanding`
  - `update_profile`
  - `escalate_to_mentor`
- Aggregate output should include:
  - p50/p95 turn latency
  - p50/p95 case latency
  - average tool calls per case
  - total tool time by bucket
  - max repeated tool count by case, computed from within-turn counts rather than summed per-case totals
- Add a submission/reporting note that separates turn latency from full-case latency. The existing
  p50/p95 metric is turn-level, and any submission claim must say that explicitly.
- Add tests that assert the new eval/trace fields are numeric summaries only, especially for
  non-cloud-safe rows.

Acceptance checks:

```bash
uv run pytest tests/test_teach_tools.py tests/test_teach_session.py tests/test_eval_runner.py tests/test_eval_metrics.py -q
uv run ruff check .
```

Expected: all tests pass and no raw text appears in the new trace/eval fields.

### Task 2: Run Governed Model and Provider Bakeoff

**Purpose:** Determine whether model/provider choice can cut latency and infra errors without reducing
task completion, refusal recall, or citation quality.

Do this only after Task 1 attribution, Task 3 loop reduction, and Task 4 slide-first hardening are
measured. Otherwise the bakeoff may pick a model to compensate for avoidable tool-loop waste.

Hard preconditions before any new provider receives eval traffic:

- Explicit owner approval for each new inference provider, recorded as a new architecture decision in
  `docs/decisions.md`.
- Per-provider review of data retention and training-on-prompts terms.
- Prefer no-train / zero-retention / enterprise-style terms. Do not assume a free or default API tier
  is acceptable.
- If a provider's terms are not acceptable, only run the 10 cloud-safe adversarial controls for a
  limited latency/structured-output screen, and label that result as incomplete because it under-tests
  teachable citation and check-generation behavior.
- Verify whether `settings.gen_*` controls both LLM paths:
  - the LangChain agent model in `src/genacademy_coach/teach_agent.py`
  - the nested check generator path through `runtime.foundation.provider` in
    `src/genacademy_coach/teach_tools.py` and `src/genacademy_coach/check_items.py`
- Either repoint both LLM paths for a true provider bakeoff, or explicitly hold check generation on one
  provider and report that as a mixed-provider result in the latency split and egress review.

Unverified candidate placeholders to research before use:

- Current measured Nebius baseline: `Qwen/Qwen3-30B-A3B-Instruct-2507`
- Current repo default fast Nebius candidate: `Qwen/Qwen3-30B-A3B-Instruct-2507-fast`
- Gemini API placeholder: `gemini-3.5-flash`
- Gemini API placeholder: `gemini-3.1-flash-lite`
- Open/open-provider placeholder: `zai-org/GLM-4.7-Flash` or OpenRouter `z-ai/glm-4.5-air`

Current source notes:

- These notes are not execution authority. Re-check all model IDs, endpoints, pricing, context windows,
  structured-output support, and privacy terms against current official provider docs immediately
  before running.
- Prior research suggested Gemini OpenAI-compatible chat access using base URL
  `https://generativelanguage.googleapis.com/v1beta/openai/`.
- Prior research suggested Gemini pricing entries for the Gemini placeholders above.
- Prior research suggested Hugging Face lists `zai-org/GLM-4.7-Flash` as a text-generation model with
  OpenAI-compatible local serving examples through vLLM and SGLang.
- Prior research suggested OpenRouter lists `z-ai/glm-4.5-air` as an API model.

Run protocol:

- Keep temperature at `0`.
- Keep the same golden 40-case set.
- Start with 1 screening run per approved candidate.
- Promote at most 2 finalists.
- Run 3 full evals per finalist.
- Use separate tags and run IDs per candidate.
- Record cost env vars correctly so `cost_usd` is not falsely zero.
- Use private LangSmith tracing only with `LANGSMITH_PROJECT=genacademy-coach-week4-eval` and
  `GENACADEMY_LANGSMITH_EVAL_EGRESS_OK=true`.
- Compare candidates against a fresh current-main full eval, not the older preferred-check or historical
  baseline artifacts.

Pass/fail gates:

- Hard pass gates:
  - refusal recall stays `1.0`
  - task completion does not regress beyond one tiny-N case without case-level explanation
  - infra errors do not increase
  - no frozen `test` split
  - no raw text committed
- Preferred improvements:
  - turn latency p50 improves by at least 20 percent
  - turn latency p95 improves by at least 20 percent
  - full-case p95 improves by at least 20 percent
  - tool overcalls decrease or stay flat
  - citation F1 stays at or above preferred-check level

### Task 3: Reduce Repeated Tool Loops

**Purpose:** Fix the biggest visible product/latency waste: repeated retrieval, repeated check
generation, and repeated escalation inside one turn.

Files:

- Modify: `src/genacademy_coach/teach_agent.py`
- Modify: `src/genacademy_coach/teach_tools.py`
- Test: `tests/test_teach_agent.py`
- Test: `tests/test_teach_tools.py`
- Possibly test: `tests/test_teach_session.py`

Behavior requirements:

- If `escalate_to_mentor` is called in a turn, the agent should return a structured refusal and stop
  calling tools for that turn.
- The tool implementation should make repeated escalation idempotent and cheap.
- Add per-tool call caps using the existing LangChain middleware boundary where appropriate. This should
  cap repeated calls to specific tools without reducing the global model-call limit.
- The system prompt should say:
  - call `retrieve_course_corpus` at most once per turn unless the first result has no citeable spans
  - call `generate_check_item_for_span` at most once per turn unless the tool returns an explicit error
  - call `escalate_to_mentor` at most once per turn, then return `refuse_escalate`
- Do not reduce the global tool-call limit until the above behavior is measured. A hard lower limit
  can create false infra failures.
- Add a regression test for the path where repeated tool loops exhaust the agent middleware and produce
  a missing structured response.

Acceptance checks:

```bash
uv run pytest tests/test_teach_agent.py tests/test_teach_tools.py tests/test_teach_session.py -q
uv run ruff check .
```

Golden-eval success:

- If Task 1 shows `edge_008` is caused by loop exhaustion, it should stop recurring as structured-output
  infra. If Task 1 shows plain malformed structured output instead, treat `edge_008` as a structured
  output/provider issue rather than a loop-reduction success criterion.
- Tool call count should fall on refusal/low-evidence cases.
- Refusal recall must remain `1.0`.

### Task 4: Make Preferred Check Selection Explicitly Slide-First

**Purpose:** Preserve the citation improvement from preferred-check selection and make it robust to
future source-priority env changes. Treat this as no-regression hardening, not as a guaranteed citation
lift beyond the historical preferred-check baseline.

Files:

- Modify: `src/genacademy_coach/teach_tools.py`
- Test: `tests/test_teach_tools.py`

Behavior requirement:

- `_preferred_check_citation_id(spans)` should choose:
  1. first retrieved `slide`
  2. first retrieved `handout`
  3. first citeable span
  4. `None` if no spans

Acceptance checks:

```bash
uv run pytest tests/test_teach_tools.py -q
```

Golden-eval success:

- Citation F1 should stay at or above preferred-check runs.
- No task or refusal regression.
- Run an isolated golden eval after this task because strict slide-first selection can change behavior
  when a handout currently outranks a slide.

### Task 5: Treat Low-Confidence Teachable Failures as Retrieval Calibration Work

**Purpose:** Avoid unsafe threshold hacks while documenting the right next experiment for
`known_failure_001` and `happy_014`.

Current findings:

- `known_failure_001`
  - expected span is retrieved
  - expected score is about `0.309`
  - all raw top-20 scores remain below the `0.40` STOP threshold for the resolved query
  - current safe behavior is refusal
  - diagnosis: genuine retrieval-confidence / threshold-calibration case
- `happy_014`
  - expected span is present
  - expected score is `0.0`
  - alternate query variants can retrieve citeable evidence over STOP, but not necessarily the golden
    expected span
  - current instability is a query-drift or possible label-audit problem, not a final-citation problem

Expected metric movement:

- None in this plan. These two cases should remain explicitly documented as accepted failures unless a
  separate calibration or label-audit task proves a safe product change.

Do not do:

- Do not globally lower STOP below `0.40`.
- Do not whitelist these case IDs.
- Do not use golden expected citation IDs at runtime.
- Do not post-hoc rewrite final citations to match labels.

Valid future experiments:

- Run an offline query-expansion calibration over seed/dev only.
- Compare topic query, concept-only query, and short generated retrieval query without using golden
  labels at runtime.
- Calibrate against adversarial negatives before accepting any lower-confidence evidence path.
- Consider a separate "low-confidence confirm" product path only if it remains grounded and does not
  answer from weak evidence.
- Audit `happy_014` separately for query drift and possible label mismatch. Any label change must be
  owner-approved and documented; it must not be used to make metrics look better after the fact.

## Deep Research Prompt

Use this prompt in ChatGPT or Gemini for current model research:

```text
I am optimizing a grounded LangChain tutor agent for latency, cost, and structured-output reliability.
It uses OpenAI-compatible Chat Completions via LangChain ChatOpenAI, tool calling, strict structured
output, temperature=0, max_tokens around 700, and a local retrieval tool. Current eval uses
Qwen/Qwen3-30B-A3B-Instruct-2507 via Nebius. Retrieval itself is fast: local p50 about 226 ms and p95
about 258 ms. The slow path is agent inference and repeated tool loops, with around 1.8M input tokens
and 55k output tokens for a 40-case eval.

Find current June 2026 model candidates for a cost-effective low-latency tutor agent that need strong
tool calling and structured JSON output. Treat every model ID below as an unverified placeholder until
confirmed against current provider docs. Compare:
- Qwen fast variants on Nebius
- Gemini 3.5 Flash and Gemini 3.1 Flash-Lite via OpenAI-compatible endpoint
- GLM open models such as GLM-4.7-Flash or GLM-4.5-Air through OpenRouter, HF Inference Providers,
  vLLM, or SGLang
- any other current high-throughput OpenAI-compatible model

For each candidate, report official model name, provider endpoint compatibility, input/output pricing
per 1M tokens, expected latency profile, structured-output/tool-call reliability notes, context window,
data privacy terms, data-retention/training-on-prompts policy, and migration risk for a LangChain
ChatOpenAI integration. Recommend a 3-model bakeoff shortlist and exact pass/fail metrics for a 40-case
golden eval.
```

## Recommended Execution Sequence

- [x] Task 1: add redacted latency attribution and aggregate metrics.
- [x] Run one current-model cloud-safe golden eval with attribution to confirm the refusal-path delay split.
      Full 40-case eval is now governed by AD-12 but has not been run after PR #45.
- [x] Task 3: reduce repeated tool loops.
- [x] Run an isolated cloud-safe golden eval and compare refusal recall, tool counts, and turn/case
      latency for the refusal path.
      Full teachable-path comparison still requires the governed full 40-case run.
- [x] Task 4: harden slide-first preferred check selection.
- [ ] Run an isolated golden eval and verify citation/task/refusal no-regression.
      Cloud-safe refusal no-regression passed; citation/task teachable no-regression still requires the
      governed full 40-case run.
- [x] Complete the AD-12 LangSmith eval-egress governance gate for the current seed/dev golden eval path.
- [ ] Complete the Task 2 governance gate for any new inference provider.
- [ ] Task 2: run approved model/provider screening evals.
- [ ] Promote at most 2 finalists, then run 3x finalist golden evals.
- [ ] Pick one latency winner only if it passes safety, quality, privacy, and cost gates.
- [x] Task 5: document accepted remaining failures and future calibration/label-audit path.
- [x] Document cloud-safe measured latency labels in `docs/week4-eval-progress-handoff.md`.
      Full measured deltas still require the governed 40-case run.

## Residual Risks

- Tiny-N eval metrics can move by one case; compare case-level deltas, not just aggregate averages.
- Some providers may support OpenAI-compatible chat but be weaker on LangChain structured output or
  tool calling.
- Faster models may reduce latency but increase refusal or citation instability.
- New inference providers are data egress decisions, not just performance choices.
- A mixed-provider bakeoff is not comparable unless the check-generation LLM path is explicitly
  included in the latency and privacy report.
- Fixing `known_failure_001` and `happy_014` safely may require retrieval calibration rather than
  agent prompt work.
