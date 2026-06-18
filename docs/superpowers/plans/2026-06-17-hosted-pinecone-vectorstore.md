# Hosted Pinecone Vectorstore Reuse Plan

Status: implementation PR in progress; requires different-model review before merge.

## Purpose

Make the Hugging Face Space capable of serving grounded Coach requests from a hosted vector index without uploading private Chroma artifacts to the Space.

This is not a new retriever. It reuses the Week-2 `genacademy-rag` vectorstore factory and keeps the same embedder/dimension contract:
`all-MiniLM-L6-v2` / `384`.

## Scope

- Replace Coach's direct `ChromaStore` construction with Week-2 `build_vectorstore(settings, collection=...)`.
- Keep local default behavior as Chroma.
- Configure the HF deploy script for a Coach-specific Pinecone index and namespace.
- Add a Pinecone Space secret path without printing or committing the key.
- Update the Space empty-corpus/status wording so it refers to the active vectorstore, not only Chroma.

## Guardrails

- No private corpus, traces, eval prompts, generated quiz text, or secrets are uploaded.
- The held-out `test` split remains unused.
- Pinecone is only storage for retrieved course chunks; grounded-or-refuse behavior is unchanged.
- The Coach uses a Coach-specific Pinecone index (`genacademy-coach`) and namespace (`GENACADEMY_COACH_COLLECTION=coach_course`) instead of reusing Week-2 production data.
- No new dependencies, direct `langgraph.*` imports, memory provider, or web framework in core.

## Verification

- Unit tests cover the vectorstore factory handoff and HF deploy variables/secrets.
- `uv run pytest -q`
- `uv run ruff check .`
- `uv run python scripts/check_eval_leak.py`
- If deployed, authenticated HF root smoke must still return `HTTP/2 200`; provider-backed behavior requires an approved, seeded Pinecone namespace.
