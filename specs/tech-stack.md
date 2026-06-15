# Tech Stack

The framework is the handout's **Track 2** (code-heavy). The discipline is **MINT** — earn each layer;
default to the lightest tool and justify every step up.

## The stack (Week-3 MVP)

| Layer | Choice | Why |
|---|---|---|
| Agent | **LangChain `create_agent`** | Standard agent entry point; a model-chooses-tools loop. Built on LangGraph, so middleware, a typed state schema, checkpointers, and HITL-interrupt middleware are available later **without a rewrite**. Matches the cohort `agentic_rag` reference; fastest to ship. |
| Generative call | **Nebius Token Factory** | Routes the `generate_check_item` call (rubric requires ≥1 Nebius call; the richest call to showcase). |
| Retrieval | **2–3 retriever tools** over the corpus | Multi-tool router/decomposition: the model picks *which* corpus (lectures / assignments / student-qa) at runtime. Tool docstrings are the routing logic; a decomposition nudge in the system prompt buys planning with no planner node. |
| Corpus | **CohortBrain processed data** + curated handouts | Pre-segmented Week 1–2 lectures/assignments with metadata + timestamps for citations. Attribution/permission to confirm before use; nothing committed to this repo. |
| State | **Within-session learner profile** (in-memory) | `style · known[] · struggled[] · coverage · transcript`. Durable cross-session state = deferred. |
| Grading | **Deterministic** where possible | MCQ grading is index-match (no model). Open-answer grading (interview pull-in) is grounded against the retrieved span. |
| Eval | **Item-quality on a hard-split, held-out test set** | answerability · unique-correct · distractor validity · citation support · no span-leakage. Deterministic grading alone masks bad items. |
| Build tooling | **Codex / Claude Code** | Vibe-coding; builder and reviewer are **different** models (AGENTS §2). |

## Binding guardrails (full text in `AGENTS.md` §3 — repeated here as stack constraints)

- **Grounded-or-refuse**; confidence from **real signals** (retrieval similarity + citation-present),
  never an LLM self-rating. Bands: STOP < 0.60 · CONFIRM 0.60–0.85 · PROCEED > 0.85.
- **Citations captured at retrieval, never reconstructed.**
- **Agenticity = runtime decisioning shown in a trace**, not a scripted loop.
- **Pure core / thin view**: agent + retrieval + grading logic is testable with no web-framework imports.

## Deliberately deferred — and the trigger that earns each

| Deferred | Earned when |
|---|---|
| **LangGraph** (explicit graph) | Cross-session memory or a real pause/resume HITL **interrupt** becomes demo-core, or state transitions must be auditable. `create_agent` covers the MVP. |
| **MCP / A2A** | More tools/pipelines than one corpus + a few read tools (MCP); a genuine multi-agent split **across systems** (A2A). Neither applies now. |
| **Mem0 cross-session memory** | The rollout — "remembers you across days" (semantic + episodic). |
| **Caching (L1/L4/L5) + model tiering** | Cost/scale matters (multi-user). Trivial for one user now. |
| **Layout-aware re-ingestion** (LlamaParse / LiteParse) | Raw PDFs with diagrams enter the corpus. CohortBrain data arrives pre-segmented, so not yet. |
| **Voice (ElevenLabs) / multimodal** | After the text engine ships and demos end-to-end. |

## Repo conventions (mirrors `genacademy-rag`)

- `AGENTS.md` is the tool-neutral source of truth; `CLAUDE.md` is a thin mirror.
- Pluggability via interface + config, not branching (`if provider == ...` scattered through logic is a
  reject).
- Reference API calls (LangChain / Nebius signatures, model IDs, embedding dimensions) are pasted
  verbatim into the relevant spec, never reconstructed from memory.
