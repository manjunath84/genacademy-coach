# Architecture Pitch — Spoken Script (modular)

**Source spec:** `docs/superpowers/specs/2026-07-04-architecture-pitch-design.md`
**Numbers:** all figures from `docs/week4-eval-dashboard-data.json` (dataset `2026-06-24-plan1`,
snapshot 2026-06-25, mean of three current-main runs).
**How to use:** M0 alone = 90-second cut. M0+M1+M2 ≈ 5 minutes. All modules + Q&A ammo ≈ 10
minutes. Never rewrite a module to fit time — drop whole modules instead.

---

## M0 — the core (deliver verbatim, ≤ 95 seconds)

<!-- M0-START -->
Every learner in this cohort has done this: to understand one concept you open the slides, scrub
the session recording, and search the handout — three tabs, zero provenance. GenAcademy Coach
replaces that with one grounded tutor: ask it anything from the course and it teaches, with the
exact slide, transcript, and handout evidence beside the answer.

Here is the architecture in one picture. The agent has freedom in the middle and gates at the
edges.

Gate one — deterministic intake. One retrieval per turn over the tagged corpus, slides and
handouts first. An evidence score maps to a band: below 0.40 the system stops, and the model
never gets a vote. Citations are captured right here, at retrieval — never reconstructed from the
answer.

The middle — the teaching brain. This is where the model is genuinely agentic: it picks the
teaching move — explain, step-by-step, quiz, re-explain differently — and the explanation lens —
low-code, code-heavy, or bridge. Every choice is logged, per turn.

Gate two — projection. The evidence panel and next-step suggestions are projections of that same
single retrieval, so the answer and its evidence can never disagree, and the system never
suggests something it would refuse.

And the number that gates release: refusal recall on adversarial questions — 1.000 every run. If it cannot cite the course, it refuses and hands you to a mentor. That is the
product.
<!-- M0-END -->

---

## M1 — agentic features (adds ~90 seconds)

What does the agent actually decide? Six teaching moves, three lenses, the re-explain strategy
after a failed check — analogy, simpler steps, or a contrastive example — and which check-question
to ask. Across turns it adapts through the session profile: what you know, where you struggled.

Why is that autonomy and not a workflow? Because the path is chosen at runtime from observations —
grade results and struggle signals — not from a fixed script. Two learners asking the same
question take different paths.

And there is a receipt. Every choice is logged per turn — today's shipped UI shows it as
decision-trace cards, and the Phase-1 workspace surfaces it as a "behind this answer" disclosure.
Our trajectory eval scores the *chosen action*, not just the final prose.

Where does this go next? The Personal Coach direction is the same sandwich at multi-agent scale:
interviewer, evaluator, coach, and curriculum-planner agents behind a deterministic orchestrator —
and the study planner follows one rule: the LLM proposes, a deterministic scheduler validates and
repairs. Feasible, or flag. One pattern at every layer. That's scoped, not built — and it slots
into the same grounded core.

## M2 — eval receipts (adds ~90 seconds)

How do we know any of this works? A frozen, hand-labeled golden set: forty cases — sixteen happy,
nine edge, five known-failure, ten adversarial — frozen before the improvement work, with the
held-out test split never indexed; a leak-check script enforces that. Three evaluator types:
deterministic code checks, trajectory eval on the agent's path, and human review. Pass bars were
fixed at design time — never reverse-engineered to pass.

The wins: citation F1 went 0.444 to 0.594 — up 0.150, clearing our 0.50 floor, still honest about
the 0.90 bar. Turn p95 latency went 11.33 seconds to 8.28 — 27 percent faster. Refusal recall and
retrieval recall held at 1.000.

The misses — and we publish these: refusal precision moved 0.833 to 0.791, and task completion
went from 94.7 percent on the infra-excluded baseline to 93.3 percent mean over all forty cases.
Cause analysis is on the dashboard: over-conservative refusals, three named cases.

And my favorite: we almost shipped a citation fallback predicted to gain up to 0.20 of citation
F1. Measured: minus 0.044, and task completion down 5.2 points. It was rejected. The eval was our
debugger.

## M3 — scale + close (adds ~60 seconds)

Status, honestly, in three states. Built and evaluated: the grounded engine — teach loop, quiz,
skill-gap diagnosis, escalation, tracing, the eval harness and public dashboard. The build slice
for this week's demo: the Tutor Workspace — evidence panel with real slide images and next-step
suggestions, design merged after independent second-model review. Scoped into the same core:
voice tutoring, a current-docs lane, controlled ingestion, cohort access, progress analytics, and
the Personal Coach. Every layer ships through the same gates: grounded-or-refuse, privacy review,
evals before release.

## Q&A ammo (one line each — 10-minute cut / prep)

| Likely question | Answer |
|---|---|
| Why not fine-tune? | Corpus changes weekly; retrieval + citations give provenance fine-tuning can't. Design choice: a 30B open model (Qwen3-30B via Nebius) with strong deterministic scaffolding — the receipts are the point, not model size. |
| How do you know citations are real? | Captured at retrieval, never reconstructed; faithfulness measured as F1; the Phase-1 panel renders only cited spans. |
| Isn't refusal recall 1.000 just refusing everything? | That's why refusal *precision* is its balancing pair — 0.791, a disclosed miss with named cases. |
| What stops hallucinated suggestions? | Chips carry corpus anchors validated before render; stale chips are dropped, never allowed to bypass refusal. |
| Why multi-agent for the Personal Coach? | Interviewer, evaluator, and coach have conflicting objectives in one prompt; role separation under a deterministic orchestrator is the same sandwich pattern. |
| Cost / latency? | ~$0.14 per full 40-case eval run (current reference, runs 2/3 only — baseline pricing env was unset); case p95 ~21.96s; turn p95 8.28s — inside the 10s production alert SLA; five production monitoring signals with alert thresholds defined. |
