# Foundation: `genacademy-rag` (Week-2) — reuse, don't reinvent

> **Why this file exists.** GenAcademy Coach is **not** a greenfield project. It is an agentic layer on
> top of the author's Week-2 system **`genacademy-rag`** (a refusal-first RAG app, deployed on Hugging
> Face Spaces). That system already provides the retrieval, chunking, grounding/refusal, citation, and
> **evaluation** machinery the Coach needs. Every planning and building agent must treat Week-2 as the
> **foundation to extend**, not a thing to rebuild. This file is the single, verified reference so the
> dependency is **never missed or re-derived from memory.**
>
> **Status:** verified on disk 2026-06-15 against the live repo. Re-verify before quoting any number
> (AGENTS §4). If a fact here drifts from the Week-2 repo, the repo wins — update this file.

## Where it lives

- **Local path:** `/Users/manjunathans/projects/GenAcademy/Week2-RAG_ContextEngineering/genacademy-rag/`
- **Package:** `src/genacademy_rag/` (installable; `core/`, `eval/`, `data/`, `web/`).
- A separate git repo (not this one) and a deployed HF Space. The Coach repo does **not** vendor it; it
  depends on it through a thin **adapter** (see "Reuse contract").

## Verified Week-2 facts (the reuse surface)

| Capability | What Week-2 already has | Module / artifact |
|---|---|---|
| **Embeddings** | `all-MiniLM-L6-v2`, **384-dim**, local via `sentence-transformers==5.5.1` (Nebius `Qwen/Qwen3-Embedding-8B` 4096-d is an alt preset) | `core/vectorstore.py`, `.env.example` |
| **Vector store** | `build_vectorstore(settings, collection=...)` selects **Chroma** (`chromadb==1.5.9`) locally by default or Pinecone for hosted serving. Eval always uses local Chroma. | `core/vectorstore.py`, `data/chroma/` |
| **Chunker** | Section-aware chunker, **A/B-tested** (see `eval/phase2-section-aware-chunking-delta.md`) | `core/chunker.py` |
| **Loaders** | markdown, PDF, Jupyter, GitHub fetcher | `core/loaders/*` |
| **Retriever** | **One** retriever over **one** active vectorstore collection/namespace (+ optional cross-encoder rerank `cross-encoder/ms-marco-MiniLM-L6-v2`, off by default) | `core/retriever.py`, `core/reranker.py` |
| **Grounding / refusal / citation** | Refusal-first pipeline; citations carry `week · title` + span metadata; deterministic JSON grader gate | `core/pipeline.py`, `core/grader.py`, `core/graph.py` |
| **Generation provider** | OpenAI-compatible behind `ModelProvider.generate()` — `openrouter \| openai \| nebius \| gemma`. **Nebius Token Factory** = the rubric-required call. | `core/providers.py` |
| **Eval harness** | Retrieval metrics (recall@k / precision@k / MRR), **refusal-correctness**, faithfulness (LLM-judge), gold schema + gold set, report generator | `eval/{retrieval_eval,faithfulness_eval,gold_schema,report}.py`, `scripts/run_eval.py`, `scripts/eval_retrieval.py` |
| **Eval corpus ingest** | Dedicated eval-corpus ingestion path | `scripts/ingest_eval_corpus.py` |
| **Schema** | `chunks_meta(id, doc_id, ordinal, page_or_section, line_start, line_end, char_start, char_end, text_preview)`; `documents(...)` | `data/datastore.py`, `genacademy.sqlite` |

### Current index state (do NOT mistake for the Coach corpus)

- Committed production index (`genacademy.sqlite`): **4 documents → 53 chunks** (GitHub-sourced: an
  agentic-AI resources README + a LangChain-basics folder).
- Section-aware eval variant (`genacademy-eval_section.sqlite`): **73 chunks**.
- **The builder's lesson deep-notes and the 6 session transcripts (~176k words) are NOT in this index.**
  Extending the index with them is a Coach build task, not a given.

### Eval assets the Coach inherits

- **12-question gold set** (`src/genacademy_rag/eval/gold/`, schema in `gold_schema.py`), categories:
  `answerable · exact_match · chunking_stress · multi_document`. Last run: recall@k **0.79**,
  precision@k **0.25**, MRR **0.58**, refusal-correctness **1.00**, faithfulness **100%** (LLM-judge —
  same-model-judge caveat noted in `eval/REPORT.md`).
- **Real student chat-questions** (corpus-**independent** — students asked them live): staged under
  `genacademy-coach/corpus/eval-questions/`. These are the **leak-safe held-out eval source** for the
  Coach (never indexed, never in prompts/demo). Split IDs/checksums will be committed by the eval
  scaffold; private question content is not.

## Reuse contract (binding — a review-blocker if violated)

1. **Reuse, don't reinvent.** The Coach **must** reuse the Week-2 embedding model, vectorstore
   schema/factory, section-aware chunker, citation metadata, retrieval + rerank, refusal/grounding
   logic, and the **eval harness** — through a thin adapter. **Building a new chunker, embedder, vector schema,
   refusal/threshold scheme, or eval harness without a written delta** explaining why the Week-2 API
   can't support the need is a **reject**.
2. **Same-embedder rule.** The index is `all-MiniLM-L6-v2` / 384-d. Reusing the index means using the
   same embedder. Switching embedders = **re-ingest a fresh collection** (dimension mismatch fails loudly
   by design). Pick one and pin it.
3. **Extend the index, don't rebuild it.** Ingest the owned corpus (notes / transcripts / slides /
   handouts) into an **extended, version-pinned** collection via the Week-2 chunker. Idempotent ingest.
   Tag every chunk with source metadata so the Coach can prefer slides/handouts without splitting the
   retriever into brittle source-specific tools.
4. **Week-2 metrics are Week-2 evidence only.** The 53-chunk recall/precision numbers do **not** transfer
   to a 176k-word transcript-heavy corpus. **Recalibrate after ingestion;** never cite Week-2 recall as
   Coach evidence.
5. **Grader: deterministic primary, judge secondary.** Pass/fail uses the deterministic grounded grader
   (`core/grader.py`). The inherited **LLM-judge faithfulness** check stays available as a *secondary
   audit*, not the gate. (This supersedes any "no LLM-judge at all" wording elsewhere.)

## First build task (before any feature code)

A **read-only audit** of the `genacademy-rag` public interfaces (`core/retriever.py`,
`core/pipeline.py`, `core/grader.py`, `core/vectorstore.py`, `core/providers.py`, `eval/*`) → a **tiny
adapter spec** naming exactly which functions the Coach calls and what it passes. This pins the
foundation contract before the agent loop is built. Until that adapter exists, treat the Week-2 API as
unknown — do not assume signatures.

## Pointer: what the Coach reuses → which Week-2 module

- retrieval tool(s) → `core/retriever.py` (+ `core/reranker.py`)
- grounding/refusal/citation → `core/pipeline.py`, `core/grader.py`
- chunking/ingest of the owned corpus → `core/chunker.py`, `core/loaders/*`, `scripts/ingest_eval_corpus.py`
- Nebius generative call → `core/providers.py`
- eval (retrieval + refusal + faithfulness audit) → `eval/*`, `scripts/run_eval.py`
- held-out eval questions → `genacademy-coach/corpus/eval-questions/` (corpus-independent, never indexed)
