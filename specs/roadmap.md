# Roadmap

Status updated: 2026-06-16.

Everything is kept, but only the teach-loop MVP is on the critical path. Pull-ins land by priority after
the grounded teach loop, eval, refusal path, and trace are demonstrably working. A shippable demo must
exist at every step ("demo cannot fail").

## Status Snapshot

### Done

- **Week-2 foundation reuse locked.** `docs/genacademy-rag-foundation.md` records the reuse contract;
  the Coach uses the Week-2 embedder, Chroma store/schema, chunking pipeline, provider boundary, and
  eval patterns instead of rebuilding them.
- **Corpus and eval safety scaffold shipped.** The local corpus layout, deterministic eval split
  manifest, and `scripts/check_eval_leak.py` are in place. Private corpus and generated eval artifacts
  stay gitignored; the held-out `test` split remains frozen and is not used for tuning.
- **Foundation adapter shipped.** Coach settings, source-priority ordering, retrieval over-fetching,
  citation-preserving span selection, and ingest/retrieval smoke tests are implemented.
- **Teach-loop MVP core shipped.** The text-first teach session supports grounded retrieval, one-span
  citations, learner-profile state, model-chosen `next_action`/strategy, re-explain on stumble, refusal
  and escalation, trace writing, and a CLI demo path.
- **Teach-loop eval shipped.** `scripts/eval_teach_loop.py` runs multi-turn teach-loop scenarios and
  reports redacted pass/fail diagnostics without exposing private eval text.
- **Redacted eval diagnostics shipped.** The eval diagnostics reuse runtime grounding helpers and emit
  only scenario IDs, filenames, counts, scores, source types, next actions, and reason codes.
- **Retrieval triage shipped.** `scripts/diagnose_teach_retrieval.py` showed that raw retrieval returns
  candidates for every dev scenario; the zero-coverage symptom was caused by the initial `0.60` STOP
  threshold filtering spans after retrieval, not by missing ingestion. PR #5 merged this diagnostic and
  the triage report.
- **STOP-threshold calibration completed.** `scripts/calibrate_teach_threshold.py` plus non-private
  negative controls support a calibrated default of `0.40`; the held-out `test` split was not used.
- **Calibration verification completed locally.** Full tests, ruff, diff whitespace check, live dev eval,
  and eval leak guard have been run on the calibration branch.
- **Teach-loop behavior hardening first pass completed.** Session-boundary grading now runs before model
  decisioning, incorrect grounded answers force `re_explain_differently` with a changed strategy, and
  generated check-item rubrics are normalized so their expected answers satisfy deterministic grading.
- **Citation-resolution hardening completed on dev.** Correct-answer turns with citeable evidence no longer
  finish as uncited stop/refusal responses, and later low-confidence retrieval calls no longer erase prior
  citeable evidence inside the same teach session. That branch's live dev eval reached `8/8` teachable
  scenarios before later demo-readiness changes reset the honest merged-main baseline.
- **Demo-ready runtime traces captured locally.** A grounded public-topic run now shows a cited teach turn
  followed by a learner-dependent `re_explain_differently` branch, and an out-of-corpus run shows
  `refuse_escalate` with one idempotent review-queue row.
- **Demo-readiness fallback merged and final merged-main evidence captured.** PR #10 added the
  first-turn grounded fallback and review fixes for action preservation, refusal boundaries,
  citation/check alignment, and scoped locked session-boundary grading. Final merged-main dev eval is
  `7/10` overall and `7/8` teachable: two failures are safe low-retrieval refusals, and one teachable
  scenario had a deterministic grading diagnostic later fixed by the grade-boundary branch. Public-topic
  demo traces show a grounded teach turn followed by a learner-dependent re-explain branch, plus a
  separate grounded refusal path.
- **MVP demo packaging.** The teach-loop engine, refusal path, trace, redacted dev eval, and final
  merged-main numbers are captured in `README.md`, `docs/demo-and-deliverables.md`, and
  `docs/teach-loop-status.md` without using the held-out `test` split.
- **Two-day score-lift strategy selected.** The final two-day plan is documented in
  `docs/two-day-score-lift-plan.md`: start with the grade-boundary diagnostic, polish same-topic lens
  switching second, and pull in grounded Quiz Mode only after the floor is stable.
- **External tutor examples used as scope checks.** Two public AI-tutor examples were used to
  pressure-test the final demo plan without treating them as templates: low-stakes within-session mastery
  framing, deterministic quiz criteria pinned from cited spans, `review_queue.jsonl` plus redacted traces
  as the instructor-review surface, and reproducibility via split manifests/checksums/idempotent ingest.
  Local review notes remain uncommitted under gitignored `tmp/`.
- **Memory options evaluated for roadmap, not implementation.** Cross-session memory remains a
  personalization pull-in, but the recommended sequence is provider-neutral: first consider a tiny
  first-party persisted profile for style/struggle tags, then compare LangMem, Mem0 open source, and Zep
  Cloud under a separate approved plan.
- **Explicit LangGraph evaluated and deferred.** The project already uses LangChain `create_agent` on
  LangGraph's runtime. Direct `langgraph.*` graph/checkpointer/store code is reserved for a future delta
  that proves `create_agent` is no longer enough, such as durable cross-session memory, HITL interrupts,
  or multi-mode orchestration that cannot stay understandable as one agent loop.
- **Same-turn grade-boundary overwrite fixed.** The teach session now preserves the session-boundary
  grade for the learner's current answer even if the agent generates a new check and calls grading again
  in the same turn. Regression tests cover both correct and incorrect boundary grades. Live dev eval shows
  the original `grade_not_correct` scenario now passes; the overall dev score remains `7/10` and `7/8`
  teachable because a different confirm-band scenario escalated before producing the expected re-explain
  trace.
- **Same-topic lens-switch demo captured.** Two live Nebius traces use the same public demo topic and
  learner answer while switching only the teaching lens: `demo-lens-low-code-20260616` and
  `demo-lens-code-heavy-20260616`. Both stay grounded in the confirm band, cite retrieved spans, and
  re-explain after the same wrong answer. The trace artifacts remain gitignored; docs record only
  redacted metadata.
- **Grounded Quiz Mode shipped.** The first pull-in generates up to 3 cited MCQs from retrieved spans,
  grades selected option IDs deterministically in Python, refuses/escalates when retrieval is not
  citeable, and writes a typed redacted quiz trace. Live Nebius trace
  `demo-quiz-agent-harness-reviewfix2-20260616` generated 3 cited questions at `0.711 confirm` evidence and graded
  answers `A,B,C` as `1/3`. The trace stores `topic_hash`, not raw topic or quiz text; the held-out
  `test` split was not used.
- **Submission packaging started.** `docs/submission-packaging-item.md` defines the active packaging
  item, `docs/submission-google-doc-draft.md` turns the demo playbook into a Google-Doc-shaped
  narrative, and `docs/vibe-coding-prompt-appendix.md` packages sanitized prompt examples without
  private corpus/eval text, API keys, or raw generated quiz content.
- **Recording and deployment docs prepared.** `docs/video-demo-script.md` provides the timed recording
  script. `docs/hugging-face-deployment-plan.md` records the Hugging Face Spaces plan, reusing the Week
  2 Docker deployment pattern and the same-embedder deployment contract.
- **Hugging Face deployment shell live-smoked privately.** A thin Gradio/Docker Space wrapper builds
  with CPU-only `torch`, boots locally in Docker, and serves a private Hugging Face Space at
  `https://huggingface.co/spaces/Manjunath84/genacademy-coach` (`HTTP/2 200`). No private corpus/index
  is uploaded; provider/corpus-backed click smoke remains pending. PR review hardening added
  no-factory-reboot-by-default, pinned Week 2 dependency SHA, startup chunk-count warnings, and redacted
  UI error IDs backed by private server tracebacks.

### In Progress

- **Demo packaging after private Space smoke.** The remaining critical path is external Google Doc
  creation/import, video recording, PR review/merge for the Space wrapper, and deciding whether to make a
  public-safe corpus/index available in the Space. Memory is intentionally held as a later
  personalization pull-in because it adds persistence/privacy surface and must not become a hidden
  source of course facts. Explicit LangGraph remains deferred for the same reason: useful for durable
  memory later, unnecessary for the two-day demo.

### Pending Before MVP Demo

- Keep the held-out `test` split unused until final evaluation/reporting.
- Decide whether to harden the remaining confirm-band refusal variance or explain it in the demo as a
  conservative escalation case.
- If memory is pulled in after the demo floor is green, write a separate implementation plan that compares
  first-party persisted profile, LangMem, Mem0 open source, and Zep Cloud before code.
- If explicit LangGraph is pulled in after memory or HITL earns it, write the delta first and preserve the
  current pure-core / thin-view boundary.
- Record the <=5-minute video from `docs/demo-and-deliverables.md`.
- Create the external Google Doc submission from `docs/submission-google-doc-draft.md`.
- Review and merge the Hugging Face Space wrapper PR; keep the Space private until a public-safe
  corpus/index decision is made.
- Flip the repo public at submission time if required.

## Teach-Loop MVP

The adaptive **teach loop**:

> intake (topic · style · track lens) → retrieve grounded span (slides/handouts first) → explain in
> style → check understanding → grade grounded → **runtime decide** (advance / re-explain-differently /
> drill / refuse+escalate) → update the within-session learner profile → loop → session report.

**MUST ship:**

- [x] A **runtime-decision trace** with real branches (the agenticity proof).
- [x] Grounded explanations + **constrained one-span citations**.
- [x] **Real-signal refusal** driven by retrieval score plus citation presence.
- [x] A **human-escalation** path via the review queue.
- [x] **Item-quality eval** on seed/dev chat-question scenarios, with redacted diagnostics.
- [x] Calibrated STOP threshold against seed/dev positives plus non-private negative controls.
- [x] One learner session, end-to-end, in under the target time; optional same-topic lens switch for the
  demo.
- [x] Final honest on-screen numbers captured from merged `main`; held-out `test` split remains untouched
  until final evaluation.

**Build order status.** Foundation adapter, eval scaffolding, leak guard, teach-loop core, eval
diagnostics, retrieval triage, threshold calibration, behavior hardening, citation-resolution hardening,
same-topic lens switching, and grounded Quiz Mode are complete on the dev/demo path. Demo trace capture,
honest dev-eval reporting, and repo demo/readme packaging are complete on merged `main`; the active gate
is final video/doc packaging. The held-out `test` split stays untouched until final evaluation.

## PULL-IN (if time, in priority order — SHOULD)

**Two-day priority.** Do not pull in features straight down this list blindly. For the final demo window,
the chosen order is: stabilize teachable eval -> lens-switch demo -> grounded Quiz Mode. Mock interview
is a Day-2 stretch only if quiz is already green.

1. **Quiz mode** — shipped first pull-in: cited MCQ generation + deterministic grading
2. **Mock-interview mode** — open-answer grounded grading + follow-up probing + cited gap report
3. **Admin upload** — low-priority pull-in for admin-authored docs/quiz questions, reusing Week-2 auth/upload
4. **ElevenLabs voice** — voice over the same text engine; text transcript remains the source of truth
5. **Track-aware retrieval** — corpus tagged by track
6. **Cross-session memory** — evaluate first-party persisted profile, LangMem, Mem0 open source, and Zep
   Cloud; memory may personalize style/struggle history, but course facts still require citations
7. **Explicit LangGraph orchestration** — only when durable memory, HITL interrupts, or multi-mode
   coordination outgrow `create_agent`
8. **Caching (L1/L4/L5) + model tiering**
9. **Multimodal slide questions**
10. **Cohort rollout** — multi-user / auth / per-user cost caps
11. **Flashcards / mind-map artifacts**
12. **GraphRAG** (course knowledge graph)

## NORTH STAR (not this week)

A full adaptive tutor that teaches + tests + interviews + **remembers you across sessions** + adapts to
style + per-track + voice/multimodal, deployed to the cohort.

## Risk caps

- **Corpus — own/local content, no publishing.** Primary corpus = local `corpus/notes`, `corpus/slides`,
  `corpus/handouts`, and `corpus/transcripts`, chunked with Week-2 machinery. Slides and handouts are
  prioritized for teaching; transcripts are support/fallback. Private corpus content remains local and
  gitignored.
- **Eval contamination.** Hard-split before any use; the **test** split is frozen and never enters
  prompts/examples/demos.
- **"Is it really an agent?"** Mitigated by the runtime-decision trace — the re-explain / refuse branches
  are learner-dependent, not scripted.
- **Threshold tuning.** Tune only on seed/dev plus non-private negative controls. Do not use the held-out
  `test` split for calibration.
- **Scope vs. one week.** Teach loop is the committed MVP; everything else is a pull-in. **Don't start a
  pull-in until the MVP demos end-to-end.**
- **Memory privacy.** Cross-session memory can store learner preferences and struggle patterns, not raw
  private corpus/eval text or uncited course claims. Provider-backed memory needs an explicit privacy and
  deletion story before implementation.
- **LangGraph scope.** Direct graph/checkpointer/store imports are future architecture, not demo polish.
  They need a written delta against the current `create_agent` boundary before code.

## Cut order if slipping (cut from the left; never cut the last two)

voice → explicit LangGraph → cross-session memory → admin upload → multimodal → flashcards → caching → track-aware retrieval → interview → quiz →
**never** the grounded **teach loop** → **never** the **refusal / eval / trace** path.
