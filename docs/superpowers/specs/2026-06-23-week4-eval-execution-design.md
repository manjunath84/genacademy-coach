# Week-4 Eval Execution — Implementation Design

> **Status:** design draft (2026-06-23). Brainstorming output for the eval **build**. The eval
> *framework* (what to measure, pass bars, schema bands, LangSmith egress rule, error-analysis loop,
> improvement hypotheses) is already settled and merged in **[`docs/week4-eval-plan.md`](../../week4-eval-plan.md)**
> and **`docs/decisions.md` AD-12** — this file does **not** restate it. It locks the open
> *implementation* decisions and the handout-grounded scope, then feeds `superpowers:writing-plans`.

## 1. Source-of-truth inputs

- **Framework / pass bars / schema bands / LangSmith egress rule:** `docs/week4-eval-plan.md` (merged).
- **Data-egress decision:** `docs/decisions.md` AD-12 (owner-approved seed/dev LangSmith eval upload;
  frozen `test` stays local).
- **Course handout (grading spec, local-only):** `localdocs/docs/Week4 Project Handout_ AI Evals.docx`.
- **Foundation reuse contract:** `docs/genacademy-rag-foundation.md`; gates/guardrails: `AGENTS.md` §2–3.

## 2. Handout-grounded scope (decided)

The handout makes the track "evaluate one of your own projects." It decides three things our plan
left open:

1. **LangSmith is a required deliverable, not optional.** Required submission = evaluation report +
   golden dataset + **LangSmith project link** + Loom; LLM-as-judge materials are **optional**.
   `week4-eval-plan.md` build-step 4 said "*optionally* wire LangSmith" — this design **upgrades
   scoped-LangSmith to a MUST stage** (Stage 4), kept inside AD-12: owner-approved seed/dev golden eval
   runs may be uploaded/traced in a private LangSmith project; the frozen `test` split stays local as the
   source of truth.
2. **Sourcing: "real beats synthetic, always"; LLM-generated < 20% of the set.** Backbone = the
   Coach's **real seed/dev student questions** (hand-labeled) + **synthetic-from-seed** (paraphrased
   real seeds, hand-labeled). Pure LLM-generated stays < 20% (likely 0 — the 10 hand-written negative
   controls already cover adversarial/refusal).
3. **Size 30–50.** Target **~30 in-corpus teachable cases (≈16 happy / 9 edge / 5 known-failure) +
   the 10 negative controls** as the refusal/adversarial battery (~40 total, inside the band, growable
   to 50 without touching frozen `test` rows). Mix follows the plan's 50/30/15/5.

## 3. Open implementation forks (decided)

### Fork 1 — cost/latency instrumentation seam

**Decision:** capture at the **`AgentPort` boundary** in `src/genacademy_coach/teach_session.py`.
- Add a `TokenUsage` value type (`input_tokens`, `output_tokens`, `total_tokens`) to `teach_types.py`.
- `AgentPort` gains a `last_usage: TokenUsage` attribute. `LangChainAgentPort.invoke` sums
  `usage_metadata` off the agent result's messages after `self._agent.invoke(...)`; `StaticAgentPort`
  reports zero usage (keeps test doubles trivial).
- `CoachSession._invoke_agent` measures wall-clock latency with `time.perf_counter()` around the port
  call (full-turn latency = retrieval + tool + LLM, which is what the plan wants for p95). Early
  returns (turn-budget / pre-invoke refusal) report `latency_ms=0`, zero usage.
- `TraceTurn` (`teach_types.py`) gains **optional, defaulted** fields: `input_tokens: int = 0`,
  `output_tokens: int = 0`, `total_tokens: int = 0`, `latency_ms: float = 0.0`. Defaults keep every
  existing trace reader/test green.
- **Cost (USD) is derived in the metrics layer, not the trace** — a single declared `PriceTable`
  (input/output USD per token by model id) keeps drifting prices (AGENTS.md §4) in one place.

**Guardrail check:** stdlib `time` + dict inspection of `usage_metadata` + `langchain_core` only — no
web imports (pure core holds), no `langgraph.*` import. Extends the typed trace; does not rebuild it.

### Fork 2 — golden dataset on-disk format

**Decision:** line-oriented JSONL for inputs + a **separate** manifest, so frozen `test` rows in
`eval/split_manifest.json` stay byte-stable.
```
eval/
  split_manifest.json                 # UNTOUCHED (frozen test/seed/dev source manifest)
  non_private_negative_controls.json  # reused as the adversarial/refusal source
  golden/
    golden_cases.jsonl                # band (a) golden inputs, one case per line
    golden_manifest.json              # version, seed, class-balance counts, cloud_safe count
  runs/
    golden-baseline-<date>.json       # band (b)+(c) run output + metric scores (redacted per cloud_safe)
    golden-postfix-<date>.json
```
- Each `golden_cases.jsonl` row carries band-(a) fields from `week4-eval-plan.md` (`case_id`,
  `query_type`, `concept`, `expected_citation_span_id`, `target_check_id`, `expected_next_action`,
  `expected_tools`, `refusal_expected`, `strategy_changed_on_stumble`, `split`, `cloud_safe`,
  `cloud_safe_reason`). Inline `user_query` / `initial_wrong_answer` / `answer_text` appear **only on
  `cloud_safe=true` rows**; non-cloud-safe rows carry a `source_ref` to a `split_manifest` id, no
  inline text. `split` ∈ {seed, dev, synthetic, negative_control} — **never `test`**.
- `expected_tools` uses the recorded tool names from `teach_tools.py`: `retrieve_course_corpus`,
  `generate_check_item`, `grade_understanding`, `update_profile`, `escalate_to_mentor`.
- Run artifacts (band b+c) apply the same redaction: `answer_text` only on cloud-safe rows.
- **Leak guard extension** (`scripts/check_eval_leak.py`): also scan `golden_cases.jsonl` to assert
  (1) no row has `split=="test"`; (2) every `cloud_safe=true` row has a non-empty `cloud_safe_reason`;
  (3) no `test` ids/checksums/phrases appear in any inline field; (4) `cloud_safe=false` rows carry no
  inline `user_query`/`answer_text`/`initial_wrong_answer`. The committed/local artifact redaction rule is
  machine-checked before public docs, commits, or unapproved uploads; owner-approved LangSmith upload may
  resolve seed/dev text locally at upload time under AD-12.
- The handout's "store as a LangSmith dataset, not a CSV" is satisfied **in addition**: the local
  JSONL is the full reproducible source of truth; owner-approved seed/dev golden rows and cloud-safe
  controls may also be uploaded as a private LangSmith dataset/experiment (Stage 4). Not either/or.

### Fork 3 — scoring / metrics code structure

**Decision:** new **pure** module + thin runner; reuse the deterministic grader; leave the legacy
harness alone.
- `src/genacademy_coach/eval_metrics.py` (pure, unit-tested, no I/O): `precision_recall_f1(tp,fp,fn)`,
  `citation_prf(predicted_ids, expected_ids)` (set-based citation_f1 — upgrades today's binary
  citation-resolution check in `grounding.py`), `tool_match(actual, expected)` (trajectory
  correctness), `recall_at_k(ranked_ids, expected_id, k=5)`, `refusal_correct(...)` confusion
  contributors, `aggregate(rows)` (per-metric P/R/F1 + latency p50/p95 + cost via `PriceTable`).
- `src/genacademy_coach/eval_runner.py` (**core**, importable/testable — `scripts/` is not on the
  import path) holds `score_golden_case` / `run_golden_eval`; `scripts/run_golden_eval.py` is a thin
  CLI over it. The runner reuses the `eval_teach_loop` 3-turn pattern, applies the grounded grader from
  `grounding.py` as the per-turn correctness signal + `eval_metrics.py`, and writes
  `eval/runs/golden-<tag>-<date>.json` (redacted per `cloud_safe`).
- **Per-case golden gate = `task_completion_pass = (final_next_action == expected_next_action) and
  (refusal_expected or grade_correct)`** — anchored on the golden `expected_next_action`, with the
  grounded grader's `grade_correct` for teachable cases (not a runtime-generated check).
- **Real seed/dev rows are `cloud_safe=false`** (real learner questions): their query text is resolved
  locally at run time via `resolve_query` over the scenario loaders, and redacted from artifacts. The
  scenario loaders (`load_scenarios` etc.) move from `scripts/eval_teach_loop.py` into a core
  `eval_scenarios.py` so both the legacy script and the runner import them.
- **Do not bloat `scripts/eval_teach_loop.py`** (keep it for legacy dev pass/fail diagnostics).
  recall@5 is measured on the raw `foundation.retrieve()` ranking **before** the
  `require_citeable_spans` threshold filter, so it reflects true top-5 recall.

**Guardrail check:** metrics in core (pure, testable, no web imports); pricing centralized; the
deterministic grader stays the gate; reuses `grounding.py` + the existing scenario pattern (no new
grader/embedder/threshold scheme).

### Fork 4 — calibrated LLM-judge shape (optional, Stage 7)

**Decision:** a single-category classifier, isolated, cloud-safe only.
- Module `src/genacademy_coach/eval_judge.py` (or `scripts/run_judge_eval.py`): classifies one binary
  — *"did the agent over-refuse a teachable confirm-band case?"* (the dominant failure category). It
  does **not** redo the agent's task and is **never** the gate.
- Compare **≥2 distinct Nebius-hosted instruct models** (IDs verified against the provider catalog at
  build, AGENTS.md §4); pick the one with higher F1 vs human labels.
- Human labels: `eval/golden/human_labels.jsonl` keyed by `case_id`
  (`over_refusal_human: bool`, `reviewer_comment`) — judgments about synthetic/cloud-safe cases only.
- Report the judge's precision/recall/F1 **vs human labels**. Pinned **RAGAS** (faithfulness /
  answer-relevancy / context P-R) runs alongside on the cloud-safe subset only, as an *understood*
  cross-check.

## 4. Build sequence (each stage = one Codex-reviewable slice)

| Stage | Deliverable | Handout day | Gate |
|---|---|---|---|
| 1 | Golden dataset: `golden_cases.jsonl` (~30 in-corpus + 10 controls) + `golden_manifest.json` + leak-guard extension + tests | Day 1 | Codex |
| 2 | Cost/latency instrumentation: `TokenUsage`, `AgentPort.last_usage`, latency capture, optional `TraceTurn` fields + tests | Day 2 (local) | Codex |
| 3 | Deterministic scoring: pure `eval_metrics.py` + `run_golden_eval.py` runner (P/R/F1 + cost/latency) + tests | Day 1/3 | Codex |
| 4 | Private LangSmith eval upload: owner-approved seed/dev golden rows + controls, code-based custom evaluators + project link (MUST per handout, AD-12-bounded) | Day 2 (cloud) | Codex |
| 5 | Baseline run + error-analysis loop: baseline artifact, human-annotate failures, LLM-cluster into 3–4 `failure_category` | Day 3 | Codex |
| 6 | 3–4 improvements (prompt-first) + re-run on the same set + per-metric/per-category delta (regressions included) + report + Loom | Day 4 | Codex |
| 7 *(optional)* | Calibrated single-category LLM-judge (≥2 models vs human labels) + pinned RAGAS, cloud-safe only | Day 3 (optional) | Codex |

## 5. Reference calls to verify at build (AGENTS.md §4 — copy verbatim, don't recall)

- LangChain `create_agent` result shape + `AIMessage.usage_metadata` keys (`input_tokens`,
  `output_tokens`, `total_tokens`) — confirm against the installed `langchain`/`langchain_core`.
- LangSmith tracing env var names — the plan uses `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` /
  `LANGSMITH_PROJECT`; the handout shows the older `LANGCHAIN_*` names. Verify the current canonical set.
- LangSmith SDK: `Client.create_dataset` / `Client.evaluate` signatures.
- Nebius model IDs for the ≥2 judge models (catalog-verified) and current per-token prices for the
  `PriceTable`.
- Pinned **RAGAS** version (the course's `ragas_compat.py` signals version churn) — pin exactly.

## 6. Guardrail compliance summary

- **Pure core / thin view:** all new logic (`eval_metrics.py`, instrumentation, dataset loader) is
  core/script with no web-framework imports.
- **No `langgraph.*`:** instrumentation reads `usage_metadata` and uses stdlib `time`; no graph imports.
- **Reuse Week-2 / existing harness:** reuses `grounding.py` grader, the `eval_teach_loop.py` scenario
  pattern, `split_eval.py`/`check_eval_leak.py`, and the negative controls; no new grader/embedder/
  threshold scheme.
- **Frozen `test` is sacred:** golden set excludes `test`; `split_manifest.json` rows stay byte-stable;
  leak guard enforces it.
- **LangSmith egress rule (AD-12):** owner-approved seed/dev golden eval runs may upload to private
  LangSmith; RAGAS/judge stays cloud-safe-only unless separately approved; the frozen `test` split and
  held-out number come from local artifacts.
