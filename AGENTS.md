# AGENTS.md — Working Agreement (GenAcademy Coach)

**Applies to ALL agents — Claude Code, Codex, Cursor, any reviewer, any future tool.** This is the
tool-neutral source of truth. Per-tool files (`CLAUDE.md`) are thin mirrors that point here. Rules do
not change with the tool.

*Status: in force, pre-build. The Week-3 handout alignment pass locked the MVP boundaries on
2026-06-15; the project is awaiting the implementation plan. Update this file when the architecture
moves.*

---

## 1. What we're building

An **adaptive, grounded AI tutor** for Gen Academy cohort members — teaches a concept in the learner's
style, checks understanding, **re-explains a different way** when they stumble, tracks what they
know/struggled with (within a session), and **refuses to answer what it can't cite** from the course
corpus (escalates to a mentor instead). One text-first engine: **teach** is the Week-3 MVP; **quiz**,
**mock interview**, **admin upload**, and **ElevenLabs voice** are pull-ins only after the teach loop,
eval, refusal path, and trace are working. Built on the author's Week-2 `genacademy-rag` retrieval
system. Full design: `specs/` + `docs/architecture-diagrams.md`.

**Foundation — reuse `genacademy-rag`, do not reinvent.** The Coach is an agentic layer on top of the
Week-2 `genacademy-rag` system, which already provides the embedder, Chroma index/schema, section-aware
chunker, refusal/grounding/citation pipeline, the Nebius provider call, and a working **eval harness**.
Treat Week-2 as the foundation to **extend**, never a thing to rebuild. The verified facts + the binding
reuse contract are in **`docs/genacademy-rag-foundation.md`** — read it before planning or building.

## 2. The gates (no skipping)

1. **No code until the plan is approved.** Flow: brainstorm → design/spec → reviewed → implementation
   plan → build. Architecture is settled *before* implementation. Applies to every new mode/slice.
2. **Builder is never the sole judge.** The agent that writes code does **not** get the last word on
   whether it's correct. A **different model or a fresh context** reviews every non-trivial change
   (Claude builds → Codex reviews, or vice-versa). Never one context grading itself.
3. **Evidence before "done".** "It should work" is not done. Show **lint + test output**, and for the
   agent loop, a **runtime-decision trace** of a real run. Green is demonstrated, not asserted.
4. **The held-out test set is sacred.** Real student chat-questions in `corpus/eval-questions/` are
   hard-split before any prompt or tuning. **Test never enters the index, prompts, examples, tuning, or
   the demo.** The regression/dev set may grow from learner-flagged or admin-authored items; the test
   set stays frozen. **Enforced** by the eval & data-split protocol in `specs/tech-stack.md`
   (deterministic split + committed manifest/checksums + a leak check).
5. **The graded differentiator is the failure path.** A demo that works on the happy path but falls
   over on the first tool failure is unfinished. Refusal + escalation + the 6 recovery mechanisms are
   built in, not bolted on.

## 3. Project guardrails (review-blockers — reject a PR that violates these)

- **Grounded or it refuses.** The tutor only teaches/asks/grades what it can cite from a retrieved span.
  Low retrieval confidence → "I can't find this in the course materials" + escalate. It does **not**
  answer from model priors. The refusal path is load-bearing, not decorative.
- **Confidence is a real signal, never an LLM self-rating.** Refuse/STOP is driven by retrieval
  similarity score + a citation-present check. The bands (STOP < 0.60 · CONFIRM 0.60–0.85 · PROCEED >
  0.85) are **calibrated against the actual index before use, not taken from a diagram** (see
  `specs/tech-stack.md`).
- **Citations captured at retrieval, never reconstructed.** Every claim carries its source
  (`week · title · timestamp` / `chunk_index`). An answer that cites a source it didn't retrieve is a
  correctness bug.
- **One retriever, source-prioritized.** The MVP uses one course-corpus retriever over the extended
  Week-2 collection. Every chunk carries `source_type`; slides and handouts are preferred for teaching,
  notes fill gaps, and transcripts are fallback/support. Add source-specific tools only if eval shows a
  measured recall gap.
- **Agenticity is the model deciding at runtime, shown in a trace.** The next action
  (`advance`, `re_explain_differently`, `drill`, `refuse_escalate`, `stop`) and the explanation strategy
  are chosen from observations, not hardcoded in Python. If the path is scripted, it's a workflow, and
  we must call it that.
- **MINT restraint — earn each layer.** One LangChain `create_agent` loop on LangGraph's internal
  runtime + a small read-mostly toolset. **No MCP, no A2A, and no _explicit_ LangGraph graph/imports**
  this week — the handout's LangChain + LangGraph track is satisfied through the LangGraph-backed
  agent runtime; we just don't hand-author a graph (see `specs/tech-stack.md` for the trigger that earns
  each).
- **Pure core / thin view.** All agent, retrieval, grading, and learner-profile logic lives in a
  testable core with **no** web-framework imports. A `from fastapi import` (or any HTTP/template import)
  inside the core is a reject.
- **`create_agent` boundary (no accidental LangGraph).** Do not import `langgraph.graph.StateGraph`,
  `langgraph.checkpoint.*`, or `langgraph.interrupt` directly this week — that's the deferred
  explicit-graph layer. Such an import in a PR is a reject (full allowed/forbidden list in
  `specs/tech-stack.md`).
- **Never invent facts or numbers the corpus doesn't support.** Faithfulness to retrieved context is the
  product.
- **Reuse the Week-2 foundation (review-blocker).** Do not build a new chunker, embedder, vector schema,
  refusal/threshold scheme, provider wrapper, or eval harness without a written delta vs
  `genacademy-rag` explaining why its API can't serve the need (`docs/genacademy-rag-foundation.md`).
  The held-out eval set is the **real student chat-questions** (corpus-independent), never indexed.
  Same-embedder rule: the index is `all-MiniLM-L6-v2` / 384-d — switching embedders means re-ingesting
  a fresh collection.

## 4. Two cheap habits (mandatory)

- **Never quote a number/fact you haven't just re-derived.** Model IDs, pricing, context windows, param
  counts, and dates *drift* — re-check against the source before writing it down.
- **Reference calls are copied verbatim, never paraphrased.** LangChain `create_agent` signatures,
  LangSmith tracing env vars, Nebius model IDs, embedding dimensions, and request schemas are pasted
  from the official source — not reconstructed from memory.

## 5. Hard "don'ts"

- **Do NOT replicate the handout's solution kits.** The Week-3 handout ships sample solutions and says
  *replicating them scores zero.* The Coach is bring-your-own (adaptive tutor) — there's no kit to copy,
  so originality is structural. Keep it that way.
- **Do NOT publish corpus material.** Course PDFs/transcripts, slides, handouts, chat-question files, and
  any third-party or cohort data are `.gitignore`d. Confirm attribution/permission before any data lands
  (see `specs/roadmap.md` risk caps).
- **Do NOT add modes/surfaces ahead of a finished teach loop.** Quiz, interview, admin upload, and
  ElevenLabs voice are pull-ins; they start only when the teach-loop MVP demos end-to-end. Scope creep
  is the main project risk.

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
- `docs/decisions.md` — the load-bearing architecture decisions (settled choices · why · rejected
  alternatives), self-contained in this repo.
- *Brainstorm archive (Week-3 planning folder, historical):* the full decision log (D1–D52), the project
  board, the option scorecards, and the improvements ledger — the long-form trail behind
  `docs/decisions.md`.

## 8. Workflow & tool bindings

This project runs on the **`ai-dev-workflow`** skill — the tool-neutral umbrella that binds the gates
above to concrete tools (superpowers + gstack). The builder may be any model; the reviewer is always a
**different** model or fresh context (gate #2). Phase map:

| Phase | Binding | Realizes |
|---|---|---|
| Idea / scope | `superpowers:brainstorm`, `office-hours` | pressure-test before code |
| **Plan** | `superpowers:write-plan` → design/plan in `docs/superpowers/{specs,plans}/` | gate #1 (no code until approved) |
| Build | `superpowers:execute-plan` | one slice at a time |
| Review | `/pr-review-toolkit:review-pr` + a different-model `/codex` challenge | gate #2 (builder ≠ reviewer) |
| Verify | `/qa`, `/health`, `/verify` + the Week-2 eval harness | gate #3 (evidence before done) |
| Ship | `/commit-commands:commit-push-pr` | reproducible, reviewed |

The superpowers design/plan anchor is `docs/superpowers/specs/2026-06-15-genacademy-coach-mvp-design.md`.
Tool-specific routing is mirrored (thin) in `CLAUDE.md` under "## Skill routing"; `AGENTS.md` stays the
source of truth — the mirror is a pointer, not a copy.
