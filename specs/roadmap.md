# Roadmap

Status updated: 2026-06-26.

The project is now past the teach-loop MVP. Teach, Quiz, Skill-Gap Diagnosis, and the local Gradio UI
are shipped. Future work is intentionally separated from the grounded core so the project stays honest:
course facts still come from retrieved citations, grading remains deterministic, and the held-out `test`
split remains unused until final evaluation/reporting.

Production hardening is tracked in [`docs/production-roadmap.md`](../docs/production-roadmap.md). That
roadmap preserves the current direction but makes "reliable" measurable before more product surface is
added: baseline + reliability bar, deterministic decision safety, the FastAPI/HTMX service boundary,
provider resilience, stable corpus references, and datastore/deployment seams.

## Active priority: Post-eval refusal precision, grading, and bounded recovery

Week-4 evaluation changed the next build order. Retrieval recall is healthy, refusal recall remains the
load-bearing guardrail, and the remaining quality work is mostly post-retrieval behavior:
false-refusal precision on teachable borderline cases, cheap concept-aware grading, then bounded Turn-2
recovery specialization. The reasoning is captured in
[`docs/agentic-orchestration-improvement-review.md`](../docs/agentic-orchestration-improvement-review.md);
the completed provenance learning note is
[`docs/post-v1-eval-provenance-learning.md`](../docs/post-v1-eval-provenance-learning.md).

The immediate priority is **not** adding more agents or direct LangGraph. It is to keep the grounded
core stable while improving the next weak decisions: how to avoid literal keyword grading false
negatives, when to salvage teachable CONFIRM-band cases, and how to run one bounded recovery cycle after
a real stumble.

Current priority stack:

1. **Done: citation label audit** — citation misses were classified in the public-safe audit map without
   moving scorer goalposts.
2. **Done: role-keyed provenance + deterministic check-span policy** — PR #53 captures
   `role -> span_id` when evidence is selected and enforces slide, then handout, then first citeable span
   for checks. Citation F1 improved from `0.45` to `0.6333` without task-completion or refusal-safety
   regression.
3. **Next: cheap semantic grading** — add deterministic synonym/concept coverage before Turn-2
   recovery so literal keyword false negatives do not pollute recovery metrics. The plan is
   [`docs/superpowers/plans/2026-06-27-semantic-check-answer-grading.md`](../docs/superpowers/plans/2026-06-27-semantic-check-answer-grading.md).
4. **CONFIRM-band false-refusal precision** — improve only cases with resolved, on-topic, citeable
   CONFIRM-band evidence where the model refused anyway. STOP remains untouched; refusal recall is the
   tripwire.
5. **Bounded Turn-2 recovery** — one-cycle diagnose → strategy map → grounded re-teach → same-span
   smaller check. No memory dependency and no six-agent split. The plan is
   [`docs/superpowers/plans/2026-06-27-bounded-turn2-recovery-orchestration.md`](../docs/superpowers/plans/2026-06-27-bounded-turn2-recovery-orchestration.md).
6. **Mock interview and explicit LangGraph decision** — mock interview remains a future pull-in, but
   direct LangGraph is earned only by durable resume, real HITL interrupt/resume, or persisted multi-mode
   routing.

Production hardening still matters, but behavior correctness stays ahead of new product surfaces:
`docs/production-roadmap.md` remains the reliability track for service boundaries, provider resilience,
stable corpus references, and datastore/deployment seams.

## Status Snapshot

### Done

- **Week-2 foundation reuse locked.** `docs/genacademy-rag-foundation.md` records the reuse contract;
  the Coach uses the Week-2 embedder, vectorstore factory/schema, chunking pipeline, provider boundary,
  and eval patterns instead of rebuilding them.
- **Corpus and eval safety scaffold shipped.** The local corpus layout, deterministic eval split
  manifest, and `scripts/check_eval_leak.py` are in place. Private corpus and generated eval artifacts
  stay gitignored; the held-out `test` split remains frozen.
- **Foundation adapter shipped.** Coach settings, source-priority ordering, retrieval over-fetching,
  citation-preserving span selection, and ingest/retrieval smoke tests are implemented.
- **Teach-loop MVP shipped.** The text-first teach session supports grounded retrieval, citations,
  learner-profile state, model-chosen `next_action`/strategy, re-explain on stumble, refusal and
  escalation, typed traces, and CLI/UI entry points.
- **Teach-loop eval shipped.** `scripts/eval_teach_loop.py` runs multi-turn teach scenarios and reports
  redacted pass/fail diagnostics without exposing private eval text.
- **Redacted eval diagnostics shipped.** Diagnostics reuse runtime grounding helpers and emit only
  scenario IDs, filenames, counts, scores, source types, next actions, and reason codes.
- **Retrieval triage and STOP-threshold calibration completed.** Local diagnostics showed the early
  zero-coverage symptom was threshold filtering, not missing ingestion. A calibrated `0.40` STOP
  threshold is supported by seed/dev positives plus non-private negative controls.
- **Teach-loop behavior hardened.** Session-boundary grading runs before model decisioning, incorrect
  grounded answers force `re_explain_differently` with a changed strategy, citations are aligned to
  retrieved spans, and review-queue refusal boundaries are tested.
- **Final teach-loop status captured.** Redacted dev evidence remains `7/10` overall and `7/8`
  teachable on 2026-06-16, with two safe low-retrieval refusals and one conservative confirm-band
  escalation path. The held-out `test` split was not used.
- **Same-topic lens switching shipped.** The learner can switch among low-code/no-code, code-heavy, and
  bridge teaching lenses for the same topic. The default personalization path is still a switchable
  teaching lens plus within-session profile state.
- **Grounded Quiz Mode shipped.** The first pull-in generates up to three cited MCQs from retrieved
  spans, validates grounding, grades selected option IDs deterministically in Python, refuses/escalates
  when retrieval is not citeable, and writes a typed redacted quiz trace.
- **Hugging Face deployment shell shipped.** A thin Gradio/Docker Space wrapper builds with CPU-only
  `torch`, boots locally in Docker, and serves a private Hugging Face Space. Hosted retrieval is
  adapter-ready through the reused Week-2 vectorstore factory, using a Coach-specific Pinecone
  index/namespace when approved. Chroma is the tested path, and no private corpus/index is seeded yet;
  the Space shows an empty-corpus notice until a public-safe corpus decision is made. The Space was
  redeployed after the Skill-Gap UI merge with allow-list upload only and authenticated `HTTP/2 200`
  root smoke.
- **Local Gradio UI shipped.** The UI is a thin view over the core teach, quiz, and skill-gap workflows.
  Teach trace cards show rendered `Decision basis` plus labeled `action ...` / `band ...` status chips.
  Quiz displays generated questions with per-question answer controls for local/private demos while
  backend calls still hide generated quiz text by default. All traces use safe allow-lists, and the core
  stays free of web imports.
- **Cohort auth/admin shipped.** The Gradio surface now has a bounded cohort login gate using the reused
  Week-2 user store, bcrypt password hashes, deploy seed-secret accounts, no default credentials in the
  shared deploy, server-side admin-only account creation, and member-hidden Admin UI. This is a cohort
  gate, not a production-grade auth platform.
- **Skill-Gap Diagnosis shipped.** The deterministic gap report composes existing teach traces, quiz
  trace rows, review-queue events, retrieval, grounding, and typed redacted traces. It produces a cited
  next-step plan or refuses/escalates if no citeable span exists; it does not add LLM mastery grading,
  memory, a second agent loop, or direct `langgraph.*` imports.
- **Privacy-first memory slice shipped.** Teach traces and review queues persist hashes instead of raw
  topics, learner inputs, observations, or generated tutor text. Optional Mem0 episodic memory is
  implemented behind `MEM0_API_KEY` plus `GENACADEMY_COACH_MEMORY_USER_SALT`; if either is absent, the
  no-op provider is used. Memory stores only style/lens/count/topic-hash learner-state and never feeds
  citations, retrieval input, grading, or refusal decisions.
- **Portfolio cleanup completed.** Submission-specific documents and screenshots are local-only under
  ignored `localdocs/`; the public repository keeps stable product, architecture, safety, and verification
  docs.

### In Progress

- **False-refusal, grading, and bounded recovery planning.** Citation provenance is merged, so the
  next work is the narrow CONFIRM-band false-refusal policy, cheap concept-aware grading, and the bounded
  Turn-2 recovery plan. The recovery plan is reviewable now, but its implementation should wait until
  the prerequisite gates are completed or explicitly accepted as risks.
- **Public-safe deployment decision.** Decide whether to keep the Space as an empty-corpus deployment
  shell or seed a small approved public-safe corpus/index into the Coach-specific Pinecone namespace.
  Do not upload private course material to a public deployment. Owner-approved private LangSmith eval
  uploads are governed separately by `docs/decisions.md` AD-12.
- **Production hardening plan.** Follow `docs/production-roadmap.md` before adding new surfaces:
  define the reliability bar, pin or concretely replace the editable `genacademy-rag` dependency,
  expand diagnostics/failure taxonomy, and decide the FastAPI sync/threadpool boundary.

### Pending

- Review and approve
  `docs/superpowers/plans/2026-06-27-bounded-turn2-recovery-orchestration.md` before any Turn-2 recovery
  implementation work.
- Keep the held-out `test` split unused until final evaluation/reporting.
- Re-run `pytest`, `ruff`, `check_eval_leak.py`, and the dev eval before any public release milestone.
- If a public-safe corpus subset is approved, ingest it separately from the private collection and
  smoke-test grounded teach, quiz, skill-gap, and safe refusal on the Space.
- Re-review public screenshots or hosted UI outputs before publishing them outside the private repo.

## Teach-Loop MVP

The adaptive teach loop:

> intake (topic · style · track lens) -> retrieve grounded span (slides/handouts first) -> explain in
> style -> check understanding -> grade grounded -> runtime decide (`advance`, `drill`,
> `re_explain_differently`, `refuse_escalate`, `stop`) -> update the within-session learner profile ->
> loop -> session report.

Completed requirements:

- [x] Runtime-decision trace with real branches.
- [x] Grounded explanations and constrained citations.
- [x] Real-signal refusal driven by retrieval score plus citation presence.
- [x] Human-escalation path via the local review queue.
- [x] Item-quality eval on seed/dev chat-question scenarios, with redacted diagnostics.
- [x] Calibrated STOP threshold against seed/dev positives plus non-private negative controls.
- [x] Local teach, quiz, and skill-gap workflows over the same grounded core.
- [x] Honest dated dev numbers; held-out `test` split remains untouched.
- [x] Cohort member/admin login gate for the Gradio app, reusing the Week-2 SQLite user/password store.

## Future Pull-Ins

This list is future-only; shipped pull-ins stay in Done. Near-term quality work now precedes new product
surfaces. Items that also appear in the active priority stack are listed here because they are planned
but not implemented; the active stack above is the binding order for the next slices.

1. **Semantic check-answer grading, cheap slice first** — keep Python as the pass/fail gate, but evolve
   open-answer checks from literal keyword matching to deterministic synonym/concept coverage before
   Turn-2 recovery. Optional embedding similarity and any LLM-judge audit are later scorer-versioned
   changes, behind data-egress approval where applicable.
2. **Bounded Turn-2 recovery specialization** — a one-cycle, grounded recovery path after a learner
   stumbles: diagnose error type, map to a strategy, re-teach from a selected recovery span, and ask a
   smaller same-span check. Memory does not influence this path until memory-hardening has its own eval.
3. **Mock-interview mode** — open-answer grounded grading, follow-up probing, and cited gap report. This
   is the likely feature family where explicit orchestration may become useful, but only if durable
   resume, HITL interrupt/resume, or persisted multi-mode routing is required.
4. **Memory hardening for cohort rollout** — decide retention, deletion, admin visibility, and whether
   Mem0 managed storage remains the right provider. Memory may personalize style/struggle history later,
   but course facts still require citations, and recovery-strategy memory needs its own eval.
5. **Cohort rollout hardening** — per-user cost caps, account lifecycle, and admin operations beyond the
   minimal login/account-creation gate.
6. **Admin upload** — low-priority pull-in for admin-authored docs/quiz questions, reusing Week-2
   auth/upload patterns only after a privacy review.
7. **Track-aware retrieval** — corpus tagged by track only if measured retrieval gaps justify it.
8. **Caching and model tiering** — latency/cost optimization after behavior is stable, especially if
   Turn-2 recovery adds model calls.
9. **Explicit LangGraph orchestration** — only when durable resume, HITL interrupts, or persisted
   multi-mode coordination outgrow `create_agent`; the feature name alone is not enough.
10. **ElevenLabs voice** — voice over the same text engine; text transcript remains the source of truth.
11. **Multimodal slide questions** — only with a clear grounded-citation path.
12. **Flashcards / mind-map artifacts** — generated only from cited spans.
13. **GraphRAG** — course knowledge graph only if the single-retriever contract shows a measured recall
   gap.

## North Star

A full adaptive tutor that teaches, tests, interviews, remembers safe learner preferences across
sessions, adapts by track, supports voice/multimodal interaction, and remains grounded in citeable course
material.

## Risk Caps

- **Corpus privacy.** Primary corpus = local `corpus/notes`, `corpus/slides`, `corpus/handouts`, and
  `corpus/transcripts`, chunked with Week-2 machinery. Private content remains local and gitignored.
- **Eval contamination.** Hard-split before any use; the `test` split is frozen and never enters
  prompts, examples, local examples, tuning, or retrieval indexes.
- **Agenticity proof.** The model chooses teach next actions from observations; Python only enforces
  schema, thresholds, citation presence, turn budgets, and refusal gates.
- **Threshold tuning.** Tune only on seed/dev plus non-private negative controls.
- **Scope control.** Teach loop is the committed core; pull-ins must reuse the grounded core unless a
  reviewed plan proves otherwise.
- **Memory privacy.** Cross-session memory can store learner preferences, counts, and topic hashes, not
  raw user IDs/emails, learner answers, generated tutor text, private corpus/eval text, retrieved spans,
  quiz prompts/options/rationales, or uncited course claims.
- **Grader evolution.** The Week-4 v1 metrics are tied to the current deterministic scorer. Any semantic
  grading, embedding-similarity, or LLM-judge change must be separately versioned, re-evaluated on the
  same golden set, and reported as a new result, not retrofitted onto the submitted baseline.
- **Demo artifact privacy.** Local/private demo trace cards may show decision basis and labeled
  action/band status, but raw trace JSON, generated screenshots, generated DOCX packets, secrets, and
  unreviewed corpus-bearing captures stay in ignored local paths such as `localdocs/` or `tmp/`.
- **LangGraph scope.** Direct graph/checkpointer/store imports are future architecture. They need a
  written delta against the current `create_agent` boundary before code.

## Cut Order If Slipping

The active-priority behavior-correctness work — citation audit, role-keyed provenance, and narrow
CONFIRM-band false-refusal precision — comes before this cut list. It is not optional feature backlog.

voice -> explicit LangGraph -> GraphRAG -> flashcards -> multimodal -> admin upload ->
track-aware retrieval -> caching/model tiering -> memory hardening -> mock interview ->
Turn-2 recovery -> semantic grading -> **never the grounded teach loop** -> **never the refusal / eval /
trace path**.
