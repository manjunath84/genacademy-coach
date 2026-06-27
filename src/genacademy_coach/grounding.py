from __future__ import annotations

import re

from genacademy_rag.core.types import Chunk, Citation, RetrievedChunk
from genacademy_rag.eval.faithfulness_eval import citation_grounding_score

from genacademy_coach.semantic_grading import SCORER_VERSION, keyword_match_mode
from genacademy_coach.teach_types import CheckItem, EvidenceBand, RetrievedSpan, UnderstandingGrade

WORD_RE = re.compile(r"[a-z0-9]+")
CITATION_MARKER_RE = re.compile(r"\[[^\]]+\]")


def normalized_terms(text: str) -> set[str]:
    return set(WORD_RE.findall(text.lower()))


def normalized_phrase(text: str) -> str:
    return " ".join(WORD_RE.findall(text.lower()))


def keyword_present(answer: str, keyword: str) -> bool:
    normalized_answer = f" {normalized_phrase(answer)} "
    normalized_keyword = normalized_phrase(keyword)
    return bool(normalized_keyword) and f" {normalized_keyword} " in normalized_answer


def evidence_score(spans: list[RetrievedSpan]) -> float:
    return max((span.score for span in spans), default=0.0)


def evidence_band(
    score: float,
    *,
    stop_threshold: float,
    confirm_threshold: float,
) -> EvidenceBand:
    if score < stop_threshold:
        return "stop"
    if score < confirm_threshold:
        return "confirm"
    return "proceed"


def require_citeable_spans(
    spans: list[RetrievedSpan],
    *,
    stop_threshold: float,
) -> list[RetrievedSpan]:
    return [
        span
        for span in spans
        if span.score >= stop_threshold and bool(span.text.strip()) and bool(span.citation_id)
    ]


def grade_understanding(answer: str, item: CheckItem) -> UnderstandingGrade:
    matched: list[str] = []
    missing: list[str] = []
    modes: dict[str, str] = {}

    for keyword in item.expected_keywords:
        mode = keyword_match_mode(answer, keyword)
        if mode is None:
            missing.append(keyword)
        else:
            matched.append(keyword)
            modes[keyword] = mode

    return UnderstandingGrade(
        correct=not missing,
        matched_keywords=matched,
        missing_keywords=missing,
        citation_id=item.citation_id,
        scorer_version=SCORER_VERSION,
        matched_keyword_modes=modes,
    )


def _ordinal_from_chunk_id(chunk_id: str) -> int:
    tail = chunk_id.rsplit("::", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def _to_week2_retrieved(span: RetrievedSpan) -> RetrievedChunk:
    citation = Citation(
        doc_id=span.doc_id,
        title=span.title,
        source_type=span.source_type,
        page_or_section=span.page_or_section,
    )
    return RetrievedChunk(
        chunk=Chunk(
            chunk_id=span.chunk_id,
            doc_id=span.doc_id,
            ordinal=_ordinal_from_chunk_id(span.chunk_id),
            text=span.text,
            citation=citation,
        ),
        score=span.score,
    )


def answer_grounded_in_spans(answer: str, spans: list[RetrievedSpan]) -> bool:
    cleaned = CITATION_MARKER_RE.sub("", answer)
    return citation_grounding_score(cleaned, [_to_week2_retrieved(span) for span in spans])
