# AGENTS.md — Working Agreement (GenAcademy Coach)

**Applies to ALL agents — Claude Code, Codex, Cursor, any reviewer, any future tool.** This is the
tool-neutral source of truth. Per-tool files (`CLAUDE.md`) are thin mirrors that point here. Rules do
not change with the tool.

*Status: in force, pre-build. The design it governs (`specs/` + `docs/architecture-diagrams.md`) was
brainstormed and independently reviewed (Codex, gpt-5.5) and is awaiting the implementation plan.
Update this file when the architecture moves.*

---

## 1. What we're building

An **adaptive, grounded AI tutor** for Gen Academy cohort members — teaches a concept in the learner's
style, checks understanding, **re-explains a different way** when they stumble, tracks what they
know/struggled with (within a session), and **refuses to answer what it can't cite** from the course
corpus (escalates to a mentor instead). Three modes on one engine: **teach** (the Week-3 MVP), **quiz**,
**mock interview**. Built on the author's Week-2 `genacademy-rag` retrieval system. Full design:
`specs/` + `docs/architecture-diagrams.md`.

## 2. The gates (no skipping)

1. **No code until the plan is approved.** Flow: brainstorm → design/spec → reviewed → implementation
   plan → build. Architecture is settled *before* implementation. Applies to every new mode/slice.
2. **Builder is never the sole judge.** The agent that writes code does **not** get the last word on
   whether it's correct. A **different model or a fresh context** reviews every non-trivial change
   (Claude builds → Codex reviews, or vice-versa). Never one context grading itself.
3. **Evidence before "done".** "It should work" is not done. Show **lint + test output**, and for the
   agent loop, a **runtime-decision trace** of a real run. Green is demonstrated, not asserted.
4. **The held-out test set is sacred.** `student_questions.jsonl` is hard-split into seed/dev/test
   *before* any prompt or tuning. **Test never enters prompts, examples, tuning, or the demo.** The
   regression/dev set may grow from learner-flagged items; the test set stays frozen.
5. **The graded differentiator is the failure path.** A demo that works on the happy path but falls
   over on the first tool failure is unfinished. Refusal + escalation + the 6 recovery mechanisms are
   built in, not bolted on.

## 3. Project guardrails (review-blockers — reject a PR that violates these)

- **Grounded or it refuses.** The tutor only teaches/asks/grades what it can cite from a retrieved span.
  Low retrieval confidence → "I can't find this in the course materials" + escalate. It does **not**
  answer from model priors. The refusal path is load-bearing, not decorative.
- **Confidence is a real signal, never an LLM self-rating.** Refuse/STOP is driven by retrieval
  similarity score + a citation-present check (bands: STOP < 0.60 · CONFIRM 0.60–0.85 · PROCEED > 0.85).
- **Citations captured at retrieval, never reconstructed.** Every claim carries its source
  (`week · title · timestamp` / `chunk_index`). An answer that cites a source it didn't retrieve is a
  correctness bug.
- **Agenticity is the model deciding at runtime, shown in a trace.** The next action (which retriever,
  re-explain vs advance vs refuse, retry/stop/escalate) is chosen from observations — not a hardcoded
  loop. If the path is scripted, it's a workflow, and we must call it that.
- **MINT restraint — earn each layer.** One `create_agent` loop + a small read-mostly toolset. **No MCP,
  no A2A, no LangGraph** this week (see `specs/tech-stack.md` for the trigger that earns each).
- **Never invent facts or numbers the corpus doesn't support.** Faithfulness to retrieved context is the
  product.

## 4. Two cheap habits (mandatory)

- **Never quote a number/fact you haven't just re-derived.** Model IDs, pricing, context windows, param
  counts, and dates *drift* — re-check against the source before writing it down.
- **Reference calls are copied verbatim, never paraphrased.** LangChain `create_agent` signatures,
  Nebius model IDs, embedding dimensions, and request schemas are pasted from the official source — not
  reconstructed from memory.

## 5. Hard "don'ts"

- **Do NOT replicate the handout's solution kits.** The Week-3 handout ships sample solutions and says
  *replicating them scores zero.* The Coach is bring-your-own (adaptive tutor) — there's no kit to copy,
  so originality is structural. Keep it that way.
- **Do NOT publish corpus material.** Course PDFs/transcripts and the CohortBrain data are `.gitignore`d.
  Confirm attribution/permission before any data lands (see `specs/roadmap.md` risk caps).
- **Do NOT add modes/surfaces ahead of a finished teach loop.** Quiz and interview are pull-ins; they
  start only when the teach-loop MVP demos end-to-end. Scope creep is the main project risk.

## 6. Definition of done (per change)

- [ ] Lint clean + tests pass — **output shown**, not claimed.
- [ ] New behavior covered by a test (core logic) or a demonstrated run (agent loop).
- [ ] Reviewed by a different model / fresh context (gate #2).
- [ ] No guardrail (§3) violated; held-out test set untouched (gate #4).
- [ ] Specs/docs updated if scope or architecture moved.

## 7. Map of the project's own docs

- `specs/mission.md` — why · audience · in/out of scope.
- `specs/tech-stack.md` — the stack + binding guardrails + what's deferred and when it's earned.
- `specs/roadmap.md` — Thursday MVP → pull-ins → north star; MUST vs SHOULD; risk caps.
- `docs/architecture-diagrams.md` — system architecture, the teach loop (agenticity proof), failure
  handling, state, eval split, the three modes, HITL, roadmap — visualized.
- *Brainstorm archive (in the Week-3 planning folder, to migrate as needed):* the full decision log
  (D1–D52), the project board, the option scorecards, and the improvements ledger.
