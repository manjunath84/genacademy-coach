# GenAcademy Coach — MVP Design (entry-point for `superpowers:write-plan`)

> **Status:** design draft, pre-build (2026-06-15). This is a **thin entry-point**, not the design
> itself — it exists so `superpowers:write-plan` has a single anchor. The canonical design lives in the
> constitution; this file points at it and frames the Thursday MVP scope. **Do not duplicate** the
> constitution here — when they disagree, the constitution wins.

## Canonical design (read these first)

- **Working agreement + gates + guardrails:** [`../../../AGENTS.md`](../../../AGENTS.md)
- **Mission / audience / scope:** [`../../../specs/mission.md`](../../../specs/mission.md)
- **Stack + what's deferred (and when it's earned):** [`../../../specs/tech-stack.md`](../../../specs/tech-stack.md)
- **Roadmap (MUST vs SHOULD · risk caps):** [`../../../specs/roadmap.md`](../../../specs/roadmap.md)
- **Architecture, visualized (Mermaid diagrams):** [`../../../docs/architecture-diagrams.md`](../../../docs/architecture-diagrams.md)
- **Load-bearing decisions (settled · why · rejected alternatives):** [`../../../docs/decisions.md`](../../../docs/decisions.md)
- **Foundation to reuse (Week-2 `genacademy-rag`):** [`../../../docs/genacademy-rag-foundation.md`](../../../docs/genacademy-rag-foundation.md)
- **Long-form trail (historical):** the brainstorm archive in the parent Week-3 folder — decision log
  (D1–D52), project board, option scorecards, improvements ledger.

## Thursday MVP — the one thing the plan must deliver

An **adaptive teach loop** on LangChain `create_agent`, grounded in the owned corpus:
**explain a concept (cited) → check understanding → re-explain a _different_ way when the learner
stumbles**, with a within-session learner profile, and **refuse-or-escalate** when retrieval can't cite
it. Quiz and mock-interview are pull-in modes — **not** in the MVP. Agenticity is proven by a
**runtime-decision trace** (re-explain vs. advance vs. refuse, chosen from observations — not a script).

## What the implementation plan (`docs/superpowers/plans/`) must cover

1. **Foundation adapter first** — the read-only audit of `genacademy-rag` public interfaces → a tiny
   adapter spec (per `genacademy-rag-foundation.md` "first build task"), **before** any agent code.
2. **Corpus ingest** — extend (don't rebuild) the Week-2 index with the owned corpus via the Week-2
   section-aware chunker; idempotent; same embedder (`all-MiniLM-L6-v2` / 384-d).
3. **The `create_agent` teach loop** — toolset (retriever, grade-understanding, profile update), the
   re-explain branch, the refuse/escalate branch. MINT restraint: no MCP / A2A / explicit LangGraph.
4. **Eval split + harness reuse** — hard seed/dev/test split of the held-out student chat-questions
   (corpus-independent, never indexed); test stays frozen; recalibrate thresholds against the new index.
5. **Failure path + HITL** — the graded differentiator: refusal + escalation + the recovery mechanisms.
6. **Demo trace + deliverables** — the runtime-decision trace, the ≤5-min video, the write-up.

## Constraints carried from the constitution (review-blockers, not aspirations)

Gates §2 (no code until plan approved · builder ≠ reviewer · evidence before done · sacred held-out test
set · failure path is the differentiator) and guardrails §3 (grounded-or-refuse · real confidence signal
· citations captured at retrieval · pure core / thin view · reuse Week-2) gate every change.
