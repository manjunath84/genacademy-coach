# Breakout Submission & Personal Coach Ideation — Session Context & Decision Log

**Date range:** 2026-07-04 (submission deadline 2026-07-05; demo days 2026-07-11/12)
**Purpose:** durable context for the session that produced the breakout-handout submission package
(PRs #62–#65), the filled team handout, and the Personal Coach ideation — so any future session (or a
second-model reviewer) can pick up without re-deriving the reasoning. Continues
`docs/coach-v2-workspace-session-context.md` (the 2026-06-30 → 07-04 workspace-design arc).

## 1. Decision timeline

1. **PR #61 merged** — the Tutor Workspace design baseline (PRD FR-1..FR-W11, architecture spec,
   FR-W10 chips design, mockups) locked onto `main`.
2. **Handout content as a versioned artifact (PR #62).** The team breakout handout `.docx` lives
   outside the repo (it carries team names/emails — never committed). Its content now has a
   privacy-clean, reviewed paste source: `docs/breakout-handout-content.md`, sections mapped to the
   handout cells (Q1 use case · Q2 knowledge/tools · Q3 autonomy/evals · section-4 project write-up).
   Codex content review (fact-check table, 15 claims) caught **two real factual errors** — corpus
   "recordings" → **transcripts** (matches the ingestion contract), and Phase-1 mis-stated as
   "Week-1 corpus" → **current index + curated Week-1 demo path** — plus a standalone-reading fix
   (tools list labeled "shipped core + Phase-1 design"). Re-review: approve, all fixes verified.
3. **Docx filled mechanically.** Backup taken first; an append-only script filled the four cells from
   the merged content (markdown → Word runs), leaving the team table and any pre-existing cell text
   untouched; results render-verified via headless PDF.
4. **Personal Coach ideation (owner-driven, adopted as direction).** Two brainstorms fused into one
   future phase family:
   - **Mastery Loop:** interview → gap map → gap-driven flash cards (extractive-only) → drills →
     mastery levels → harder re-interview. Multi-agent teaching value: interviewer / evaluator /
     coach / curriculum-planner roles behind a deterministic orchestrator ("sentiment" reframed as
     evidence-bound confidence/fluency signals; model judgment stays behind the AD-13 ladder).
   - **Study Planner:** placement assessment (MCQ sweep + targeted interview) → skill-gap map →
     personalized plan. Core pattern: **LLM proposes, deterministic scheduler validates/repairs**
     (prereqs, time arithmetic, spaced review, chunking). Plan thesis: **"feasible or flag"** — the
     plan-level analogue of grounded-or-refuse (never silently over-schedule). Three modes:
     agent-planned / co-planned with locked user edits / fully manual. Bounded replanning only.
   - Placement: gated phase after Workspace Phase 1 + the roadmap's refusal-precision work; needs its
     own plan + privacy review per AGENTS §5. Design addendum PR **queued, not yet written**. Every
     plan/chip-style item must carry a corpus anchor ("never schedule what you can't teach").
5. **Full-vision reframe (PR #63, owner call).** The handout should present the whole system as one
   design, without a "later phases" list. Status paragraph became three states: **Built & evaluated /
   Build slice for this week's demo / Scoped, slotting into the same grounded core**, closing on the
   gates line. Codex blocking finding applied: **"Designed" → "Scoped"** for not-yet-specced items
   (Personal Coach presented as direction/concept); "In build this week" → "Build slice for this
   week's demo". Kept deliberately (rationale on PR): the learner-pain sentence about scrubbing
   session recordings describes learner behavior, not corpus ingestion.
6. **Thesis vision sentence (PR #64, owner call).** The thesis now announces the ambition up front:
   "One grounded core, **scoped to grow** into the full platform: voice tutoring, current-docs
   awareness, controlled content ingestion, cohort access, progress analytics, and a Personal
   Coach…" — headline level only; the status block keeps the honesty detail. Codex: approve, zero
   blocking; optional nit (thesis "direction" wording) skipped with recorded rationale.
7. **MCQ/quiz mentions (PR #65, owner call).** Quizzes/MCQs added to both Personal Coach mentions,
   phrased as **reuse of the shipped quiz engine** (Built & evaluated bucket) — no new-capability
   overclaim, and it strengthens the architecture-reuse story. Codex: approve, zero findings, with
   the reuse claim source-verified (`quiz_items.py`, `quiz_types.py`, roadmap).
8. **Docx patched surgically after each merge** — in-place paragraph swaps (status block, thesis,
   scoped bucket) touching only this session's own appended text; each patch render-verified.
9. **Team email drafted** (two teammates): deadline heads-up, Q1-shortlist recap, submit-today plan,
   objections-today window, build/demo invite for July 11/12. Teammate names/emails stay out of the
   repo.
10. **Ops learning (Codex CLI):** `codex exec` in a background shell blocks forever on open stdin
    ("Reading additional input from stdin…") — always launch with stdin closed (`</dev/null`).

## 2. Artifact map

| Artifact | Path | State (2026-07-04) |
|---|---|---|
| Handout paste source (Q1/Q2/Q3/§4) | `docs/breakout-handout-content.md` | merged via PRs #62–#65, five Codex passes total |
| Team handout (submission file) | outside the repo (carries team emails) | filled + thrice patched, render-verified, submit-ready; pre-fill backup alongside |
| Fill/patch scripts + review prompts/outputs | `tmp/` | gitignored, one-off operational |
| Workspace-arc context log | `docs/coach-v2-workspace-session-context.md` | loose-ends section trued up in this PR |
| This context log | `docs/breakout-submission-session-context.md` | this PR |

## 3. Guardrails exercised this session

- **Falsifiability as the review bar:** every handout claim had to survive "could a demo-day reviewer
  disprove this from the repo?" — two claims failed and were fixed before submission.
- **Status-language discipline:** built ≠ in-build ≠ scoped; "Scoped" is the honest word for
  brainstorm-level items; reuse of shipped capability is stated as reuse.
- **Privacy boundary:** team names/emails and corpus filenames never enter the repo; the submission
  `.docx` is the only artifact carrying personal data and stays outside version control.
- **Builder ≠ reviewer, recorded:** every PR carries the Codex review + resolution (or
  skip-with-rationale) as comments.

## 4. Loose ends

- **Owner submits** the handout (deadline 2026-07-05) and sends the team email.
- **Phase-1 build not started:** next step is `writing-plans` for the Tutor Workspace slice, then
  build + demo prep (architecture one-pager; curated Week-1 demo path; optional Personal Coach
  mockups) for July 11/12.
- **Personal Coach design addendum PR** — queued (loop spec, planner propose-validate-repair,
  factor model, privacy rules, phase gate, learning-objectives map).
- **PR #58** — earlier session context carried it as "open with one unaddressed finding"; that was
  stale: it merged 2026-06-29 ("Document evidence-bound grading guardrails"). Corrected after the
  Codex record-accuracy review of this log caught the claim against git history.
- Handout template's own footer says demo "July 12 to 13" while its body says July 11th/12th —
  template-internal inconsistency, not ours to fix.
