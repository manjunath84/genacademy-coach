# GenAcademy Coach

An adaptive, grounded **AI tutor** over the Gen Academy cohort corpus. It teaches each learner in their
own style, checks understanding, **re-explains a different way when they stumble**, remembers what they
know and struggled with (within a session), and **refuses to bluff** — it only teaches what it can cite
from the course materials, and escalates the rest to a human mentor.

> **Status: pre-build (design gate).** This repo currently holds the **constitution** — mission, tech
> stack, roadmap — plus the architecture design. No application code yet; the build follows the approved
> plan (see [`AGENTS.md`](AGENTS.md) §2, the gates). Private during the build.

Built as the **Week-3 (The Agentic Leap)** project of the *Mastering Agentic AI* Bootcamp, layered on
the author's Week-2 RAG system (`genacademy-rag` / *GenAcademy Compass*).

## What it is

One agent engine, three modes that share it:

- **Teach** *(Thursday MVP)* — explain a concept grounded in the corpus → check understanding →
  re-explain a different way until it clicks.
- **Quiz** *(pull-in)* — adaptive MCQ with deterministic grading.
- **Mock interview** *(pull-in)* — open-answer grounded grading + follow-up probing.
- **Admin upload / ElevenLabs voice** *(pull-ins)* — added only after the text teach loop, refusal path,
  eval split, and trace are demoable end-to-end.

The differentiator is **personalization** (never the same answer to everyone) on top of a **won't-bluff**
grounding discipline.

## The constitution

- [`specs/mission.md`](specs/mission.md) — why · audience · in/out of scope
- [`specs/tech-stack.md`](specs/tech-stack.md) — the stack + binding guardrails + what's deferred
- [`specs/roadmap.md`](specs/roadmap.md) — Thursday MVP → pull-ins → north star (MUST vs SHOULD)
- [`AGENTS.md`](AGENTS.md) — the working agreement every build agent follows
- [`docs/architecture-diagrams.md`](docs/architecture-diagrams.md) — the agentic flow, visualized

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
