# Roadmap

Everything is kept; only the Thursday MVP is committed; pull-ins land by priority as time allows. A
shippable demo must exist at every step ("demo cannot fail").

## NOW — Thursday MVP (committed, MUST)

The adaptive **teach loop**:

> intake (topic · style · track) → retrieve grounded span (slides/handouts first) → explain in style → check understanding →
> grade grounded → **runtime decide** (advance / re-explain-differently / drill / refuse+escalate) →
> update the within-session learner profile → loop → session report.

**MUST ship:**

- A **runtime-decision trace** with real branches (the agenticity proof).
- Grounded explanations + **constrained one-span citations**.
- **Real-signal refusal** + at least **one recovered tool failure on camera**.
- A **human-escalation** path (the review-queue card).
- **Item-quality eval** on a **held-out chat-question** test set, with honest on-screen numbers.
- One persona, end-to-end, in under the target time.

**Build order.** Foundation adapter first, then eval scaffolding — `split_eval.py` +
`eval/split_manifest.json` + `check_eval_leak.py` must exist and pass **before any prompt template is
written** (else "the test set is sacred" is unenforceable). **Wednesday checkpoint:** if the teach loop
isn't demoable on *real* retrieval by end of Wednesday, cut every pull-in and harden the refusal path
instead — a working refusal + one re-explain branch beats a full stack with no second pass.

## PULL-IN (if time, in priority order — SHOULD)

1. **Quiz mode** — adaptive MCQ, deterministic grading
2. **Mock-interview mode** — open-answer grounded grading + follow-up probing
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
- **Scope vs. one week.** Teach loop committed; everything else is a pull-in. **Don't start a pull-in
  until the MVP demos end-to-end.**

## Cut order if slipping (cut from the left; never cut the last two)

voice → admin upload → multimodal → flashcards → caching → track-aware retrieval → interview → quiz →
**never** the grounded **teach loop** → **never** the **refusal / eval / trace** path.
