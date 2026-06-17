# GenAcademy Coach

An adaptive, grounded AI tutor for Gen Academy course material. It teaches a learner through a
course concept, checks understanding, re-explains with a different strategy when the learner stumbles,
tracks known and struggled topics within the session, and refuses to answer when it cannot cite course
evidence.

Built as the Week-3 "Agentic Leap" project of the Mastering Agentic AI Bootcamp, layered on the
author's Week-2 RAG system (`genacademy-rag` / GenAcademy Compass).

## Status

| Surface | Status | Notes |
|---|---|---|
| Grounded teach loop | Shipped | LangChain `create_agent` chooses `next_action` and strategy; Python enforces grounding, citations, turn limits, and refusal safety. |
| Refusal + mentor queue | Shipped | Unsupported topics refuse and write local review-queue events instead of answering from model priors. |
| Redacted eval + leak guard | Shipped | Dev evidence is `7/10` overall and `7/8` teachable on 2026-06-16; held-out `test` split remains unused. |
| Same-topic lens switch | Shipped | The learner can switch among low-code/no-code, code-heavy, and bridge teaching lenses for the same topic. |
| Grounded Quiz Mode | Shipped pull-in | Generates cited MCQs from retrieved spans and grades selected option IDs deterministically in Python. |
| Skill-Gap Diagnosis | Shipped pull-in | Produces a deterministic, cited next-step report from teach/quiz traces and review-queue events. |
| Local Gradio UI | Shipped | Thin web view over teach, quiz, and skill-gap workflows; core logic has no web-framework imports. |
| Hugging Face Space | Deployment shell | Private Space smoke-passes HTTP; no private corpus/index is uploaded, so the public shell shows an empty-corpus notice. |
| Mock interview / admin upload / voice / cross-session memory | Roadmap | Deferred until they earn separate plans and privacy reviews. |

Private course material, traces, review queues, screenshots, and handoff packaging stay local-only.
Local handoff materials can live under ignored `localdocs/`.
The repository tracks structure, code, redacted metrics, and safety checks.

## Architecture

The system has one agentic loop and two deterministic pull-ins:

- **Teach** — retrieve course evidence, explain with a chosen teaching lens, ask a grounded check,
  grade deterministically, and let the model choose the next action.
- **Quiz** — generate cited MCQs from retrieved spans, validate grounding, and grade in Python.
- **Skill-Gap Diagnosis** — rank gaps from existing trace and quiz signals, then retrieve cited
  next-step material for each gap.

Architecture diagrams live in [`docs/architecture-diagrams.md`](docs/architecture-diagrams.md):

| Need | Diagram |
|---|---|
| Local app, deployment shell, and private-data boundary | [Product surface and deployment boundary](docs/architecture-diagrams.md#1-product-surface-and-deployment-boundary) |
| Shared grounded core across teach, quiz, and skill-gap | [System architecture](docs/architecture-diagrams.md#2-system-architecture) |
| Agentic teach decisioning | [Adaptive teach loop](docs/architecture-diagrams.md#3-adaptive-teach-loop) and [Teach agent orchestration](docs/architecture-diagrams.md#4-teach-agent-orchestration) |
| Deterministic assessment and diagnosis | [Quiz Mode flow](docs/architecture-diagrams.md#5-grounded-quiz-mode-flow) and [Skill-Gap Diagnosis flow](docs/architecture-diagrams.md#6-skill-gap-diagnosis-flow) |
| Redaction and held-out eval boundaries | [Local UI flow and redaction boundary](docs/architecture-diagrams.md#7-local-ui-flow-and-redaction-boundary) and [Corpus and eval boundary](docs/architecture-diagrams.md#10-corpus-and-eval-boundary) |

## Design Principles

- **Grounded or refuse.** The tutor only teaches what it can cite from retrieved course spans.
- **Runtime agenticity.** In teach mode, the model chooses `advance`, `drill`,
  `re_explain_differently`, `refuse_escalate`, or `stop` from observations.
- **Deterministic grading.** Quiz and check grading are Python gates, not LLM self-assessment.
- **Citations captured at retrieval.** Citations are derived from retrieved span metadata, never
  reconstructed by the model.
- **Pure core, thin view.** Retrieval, teaching, grading, diagnosis, and trace logic stay in the core;
  Gradio is only a presentation wrapper.
- **Protected eval split.** The held-out `test` split is never indexed, prompted, tuned against, or
  used for local examples.

## Documentation

- [`AGENTS.md`](AGENTS.md) — working agreement and project guardrails.
- [`specs/mission.md`](specs/mission.md) — project scope and audience.
- [`specs/tech-stack.md`](specs/tech-stack.md) — stack decisions and constraints.
- [`specs/roadmap.md`](specs/roadmap.md) — shipped work, active work, and future pull-ins.
- [`docs/architecture-diagrams.md`](docs/architecture-diagrams.md) — system and flow diagrams.
- [`docs/decisions.md`](docs/decisions.md) — load-bearing architecture decisions.
- [`docs/genacademy-rag-foundation.md`](docs/genacademy-rag-foundation.md) — Week-2 reuse contract.
- [`docs/hugging-face-deployment-plan.md`](docs/hugging-face-deployment-plan.md) — deployment wrapper
  and public-data constraints.
- [`docs/teach-loop-status.md`](docs/teach-loop-status.md) — redacted teach-loop status and eval
  evidence.
- [`docs/build-learnings.md`](docs/build-learnings.md) — implementation lessons and tradeoffs.
- [`docs/superpowers/plans/2026-06-17-skill-gap-diagnosis.md`](docs/superpowers/plans/2026-06-17-skill-gap-diagnosis.md)
  — reviewed plan behind the Skill-Gap Diagnosis slice.
- [`docs/superpowers/plans/2026-06-17-skill-gap-ui-wrapper.md`](docs/superpowers/plans/2026-06-17-skill-gap-ui-wrapper.md)
  — thin-view plan for the Gradio Skill-Gap tab.

## Local Setup

```bash
uv sync
cp .env_example .env
```

Fill `.env` with provider credentials. The local course corpus and generated traces are intentionally
gitignored.

Launch the local UI:

```bash
uv run python app.py
```

Run verification:

```bash
uv run pytest -q
uv run ruff check .
uv run python scripts/check_eval_leak.py
```

Run the redacted dev eval when provider credentials and the local corpus are available:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/eval_teach_loop.py \
    --split dev \
    --limit 10 \
    --json-out eval/runs/teach-loop-dev.json
```

Do not run or tune against `--split test` until final evaluation/reporting.

## What Changed From Week 2

The Week-2 project provided the RAG foundation: embedder, Chroma schema, chunking pipeline, citation
metadata, provider boundary, eval harness, and refusal-first discipline.

This project adds the agentic layer:

- a teach loop with model-chosen next actions,
- within-session learner profile state,
- strategy switching after stumbles,
- deterministic quiz assessment,
- deterministic skill-gap diagnosis,
- typed redacted traces,
- local Gradio UI over the same core.

Cross-session memory and explicit LangGraph orchestration are deliberately deferred. They are useful
future layers, but this version keeps personalization within the session and relies on LangChain
`create_agent` on LangGraph's runtime without importing `langgraph.*` directly.
