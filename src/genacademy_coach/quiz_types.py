from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from genacademy_coach.teach_types import EvidenceBand


def normalize_option_id(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 1 or not normalized.isalpha():
        raise ValueError("option_id must be a single letter")
    return normalized


class QuizOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_id: str
    text: str

    @field_validator("option_id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        return normalize_option_id(value)

    @field_validator("text")
    @classmethod
    def require_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("option text must be non-empty")
        return text


class QuizQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    prompt: str
    options: list[QuizOption] = Field(min_length=4, max_length=4)
    correct_option_id: str
    expected_answer: str
    rationale: str
    citation_id: str
    expected_keywords: list[str] = Field(min_length=1)

    @field_validator("question_id", "prompt", "expected_answer", "rationale", "citation_id")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("field must be non-empty")
        return text

    @field_validator("correct_option_id")
    @classmethod
    def normalize_correct_id(cls, value: str) -> str:
        return normalize_option_id(value)

    @field_validator("expected_keywords")
    @classmethod
    def normalize_keywords(cls, value: list[str]) -> list[str]:
        normalized = [item.strip().lower() for item in value if item.strip()]
        if not normalized:
            raise ValueError("expected_keywords must contain at least one non-empty value")
        return normalized

    @model_validator(mode="after")
    def validate_option_contract(self) -> QuizQuestion:
        option_ids = [option.option_id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("option IDs must be unique")
        option_texts = [option.text.casefold() for option in self.options]
        if len(option_texts) != len(set(option_texts)):
            raise ValueError("option text must be unique")
        if self.correct_option_id not in set(option_ids):
            raise ValueError("correct_option_id must match an option")
        return self


class QuizGrade(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    selected_option_id: str
    correct_option_id: str
    correct: bool
    citation_id: str


class QuizTraceRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    topic_hash: str
    evidence_score: float
    evidence_band: EvidenceBand
    citation_ids: list[str]
    question_ids: list[str]
    selected_option_ids: list[str] = Field(default_factory=list)
    correctness: list[bool] = Field(default_factory=list)
    refusal_reason: str | None = None
    actions: list[str] = Field(default_factory=list)


class QuizSessionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    questions: list[QuizQuestion] = Field(default_factory=list)
    grades: list[QuizGrade] = Field(default_factory=list)
    score: int = 0
    refusal_reason: str | None = None
    trace_path: str


def grade_quiz_selection(question: QuizQuestion, selected_option_id: str) -> QuizGrade:
    selected = normalize_option_id(selected_option_id)
    option_ids = {option.option_id for option in question.options}
    if selected not in option_ids:
        raise ValueError(f"unknown option_id: {selected}")
    return QuizGrade(
        question_id=question.question_id,
        selected_option_id=selected,
        correct_option_id=question.correct_option_id,
        correct=selected == question.correct_option_id,
        citation_id=question.citation_id,
    )


def grade_quiz(
    questions: list[QuizQuestion],
    selected_option_ids: list[str],
) -> list[QuizGrade]:
    if len(questions) != len(selected_option_ids):
        raise ValueError(
            f"expected {len(questions)} answers, received {len(selected_option_ids)}"
        )
    return [
        grade_quiz_selection(question, selected)
        for question, selected in zip(questions, selected_option_ids, strict=True)
    ]
