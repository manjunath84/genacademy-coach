# Two-Day Score-Lift Plan

Status: proposed next build sequence for the final two days before demo. This plan reflects the
second-opinion strategy review after PR #10 and keeps the held-out `test` split untouched.

## Goal

Improve the Week 3 submission score without destabilizing the shipped grounded tutor. The current
merged-main baseline is already demoable:

- Teach-loop MVP is merged, reviewed, and live-verified.
- Final dev eval is `7/10` overall and `7/8` teachable.
- Two non-passing scenarios are safe low-retrieval refusals.
- One teachable scenario has a remaining deterministic `grade_not_correct` diagnostic.

The score-lift strategy is to raise the floor first, then add one visible pull-in.

## Ranking

| Rank | Move | Score lift | Risk | Why |
|---|---|---|---|---|
| 1 | Fix the remaining `grade_not_correct` diagnostic | High | Low | Could move teachable dev evidence from `7/8` to `8/8` without adding scope. |
| 2 | Same-topic lens-switch demo | High | Very low | Makes "adaptive" visible using the existing engine: same concept, different teaching lenses. |
| 3 | Grounded Quiz Mode | High | Low/medium | Adds a real second mode while reusing retrieval, citations, refusal, and deterministic grading. |
| 4 | Mock interview | Highest ceiling | High | Strong agentic story, but open-answer grading and follow-up probing are risky in two days. Stretch only. |

## Recommended Sequence

### Day 1 Morning: Raise the Floor

1. Diagnose and fix the remaining `grade_not_correct` dev failure.
2. Rerun the redacted dev eval on `--split dev --limit 10`.
3. Keep the two safe low-retrieval refusals framed as the refusal path working, not as product misses.

Acceptance:

- Dev eval remains redacted.
- Held-out `test` split remains untouched.
- If the fix works, teachable evidence should be `8/8`.
- If the fix does not land cleanly, keep the `7/8` teachable baseline and explain the remaining
  diagnostic directly in the demo.

### Day 1 Midday: Polish Adaptivity

1. Add a repeatable same-topic lens-switch demo.
2. Show the same concept through `low_code_no_code` and `code_heavy` teaching lenses.
3. Capture trace metadata that proves the model still uses grounded evidence.

Acceptance:

- The demo uses the existing teach-loop engine.
- No new corpus tagging or track-aware retriever is required.
- The artifact is easy to show in the video.

### Day 1 Afternoon: Pull In Quiz Mode

Build only the smallest grounded quiz slice:

- CLI: `scripts/run_quiz_demo.py`
- Reuse the existing foundation/retrieval/citation types.
- Generate 3 cited multiple-choice questions from retrieved spans.
- Grade deterministically.
- Refuse if retrieval is below threshold.
- Write a local quiz trace.
- Add focused tests for question shape, grading, and refusal.
- Update README, roadmap, and demo docs.

Quiz Mode still needs its own approved implementation plan and fresh-context review before code
per AGENTS sections 2 and 8; this sequencing doc is not build approval.

Hard stop:

- If quiz is not green and stable by end of Day 1, cut it from the live demo and keep it as a
  documented stretch.

### Day 2: Package, Then Stretch Only If Clean

1. If Day 1 is clean, consider a tightly timeboxed mock-interview prototype.
2. If mock interview is not green by noon, cut it.
3. Spend the afternoon on the 5-minute video and Google Doc.

## Avoid In This Window

- Voice: high integration risk and weak proof of the core tutor.
- Cross-session memory: too much state and too hard to show reliably in five minutes.
- GraphRAG: conflicts with the current one-retriever discipline and adds infra risk.
- Multimodal: a new modality, not needed for the current score lift.
- Admin upload, caching, cohort rollout, flashcards: useful later, weak demo lift now.

## Review Gate

Every non-trivial implementation PR still needs a different-model or fresh-context review before merge.
Do not use the held-out `test` split for tuning, prompt iteration, demo prep, or pull-in validation.
