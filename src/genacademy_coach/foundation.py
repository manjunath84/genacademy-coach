from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from genacademy_rag.config import Settings as RagSettings
from genacademy_rag.core.chunker import build_chunker
from genacademy_rag.core.pipeline import IngestPipeline
from genacademy_rag.core.providers import build_provider
from genacademy_rag.core.reranker import build_reranker
from genacademy_rag.core.retriever import DEFAULT_CANDIDATE_K, HybridRetriever
from genacademy_rag.core.types import Document, RetrievedChunk
from genacademy_rag.core.vectorstore import VectorStore, build_vectorstore
from genacademy_rag.data.datastore import SQLiteDatastore

from genacademy_coach.settings import CoachSettings


def source_priority_map(source_priority: tuple[str, ...]) -> dict[str, int]:
    return {source_type: rank for rank, source_type in enumerate(source_priority)}


def reorder_spans(spans: list[dict[str, Any]], priority: dict[str, int]) -> list[dict[str, Any]]:
    return sorted(
        spans,
        key=lambda item: (
            priority.get(str(item.get("source_type", "")), len(priority)),
            -float(item.get("score", 0.0)),
            str(item.get("chunk_id", "")),
        ),
    )


def select_retrieved_spans(
    spans: list[dict[str, Any]],
    priority: dict[str, int],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    ordered = reorder_spans(spans, priority)
    selected = ordered[:limit]
    top_scored = max(
        spans,
        key=lambda item: (float(item.get("score", 0.0)), str(item.get("chunk_id", ""))),
        default=None,
    )
    if top_scored is not None and top_scored not in selected:
        selected = [*selected[:-1], top_scored] if selected else [top_scored]
    return selected


def rag_settings_for_coach(coach: CoachSettings) -> RagSettings:
    return replace(
        RagSettings.from_env(),
        chroma_dir=coach.chroma_dir,
        sqlite_path=coach.sqlite_path,
    )


def build_course_vectorstore(
    coach: CoachSettings,
    rag: RagSettings | None = None,
) -> VectorStore:
    return build_vectorstore(
        rag or rag_settings_for_coach(coach),
        collection=coach.course_collection,
    )


@dataclass
class Foundation:
    rag_settings: RagSettings
    coach_settings: CoachSettings
    provider: Any
    store: VectorStore
    datastore: SQLiteDatastore
    chroma_dir: Path
    sqlite_path: Path

    @classmethod
    def build(
        cls,
        coach_settings: CoachSettings | None = None,
        *,
        provider: Any | None = None,
    ) -> Foundation:
        coach = coach_settings or CoachSettings.from_env()
        rag = rag_settings_for_coach(coach)
        active_provider = provider or build_provider(rag)
        store = build_course_vectorstore(coach, rag)
        datastore = SQLiteDatastore(coach.sqlite_path)
        return cls(
            rag_settings=rag,
            coach_settings=coach,
            provider=active_provider,
            store=store,
            datastore=datastore,
            chroma_dir=coach.chroma_dir,
            sqlite_path=coach.sqlite_path,
        )

    def ingest(self, docs: list[Document]) -> int:
        chunker = build_chunker(
            "section",
            chunk_size=self.rag_settings.chunk_size,
            chunk_overlap=self.rag_settings.chunk_overlap,
            section_max_chars=self.rag_settings.section_chunk_max_chars,
            section_overlap=self.rag_settings.section_chunk_overlap,
        )
        pipe = IngestPipeline(
            chunker=chunker,
            provider=self.provider,
            store=self.store,
            datastore=self.datastore,
        )
        return pipe.ingest(docs)

    def retriever(self) -> HybridRetriever:
        return HybridRetriever(
            store=self.store,
            provider=self.provider,
            all_chunks=self.store.get_all_chunks(),
            # Over-fetch from Week-2 so Coach can apply source-priority ordering afterward.
            top_k=self.coach_settings.retrieval_candidate_k,
            candidate_k=max(DEFAULT_CANDIDATE_K, self.coach_settings.retrieval_candidate_k),
            reranker=build_reranker(self.rag_settings),
            rerank_pool=self.rag_settings.rerank_pool,
        )

    def retrieve(self, query: str) -> list[dict[str, Any]]:
        results: list[RetrievedChunk] = self.retriever().retrieve(query)
        spans = [
            {
                "chunk_id": item.chunk.chunk_id,
                "doc_id": item.chunk.doc_id,
                "text": item.chunk.text,
                "score": item.score,
                "title": item.chunk.citation.title,
                "source_type": item.chunk.citation.source_type,
                "page_or_section": item.chunk.citation.page_or_section,
            }
            for item in results
        ]
        priority = source_priority_map(self.coach_settings.source_priority)
        return select_retrieved_spans(
            spans,
            priority,
            limit=self.coach_settings.retrieval_top_k,
        )
