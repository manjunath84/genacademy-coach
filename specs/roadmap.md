# Roadmap

Status updated: 2026-06-17.

The project is now past the teach-loop MVP. Teach, Quiz, Skill-Gap Diagnosis, and the local Gradio UI
are shipped. Future work is intentionally separated from the grounded core so the project stays honest:
course facts still come from retrieved citations, grading remains deterministic, and the held-out `test`
split remains unused until final evaluation/reporting.

## Status Snapshot

### Done

- **Week-2 foundation reuse locked.** `docs/genacademy-rag-foundation.md` records the reuse contract;
  the Coach uses the Week-2 embedder, Chroma store/schema, chunking pipeline, provider boundary, and
  eval patterns instead of rebuilding them.
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
  bridge teaching lenses for the same topic. Current personalization is a switchable teaching lens plus
  within-session profile state, not cross-session clustering or provider-backed memory.
- **Grounded Quiz Mode shipped.** The first pull-in generates up to three cited MCQs from retrieved
  spans, validates grounding, grades selected option IDs deterministically in Python, refuses/escalates
  when retrieval is not citeable, and writes a typed redacted quiz trace.
- **Hugging Face deployment shell shipped.** A thin Gradio/Docker Space wrapper builds with CPU-only
  `torch`, boots locally in Docker, and serves a private Hugging Face Space. No private corpus/index is
  uploaded; the Space shows an empty-corpus notice until a public-safe corpus decision is made.
- **Local Gradio UI shipped.** The UI is a thin view over the core teach, quiz, and skill-gap workflows.
  It uses safe trace allow-lists, hides generated quiz text by default, and keeps the core free of web
  imports.
- **Skill-Gap Diagnosis shipped.** The deterministic gap report composes existing teach traces, quiz
  trace rows, review-queue events, retrieval, grounding, and typed redacted traces. It produces a cited
  next-step plan or refuses/escalates if no citeable span exists; it does not add LLM mastery grading,
  memory, a second agent loop, or direct `langgraph.*` imports.
- **Portfolio cleanup completed.** Submission-specific documents and screenshots are local-only under
  ignored `localdocs/`; the public repository keeps stable product, architecture, safety, and verification
  docs.

### In Progress

- **Public-safe deployment decision.** Decide whether to keep the Space as an empty-corpus deployment
  shell or upload a small approved public-safe corpus/index. Do not upload private course material.
- **Review and land PR #28.** The Skill-Gap UI wrapper is a thin Gradio tab over the shipped core and
  safe trace allow-list.

### Pending

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

## Future Pull-Ins

This list is future-only; shipped pull-ins stay in Done.

1. **Mock-interview mode** — open-answer grounded grading, follow-up probing, and cited gap report.
2. **Admin upload** — low-priority pull-in for admin-authored docs/quiz questions, reusing Week-2
   auth/upload patterns only after a privacy review.
3. **ElevenLabs voice** — voice over the same text engine; text transcript remains the source of truth.
4. **Track-aware retrieval** — corpus tagged by track if measured retrieval gaps justify it.
5. **Cross-session memory** — evaluate first-party persisted profile, LangMem, Mem0 open source, and
   Zep Cloud. Memory may personalize style/struggle history, but course facts still require citations.
6. **Explicit LangGraph orchestration** — only when durable memory, HITL interrupts, or multi-mode
   coordination outgrow `create_agent`.
7. **Caching and model tiering** — latency/cost optimization after behavior is stable.
8. **Multimodal slide questions** — only with a clear grounded-citation path.
9. **Cohort rollout** — multi-user auth, per-user cost caps, and admin operations.
10. **Flashcards / mind-map artifacts** — generated only from cited spans.
11. **GraphRAG** — course knowledge graph if the single-retriever contract shows a measured recall gap.

## North Star

A full adaptive tutor that teaches, tests, interviews, remembers learner preferences across sessions,
adapts by track, supports voice/multimodal interaction, and remains grounded in citeable course material.

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
- **Memory privacy.** Cross-session memory can store learner preferences and struggle patterns, not raw
  private corpus/eval text or uncited course claims.
- **LangGraph scope.** Direct graph/checkpointer/store imports are future architecture. They need a
  written delta against the current `create_agent` boundary before code.

## Cut Order If Slipping

voice -> explicit LangGraph -> cross-session memory -> admin upload -> multimodal -> flashcards ->
caching -> track-aware retrieval -> interview -> **never the grounded teach loop** -> **never the
refusal / eval / trace path**.
