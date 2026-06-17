# Mission

## Why this exists

Cohort members learn the same material at different depths and in different ways — PMs, founders, and
operators learn through analogies and examples; engineers need depth; many need a concept explained two
or three different ways before it clicks. A single static explanation (a slide, a doc, one LLM answer)
serves none of them well. **GenAcademy Coach is a tutor that doesn't give the same answer to everyone** —
it adapts the explanation to the learner, checks that it landed, and tries again *differently* when it
didn't.

It does this **without bluffing**: it teaches only what it can ground in the cohort's own materials,
cites the source, and escalates anything outside the corpus to a human mentor. Grounded honesty is the
brand, inherited from the Week-2 `genacademy-rag` system this is built on.

## One-liner

> My agent helps a **Gen Academy cohort learner master a course concept** in a web chat, replacing the
> *re-watch-the-lecture-and-hope-it-clicks* loop. It explains the concept grounded in the corpus, checks
> understanding, and — when the learner stumbles — **re-explains a different way** (analogy for a PM,
> depth for an engineer) on its own using a source-prioritized course retriever + an item generator; it
> hands off to a human mentor when a question falls outside the corpus or grounding confidence is low
> (it refuses to bluff); and **I'll know it works when a learner goes from "I don't get it" to passing a
> grounded check-question in under 10 minutes, 8 times out of 10, on a held-out test set.**

## Who it's for

- **Primary:** Gen Academy cohort members, across both tracks — **no-code/low-code** and **code-heavy**.
  Track is a **teaching lens**, not a learner identity. The same learner can ask for a no-code/low-code
  explanation, a code-heavy explanation, or a bridge from one to the other for the same topic. For Week
  3, track changes explanation style/examples (workflow analogies vs. Python/LangGraph specifics), not
  the retrieval corpus.
- **Audience tilt:** technical but not-yet-AI-fluent learners — keep AI terms verbatim and define them in
  the sentence around first use, so the next paper/doc they read is easier, not harder.

## In scope (Week 3)

- The adaptive **teach loop** (explain → check → re-explain-differently) with a within-session learner
  profile (style · known · struggled).
- Grounded explanations + check-questions with **constrained one-span citations**; **real-signal
  refusal** (retrieval score + citation-present).
- **Item-quality eval** on a hard-split, **held-out** chat-question test set; a **runtime-decision trace**
  as the agenticity proof and the demo centerpiece.
- One learner session, end-to-end, with the option to switch teaching lenses.
- A minimal Hugging Face/Gradio demo surface for teach and quiz, kept as a thin wrapper over the same
  core engine; no cohort auth, admin upload, memory, or private corpus publishing.

## Out of scope (Week 3 — see `roadmap.md` for when each is earned)

- Quiz and mock-interview modes (the top two pull-ins). Mock interview reuses the same grounded engine:
  it asks open-ended questions, grades against cited expected points, follows up on gaps, and produces a
  session report.
- Track-aware *retrieval* (Week-3 track = prompt-level style only).
- Admin upload for new docs/quiz questions (low-priority pull-in after the MVP is demoable).
- ElevenLabs voice (pull-in idea over the same text engine; text transcript stays source of truth).
- Cross-session memory (Mem0), caching at scale, multimodal, cohort rollout/auth, and production-grade
  deployment operations.

## How I'll know it worked

End-to-end task completion, measured as a **reproducible eval protocol** (scripted — not dependent on
live humans for the MVP):

- Run **N ≥ 10 scripted learner-simulation scenarios** over held-out **test** concepts. Each scenario
  starts from a wrong or partial answer; the tutor must drive the learner-sim to a check-answer within a
  **step/time budget** (target ≈ under 10 minutes of interaction). Target N is ≥ 10; if fewer usable
  held-out scenarios exist, report the actual N and failure modes honestly rather than padding the set.
  Treat N < 10 as a smoke eval, not proof of the 8/10 target.
- **Target: ≥ 8/10 scenarios pass.** *Pass* = the **deterministic grounded grader** marks the final
  check-answer correct **and** every citation shown resolves to a retrieved span.
- **Supporting component metric:** item quality on the test set — answerability · citation support · no
  span-leakage. Distractor validity belongs to the quiz pull-in, not the teach-loop MVP.

Not "looks good."
