# Submission Packaging Item

## What This Item Is

This item packages the already-built GenAcademy Coach work into submission-ready evidence for the Week 3
handout: the external Google Doc, the <=5-minute video, and the prompt/workflow appendix.

It is a documentation and narrative task, not a new product feature. The goal is to make the judging
story easy to follow without changing the tutor runtime.

## Why It Exists Now

After PR #16, the core demo floor is in place:

- Teach Mode works end-to-end with grounded retrieval, learner-dependent re-explanation, refusal, and
  trace evidence.
- Same-topic lens switching is captured as the personalization proof.
- Grounded Quiz Mode is shipped as the first deterministic pull-in.
- The roadmap, status docs, and demo playbook already record redacted evidence.

The remaining submission risk is not code. It is presentation: the evaluator needs to see what was
built, why the scope was chosen, how privacy/eval leakage was avoided, what failed along the way, and
what evidence backs each claim.

## Deliverables

This item creates or updates:

- `docs/submission-google-doc-draft.md` — the Google-Doc-shaped narrative: overview, dataset, prompts,
  architecture, iterations, learnings, evidence, and next steps.
- `docs/vibe-coding-prompt-appendix.md` — sanitized prompt examples and workflow patterns used during
  the build.
- `docs/demo-and-deliverables.md` — the recording script and final deliverables checklist.
- `specs/roadmap.md` — status update showing that submission packaging is now the active step.
- `README.md` — links to the packaged submission docs.

## Inputs

Use only redacted or safe repo artifacts:

- `README.md`
- `docs/demo-and-deliverables.md`
- `docs/teach-loop-status.md`
- `docs/build-learnings.md`
- `docs/architecture-diagrams.md`
- `docs/two-day-score-lift-plan.md`
- `specs/roadmap.md`
- safe trace names, scores, evidence bands, action names, and citation IDs already recorded in docs

Do not paste raw trace text unless it is already a safe redacted metadata surface.

## Guardrails

- Do not include private corpus excerpts.
- Do not include held-out eval questions, checksums, or n-grams.
- Do not include generated quiz question text, option text, expected answers, rationales, or keywords.
- Do not include API keys or `.env` values.
- Do not claim held-out test performance unless the `test` split is explicitly run for final reporting.
- Do not imply Quiz Mode is the agenticity proof; Teach Mode remains the runtime-decision proof.
- Do not make memory or explicit LangGraph sound shipped. They are roadmap items.

## Done Criteria

- The Google Doc draft can be copied into the external submission without needing private repo context.
- The prompt appendix shows the vibe-coding process without exposing private data.
- The video script points to exact local commands and redacted artifacts.
- Roadmap and README point to the new packaging docs.
- `scripts/check_eval_leak.py` passes after the docs are added.
- Markdown links resolve.

## What Comes After

1. Record the <=5-minute video using `docs/demo-and-deliverables.md`.
2. Create the external Google Doc from `docs/submission-google-doc-draft.md`.
3. Keep the repo private until final review, then flip public only if required for submission.
4. After submission, choose the next product plan: memory, mock interview, or the remaining
   confirm-band refusal hardening.
