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

### In Progress

- **Teach-loop behavior hardening.** Live dev eval at the calibrated `0.40` threshold improved coverage
  to `8/10` scenarios with spans and `3/10` overall pass rate. The current bottleneck is no longer
  retrieval coverage; it is grading, strategy-change, and runtime-decision trace behavior on recovered
  teachable scenarios.

### Pending Before MVP Demo

- Get a fresh different-model review of the threshold-calibration change before merge.
- Merge calibration only if the grounded/refusal behavior remains safe.
- Capture a demo-ready runtime-decision trace showing at least one grounded teach path and one refusal or
  re-explain branch.
- Keep the held-out `test` split unused until final evaluation/reporting.

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
- [ ] One learner session, end-to-end, in under the target time; optional same-topic lens switch for the
  demo.
- [ ] Final honest on-screen numbers; held-out `test` split remains untouched until final evaluation.

**Build order status.** Foundation adapter, eval scaffolding, leak guard, teach-loop core, eval
diagnostics, retrieval triage, and threshold calibration are complete. The active gate is teach-loop
behavior hardening on recovered teachable scenarios. If behavior hardening does not produce a demoable
path, cut every pull-in and harden refusal plus one re-explain branch.

## PULL-IN (if time, in priority order — SHOULD)

1. **Quiz mode** — adaptive MCQ, deterministic grading
2. **Mock-interview mode** — open-answer grounded grading + follow-up probing + cited gap report
3. **Admin upload** — low-priority pull-in for admin-authored docs/quiz questions, reusing Week-2 auth/upload
4. **ElevenLabs voice** — voice over the same text engine; text transcript remains the source of truth
5. **Track-aware retrieval** — corpus tagged by track
6. **Cross-session memory** — Mem0 (semantic + episodic): "remembers you across days"
7. **Caching (L1/L4/L5) + model tiering**
8. **Multimodal slide questions**
9. **Cohort rollout** — multi-user / auth / per-user cost caps
10. **Flashcards / mind-map artifacts**
11. **GraphRAG** (course knowledge graph)

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

## Cut order if slipping (cut from the left; never cut the last two)

voice → admin upload → multimodal → flashcards → caching → track-aware retrieval → interview → quiz →
**never** the grounded **teach loop** → **never** the **refusal / eval / trace** path.
