# Week 3 Demo Recording Script

> Target: <=5 minutes. Use this as the spoken script and screen checklist. Do not show raw corpus text,
> private eval questions, `.env`, API keys, or full trace payloads on screen.

## Pre-Recording Setup

1. Open the repo root in the terminal.
2. Keep one editor tab open with `docs/demo-and-deliverables.md`.
3. Keep one editor tab open with `specs/roadmap.md`.
4. Keep trace output views narrow enough to show metadata only: `next_action`, `strategy`,
   `evidence_score`, `evidence_band`, `citation_ids`, `faithfulness_ok`, `refusal_reason`.
5. Do not run `--split test`.

Recommended terminal environment:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40
```

## Shot List

| Time | Screen | Say |
|---|---|---|
| 0:00-0:20 | README title + one-line status | "This is GenAcademy Coach: a grounded adaptive tutor built on my Week 2 RAG system. The core promise is simple: it teaches from cited course evidence, adapts when the learner stumbles, and refuses when it cannot cite." |
| 0:20-0:45 | `specs/roadmap.md` cut list | "The first decision was scope. I cut memory, voice, admin UI, explicit LangGraph, and mock interview until the grounded teach loop worked end-to-end. That kept the demo from becoming a pile of half-features." |
| 0:45-2:05 | Teach demo command + redacted trace metadata | "Here the learner asks about a public demo topic. The tutor retrieves course evidence, explains, asks a grounded check, and then reacts to the learner's wrong answer. The key evidence is the runtime trace: the model chooses `drill` first, then `re_explain_differently`; Python only enforces grounding and safety." |
| 2:05-2:45 | Refusal command + review queue row count | "The failure path is load-bearing. For an out-of-corpus topic, the system does not invent an answer. Retrieval evidence is `stop`, the tutor refuses, and it writes one mentor-review queue row." |
| 2:45-3:25 | Dev eval status doc | "I did not use the held-out test split for tuning or demo prep. The redacted dev eval is `7/10` overall and `7/8` teachable. Two failures are safe refusals. The remaining teachable variance is a conservative escalation case, not a hallucination." |
| 3:25-4:10 | Same-topic lens-switch metadata | "To show personalization without risky memory, I used controlled contrast: same topic, same learner answer, different teaching lens. The grounding metadata stays stable; the explanation shown live changes by lens." |
| 4:10-4:45 | Quiz Mode command + redacted quiz trace metadata | "Quiz Mode is the first pull-in, not the agenticity proof. The model generates cited MCQs from retrieved spans, but Python owns the answer key and deterministic grading. The trace stores only `topic_hash`, IDs, scores, booleans, and actions." |
| 4:45-5:00 | `docs/submission-google-doc-draft.md` or roadmap | "The next steps are submission packaging, then future pull-ins: memory, mock interview, or deployment polish. The main learning was to raise the floor before adding new surfaces." |

## Commands To Run Or Show

Grounded teach loop:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_teach_demo.py \
    --session-id demo-grounded-main-final-20260616 \
    --topic "agent harness" \
    --style analogy \
    --track-lens code_heavy \
    --learner-answer "It is just one prompt with no tool checks or feedback."
```

Refusal path:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_teach_demo.py \
    --session-id demo-refusal-main-final-20260616 \
    --topic "Gen Academy cafeteria menu" \
    --style concise \
    --track-lens low_code_no_code
```

Same-topic lens switch:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_teach_demo.py \
    --session-id demo-lens-low-code-20260616 \
    --topic "agent harness" \
    --style analogy \
    --track-lens low_code_no_code \
    --learner-answer "It is just one prompt with no tool checks or feedback."

GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_teach_demo.py \
    --session-id demo-lens-code-heavy-20260616 \
    --topic "agent harness" \
    --style analogy \
    --track-lens code_heavy \
    --learner-answer "It is just one prompt with no tool checks or feedback."
```

Grounded quiz:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_quiz_demo.py \
    --session-id demo-quiz-agent-harness-reviewfix2-20260616 \
    --topic "agent harness" \
    --question-count 3 \
    --answers A,B,C
```

Leak guard to show if time:

```bash
uv run python scripts/check_eval_leak.py
```

## Evidence To Show, Not Read Aloud Fully

- `docs/teach-loop-status.md` for redacted eval and live-trace metadata.
- `docs/demo-and-deliverables.md` for the evidence table.
- `docs/build-learnings.md` for the "what changed my mind" section.
- `docs/submission-google-doc-draft.md` for the written submission.

## Redaction Rules During Recording

- OK to show: file names, scenario counts, scores, bands, action names, strategy names, citation IDs,
  booleans, selected option IDs, and pass/fail counts.
- Do not show: raw corpus spans, private eval questions, generated quiz question text, option text,
  expected answers, rationales, keywords, `.env`, API keys, or full trace payloads.

## Fallback If A Live Nebius Call Is Slow

Use the already-captured evidence in `docs/teach-loop-status.md` and
`docs/demo-and-deliverables.md`. Say:

> "These are the same commands I ran locally. The trace files are gitignored for privacy, so I am showing
> the committed redacted metadata instead of raw trace text."

This keeps the demo honest without risking a stalled live model call during recording.
