import pytest
from pydantic import ValidationError

from genacademy_coach.quiz_types import (
    QuizQuestion,
    grade_quiz,
    grade_quiz_selection,
)


def quiz_question(**overrides) -> QuizQuestion:
    row = {
        "question_id": "q1",
        "prompt": "Which option is supported by the cited span?",
        "options": [
            {"option_id": "a", "text": "Attention focuses relevant context."},
            {"option_id": "B", "text": "Attention stores customer profiles."},
            {"option_id": "C", "text": "Attention removes all tools."},
            {"option_id": "D", "text": "Attention disables retrieval."},
        ],
        "correct_option_id": "a",
        "expected_answer": "Attention focuses relevant context.",
        "rationale": "The cited span says attention focuses relevant context.",
        "citation_id": "note/attention::0",
        "expected_keywords": [" relevant context "],
    }
    row.update(overrides)
    return QuizQuestion.model_validate(row)


def test_quiz_question_normalizes_option_ids_and_keywords():
    question = quiz_question()

    assert [option.option_id for option in question.options] == ["A", "B", "C", "D"]
    assert question.correct_option_id == "A"
    assert question.expected_keywords == ["relevant context"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"options": [{"option_id": "AA", "text": "bad"}]},
        {
            "options": [
                {"option_id": "A", "text": "same"},
                {"option_id": "A", "text": "different"},
            ]
        },
        {
            "options": [
                {"option_id": "A", "text": "same"},
                {"option_id": "B", "text": "same"},
            ]
        },
        {"correct_option_id": "Z"},
        {"expected_keywords": ["  "]},
        {"citation_id": ""},
        {"confidence": 0.99},
    ],
)
def test_quiz_question_rejects_invalid_contracts(overrides):
    with pytest.raises(ValidationError):
        quiz_question(**overrides)


def test_grade_quiz_selection_is_deterministic_by_option_id():
    question = quiz_question()

    grade = grade_quiz_selection(question, "a")
    miss = grade_quiz_selection(question, "B")

    assert grade.correct is True
    assert grade.selected_option_id == "A"
    assert miss.correct is False
    assert miss.correct_option_id == "A"
    assert miss.citation_id == "note/attention::0"


def test_grade_quiz_selection_rejects_unknown_option_id():
    with pytest.raises(ValueError, match="unknown option_id"):
        grade_quiz_selection(quiz_question(), "Z")


def test_grade_quiz_requires_one_answer_per_question():
    with pytest.raises(ValueError, match="expected 1 answers"):
        grade_quiz([quiz_question()], [])
