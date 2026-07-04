# Breakout Handout — Project Content (paste source)

**Date:** 2026-07-04
**Purpose:** versioned, privacy-clean source for the team breakout handout (the `.docx` lives outside
this repo because it carries team names/emails — it is never committed). Each section below maps to
one cell of the handout; the fill step copies them over verbatim.
**Grounded in:** `docs/coach-product-requirements.md` (FR-1..FR-W11) and the merged Tutor Workspace
design package (PR #61, independently reviewed).

---

## Q1 — Pick the use case *(→ handout Q1 cell)*

**Adaptive GenAcademy AI Tutor & Q&A Coach** — a grounded tutor over the actual course corpus
(slides, live-session recordings, handouts, cohort Q&A).

- **Problem:** to understand one concept, a learner re-opens the slides, scrubs the session recording,
  and searches the handout and chat separately. No single place explains a topic *and* shows exactly
  where it came from.
- **Who benefits:** cohort members (both low-code and code-heavy tracks — the tutor adapts its
  explanation lens, not its facts), plus mentors who receive only the questions the corpus genuinely
  can't answer.
- **Why an agent, not a chatbot:** it chooses the next *teaching* move (explain, step-by-step, quiz,
  re-explain differently, refuse + escalate) based on how the learner is doing — but it can never
  choose to answer without course evidence. **Grounded or it refuses.**

## Q2 — Knowledge and tools *(→ handout Q2 cell)*

**What the agent knows (RAG at the center):**
- A metadata-tagged course corpus: slides, live-session transcripts, handouts, cohort Q&A — tagged by
  week, session, source type, and citation id, with a corpus version.
- **One source-prioritized retrieval per turn**; citations are captured at retrieval time and role-keyed
  to the parts of the answer they support — never reconstructed after generation.
- The companion context panel is a **projection of that same retrieval**: it shows only the spans the
  answer actually cited (including the real slide image for slide citations) — no second search that
  could disagree with the answer.

**Tools the agent calls (two kinds — this distinction is the design):**
- *Agent-chosen (the teaching brain):* teaching-action selector (explain / step-by-step / clarify /
  quiz / re-explain / refuse+escalate) · explanation-lens selector (low-code / code-heavy / bridge) ·
  grounded check-question generator.
- *Always-run, deterministic (never the model's call):* course retriever + strict source filters ·
  confidence-band gate with a hard refusal floor · citation capture · context-panel projection (incl.
  slide-image lookup) · next-step suggestion builder (anchored to the corpus) · deterministic answer
  grading floor · mentor-escalation queue · session memory (derived state only, privacy-scoped).

## Q3 — Autonomy and evals *(→ handout Q3 cell)*

- **Autonomy:** agentic in *teaching* (which move, which lens, when to re-explain — logged per turn);
  deterministic in *grounding* (retrieval, filters, citations, confidence bands, refusal, privacy).
  The agent cannot answer uncited, ignore retrieval confidence, silently widen a learner's filter, or
  treat web content as course content.
- **Evals:** a frozen, hand-labeled golden set scored on retrieval recall, citation-faithfulness F1,
  **refusal recall on negative controls (hard release gate = 1.000)**, refusal precision, filter
  correctness, latency, and cost — with an honest baseline → post-improvement delta (regressions
  disclosed) on a public eval dashboard.

## Our project *(→ handout section-4 cell: "Use case, where RAG fits, tools, autonomy vs workflow, evaluation")*

**Thesis.** A grounded AI tutor over the actual GenAcademy corpus. It answers only from retrieved
course evidence, shows the exact source beside every answer in a split-pane **Tutor Workspace**, and
**refuses and routes to a mentor when it can't ground the answer.** Agentic in how it teaches;
deterministic in grounding.

**The demo moment.** Ask *"What is LangChain and why use it instead of calling an LLM API directly?"*
→ plain-English tutor answer with citations → the right panel shows the actual course slide (real
slide image), the instructor's live explanation, and the handout excerpt that grounded it → a short
check question → suggested next steps anchored to the course ("Next: → Agents & tool calling", "Quiz
me on this"). Then ask something outside the corpus and the tutor **declines and offers a mentor**
instead of bluffing — with recovery suggestions routing back into the course.

**Where RAG fits.** One source-prioritized retriever over the metadata-tagged corpus (week · session ·
source type · citation id · corpus version). Slides and handouts lead, transcripts support; citations
are captured at retrieval and role-keyed to answer segments. The context panel is a projection of the
same single retrieval — it renders only cited spans, so the answer and its evidence can never disagree.

**Tools the agent calls.** Teaching brain (agent-chosen): action selector · lens selector · check-question
generator. Deterministic pipeline (always runs): retriever + strict filters · confidence-band gate +
refusal floor · citation capture · panel projection with real slide images · anchored next-step
suggestions · grading floor · mentor escalation · privacy-scoped session memory.

**Autonomy vs. workflow.**
- *The agent decides:* the teaching move, the explanation lens, when to re-explain after a failed
  check, which check question to ask. Every choice is logged per turn (inspectable "behind this
  answer" view — hidden from learners by default).
- *The system locks:* no answer without citations · deterministic refusal below the confidence floor ·
  learner filters are strict (never silently widened) · suggestions must carry a corpus anchor (the
  system can never suggest something it would then refuse) · no web content dressed as course content ·
  no raw learner text in logs.

**How we evaluate it.** Frozen, hand-labeled golden dataset (dev/test split; test held out), versioned
in an eval platform, scored on: retrieval recall · citation-faithfulness F1 (floor 0.50) · **refusal
recall on negative controls = 1.000 as a hard release gate** · refusal precision · filter correctness ·
turn p95 latency · cost per run. Baseline → post-improvement delta reported honestly (one measured
improvement already public: citation F1 0.45 → 0.6333 with no refusal-safety regression). Current
values live on the project's public eval dashboard.

**Status & scope.** The grounded engine is built and evaluated (teach loop, quiz, skill-gap diagnosis,
escalation, tracing, eval harness + public dashboard). The Tutor Workspace (context panel, slide-image
card, next-step suggestions) is fully designed, adversarially reviewed by a second model, and merged;
Phase-1 build is next, on the Week-1 corpus, text-first. Later phases (each gated): agentic panel
curation → opt-in current-docs lookup (separate, clearly-labeled lane) → voice in/out → consent-gated
tutor voice → admin ingestion with eval-contamination checks → cohort auth → learner progress view.

---

*Privacy note for the fill step: this file carries no team emails, no corpus filenames, no learner
data. The team table in the `.docx` is left untouched by the automated fill.*
