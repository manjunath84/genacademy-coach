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
> depth for an engineer) on its own using 3 retrieval tools + an item generator; it hands off to a human
> mentor when a question falls outside the corpus or grounding confidence is low (it refuses to bluff);
> and **I'll know it works when a learner goes from "I don't get it" to passing a grounded check-question
> in under 10 minutes, 8 times out of 10, on a held-out test set.**

## Who it's for

- **Primary:** Gen Academy cohort members, across both tracks — **no-code/low-code** and **code-heavy**.
  Each learner picks a mode (teach / quiz / interview) and a track; for Week 3, **track is a
  style/example selector** (workflow analogies vs. Python/LangGraph specifics), not a separate corpus.
- **Audience tilt:** technical but not-yet-AI-fluent learners — keep AI terms verbatim and define them in
  the sentence around first use, so the next paper/doc they read is easier, not harder.

## In scope (Week 3)

- The adaptive **teach loop** (explain → check → re-explain-differently) with a within-session learner
  profile (style · known · struggled).
- Grounded explanations + check-questions with **constrained one-span citations**; **real-signal
  refusal** (retrieval score + citation-present).
- **Item-quality eval** on a hard-split, **held-out** test set; a **runtime-decision trace** as the
  agenticity proof and the demo centerpiece.
- One persona, end-to-end.

## Out of scope (Week 3 — see `roadmap.md` for when each is earned)

- Quiz and mock-interview modes (the top two pull-ins).
- Track-aware *retrieval* (Week-3 track = prompt-level style only).
- Cross-session memory (Mem0), caching at scale, voice, multimodal, cohort deployment/auth.

## How I'll know it worked

End-to-end task completion: a learner reaches a passing **grounded check-answer** on the target concept
in **under 10 minutes, 8/10 sessions**, measured on the held-out test set — plus supporting item-quality
numbers (answerability · unique-correct · distractor validity · citation support · no span-leakage). Not
"looks good."
