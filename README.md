# GenAcademy Coach

An adaptive, grounded **AI tutor** over the Gen Academy cohort corpus. It teaches each learner in their
own style, checks understanding, **re-explains a different way when they stumble**, remembers what they
know and struggled with (within a session), and **refuses to bluff** — it only teaches what it can cite
from the course materials, and escalates the rest to a human mentor.

> **Implementation status:** teach-loop MVP implemented, merged, live Nebius-verified, and reviewed by
> separate Gemini/Claude contexts. The final merged-main evidence is `7/10` on the dev eval and `7/8`
> on teachable scenarios, with two safe low-retrieval refusals and one remaining deterministic grading
> diagnostic. Private corpus files remain local-only; only structure, redacted diagnostics, and leak
> checks are versioned.

Built as the **Week-3 (The Agentic Leap)** project of the *Mastering Agentic AI* Bootcamp, layered on
the author's Week-2 RAG system (`genacademy-rag` / *GenAcademy Compass*).

## What it is

One agent engine, three modes that share it:

- **Teach** *(Thursday MVP)* — explain a concept grounded in the corpus → check understanding →
  re-explain a different way until it clicks.
- **Quiz** *(pull-in)* — adaptive MCQ with deterministic grading.
- **Mock interview** *(pull-in)* — open-answer questions, grounded grading against cited expected
  points, follow-up probing, and a short gap report.
- **Admin upload / ElevenLabs voice** *(pull-ins)* — added only after the text teach loop, refusal path,
  eval split, and trace are demoable end-to-end.

The differentiator is **personalization** (never the same answer to everyone) on top of a **won't-bluff**
grounding discipline. Track is a teaching lens, not a learner identity: the same learner can ask for a
low-code/no-code explanation, a code-heavy explanation, or a bridge between them for the same topic.

## The constitution

- [`specs/mission.md`](specs/mission.md) — why · audience · in/out of scope
- [`specs/tech-stack.md`](specs/tech-stack.md) — the stack + binding guardrails + what's deferred
- [`specs/roadmap.md`](specs/roadmap.md) — Thursday MVP → pull-ins → north star (MUST vs SHOULD)
- [`AGENTS.md`](AGENTS.md) — the working agreement every build agent follows
- [`docs/architecture-diagrams.md`](docs/architecture-diagrams.md) — the agentic flow, visualized
- [`docs/demo-and-deliverables.md`](docs/demo-and-deliverables.md) — final demo script, evidence, and
  submission checklist
- [`docs/teach-loop-status.md`](docs/teach-loop-status.md) — redacted live trace and eval evidence

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

## Current Demo Evidence

Final merged-main evidence was captured on 2026-06-16 without using the held-out `test` split:

- Grounded teach trace: `traces/demo-grounded-main-final-20260616.jsonl`
  - Turn 1: `drill`, strategy `short_drill`, evidence `0.711 confirm`, faithful.
  - Turn 2: `re_explain_differently`, strategy `contrastive_example`, evidence `0.819 confirm`,
    faithful.
- Refusal trace: `traces/demo-refusal-main-final-20260616.jsonl`
  - `refuse_escalate`, evidence `0.0 stop`, exactly one review-queue row.
- Dev eval artifact: `eval/runs/teach-loop-dev-main-final-20260616.json`
  - `7/10` overall, `7/8` teachable, `2` safe low-retrieval refusals.
  - Remaining failure: one deterministic `grade_not_correct` diagnostic, with citations resolved and a
    runtime-decision trace present.

Run the same public-topic demo locally:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_teach_demo.py \
    --topic "agent harness" \
    --style analogy \
    --track-lens code_heavy \
    --learner-answer "It is just one prompt with no tool checks or feedback."
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
