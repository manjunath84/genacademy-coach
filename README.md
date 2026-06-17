# GenAcademy Coach

An adaptive, grounded **AI tutor** over the Gen Academy cohort corpus. It teaches each learner in their
own style, checks understanding, **re-explains a different way when they stumble**, remembers what they
know and struggled with (within a session), and **refuses to bluff** — it only teaches what it can cite
from the course materials, and escalates the rest to a human mentor.

> **Implementation status:** teach-loop MVP implemented, merged, live Nebius-verified, and reviewed by
> separate Gemini/Claude contexts. The latest dev evidence remains `7/10` on the dev eval and `7/8`
> on teachable scenarios, with two safe low-retrieval refusals. The original same-turn grading overwrite
> is fixed; the remaining live-run variance is a confirm-band refusal/structured-output path. Grounded
> Quiz Mode is also implemented as a deterministic MCQ pull-in. Private corpus files remain local-only;
> only structure, redacted diagnostics, and leak checks are versioned. A private Hugging Face Space
> deployment shell is live-smoked at
> `https://huggingface.co/spaces/Manjunath84/genacademy-coach`; no private corpus/index is uploaded, so
> provider/corpus-backed click smoke remains pending. The Space shows an empty-corpus deployment-shell
> notice rather than presenting safe refusals as a broken demo.

Built as the **Week-3 (The Agentic Leap)** project of the *Mastering Agentic AI* Bootcamp, layered on
the author's Week-2 RAG system (`genacademy-rag` / *GenAcademy Compass*).

## Shipped vs. Roadmap

| Surface | Status | Proof / limit |
|---|---|---|
| Grounded teach loop | **Shipped** | Local CLI + Gradio UI; model chooses `next_action`/strategy while Python enforces grounding, citation, and refusal safety. |
| Refusal + mentor queue | **Shipped** | Out-of-corpus topics refuse/escalate instead of answering from priors; review queue stays local/gitignored. |
| Redacted eval + leak guard | **Shipped** | Latest dev evidence is `7/10` overall and `7/8` teachable on 2026-06-16; held-out `test` split remains unrun. |
| Same-topic lens switch | **Shipped** | Same public topic and learner answer, different teaching lens; grounding metadata stays stable as the control. |
| Grounded Quiz Mode | **Shipped pull-in** | Cited MCQ generation with deterministic Python grading; UI hides generated question text by default for recording. |
| Local Gradio web chat | **Shipped** | Demo-ready local UI and screenshot packet are committed; no public tunnel or private corpus exposure. |
| Hugging Face Space | **Live deployment shell** | Private Space HTTP smoke passed; no private corpus/index uploaded, so grounded click smoke is pending. |
| Skill-Gap Diagnosis | **Planned standout workflow** | Spec drafted only; needs fresh-context review before code. |
| Mock Interview / admin upload / voice / memory | **Roadmap** | Deferred pull-ins; not part of the shipped Week-3 demo. |

## Grader's 5-Minute Path

1. Watch the UI flow from the canonical packet:
   [`docs/demo-walkthrough-with-screenshots.docx`](docs/demo-walkthrough-with-screenshots.docx).
2. Check the redacted trace evidence:
   [`docs/teach-loop-status.md`](docs/teach-loop-status.md) and the screenshot inventory
   [`docs/ui-screenshot-inventory.md`](docs/ui-screenshot-inventory.md).
3. Inspect the dated dev eval artifact:
   [`eval/runs/teach-loop-dev-main-final-20260616.json`](eval/runs/teach-loop-dev-main-final-20260616.json).
4. Run one local grounded teach command:

   ```bash
   GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
     uv run python scripts/run_teach_demo.py \
       --topic "agent harness" \
       --style analogy \
       --track-lens code_heavy \
       --learner-answer "It is just one prompt with no tool checks or feedback."
   ```

5. Open the deployment proof:
   [`https://huggingface.co/spaces/Manjunath84/genacademy-coach`](https://huggingface.co/spaces/Manjunath84/genacademy-coach).
   It is intentionally a live shell until a public-safe corpus subset is approved and uploaded.
6. Read the hardening docs:
   [`docs/grading-gap-audit.md`](docs/grading-gap-audit.md) and
   [`docs/submission-hardening-plan.md`](docs/submission-hardening-plan.md).

## What it is

One agent engine with shipped teach/quiz surfaces and explicit roadmap pull-ins:

- **Teach** *(Thursday MVP)* — explain a concept grounded in the corpus → check understanding →
  re-explain a different way until it clicks.
- **Quiz** *(first pull-in shipped)* — cited MCQ generation with deterministic grading.
- **Skill-Gap Diagnosis** *(planned standout workflow)* — deterministic, cited next-step report from
  teach/quiz traces and review-queue events; spec only until reviewed.
- **Mock interview / admin upload / ElevenLabs voice / cross-session memory** *(roadmap pull-ins)* —
  added only after the text teach loop, refusal path, eval split, and trace are demoable end-to-end.

The differentiator is **personalization** (never the same answer to everyone) on top of a **won't-bluff**
grounding discipline. Track is a teaching lens, not a learner identity: the same learner can ask for a
low-code/no-code workflow lens, a code-heavy implementation lens, or a bridge between them for the same
topic. Current personalization is switchable teaching lens plus within-session profile state, not
cross-session ML clustering or provider-backed memory.

## The constitution

- [`specs/mission.md`](specs/mission.md) — why · audience · in/out of scope
- [`specs/tech-stack.md`](specs/tech-stack.md) — the stack + binding guardrails + what's deferred
- [`specs/roadmap.md`](specs/roadmap.md) — Thursday MVP → pull-ins → north star (MUST vs SHOULD)
- [`AGENTS.md`](AGENTS.md) — the working agreement every build agent follows
- [`docs/architecture-diagrams.md`](docs/architecture-diagrams.md) — the agentic flow, visualized
- [`docs/demo-and-deliverables.md`](docs/demo-and-deliverables.md) — final demo script, evidence, and
  submission checklist
- [`docs/video-demo-script.md`](docs/video-demo-script.md) — timed spoken script and screen checklist
  for the <=5-minute recording
- [`docs/submission-packaging-item.md`](docs/submission-packaging-item.md) — what the current
  submission-packaging item is, what it produces, and its guardrails
- [`docs/submission-google-doc-draft.md`](docs/submission-google-doc-draft.md) — external Google Doc
  draft, kept free of private corpus/eval text
- [`docs/vibe-coding-prompt-appendix.md`](docs/vibe-coding-prompt-appendix.md) — sanitized prompts and
  workflow examples for the submission
- [`docs/hugging-face-deployment-plan.md`](docs/hugging-face-deployment-plan.md) — Hugging Face Spaces
  deployment wrapper, settings, and smoke-test checklist, based on the Week 2 deployment pattern
- [`docs/teach-loop-status.md`](docs/teach-loop-status.md) — redacted live trace and eval evidence
- [`docs/two-day-score-lift-plan.md`](docs/two-day-score-lift-plan.md) — final score-lift sequence:
  grading diagnostic, lens-switch demo, then grounded Quiz Mode
- [`docs/grading-gap-audit.md`](docs/grading-gap-audit.md) — strict submission-risk audit by rubric area
- [`docs/submission-hardening-plan.md`](docs/submission-hardening-plan.md) — P0/P1/P2 hardening plan and
  human-run submission runbooks
- [`docs/superpowers/plans/2026-06-17-skill-gap-diagnosis.md`](docs/superpowers/plans/2026-06-17-skill-gap-diagnosis.md)
  — spec for the planned Skill-Gap Diagnosis standout workflow

## Build track

Code-heavy (handout Track 2): **LangChain `create_agent`** on LangGraph's runtime, **Nebius Token
Factory** for the generative call, vibe-coded with Codex / Claude Code. Full rationale in
[`specs/tech-stack.md`](specs/tech-stack.md).

## What we carry from Week 2 (and what changed)

Built on `genacademy-rag` (*GenAcademy Compass*) — the compounding arc, made concrete:

- **Reused:** the embedding model, Chroma index/schema, section-aware chunker, citation metadata,
  provider surface, eval harness, and refusal-first / won't-bluff discipline.
- **Extended:** the local course corpus is ingested into an extended collection; retrieval becomes a
  **single source-prioritized course retriever** where slides/handouts lead, notes fill gaps, and
  transcripts support/fallback.
- **New:** the adaptive **teach loop** + **within-session learner profile** — the agentic layer Week 2
  didn't have.
- **Deferred deliberately:** cross-session memory and explicit LangGraph orchestration. They are useful
  personalization architecture, but this demo keeps memory within the session and uses LangChain
  `create_agent` on LangGraph's runtime until durable memory or HITL earns a separate plan.

## Current Demo Evidence

Final merged-main evidence was captured on 2026-06-16 without using the held-out `test` split:

- Grounded teach trace: `traces/demo-grounded-main-final-20260616.jsonl`
  - Turn 1: `drill`, strategy `short_drill`, evidence `0.711 confirm`, faithful.
  - Turn 2: `re_explain_differently`, strategy `contrastive_example`, evidence `0.819 confirm`,
    faithful.
- Refusal trace: `traces/demo-refusal-main-final-20260616.jsonl`
  - `refuse_escalate`, evidence `0.0 stop`, exactly one review-queue row.
- Same-topic lens-switch traces:
  - `traces/demo-lens-low-code-20260616.jsonl`: same topic through the `low_code_no_code` lens; turns
    stayed grounded (`0.711` / `0.753 confirm`) and faithful.
  - `traces/demo-lens-code-heavy-20260616.jsonl`: same topic through the `code_heavy` lens; turns stayed
    grounded (`0.711` / `0.753 confirm`) and faithful.
- Grounded quiz trace: `traces/demo-quiz-agent-harness-reviewfix2-20260616.jsonl`
  - `3` cited MCQs generated, evidence `0.711 confirm`, answers `A,B,C` graded deterministically as
    `1/3`, no refusal; the trace stores `topic_hash`, not the raw topic or quiz text.
- Dev eval artifact: `eval/runs/teach-loop-dev-main-final-20260616.json`
  - `7/10` overall, `7/8` teachable, `2` safe low-retrieval refusals.
  - Follow-up grade-boundary run fixes the original same-turn grade overwrite; latest dev evidence still
    has one teachable failure from a separate confirm-band refusal path.

Run the same public-topic demo locally:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_teach_demo.py \
    --topic "agent harness" \
    --style analogy \
    --track-lens code_heavy \
    --learner-answer "It is just one prompt with no tool checks or feedback."
```

Switch only the teaching lens for the same public topic:

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

Run the grounded quiz demo locally:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_quiz_demo.py \
    --session-id demo-quiz-agent-harness-reviewfix2-20260616 \
    --topic "agent harness" \
    --question-count 3 \
    --answers A,B,C
```

Run the redacted dev eval:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/eval_teach_loop.py \
    --split dev \
    --limit 10 \
    --json-out eval/runs/teach-loop-dev.json
```

Do not run or tune against `--split test` until final evaluation/reporting.
