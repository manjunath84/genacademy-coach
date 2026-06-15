# Architecture Decisions

The load-bearing, **settled** decisions behind GenAcademy Coach — each with *why* and the *alternative
we rejected*, so a coding agent (or a future contributor) doesn't re-litigate them. Self-contained: you
don't need any external doc to understand these. The full long-form trail (every decision D1–D52, with
the brainstorm context) lives in the Week-3 planning folder's decision log; the `(D##)` tags below map
to it.

> These are settled for the Week-3 build. Reopening one needs a new entry here + a note in the affected
> spec — not a quiet change mid-build.

---

### AD-1 — Direction: an adaptive, grounded tutor on top of `genacademy-rag` (D1)
**Decision.** Build a bring-your-own use case — an adaptive AI tutor — layered on the author's Week-2
RAG system, rather than one of the handout's six pre-scoped use cases.
**Why.** It compounds prior work (a visible build-in-public arc), targets the cohort's own pain, and —
because it's bring-your-own — there's no handout solution kit to accidentally replicate (replication
scores zero). Originality is structural.
**Rejected.** 3E Code Review (clean eval but disconnected from the author's work); 3A Market Research
(low ceiling); the content-pipeline slice (better *life* project, weaker *Week-3* agentic demo).

### AD-2 — Headline = the adaptive teach loop; quiz + interview are modes (D47/D48)
**Decision.** The Thursday MVP is the **teach loop** (explain → check → re-explain-a-different-way) with
a within-session learner profile. Quiz and mock-interview are pull-in modes on the same engine.
**Why.** Personalization is the differentiator and the emotional demo beat ("it explained it three ways
until it clicked"); the re-explain branch is genuinely agentic (learner-dependent path).
**Rejected.** Mock-interviewer-only or quiz-only as the headline — narrower story, and quiz alone risks
looking like a "PDF→MCQ" wrapper.

### AD-3 — Framework: LangChain `create_agent` for the whole week (D44)
**Decision.** Use `create_agent` for the entire Week-3 ship. Do **not** hand-author an explicit
LangGraph graph this week.
**Why.** `create_agent` is the standard agent entry point and is **built on LangGraph**, so middleware,
a typed state schema, checkpointers, and HITL-interrupt middleware are available later *without a
rewrite*. The MVP's state is within-session and its HITL is an escalation card (not a pause/resume), so
the graph's primitives aren't needed yet. Fastest path; matches the cohort `agentic_rag` reference.
**Trigger to promote.** Cross-session memory, a real pause/resume interrupt, or auditable state
transitions becoming demo-core.
**Rejected.** Explicit LangGraph from day 1 (slower ramp, eats failure-path polish) — unless *learning
LangGraph* is itself a goal, which is a separate post-ship track.

### AD-4 — Grounding: constrained one-span citation + real-signal confidence (D42/D43)
**Decision.** Generated explanations/questions quote **one narrow retrieved span**; the answer cites the
exact text + metadata (`week · title · timestamp`). Refuse/STOP is driven by a **real** signal —
retrieval similarity score + a citation-present check — with bands STOP < 0.60 · CONFIRM 0.60–0.85 ·
PROCEED > 0.85. MCQ grading is deterministic.
**Why.** "Won't bluff" is the brand; it must be mechanical, not vibes. Citations captured at retrieval
can't be hallucinated.
**Rejected.** LLM **self-rated** confidence (uncalibrated, gameable) and an LLM-judge verifier in the
MVP (defer to a later mode with calibration).

### AD-5 — Eval: item-quality on a hard-split, held-out test set (D40/D41)
**Decision.** Evaluate **item quality** (answerability · unique-correct · distractor validity · citation
support · no span-leakage), not just deterministic grading. Hard-split `student_questions.jsonl` into
seed/dev/test **before any use**; the test split is frozen and never enters prompts/examples/demos.
Enforcement protocol in `specs/tech-stack.md`.
**Why.** Deterministic grading alone masks bad items. The original plan reused the questions as both
seed and gold — a data-leak the review caught.
**Rejected.** Grading-accuracy-only eval; using the same question pool for seeding and scoring.

### AD-6 — Agenticity proof = a runtime-decision trace (D21/D46)
**Decision.** The "is it really an agent?" defense is a **trace of model-chosen actions at runtime**
(which retriever, re-explain vs advance vs refuse, retry/stop/escalate), not the mere existence of a
branch in a diagram.
**Why.** A hardcoded loop could fake any single branch; only the runtime trace shows the path is
learner-dependent and unscripted. If the path is scripted, it's a workflow and we say so.
**Rejected.** Claiming "agent" from architecture shape alone.

### AD-7 — MINT restraint: no MCP, no A2A, no explicit LangGraph; 2–3 retriever tools (D30/D34/D39)
**Decision.** One `create_agent` loop + **2–3 retriever tools** (lectures / assignments / student-qa)
that the model routes across (docstrings = routing logic). No MCP, no A2A, no hand-authored graph.
**Why.** Earn each layer. One corpus + a few read tools needs no protocol; the single-agent loop needs
no A2A. Restraint is what a senior reaches for and what the lecturer rewards.
**Rejected.** Multi-agent from day 1; an MCP server as a core dependency (optional flex at most).

### AD-8 — Track = a prompt-level style selector this week (D49)
**Decision.** "No-code vs code-heavy" track is a **style/example selector** in the prompt (workflow
analogies vs Python/LangGraph specifics), not a separate track-filtered corpus.
**Why.** Keeps the author's track feature while avoiding the scope of corpus tagging + track-filtered
retrieval in week one.
**Rejected/Deferred.** Track-aware *retrieval* (corpus tagged by track) → pull-in.

### AD-9 — Corpus = CohortBrain processed data + curated handouts (D33/D45)
**Decision.** Ground on the pre-segmented CohortBrain Week 1–2 data (lectures/assignments with metadata
+ timestamps) plus curated handouts.
**Why.** It arrives clean and citation-ready, which resolves the corpus-completeness/parsing risk.
**Still open (pre-build task).** Confirm attribution/permission, pin a corpus version, spot-check vs
authoritative sources. **No corpus is committed to this repo.**
**Rejected/Deferred.** Layout-aware PDF re-ingestion (LlamaParse/LiteParse) — only if raw PDFs enter the
corpus later.

### AD-10 — Deferred pull-ins and their triggers (D9/D32/D27/D20/D51)
**Decision.** Cross-session memory (Mem0), caching (L1/L4/L5) + model tiering, voice (ElevenLabs),
multimodal slide questions, and cohort rollout (multi-user/auth/cost) are **kept on the roadmap but not
built this week**.
**Why.** Each is earned by a concrete trigger (see `specs/tech-stack.md` and `specs/roadmap.md`):
cross-session memory at rollout; caching when multi-user cost matters; voice after the text engine
ships; deployment as a post-Week-3 fast-follow so it doesn't eat the graded failure-path polish.
**Rejected.** Shipping any of these inside the Week-3 window at the expense of the teach-loop MVP.
