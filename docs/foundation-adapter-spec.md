# Foundation Adapter Spec

Status: implementation-pinned after reading the Week-2 repo.

## Week-2 package

Local editable dependency: `../../Week2-RAG_ContextEngineering/genacademy-rag`.

This dependency supplies reusable code only. It does not contain the Week-3 owned course corpus. The
source documents to ingest live under this repo's ignored `corpus/` directory.

## Imports the Coach adapter may use

- `from genacademy_rag.config import Settings`
- `from genacademy_rag.core.chunker import build_chunker`
- `from genacademy_rag.core.pipeline import IngestPipeline`
- `from genacademy_rag.core.providers import build_provider`
- `from genacademy_rag.core.reranker import build_reranker`
- `from genacademy_rag.core.retriever import DEFAULT_CANDIDATE_K, HybridRetriever`
- `from genacademy_rag.core.types import Citation, Chunk, Document, RetrievedChunk`
- `from genacademy_rag.core.vectorstore import ChromaStore`
- `from genacademy_rag.data.datastore import SQLiteDatastore`

## Week-2 calls

- `Settings.from_env()` supplies provider, embedder, chunking, rerank, and top-k config. The Coach
  adapter calls it for reusable Week-2 settings, then pins the returned Chroma and SQLite paths to
  `CoachSettings.chroma_dir` and `CoachSettings.sqlite_path`.
- `build_provider(settings)` returns a provider with `embed(texts)` and `generate(messages, ...)`.
- `ChromaStore(persist_dir=coach_settings.chroma_dir, collection="coach_course")` stores course
  vectors.
- `SQLiteDatastore(coach_settings.sqlite_path)` stores document/chunk metadata.
- `build_chunker("section", chunk_size=..., chunk_overlap=..., section_max_chars=..., section_overlap=...)`
  returns the section-aware chunker.
- `IngestPipeline(chunker=..., provider=..., store=..., datastore=...)` prepares and commits Week-2
  `Document` objects.
- `HybridRetriever(store=..., provider=..., all_chunks=store.get_all_chunks(), top_k=..., candidate_k=DEFAULT_CANDIDATE_K, reranker=build_reranker(settings), rerank_pool=settings.rerank_pool)`
  retrieves `RetrievedChunk` objects.

## Audited Week-2 path fields

- `Settings.from_env()` uses `GENACADEMY_DATA_DIR` as the default parent for `chroma_dir` and
  `sqlite_path`.
- `CoachSettings.data_dir` uses `GENACADEMY_COACH_DATA_DIR` or defaults to `genacademy-coach/data/`.
- Coach exposes one artifact relocation knob for this slice: `GENACADEMY_COACH_DATA_DIR`. Chroma and
  SQLite stay under that directory by construction.
- Week-2 also honors `GENACADEMY_CHROMA_DIR` and `GENACADEMY_SQLITE`, so the adapter must not trust
  those returned path fields. It replaces them with Coach-derived paths before constructing stores.
- `SQLiteDatastore` creates the parent directory but does not expose the SQLite path after
  construction.
- The Coach adapter must store `chroma_dir` and `sqlite_path` on `Foundation`, assert both resolve
  under `CoachSettings.data_dir`, and assert a real ingest does not write into simulated Week-2
  artifact paths. This prevents stale Week-2 environment variables from writing artifacts into the
  sibling `genacademy-rag` repo.

## Data ownership boundary

- `genacademy-rag` = reusable RAG machinery and existing Week-2 eval/demo corpus.
- `genacademy-coach/corpus/` = Week-3 owned course corpus: notes, transcripts, slides, handouts, and
  never-indexed eval questions.
- `genacademy-coach/data/` = generated local Coach Chroma/SQLite artifacts, ignored by git.
- The adapter converts local Coach corpus files into Week-2 `Document` objects, then passes those
  objects into Week-2 `IngestPipeline`.
- No code should assume Week-2 already has the Coach corpus indexed.

## Eval harness delta

Week-2's eval harness scores retrieval/faithfulness against a gold set. It does not provide the
Coach-owned held-out chat-question split, private-source manifest, or leak guard. `eval_split.py` is
additive data governance for the sacred held-out set; it is not a replacement for the Week-2 retrieval
or faithfulness evaluators.

## Coach rules

- The Coach repo must not import `langgraph.*` directly.
- The Coach repo must not rebuild the embedder, chunker, vector schema, refusal scheme, or eval
  harness.
- The Coach repo may create text loaders for local `.pptx` and `.docx` files because Week-2 does not
  provide those loaders.
- The MVP is text-only RAG. Multimodal RAG is deferred until extraction reports or eval failures show
  that image-only slide content blocks the teach loop.
