import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from genacademy_coach.quiz_trace import QuizTraceWriter
from genacademy_coach.quiz_types import QuizTraceRow


def test_quiz_trace_row_fields_are_exact_allow_list():
    assert set(QuizTraceRow.model_fields) == {
        "session_id",
        "topic_hash",
        "evidence_score",
        "evidence_band",
        "citation_ids",
        "question_ids",
        "selected_option_ids",
        "correctness",
        "refusal_reason",
        "actions",
    }


def test_quiz_trace_is_allow_list_not_rich_quiz_state(tmp_path):
    path = QuizTraceWriter(tmp_path).append(
        QuizTraceRow(
            session_id="quiz-1",
            topic_hash="abc123",
            evidence_score=0.91,
            evidence_band="proceed",
            citation_ids=["note/attention::0"],
            question_ids=["q1"],
            selected_option_ids=["A"],
            correctness=[True],
            actions=["retrieve_course_corpus", "generate_quiz_items", "grade_quiz"],
        )
    )

    serialized = Path(path).read_text(encoding="utf-8")
    row = json.loads(serialized)
    assert row["question_ids"] == ["q1"]


def test_quiz_trace_row_rejects_raw_quiz_fields():
    with pytest.raises(ValidationError):
        QuizTraceRow(
            session_id="quiz-1",
            topic_hash="abc123",
            evidence_score=0.91,
            evidence_band="proceed",
            citation_ids=["note/attention::0"],
            question_ids=["q1"],
            selected_option_ids=["A"],
            correctness=[True],
            actions=["retrieve_course_corpus", "generate_quiz_items", "grade_quiz"],
            prompt="PRIVATE PROMPT",
        )


def test_quiz_trace_does_not_use_teach_trace_turn_model():
    fields = set(QuizTraceRow.model_fields)

    assert "learner_message" not in fields
    assert "next_action" not in fields
    assert "strategy" not in fields
