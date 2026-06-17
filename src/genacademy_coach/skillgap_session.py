from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from genacademy_coach.escalation import append_review_queue
from genacademy_coach.grounding import evidence_band, evidence_score, require_citeable_spans
from genacademy_coach.skillgap_types import SkillGapItem, SkillGapReport, SkillGapTraceRow
from genacademy_coach.teach_types import RetrievedSpan

NO_CITEABLE_SKILL_GAP_REVIEW = "no citeable course corpus found for skill gap review"
SAFE_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def validate_skillgap_session_id(value: str) -> str:
    session_id = value.strip()
    if not session_id:
        raise ValueError("session id is required")
    if session_id in {".", ".."} or not SAFE_SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError(
            "session id may only contain letters, numbers, dots, dashes, underscores, or colons"
        )
    return session_id


def _span_from_row(row: dict[str, Any]) -> RetrievedSpan:
    return RetrievedSpan(
        chunk_id=str(row["chunk_id"]),
        doc_id=str(row["doc_id"]),
        text=str(row["text"]),
        score=float(row["score"]),
        title=str(row["title"]),
        source_type=str(row["source_type"]),
        page_or_section=row.get("page_or_section"),
    )


def _review_next_for_span(span: RetrievedSpan) -> str:
    metadata = [span.source_type.strip()] if span.source_type.strip() else []
    if span.page_or_section is not None and str(span.page_or_section).strip():
        metadata.append(str(span.page_or_section).strip())
    suffix = f" ({', '.join(metadata)})" if metadata else ""
    return f"Review {span.title}{suffix} at {span.citation_id}."


@dataclass
class _GapAggregate:
    gap_id: str
    topic_hash: str
    source_session_ids: set[str] = field(default_factory=set)
    quiz_correct: int = 0
    quiz_total: int = 0
    struggle_count: int = 0
    refusal_count: int = 0
    confirm_count: int = 0

    @property
    def priority_score(self) -> int:
        quiz_incorrect = self.quiz_total - self.quiz_correct
        return (
            quiz_incorrect * 3
            + self.struggle_count * 2
            + self.refusal_count * 2
            + self.confirm_count
            - self.quiz_correct * 2
        )


class SkillGapTraceWriter:
    def __init__(self, trace_dir: Path):
        self._trace_dir = trace_dir

    def append(self, row: SkillGapTraceRow) -> Path:
        self._trace_dir.mkdir(parents=True, exist_ok=True)
        path = self._trace_dir / f"{row.session_id}.jsonl"
        payload = row.model_dump(mode="json")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
        return path


@dataclass
class SkillGapSession:
    session_id: str
    source_session_ids: list[str]
    settings: Any
    foundation: Any
    trace_writer: SkillGapTraceWriter = field(init=False)

    def __post_init__(self) -> None:
        self.session_id = validate_skillgap_session_id(self.session_id)
        self.source_session_ids = [
            validate_skillgap_session_id(session_id) for session_id in self.source_session_ids
        ]
        if not self.source_session_ids:
            raise ValueError("source_session_ids must contain at least one session")
        self.trace_writer = SkillGapTraceWriter(self.settings.trace_dir)

    def run(self) -> SkillGapReport:
        aggregates = self._load_aggregates()
        items = [self._review_gap(gap) for gap in self._rank_gaps(aggregates)]
        trace_path = self._write_trace(items)
        return SkillGapReport(
            session_id=self.session_id,
            source_session_ids=list(self.source_session_ids),
            items=items,
            trace_path=str(trace_path),
        )

    def _load_aggregates(self) -> dict[str, _GapAggregate]:
        aggregates: dict[str, _GapAggregate] = {}
        for session_id in self.source_session_ids:
            trace_path = self.settings.trace_dir / f"{session_id}.jsonl"
            if trace_path.exists():
                for row in _jsonl_rows(trace_path):
                    if "gap_id" in row:
                        continue
                    if "turn" in row:
                        self._add_teach_signal(aggregates, session_id, row)
                    elif "question_ids" in row:
                        self._add_quiz_signal(aggregates, session_id, row)
        self._add_review_queue_signals(aggregates)
        return aggregates

    def _aggregate(
        self,
        aggregates: dict[str, _GapAggregate],
        *,
        gap_id: str,
        topic_hash: str,
        session_id: str,
    ) -> _GapAggregate:
        gap = aggregates.get(gap_id)
        if gap is None:
            gap = _GapAggregate(gap_id=gap_id, topic_hash=topic_hash)
            aggregates[gap_id] = gap
        if gap.topic_hash.startswith("derived-") and not topic_hash.startswith("derived-"):
            gap.topic_hash = topic_hash
        gap.source_session_ids.add(session_id)
        return gap

    def _add_teach_signal(
        self,
        aggregates: dict[str, _GapAggregate],
        session_id: str,
        row: dict[str, Any],
    ) -> None:
        citation_ids = [str(item) for item in row.get("retrieved_citation_ids", [])]
        action = str(row.get("next_action", ""))
        gap_id = citation_ids[0] if citation_ids else f"teach:{session_id}"
        gap = self._aggregate(
            aggregates,
            gap_id=gap_id,
            topic_hash=f"derived-{_hash_text(gap_id)}",
            session_id=session_id,
        )
        if action in {"re_explain_differently", "drill"}:
            gap.struggle_count += 1
        if action == "refuse_escalate":
            gap.refusal_count += 1
        if row.get("evidence_band") == "confirm":
            gap.confirm_count += 1

    def _add_quiz_signal(
        self,
        aggregates: dict[str, _GapAggregate],
        session_id: str,
        row: dict[str, Any],
    ) -> None:
        citation_ids = [str(item) for item in row.get("citation_ids", [])]
        question_ids = [str(item) for item in row.get("question_ids", [])]
        correctness = [bool(item) for item in row.get("correctness", [])]
        topic_hash = str(row.get("topic_hash") or f"derived-{_hash_text(session_id)}")
        if row.get("refusal_reason"):
            gap_id = citation_ids[0] if citation_ids else f"quiz:{session_id}:refusal"
            gap = self._aggregate(
                aggregates,
                gap_id=gap_id,
                topic_hash=topic_hash,
                session_id=session_id,
            )
            gap.refusal_count += 1
            return
        for index, correct in enumerate(correctness):
            gap_id = (
                citation_ids[index]
                if index < len(citation_ids)
                else question_ids[index]
                if index < len(question_ids)
                else f"quiz:{session_id}:{index + 1}"
            )
            gap = self._aggregate(
                aggregates,
                gap_id=gap_id,
                topic_hash=topic_hash,
                session_id=session_id,
            )
            gap.quiz_total += 1
            if correct:
                gap.quiz_correct += 1
            if row.get("evidence_band") == "confirm":
                gap.confirm_count += 1

    def _add_review_queue_signals(self, aggregates: dict[str, _GapAggregate]) -> None:
        path = self.settings.review_queue_path
        if not path.exists():
            return
        source_ids = set(self.source_session_ids)
        for row in _jsonl_rows(path):
            session_id = str(row.get("session_id", ""))
            if session_id not in source_ids:
                continue
            reason = str(row.get("reason") or "review")
            citation_ids = [str(item) for item in row.get("citation_ids", [])]
            gap_id = (
                citation_ids[0]
                if citation_ids
                else f"review:{session_id}:{_hash_text(reason)}"
            )
            gap = self._aggregate(
                aggregates,
                gap_id=gap_id,
                topic_hash=f"derived-{_hash_text(gap_id)}",
                session_id=session_id,
            )
            gap.refusal_count += 1

    def _rank_gaps(self, aggregates: dict[str, _GapAggregate]) -> list[_GapAggregate]:
        return sorted(
            aggregates.values(),
            key=lambda gap: (-gap.priority_score, gap.gap_id),
        )

    def _review_gap(self, gap: _GapAggregate) -> SkillGapItem:
        raw_spans = [_span_from_row(row) for row in self.foundation.retrieve(gap.gap_id)]
        score = evidence_score(raw_spans)
        band = evidence_band(
            score,
            stop_threshold=self.settings.stop_threshold,
            confirm_threshold=self.settings.confirm_threshold,
        )
        citeable_spans = require_citeable_spans(
            raw_spans,
            stop_threshold=self.settings.stop_threshold,
        )
        if not citeable_spans:
            append_review_queue(
                self.settings.review_queue_path,
                session_id=self.session_id,
                topic=gap.gap_id,
                reason=NO_CITEABLE_SKILL_GAP_REVIEW,
                score=score,
                citation_ids=[],
            )
            return SkillGapItem(
                gap_id=gap.gap_id,
                topic_hash=gap.topic_hash,
                source_session_ids=sorted(gap.source_session_ids),
                priority_score=gap.priority_score,
                evidence_score=score,
                evidence_band=band,
                quiz_correct=gap.quiz_correct,
                quiz_total=gap.quiz_total,
                struggle_count=gap.struggle_count,
                refusal_count=gap.refusal_count,
                next_action="refuse_escalate",
                escalated=True,
                reason_code=NO_CITEABLE_SKILL_GAP_REVIEW,
            )
        span = citeable_spans[0]
        return SkillGapItem(
            gap_id=gap.gap_id,
            topic_hash=gap.topic_hash,
            source_session_ids=sorted(gap.source_session_ids),
            priority_score=gap.priority_score,
            evidence_score=score,
            evidence_band=band,
            citation_ids=[span.citation_id],
            quiz_correct=gap.quiz_correct,
            quiz_total=gap.quiz_total,
            struggle_count=gap.struggle_count,
            refusal_count=gap.refusal_count,
            next_action="review_next",
            review_next=_review_next_for_span(span),
        )

    def _write_trace(self, items: list[SkillGapItem]) -> Path:
        path = self.settings.trace_dir / f"{self.session_id}.jsonl"
        if path.exists():
            path.unlink()
        self.settings.trace_dir.mkdir(parents=True, exist_ok=True)
        path.touch()
        for item in items:
            self.trace_writer.append(
                SkillGapTraceRow(
                    session_id=self.session_id,
                    topic_hash=item.topic_hash,
                    gap_id=item.gap_id,
                    source_session_ids=item.source_session_ids,
                    evidence_score=item.evidence_score,
                    evidence_band=item.evidence_band,
                    citation_ids=item.citation_ids,
                    quiz_correct=item.quiz_correct,
                    quiz_total=item.quiz_total,
                    struggle_count=item.struggle_count,
                    refusal_count=item.refusal_count,
                    next_action=item.next_action,
                    escalated=item.escalated,
                    reason_code=item.reason_code,
                )
            )
        return path


def _jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            rows.append(value)
    return rows
