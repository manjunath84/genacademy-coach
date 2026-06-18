# Roadmap

Status updated: 2026-06-18.

The project is now past the teach-loop MVP. Teach, Quiz, Skill-Gap Diagnosis, and the local Gradio UI
are shipped. Future work is intentionally separated from the grounded core so the project stays honest:
course facts still come from retrieved citations, grading remains deterministic, and the held-out `test`
split remains unused until final evaluation/reporting.

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

- **Public-safe deployment decision.** Decide whether to keep the Space as an empty-corpus deployment
  shell or seed a small approved public-safe corpus/index into the Coach-specific Pinecone namespace.
  Do not upload private course material.

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
- [x] Cohort member/admin login gate for the Gradio app, reusing the Week-2 SQLite user/password store.

## Future Pull-Ins

This list is future-only; shipped pull-ins stay in Done.

1. **Mock-interview mode** — open-answer grounded grading, follow-up probing, and cited gap report.
2. **Admin upload** — low-priority pull-in for admin-authored docs/quiz questions, reusing Week-2
   auth/upload patterns only after a privacy review.
3. **ElevenLabs voice** — voice over the same text engine; text transcript remains the source of truth.
4. **Track-aware retrieval** — corpus tagged by track if measured retrieval gaps justify it.
5. **Memory hardening for cohort rollout** — decide retention, deletion, admin visibility, and whether
   Mem0 managed storage remains the right provider. Memory may personalize style/struggle history, but
   course facts still require citations.
6. **Explicit LangGraph orchestration** — only when durable memory, HITL interrupts, or multi-mode
   coordination outgrow `create_agent`.
7. **Caching and model tiering** — latency/cost optimization after behavior is stable.
8. **Multimodal slide questions** — only with a clear grounded-citation path.
9. **Cohort rollout hardening** — per-user cost caps, account lifecycle, and admin operations beyond
   the minimal login/account-creation gate.
10. **Flashcards / mind-map artifacts** — generated only from cited spans.
11. **GraphRAG** — course knowledge graph if the single-retriever contract shows a measured recall gap.

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
- **Demo artifact privacy.** Local/private demo trace cards may show decision basis and labeled
  action/band status, but raw trace JSON, generated screenshots, generated DOCX packets, secrets, and
  unreviewed corpus-bearing captures stay in ignored local paths such as `localdocs/` or `tmp/`.
- **LangGraph scope.** Direct graph/checkpointer/store imports are future architecture. They need a
  written delta against the current `create_agent` boundary before code.

## Cut Order If Slipping

voice -> explicit LangGraph -> memory hardening -> admin upload -> multimodal -> flashcards ->
caching -> track-aware retrieval -> interview -> **never the grounded teach loop** -> **never the
refusal / eval / trace path**.
