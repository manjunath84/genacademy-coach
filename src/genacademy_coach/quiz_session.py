from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from genacademy_coach.escalation import append_review_queue
from genacademy_coach.grounding import evidence_band, evidence_score, require_citeable_spans
from genacademy_coach.privacy import topic_hash
from genacademy_coach.quiz_items import generate_quiz_question
from genacademy_coach.quiz_trace import QuizTraceWriter
from genacademy_coach.quiz_types import (
    QuizGrade,
    QuizQuestion,
    QuizSessionResult,
    QuizTraceRow,
    grade_quiz,
)
from genacademy_coach.teach_types import EvidenceBand, RetrievedSpan

NO_CITEABLE_QUIZ_CORPUS = "no citeable course corpus found for quiz"
NO_GROUNDED_QUIZ_ITEMS = "could not generate grounded quiz items"


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


@dataclass
class QuizSession:
    session_id: str
    topic: str
    settings: Any
    foundation: Any
    question_count: int = 3
    trace_writer: QuizTraceWriter = field(init=False)

    def __post_init__(self) -> None:
        if self.question_count <= 0:
            raise ValueError("question_count must be positive")
        self.trace_writer = QuizTraceWriter(self.settings.trace_dir)

    def run(self, selected_option_ids: list[str] | None = None) -> QuizSessionResult:
        raw_spans, spans = self._retrieve_spans()
        score = evidence_score(raw_spans)
        band = evidence_band(
            score,
            stop_threshold=self.settings.stop_threshold,
            confirm_threshold=self.settings.confirm_threshold,
        )
        if not spans:
            return self._refuse(NO_CITEABLE_QUIZ_CORPUS, score=score, band=band)

        questions = self._generate_questions(spans)
        if len(questions) != self.question_count:
            return self._refuse(
                NO_GROUNDED_QUIZ_ITEMS,
                score=score,
                band=band,
                citation_ids=[span.citation_id for span in spans],
            )

        grades: list[QuizGrade] = (
            grade_quiz(questions, selected_option_ids) if selected_option_ids is not None else []
        )
        trace_path = self._write_trace(
            evidence_score_value=score,
            evidence_band_value=band,
            citation_ids=[question.citation_id for question in questions],
            question_ids=[question.question_id for question in questions],
            selected_option_ids=[grade.selected_option_id for grade in grades],
            correctness=[grade.correct for grade in grades],
            actions=["retrieve_course_corpus", "generate_quiz_items", "grade_quiz"]
            if grades
            else ["retrieve_course_corpus", "generate_quiz_items"],
        )
        return QuizSessionResult(
            session_id=self.session_id,
            questions=questions,
            grades=grades,
            score=sum(1 for grade in grades if grade.correct),
            trace_path=str(trace_path),
        )

    def _retrieve_spans(self) -> tuple[list[RetrievedSpan], list[RetrievedSpan]]:
        raw_spans = [_span_from_row(row) for row in self.foundation.retrieve(self.topic)]
        citeable_spans = require_citeable_spans(
            raw_spans,
            stop_threshold=self.settings.stop_threshold,
        )
        return raw_spans, citeable_spans

    def _generate_questions(self, spans: list[RetrievedSpan]) -> list[QuizQuestion]:
        questions: list[QuizQuestion] = []
        for span in spans:
            if len(questions) == self.question_count:
                break
            try:
                questions.append(
                    generate_quiz_question(
                        self.foundation.provider,
                        span,
                        question_id=f"q{len(questions) + 1}",
                    )
                )
            except (ValueError, ValidationError):
                continue
        return questions

    def _refuse(
        self,
        reason: str,
        *,
        score: float,
        band: EvidenceBand,
        citation_ids: list[str] | None = None,
    ) -> QuizSessionResult:
        cited = citation_ids or []
        append_review_queue(
            self.settings.review_queue_path,
            session_id=self.session_id,
            topic_hash=topic_hash(self.topic),
            reason=reason,
            score=score,
            citation_ids=cited,
        )
        trace_path = self._write_trace(
            evidence_score_value=score,
            evidence_band_value=band,
            citation_ids=cited,
            question_ids=[],
            selected_option_ids=[],
            correctness=[],
            refusal_reason=reason,
            actions=["retrieve_course_corpus", "refuse_escalate"],
        )
        return QuizSessionResult(
            session_id=self.session_id,
            score=0,
            refusal_reason=reason,
            trace_path=str(trace_path),
        )

    def _write_trace(
        self,
        *,
        evidence_score_value: float,
        evidence_band_value: EvidenceBand,
        citation_ids: list[str],
        question_ids: list[str],
        selected_option_ids: list[str],
        correctness: list[bool],
        actions: list[str],
        refusal_reason: str | None = None,
    ) -> Path:
        return self.trace_writer.append(
            QuizTraceRow(
                session_id=self.session_id,
                topic_hash=topic_hash(self.topic),
                evidence_score=evidence_score_value,
                evidence_band=evidence_band_value,
                citation_ids=citation_ids,
                question_ids=question_ids,
                selected_option_ids=selected_option_ids,
                correctness=correctness,
                refusal_reason=refusal_reason,
                actions=actions,
            )
        )
