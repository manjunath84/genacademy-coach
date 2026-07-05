# Architecture Pitch Design — July 11/12 Demo Days

**Date:** 2026-07-04
**Status:** design (no artifacts built yet — this spec gates the build)
**Grounded in:** the merged Tutor Workspace design package (PR #61), `docs/architecture-diagrams.md`
(shipped-system map), and `docs/week4-eval-dashboard-data.json` (all quoted numbers).

## 1. Goal & constraints

One pitch package for the July 11/12 demo days that makes two stories land: **the agentic-features
story** (what the agent genuinely decides, and why that is autonomy rather than a workflow) and
**the evaluation story** (bars set before runs, deltas published including misses). The slot format
is unknown, so the pitch is **modular**: a 90-second core that expands to ~5 or ~10 minutes by
adding modules, never by rewriting.

Constraints:
- **Public-safe by construction.** Every artifact ships in the public repo: synthetic content only,
  numbers only from the committed dashboard JSON, no corpus text, no team personal data.
- **Falsifiable.** Every claim must survive "could a reviewer disprove this from the repo?" —
  built vs design-merged vs scoped stays explicit (same three-state discipline as the handout).
- **Demo-adjacent.** The pitch flow mirrors the live demo turn, so the audience sees the diagram
  they just watched happen.

## 2. Chosen shape (and what was rejected)

**Chosen: "one turn, two brains" — turn anatomy as the spine.** The whole pitch walks a single
learner turn through the system; the agentic/deterministic split is the visual backbone. The eval
module pairs each guardrail with the metric that proves it (borrowed from the rejected
"guardrail tour" shape), and the close borrows the classic roadmap beat.

Rejected as primary shapes:
- *Guardrail tour* (invariants-first): maximal rigor, but reads like a compliance talk and
  demotes the agentic story.
- *Three-act product story*: familiar but generic; the split becomes one slide instead of the pitch.

**Thesis line (repeated verbatim in every cut):**
> "The agent has freedom in the middle and gates at the edges."

## 3. The sandwich flow (centerpiece diagram content)

One learner turn, three horizontal bands plus a refusal branch and a next-turn loop. Content spec
for the one-pager (rendering follows the mockup theme):

**Band 1 — deterministic intake (system's call; model cannot override):**
1. One source-prioritized retrieval — slides/handouts lead via source-priority ordering (shipped).
   Strict week/session/source filters ("never silently widened") are a PRD/Phase-1 requirement and
   carry the build-slice tag on the one-pager.
2. Evidence score → band: STOP < 0.40 · CONFIRM 0.40–0.85 · PROCEED > 0.85 (shipped).
3. Citations captured at retrieval — never reconstructed from the answer (shipped); role-keying
   per answer part arrives with the panel (Phase-1).

**Band 2 — teaching brain (agent's call; every choice logged per turn):**
4. Teaching move: explain / step-by-step / clarify / quiz / re-explain / refuse+escalate.
5. Explanation lens: low-code / code-heavy / bridge.
6. Grounded check-question generated from a cited span.

**Band 3 — deterministic projection:**
7. *(Phase-1 build slice — design merged, not built)* Panel = projection of the *same* retrieval:
   cited spans by lane + the real slide image (answer and evidence can never disagree — no second
   search).
8. *(Phase-1 build slice)* Next-step chips, corpus-anchored only ("never suggest what you'd
   refuse").
9. *(shipped)* Trace + eval capture → the dashboard numbers.

**Refusal branch (from the STOP band):** refuse + mentor escalation + recovery chips routing back
into the corpus. Caption: "refusal is a feature with its own metric, not an error page."

**Next-turn loop:** deterministic grade of the learner's check-answer updates `known[]`/`struggled[]`;
the agent *observes* that and may choose re-explain-differently (analogy / simpler steps /
contrastive). This loop is the autonomy evidence: same question, different learners, different paths.

Module mapping shown as small print per band (grounding.py · teach_agent.py · semantic_grading.py ·
escalation.py · trace.py). Bands 1–2, the refusal branch, and trace/eval capture map to shipped
modules; the panel, chips, and strict filters carry a visible build-slice tag. The one-pager uses
a two-state legend (● shipped · ◐ Phase-1 build slice) — the handout's three-state honesty, in
diagram form.

## 4. Narrative modules

### M0 — 90-second core (always delivered)
Beat list: (1) problem in one line (four sources, zero provenance → one tutor that shows its
evidence); (2) thesis line + sandwich diagram walk, ~15 seconds per band; (3) the release-gate
line: "refusal recall on adversarial questions is 1.000 — held across every run — and that number
gates release."

### M1 — agentic features (adds ~90s)
Four beats, escalating:
1. **What the agent decides:** six teaching moves, three lenses, re-explain strategy after a miss,
   which check-question to ask; across turns it adapts via the session profile.
2. **Why that's autonomy, not workflow:** the path is chosen at runtime from observations
   (grade results, struggle signals), not from a fixed script.
3. **The receipt:** every choice is logged per turn; today's shipped UI shows it as decision-trace
   cards, and the Phase-1 workspace renames it to the "behind this answer" disclosure (trajectory
   eval scores the *chosen action*, not just the prose).
4. **The scale-out:** the Personal Coach direction is the same sandwich at multi-agent scale —
   interviewer / evaluator / coach / curriculum-planner agents behind a deterministic
   orchestrator; the study planner is "LLM proposes, deterministic scheduler validates and
   repairs — feasible or flag." One pattern at every layer. (Status language: scoped direction.)

### M2 — eval receipts (adds ~90s)
Structure: dataset → evaluator types → bars → deltas → honesty beats.
- Frozen 40-case hand-labeled golden set (16 happy / 9 edge / 5 known-failure / 10 adversarial),
  dataset version frozen before improvement work; held-out test split never indexed (leak-check
  script enforces).
- Three evaluator types: deterministic code checks · trajectory eval (path-level: retrieval, tool
  use, chosen action, citation) · human review.
- Pass bars fixed at design time, never reverse-engineered.
- **Honesty beat 1 (disclosed misses):** refusal precision 0.833 → 0.791 and task completion
  94.7% (infra-excluded baseline, 36/38) → 93.3% (current mean, all 40 cases) moved the wrong
  way; both published with cause analysis (over-conservative refusals — the dominant remaining
  failure mode, 3 cases, all named on the dashboard).
- **Honesty beat 2 (the rejected lever):** a broad citation-fallback was predicted to gain
  +0.10–0.20 citation F1; measured −0.044 *and* −5.2pp task completion → **not shipped**.
  Line: "the eval was our debugger."
- Wins quoted alongside: citation F1 0.444 → 0.594 (+0.150, clears the 0.50 floor, honest about
  the 0.90 bar), turn p95 11.33s → 8.28s (−27%), refusal recall and retrieval recall@5 held at
  1.000.

### M3 — scale + close (adds ~60s)
Three-state status (built & evaluated / build slice this week / scoped into the same core), the
full-platform sentence (voice, current-docs, ingestion, cohort access, analytics, Personal Coach),
closing line: "every layer ships through the same gates: grounded-or-refuse, privacy review,
evals before release."

### Q&A ammo sheet (10-minute cut / prep, one line each)
- *Why not fine-tune?* Corpus changes weekly; retrieval + citations give provenance fine-tuning
  can't. Design choice: a 30B open model (Qwen3-30B via Nebius) with strong deterministic
  scaffolding — the receipts are the point, not model size.
- *How do you know citations are real?* Captured at retrieval, role-keyed; faithfulness measured
  as F1; the panel renders only cited spans.
- *Isn't refusal recall 1.000 just refusing everything?* That's why refusal *precision* is
  tracked as its balancing pair — currently 0.791, a disclosed miss with named cases.
- *What stops hallucinated suggestions?* Chips carry corpus anchors validated before render;
  stale chips are dropped, never allowed to bypass refusal.
- *Why multi-agent for the Personal Coach?* Interviewer, evaluator, and coach have genuinely
  conflicting objectives in one prompt; role separation under a deterministic orchestrator is the
  same sandwich pattern.
- *Cost/latency?* ~$0.14 per full 40-case eval run (current reference, runs 2/3 only — baseline
  cost not comparable, pricing env was unset); case p95 ~21.96s; turn p95 8.28s — inside the
  dashboard's 10s production alert SLA; five production monitoring signals with alert thresholds
  already defined. *(Amended 2026-07-04 after PR #70 review: originally quoted "against a 12s
  bar" — the dashboard JSON does not carry 12s, and the numbers policy binds artifacts to the
  dashboard.)*

## 5. Numbers policy (hard rule)

All quoted figures come from `docs/week4-eval-dashboard-data.json` (dataset `2026-06-24-plan1`,
snapshot 2026-06-25, mean of three current-main runs) and are labeled as that run set. The older
"citation F1 0.45 → 0.6333" figure circulating in earlier material is from a different
measurement and **must not be mixed** into the pitch. If the dashboard regenerates before July 11,
re-pull every number; never hand-edit.

## 6. Artifacts to build (next phase)

| Artifact | Path | Notes |
|---|---|---|
| Architecture one-pager | `docs/assets/pitch/architecture-pitch-onepager.html` + `.png` | Sandwich flow center; receipts strip below; scale-out strip + gates footer. Same visual theme + HTML→PNG pipeline as the workspace mockups (local http.server + Playwright, 1440-wide). |
| Spoken script | `docs/assets/pitch/pitch-script.md` | M0 verbatim (~230 words) + M1–M3 expansion paragraphs + Q&A ammo table. Modular cut marks. |
| Deck skeleton | *deferred* | Only if the format turns out to be a long slot; the one-pager + script cover 90s–10min. |

Acceptance criteria:
1. One-pager renders clean at 1440px; PNG committed; no private content (privacy scan passes).
2. Every number on the one-pager string-matches `week4-eval-dashboard-data.json`.
3. Script reads aloud at ≤ 95 seconds for M0 (timed), each module ≤ 2 minutes.
4. Status language on the one-pager keeps the three-state discipline (built / build slice / scoped).
5. Second-model (Codex) review of the PR before merge — content accuracy + status language +
   privacy scan.

## 7. Out of scope

Product code (Phase-1 Tutor Workspace build is its own plan), new eval work, changes to the
dashboard, the Personal Coach design addendum (separately queued), and any deck build before the
slot format is known.
