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

The differentiator is **personalization** (never the same answer to everyone) on top of a **won't-bluff**
grounding discipline.

## The constitution

- [`specs/mission.md`](specs/mission.md) — why · audience · in/out of scope
- [`specs/tech-stack.md`](specs/tech-stack.md) — the stack + binding guardrails + what's deferred
- [`specs/roadmap.md`](specs/roadmap.md) — Thursday MVP → pull-ins → north star (MUST vs SHOULD)
- [`AGENTS.md`](AGENTS.md) — the working agreement every build agent follows
- [`docs/architecture-diagrams.md`](docs/architecture-diagrams.md) — the agentic flow, visualized

## Build track

Code-heavy (handout Track 2): **LangChain `create_agent`**, **Nebius Token Factory** for the generative
call, vibe-coded with Codex / Claude Code. Full rationale in [`specs/tech-stack.md`](specs/tech-stack.md).
