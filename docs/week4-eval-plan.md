# Week 4 — Evaluation Plan (AI Evals)

Status: planning draft. Date: 2026-06-21. Target completion: Thursday 2026-06-25.

Week 4 shifts the question from *can the teach agent run* to *does it measurably work*. This document is
the filled evaluation framework for the GenAcademy Coach **teach-loop agent**. It is the plan that gates
the eval build; **no eval code, dataset, LangSmith wiring, or runs are produced by the doc itself** —
those are the next task, gated on approval of this file.

It deliberately **reuses the Coach's existing local-first eval system** rather than rebuilding it, and
keeps the privacy boundary intact: the frozen held-out `test` split and any run over raw learner text
stay on the local harness; only synthetic / corpus-derived **cloud-safe** rows ever reach a third-party
judge or tracer. This matches the course's own guidance — build metrics ground-up in a notebook first,
treat eval platforms as an optional management layer — and the data-egress decision recorded as
**AD-12** in `docs/decisions.md`.

## Evaluation one-liner

Run the Coach teach agent over a versioned **30–50 case** class-balanced golden dataset; score each turn
with deterministic code metrics (task completion, `citation_f1`, tool/trajectory match, retrieval
recall@5, refusal correctness) reported as **precision / recall / F1**, each **paired** with a
cost/latency metric (p95 latency, cost/run, tokens); cross-check quality on the **cloud-safe subset only**
with pinned **RAGAS** and a calibrated **LLM-judge** (targeted at the one dominant failure category,
validated against human labels across ≥2 judge models); establish a baseline, run the error-analysis
loop, ship 3–4 improvements, and **report the measured per-metric and per-category delta** — with the
cloud-safe runs mirrored to a private LangSmith project and the held-out number coming from local
artifacts.

## Framework table (filled)

| Field | Filled for the Coach teach-loop agent |
|---|---|
| **Agent under test** | The teach-loop agent (`src/genacademy_coach/teach_agent.py`, `teach_session.py`): LangChain `create_agent`, temperature 0, model-chosen `next_action` ∈ {`advance`, `drill`, `re_explain_differently`, `refuse_escalate`, `stop`} + `strategy`, grounded by one source-prioritized retriever. |
| **User outcome** | A learner reaches a correct check-answer on a concept within the turn/time budget, taught from **citeable** course spans, with safe refusal/escalation when no span supports an answer. |
| **Metrics (3–5, each paired quality + cost)** | (1) Teach task-completion; (2) `citation_f1`; (3) tool/trajectory correctness; (4) retrieval recall@5; (5) refusal correctness on out-of-corpus. Each paired with **p95 latency + cost/run + tokens**. RAGAS faithfulness/answer-relevancy/context-precision-recall is a secondary cross-check on cloud-safe rows. |
| **Judge method per metric** | Deterministic Python (the gate) for task-completion, `citation_f1`, tool match, retrieval recall@5, refusal; **RAGAS LLM-judge** + a **calibrated single-category LLM-judge** for the quality lens — cloud-safe rows only. |
| **Golden dataset** | Source: corpus-derived seed/dev (`scripts/split_eval.py`) + synthetic-from-seed + 10 negative controls. Size 30–50. Mix ≈50% happy / 30% edge / 15% known-failure / 5% adversarial, class-balanced. Labeling: human-authored expected answer + expected citation span + expected tool + expected next action. |
| **Pass bars** | task-completion F1 ≥ 0.85 and no regression vs baseline; `citation_f1` ≥ 0.90; tool/trajectory match ≥ 0.95; retrieval recall@5 ≥ 0.90; refusal **recall = 1.0** on negative controls (never bluff) with precision ≥ 0.80 (bound over-refusal); RAGAS faithfulness ≥ 0.90 / answer-relevancy ≥ 0.85 / context P/R ≥ 0.80 (cloud-safe, secondary). Cost/latency bars anchored to the measured baseline (no regression without it being called out). |
| **Instrumentation** | Existing redacted trace (`traces/<session_id>.json`) + the **new** token/latency capture at the agent boundary (the current gap). |
| **Baseline plan** | Freeze a baseline run over the golden set on the current prompt/threshold/model; record every metric + cost/latency + the run config (model ID, params, prompt/corpus version, thresholds, dependency + git SHA, per Phase 0 of `docs/production-roadmap.md`). |
| **Failure-analysis plan** | The error-analysis loop (below): code pass/fail → human-annotate failures → LLM-cluster into 3–4 named categories → tag → fix → re-run on the same set → track per-category movement. |
| **Improvement hypotheses (3–4)** | (H1) Relax the confirm-band teaching prompt so confirm-band cases teach-with-caveat instead of over-refusing; (H2) tune source-priority / over-fetch for low-retrieval edge concepts; (H3) tighten the citation-at-retrieval selection to raise `citation_f1`; (H4) add an invalid/unparseable-decision deterministic fallback to remove non-completion noise. |
| **Post-improvement plan** | Re-run on the **same** golden set, report per-metric and per-category delta (regressions included), keep the deterministic grader as the gate. |
| **What's next** | Online monitoring (`docs/production-roadmap.md` Phase 7): production failures (PII-stripped) become new golden rows; thresholds/alerts on latency/quality/tool-failure/cost. |

## Metric set (mapped to the existing harness)

**Classification-style** metrics (task-completion, refusal correctness, `citation_f1`, `tool_f1`) are
reported as **precision / recall / F1**, not bare accuracy — accuracy lies on imbalanced sets, and the
golden set is deliberately class-balanced. **Rank / scalar** metrics keep their native definitions
(retrieval `recall@5`; RAGAS faithfulness / answer-relevancy / context-precision-recall as 0–1 scores),
read against their own pass bars below. Each metric is **paired** with a cost/latency metric so
improvements are read on the **accuracy ↔ cost ↔ speed** triangle.

| Metric | What it measures | Reuses | Paired cost/latency |
|---|---|---|---|
| **Teach task-completion** | Reached a correct check-answer within the turn/time budget; deterministic grounded grader marks the final answer correct. **This is the pass/fail gate.** | `grounding.py` grader, `scripts/eval_teach_loop.py` | p95 latency/turn |
| **`citation_f1`** (code metric) | Precision/recall/F1 of cited span IDs vs `expected_citation_span_id` — upgrades today's **binary** citation-resolution check. | `grounding.py` citation resolution | cost/run |
| **Tool / trajectory correctness** | Actual tool sequence vs an `expected_tools`-style field on each case (e.g. `retrieve_course_corpus` present and ordered). | trace `tool_calls`, `teach_types.py` | tokens (incl. tool calls) |
| **Retrieval recall@5** | Did the expected span appear in the top-5 retrieved chunks. | `scripts/diagnose_teach_retrieval.py` | retrieval time |
| **Refusal correctness** | Recall (caught every out-of-corpus / below-threshold case) and precision (did not over-refuse teachable in-corpus cases). | `eval/non_private_negative_controls.json` (10 controls), confidence bands | p95 latency |
| **RAGAS** (secondary, cloud-safe only) | faithfulness, answer relevancy, context precision/recall — an *understood* cross-check, **never the gate**. | new evaluator, pinned RAGAS | judge tokens/cost |

**LLM-as-judge — targeted, last, optional.** A single judge is calibrated to the Coach's **one dominant
failure category**: *conservative confirm-band over-refusal* (the 2026-06-16 dev evidence is 7/8
teachable with the one remaining teachable failure being a cautious refusal in a confirm-band retrieval
case). The judge classifies "did the agent over-refuse a teachable confirm-band case?" — it does **not**
redo the agent's task. Report the **judge's** precision / recall / F1 **against human labels**, and
**compare ≥2 judge models** to pick the better-calibrated one. Cost is summed across the judge's own
calls (see below).

**Cost / latency definition (the metric-pair other half — the current gap).**
- **Cost (USD)** = Σ over **every** LLM call of `input_tokens × input_price + output_tokens ×
  output_price`, plus any embedding / rerank / vector-store and LLM-judge costs — summed across
  generation, intermediate reasoning, tool calls, retrieval, the judge, and retries. (Output **price per
  token** is typically ~3–5× input price, so concise outputs matter; this is a price ratio, not a token
  ratio.) Track `input_tokens` / `output_tokens` / `cost_usd` as separate columns.
- **Latency** = TTFT + tokens/sec + inter-token + retrieval time + tool time; **report p95**.
- Levers (each re-measured — whack-a-mole): cap steps/retries, early-stop, right-size model, cache,
  summarize context, parallelize tool calls, smaller judge.
This is instrumented **new** at the agent boundary (`teach_agent.py` / `teach_session.py`); the current
trace (`session_id`, `turn`, `next_action`, `strategy`, `evidence_score`, `evidence_band`,
`faithfulness_ok`, `tool_calls`, `retrieved_citation_ids`) does not yet carry tokens or per-call duration.

## Golden-dataset spec

Target **30–50** cases, **class-balanced** across scenario types, handout mix ≈ **50% happy / 30% edge /
15% known-failure / 5% adversarial**.

**Schema is the builder's own design over the tutoring domain.** It extends the Coach's existing
seed/dev scenario shape (`{"concept", "initial_wrong_answer", "expected_citation_span_id",
"target_check_id"}` from `specs/tech-stack.md` §Success-Metric Protocol) and reuses the Coach's typed
signals from `teach_types.py` — it does **not** clone a compliance-router CSV. Three bands of columns
plus a human verdict:

| Band | Columns (designed for the tutoring domain) |
|---|---|
| **(a) Golden inputs** | `case_id`, `query_type` (happy/edge/known_failure/adversarial), `concept`, `user_query` *(inline text on cloud-safe rows only; hash/ID on test)*, `initial_wrong_answer` (stumble cases), `expected_citation_span_id`, `target_check_id`, `expected_next_action`, `expected_tools`, `refusal_expected`, `strategy_changed_on_stumble`, `split`, `cloud_safe`, `cloud_safe_reason` (required when `cloud_safe=true`) |
| **(b) Run output** | `actual_next_action`, `actual_strategy`, `actual_tools`, `retrieved_citation_ids`, `evidence_score`, `evidence_band`, `faithfulness_ok`, `answer_text` *(cloud-safe only)*, `turns_used`, `latency_p50_ms`, `latency_p95_ms`, `input_tokens`, `output_tokens`, `cost_usd` |
| **(c) Metric scores** | `task_completion_pass`, `citation_precision/recall/f1`, `tool_f1`, `retrieval_recall_at_5`, `refusal_correct`, RAGAS columns *(cloud-safe only)* |
| **(d) Human verdict** | `overall_pass_fail`, `reviewer_comment` (free text), `failure_category` (filled during error analysis) |

**Sourcing.** Corpus-derived seed/dev via `scripts/split_eval.py` + synthetic-from-seed expansion + the
10 entries in `eval/non_private_negative_controls.json` (out-of-domain → adversarial/refusal cases).
**The frozen private `test` split stays in the existing manifest + private-files form** (`eval/split_manifest.json`,
no inline question text) and is **excluded from LangSmith and RAGAS**. Only rows that pass the
**cloud-safe rule** (defined below) carry inline text and upload to a LangSmith dataset. Everything is
versioned and tagged for baseline vs re-eval — but the version bump records **seed/dev or golden-row
growth only**. Expansion touches **seed/dev only**: the frozen `test` entries and their checksums in
`eval/split_manifest.json` stay **byte-stable**, so a `version` bump never means a `test`-split edit. If
golden/dev versioning ever needs to move independently, split it into a separate golden manifest rather
than rewriting the `test` rows.

## LangSmith + RAGAS playbook (scoped)

- **Project:** `genacademy-coach-week4-eval`, default-private LangSmith workspace.
- **Env vars:** `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` (the same trio already
  documented in `specs/tech-stack.md`).
- **Masking on (defense-in-depth):** enable input/output masking (`hide_inputs` / `hide_outputs` /
  anonymizer) and a short **retention TTL** on the cloud-safe rows that do get traced. This is
  belt-and-suspenders, **not** permission to trace borderline rows: any run that could include real
  learner text or private-corpus spans is **never traced at all** — it runs local-only per the
  cloud-safe rule and AD-12. Masking protects against mislabeling, it does not widen what may be sent.
- **Cloud-safe rule (what `cloud_safe=true` is allowed to mean).** A row is cloud-safe **only if** it
  contains **none** of: verbatim private course-corpus spans, real learner questions, raw generated tutor
  prose, or close paraphrases of any private material. "Corpus-derived" alone is **not** sufficient — a
  reworded private span is still private. Synthetic-from-seed and out-of-domain negative controls
  qualify; a private span dressed up as `user_query`/`answer_text` does not. Every `cloud_safe=true` row
  carries a required `cloud_safe_reason` justifying it (e.g. "synthetic, no private text"), and the
  `check_eval_leak.py`-style guard runs before any upload. When in doubt, mark `cloud_safe=false` and
  keep it local.
- **What's traced:** cloud-safe rows **only** (per the rule above). The frozen `test` split and any run
  over raw learner text are **never** traced — they run on the local harness.
- **Evaluators:** code-based `citation_f1` + tool/trajectory check + the deterministic grounded grader
  (the gate) run locally and, for cloud-safe rows, as LangSmith custom evaluators; **RAGAS** LLM-judge
  metrics and the calibrated single-category judge run on **cloud-safe rows only**.
- **Pin RAGAS exactly** — the course repo's `ragas_compat.py` signals RAGAS version churn, so pin the
  exact version and treat its scores as *understood*, not blindly trusted.
- **Run comparison:** baseline vs post-improvement via LangSmith experiments **and** local artifacts; the
  report cites the LangSmith project link for cloud-safe runs, but the **held-out `test` number comes from
  local artifacts only**. The notebook / local harness stays the source of truth.

## Failure-analysis + improvement playbook

The error-analysis loop (the "Hamel Hussain" method) is the regression mechanism — evals are a **loop,
not a one-time gate**:

1. Run the agent on the golden set → one run-output row per case.
2. Code-based pass/fail (deterministic grader + `citation_f1` + `tool_f1`) → **check class balance**.
3. **Human-annotate** each failed row with a one-line `reviewer_comment`.
4. **LLM-cluster** those comments into **3–4 named `failure_category`** values.
5. Tag all failures with their category.
6. **Fix prompt-first**, then retrieval tuning / STOP threshold / tool design — **one lever at a time**.
7. **Re-run on the same set** → track per-category movement, **including regressions** (honesty about
   negative deltas is the graded behavior).

**Levers mapped to the Coach's known failure modes:**

| Known failure mode | First lever |
|---|---|
| Conservative confirm-band over-refusal (the dominant teachable failure) | Prompt (teach-with-caveat in confirm band) → then STOP/CONFIRM band re-calibration |
| Empty / low retrieval on edge concepts | Retrieval tuning: source-priority, over-fetch, span selection |
| Citation mismatch | Tighten citation-at-retrieval discipline in `grounding.py` |
| Schema / invalid-decision noise | Deterministic invalid-output fallback → `refuse_escalate`/`stop` |

**Tooling order is explicit: notebook / Excel first, platform (LangSmith) optional.** Build the metrics
ground-up; do not blindly trust off-the-shelf evaluators.

## Day-by-day (executing these days is the NEXT task, gated on approval of this doc)

| Day | Focus |
|---|---|
| Mon 06-22 | Design the golden-dataset schema (Coach-native, above); build 30–50 class-balanced cases; finalize the metric set + pass bars. |
| Tue 06-23 | Instrument cost/latency at the agent boundary; wire scoring (`citation_f1`, `tool_f1`, deterministic grader, RAGAS on the cloud-safe subset). |
| Wed 06-24 | Baseline run; run the error-analysis loop (human-annotate → LLM-cluster → failure categories). |
| Thu 06-25 | Ship 3–4 improvements; re-run on the same set; measure per-metric + per-category delta; write the report; record the Loom. |

## Build sequence for the next task (described, not executed here)

1. Expand the golden set to 30–50 (class-balanced) via `scripts/split_eval.py` seed/dev + synthetic-from-seed;
   hand-label in the schema above (with `expected_tools`).
2. Add token/latency capture to the trace at the agent boundary (`teach_agent.py` / `teach_session.py`).
3. Add `citation_f1` + pinned RAGAS evaluators alongside the deterministic grader, reporting precision/recall/F1.
4. Optionally wire LangSmith (`client.create_dataset` + `client.evaluate`) on the **cloud-safe** subset
   with masking — the notebook stays the source of truth.
5. Run the baseline, then the error-analysis loop (human-annotate → LLM-cluster → categorize).
6. Calibrate the single-category LLM-judge to the dominant failure category; compare ≥2 judge models vs human labels.
7. Implement 3–4 improvements, re-run on the same set, report per-metric + per-category delta.
8. Write the report + record the Loom.

## Out of scope (this plan)

- Writing eval code, building the dataset, wiring LangSmith/RAGAS, or running evals — those are the next
  task, gated on approval of this doc.
- Touching, growing, or editing the frozen `test` split.
- Sending any private corpus span, real learner question, or raw tutor prose through a third-party judge
  or tracer (AD-12).
