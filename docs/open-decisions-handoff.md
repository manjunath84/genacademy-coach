# Open Decisions — Handoff & Record (resolved, pre-build Pass 4)

> **Two jobs:** (1) the **record** of the Pass-4 review + what was done in that session; (2) the
> historical handoff that drove the 2026-06-15 decision-lock pass.
> **Status:** resolved into the constitution (`AGENTS.md`, `specs/*`, `docs/decisions.md`,
> `docs/architecture-diagrams.md`). No application code until the plan is approved (AGENTS §2 gate 1).
> **Date:** 2026-06-15. **Reviewers so far:** Codex ×2, Kimchi, Claude Opus 4.8 + a Codex consult.
>
> **How to use this in Codex:** run from inside the `genacademy-coach` repo so Codex can also read `AGENTS.md`,
> `specs/*`, and `docs/genacademy-rag-foundation.md`. A ready prompt is at the bottom.

---

## A. The project in five lines

- **GenAcademy Coach** — an adaptive, grounded AI **tutor**. Teaches a course concept, checks understanding,
  **re-explains a different way** when the learner stumbles, and **refuses to answer what it can't cite**.
- **Thursday MVP** = the teach loop only. Quiz + mock-interview are pull-ins.
- Built on **LangChain `create_agent`**, layered on the author's Week-2 RAG system **`genacademy-rag`**.
- It's a judged bootcamp competition (Consistency · Creativity · Execution · Technical thinking · Initiative) + build-in-public.
- The brand is **won't-bluff grounding** + **personalization** ("explained it three ways until it clicked").

## B. The foundation — `genacademy-rag` (reuse, don't reinvent)

Full detail in `docs/genacademy-rag-foundation.md`. Key inheritable assets (verified on disk):
- Embedder `all-MiniLM-L6-v2` (384-d, local), **Chroma** index + `chunks_meta` schema, section-aware chunker
  (A/B-tested), refusal/grounding/citation pipeline, deterministic JSON grader, Nebius provider call.
- A working **eval harness**: retrieval metrics (recall@k/precision@k/MRR) + **refusal-correctness** + an
  **LLM-judge** faithfulness check + a 12-Q gold set.
- The current index is tiny (4 docs / 53 chunks) — the owned corpus is **not** indexed yet; extending it is a build task.
- **Reuse contract (binding):** no new chunker/embedder/vector-schema/refusal-scheme/eval-harness without a
  written delta vs Week-2. Same-embedder rule (384-d or re-ingest fresh). Extend the index, don't rebuild.

## C. Corpus (now consolidated in one place — `corpus/`)

- `notes/` (7 lesson deep-notes), `transcripts/` (6 sessions, ~176k words), `slides/` (7 decks),
  `handouts/` (13 PDFs incl. A2A, agent-memory, caching, glossaries) — staged for indexing via the
  Week-2 ingestion path.
- `eval-questions/` — real student chat-questions (W1S2, W2S1, W2S2, W3S1). **NEVER INDEXED.** This is the
  leak-safe held-out eval source (students asked these live → corpus-independent → can't be "memorized").
- All content gitignored (never republished — AGENTS §5).

## D. The review findings (what this handoff is downstream of)

All confirmed by the Codex consult; severities are the agreed final.
- **H1 (HIGH)** — eval protocol still hard-codes a nonexistent `student_questions.jsonl` / "CohortBrain".
  **Resolved direction:** drop that file entirely; eval source = real chat-questions (test) + NotebookLM/Quiz-Yourself (dev-seed).
- **H2 (HIGH)** — the 3 retriever tools are CohortBrain partitions that don't exist; Week-2 ships on one collection → **Decision 1**.
- **H3 (HIGH)** — agent-vs-workflow is unpinned; wrapping the inherited RAG pipeline in `if/else` would be a workflow, not an agent → **Decision 5**.
- **M1** — "no re-ingest" is wrong; the owned corpus must be ingested fresh (extend the index).
- **M2** — transcript filler + the partial W2-S2 are retrieval poison; tag/exclude at ingest.
- **M3** — "distractor validity" is an MCQ metric; teach MVP uses open check-questions → **Decision 3**.
- **M5 (MED-HIGH)** — one global confidence band over heterogeneous sources is brittle; calibrate per source-type.
- **Codex additions:** (a) leak-check the chat-questions against transcript chunks (a student may have asked a
  question the lecturer answered verbatim); (b) keep the inherited LLM-judge as a **secondary audit**, not the
  gate (the "no judge at all" rule conflicts with inherited code) → **Decision 3**; (c) **first build task = a
  read-only audit of genacademy-rag's interfaces → a tiny adapter spec** (the Week-2 API is currently unpinned —
  the biggest invisible risk); (d) the **HTML trace viewer is over-engineered for Thursday** → **Decision 4**.

## E. The 6 decisions resolved by the constitution update

For each: **the original question · prior spec · trade-off · resolved direction**. The canonical record
now lives in `docs/decisions.md`.

### Decision 1 — Retriever count (1 vs 3)
- **Question:** one retriever over the whole extended corpus, or three partitioned tools?
- **Current spec:** 3 tools (`retrieve_lectures/assignments/student_qa`) — CohortBrain partitions that don't exist; Week-2 uses one Chroma collection.
- **Trade-off:** 3 tools = a flashier "model routes across corpora at runtime" agenticity beat, but on a
  few-hundred-chunk corpus each index is sparse → **worse recall** + more build risk. 1 tool = better recall,
  simpler, faster; the agenticity proof leans on the re-explain-strategy decision (stronger anyway).
- **Recommendation:** **one** retriever over the extended collection, every chunk tagged `source_type`; split
  into filtered tools **only if** a measured recall gap justifies it.

### Decision 2 — Eval source (mostly settled — confirm)
- **Question:** where do eval questions come from now that `student_questions.jsonl` is dropped?
- **Recommendation:** **held-out TEST = the real student chat-questions** (corpus-independent, leak-safe).
  **dev/seed = NotebookLM quizzes + the deep-notes' "Quiz Yourself" sets** (corpus-derived → never the test).
  Run a leak-check of test questions vs transcript chunks (Codex). NotebookLM is optional (regenerable from the corpus).

### Decision 3 — Grader (deterministic gate + judge as secondary audit)
- **Question:** what marks a learner's answer right/wrong?
- **Current spec:** deterministic grader, and "no LLM-judge in the MVP" — but Week-2 already ships an LLM-judge.
- **Recommendation:** **deterministic grounded grader = the pass/fail gate** (exact/normalized match + citation
  resolves; repeatable, honest). **Inherited LLM-judge = a secondary faithfulness audit**, not the gate. (Fixes
  the "no judge at all" conflict + M3: teach-MVP item quality = answerability + citation-support + no-leakage; reserve distractor-validity for the quiz pull-in.)

### Decision 4 — Trace artifact (CLI/JSON vs HTML viewer)
- **Question:** what form does the runtime-decision trace (the agenticity proof) take for Thursday?
- **Current spec:** a polished HTML viewer (~2 hr of UI).
- **Trade-off:** HTML looks nice in the demo but competes with the failure-path polish that actually wins the
  judged criteria. CLI/JSON + a screenshot proves the same thing for near-zero cost.
- **Recommendation:** **CLI/JSON trace + screenshot for the MVP; HTML only if time remains** (MVP-protection).

### Decision 5 — Agent-vs-workflow commitment
- **Question:** is the teach loop a real agent or a workflow dressed as one?
- **Sharpest judge test (Codex):** "Show the trace where the model, after seeing the learner's actual wrong
  answer + retrieved evidence, **chooses** the next action and the re-explanation **strategy**. Now run the same
  concept with a different wrong answer and show a **different** chosen strategy without changing Python control flow."
- **Recommendation (a commitment, not a fork):** **one `create_agent` ReAct loop**; the model emits a structured
  `next_action ∈ {advance, re_explain_differently, drill, refuse_escalate, stop}` **plus** a `strategy`, chosen
  from observations. Python may enforce safety gates (schema, score thresholds, max turns) but **must not**
  implement `if wrong: reexplain` as the core adaptation. A Python state-machine-around-the-LLM is a **review-blocker**.

### Decision 6 — Admin-upload feature (scope)
- **Question:** the author wants an **admin screen to upload documents into the corpus** (for quiz/interview
  content). Where does it land?
- **Context:** genacademy-rag **already has** admin/member auth + an upload path (`web/auth.py`, `data/uploads`,
  `documents.uploaded_by/status`). So this is an **extension of inherited machinery**, not new work.
- **Recommendation:** **roadmap pull-in (near cohort-rollout), NOT the Thursday MVP** — it must not eat the
  graded failure-path polish. **Cheap seam to leave open now:** idempotent, version-pinned ingestion (an uploaded
  doc re-indexes cleanly). Build the feature later; reuse Week-2 auth+upload when it's earned.

## F. Already locked this session
- `student_questions.jsonl` / CohortBrain → **dropped** (to be purged from AGENTS gate 4, tech-stack, decisions AD-5, Diagram 6).
- `genacademy-rag` is now a **first-class, never-missed foundation** (`docs/genacademy-rag-foundation.md` + AGENTS §1/§3 clauses).
- Corpus **consolidated** into `corpus/` with a leak-safe `eval-questions/` zone.
- NotebookLM is **off the critical path** (corpus-derived → regenerable; can't be the held-out test).

## G. Questions for Codex
1. For **each** of the 6 decisions: agree or disagree with the recommendation, one paragraph of reasoning. Push hardest on **Decision 1** (retriever count) and **Decision 4** (trace artifact) — the two real trade-offs.
2. **Decision 5:** is the proposed commitment enough to survive the judge test, or is there a sharper failure mode?
3. What do these 6 decisions **miss**? What is the **single biggest risk** to shipping the Thursday teach-loop MVP?
4. Anything **over-engineered** for a one-builder, one-week MVP that should be cut now?
