from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain.tools import tool

from genacademy_coach.check_items import generate_check_item
from genacademy_coach.escalation import append_review_queue
from genacademy_coach.grounding import (
    evidence_band,
    evidence_score,
    require_citeable_spans,
)
from genacademy_coach.grounding import (
    grade_understanding as grade_answer_understanding,
)
from genacademy_coach.teach_types import (
    CheckItem,
    EvidenceBand,
    LearnerProfile,
    RetrievedSpan,
    UnderstandingGrade,
)


@dataclass
class TeachRuntime:
    session_id: str
    topic: str
    profile: LearnerProfile
    foundation: Any
    stop_threshold: float
    confirm_threshold: float
    review_queue_path: Path
    last_spans: list[RetrievedSpan] = field(default_factory=list)
    current_check: CheckItem | None = None
    last_grade: UnderstandingGrade | None = None
    grade_locked: bool = False
    tool_calls: list[str] = field(default_factory=list)
    escalation_queued: bool = False

    def record_tool(self, name: str) -> None:
        self.tool_calls.append(name)

    def current_evidence_score(self) -> float:
        return evidence_score(self.last_spans)

    def current_evidence_band(self) -> EvidenceBand:
        return evidence_band(
            self.current_evidence_score(),
            stop_threshold=self.stop_threshold,
            confirm_threshold=self.confirm_threshold,
        )


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


def build_teach_tools(runtime: TeachRuntime):
    @tool
    def retrieve_course_corpus(query: str) -> str:
        """Retrieve citeable Gen Academy course spans for the learner's current topic."""
        runtime.record_tool("retrieve_course_corpus")
        spans = [_span_from_row(row) for row in runtime.foundation.retrieve(query)]
        citeable_spans = require_citeable_spans(
            spans,
            stop_threshold=runtime.stop_threshold,
        )
        if citeable_spans:
            runtime.last_spans = citeable_spans
        rows = [
            {
                "citation_id": span.citation_id,
                "title": span.title,
                "source_type": span.source_type,
                "score": span.score,
                "evidence_band": runtime.current_evidence_band(),
                "text": span.text,
            }
            for span in citeable_spans
        ]
        return json.dumps(rows, sort_keys=True)

    @tool
    def generate_check_item_for_span(citation_id: str) -> str:
        """Generate a short grounded check question for a retrieved citation ID."""
        runtime.record_tool("generate_check_item")
        span_by_id = {span.citation_id: span for span in runtime.last_spans}
        if citation_id not in span_by_id:
            return json.dumps({"error": f"unknown citation_id: {citation_id}"})
        runtime.current_check = generate_check_item(
            runtime.foundation.provider,
            span_by_id[citation_id],
        )
        return runtime.current_check.model_dump_json()

    @tool
    def grade_understanding(answer: str) -> str:
        """Grade the learner answer against the current grounded check item."""
        runtime.record_tool("grade_understanding")
        if runtime.grade_locked and runtime.last_grade is not None:
            return runtime.last_grade.model_dump_json()
        if runtime.current_check is None:
            return json.dumps({"error": "no current check item"})
        runtime.last_grade = grade_answer_understanding(answer, runtime.current_check)
        runtime.profile.last_grade_correct = runtime.last_grade.correct
        return runtime.last_grade.model_dump_json()

    @tool
    def update_profile(known: list[str], struggled: list[str]) -> str:
        """Update the within-session learner profile with concepts known or struggled with."""
        runtime.record_tool("update_profile")
        runtime.profile.known = sorted(set([*runtime.profile.known, *known]))
        runtime.profile.struggled = sorted(set([*runtime.profile.struggled, *struggled]))
        return runtime.profile.model_dump_json()

    @tool
    def escalate_to_mentor(reason: str) -> str:
        """Queue a mentor review when the tutor cannot cite a safe answer."""
        runtime.record_tool("escalate_to_mentor")
        if not runtime.escalation_queued:
            append_review_queue(
                runtime.review_queue_path,
                session_id=runtime.session_id,
                topic=runtime.topic,
                reason=reason,
                score=runtime.current_evidence_score(),
                citation_ids=[span.citation_id for span in runtime.last_spans],
            )
            runtime.escalation_queued = True
        return json.dumps({"queued": True, "reason": reason}, sort_keys=True)

    return [
        retrieve_course_corpus,
        generate_check_item_for_span,
        grade_understanding,
        update_profile,
        escalate_to_mentor,
    ]
