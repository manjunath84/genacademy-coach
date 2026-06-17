from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from genacademy_coach.grounding import (
    answer_grounded_in_spans,
    keyword_present,
    normalized_terms,
)
from genacademy_coach.quiz_types import QuizOption, QuizQuestion
from genacademy_coach.teach_types import RetrievedSpan

SYSTEM_PROMPT = "You write short grounded multiple-choice quiz questions. Reply only with JSON."
USER_TEMPLATE = """Use only the cited course span below.

Citation ID: {citation_id}
Title: {title}
Span:
{span_text}

Create one multiple-choice question. Return exactly this JSON object shape:
{{
  "prompt": "Which statement is directly supported by the cited span?",
  "options": [
    {{"option_id": "A", "text": "Supported answer"}},
    {{"option_id": "B", "text": "Distractor"}},
    {{"option_id": "C", "text": "Distractor"}},
    {{"option_id": "D", "text": "Distractor"}}
  ],
  "correct_option_id": "A",
  "expected_answer": "The supported option restated plainly.",
  "rationale": "Short explanation grounded in the span.",
  "expected_keywords": ["supported term"]
}}

Rules:
- Use exactly four options with IDs A, B, C, and D.
- Keep the prompt generic; do not add course facts to the prompt.
- Write the correct option, expected_answer, and rationale using exact wording copied from the span.
- The correct option, expected_answer, rationale, and expected_keywords must be supported by the
  span.
- Do not include a citation_id field in your JSON.
"""


class RawQuizQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str
    options: list[QuizOption] = Field(min_length=4, max_length=4)
    correct_option_id: str
    expected_answer: str
    rationale: str
    expected_keywords: list[str] = Field(min_length=1)


GENERIC_PROMPT_TERMS = frozenset(
    {
        "according",
        "a",
        "an",
        "answer",
        "are",
        "as",
        "at",
        "best",
        "be",
        "by",
        "can",
        "below",
        "cited",
        "course",
        "described",
        "directly",
        "does",
        "following",
        "from",
        "how",
        "in",
        "is",
        "it",
        "matches",
        "most",
        "of",
        "on",
        "option",
        "or",
        "question",
        "select",
        "span",
        "statement",
        "supported",
        "that",
        "the",
        "this",
        "to",
        "what",
        "which",
        "why",
        "with",
        "where",
    }
)


def _correct_option_text(raw: RawQuizQuestion) -> str:
    correct_id = raw.correct_option_id.strip().upper()
    correct_option = next(
        (option for option in raw.options if option.option_id == correct_id),
        None,
    )
    if correct_option is None:
        raise ValueError("correct_option_id must match an option")
    return correct_option.text


def _supported_keywords(raw: RawQuizQuestion, span: RetrievedSpan) -> list[str]:
    correct_text = _correct_option_text(raw)
    grounded_text = " ".join([raw.expected_answer, raw.rationale, correct_text])
    supported = [
        keyword.strip().lower()
        for keyword in raw.expected_keywords
        if keyword_present(grounded_text, keyword) and keyword_present(span.text, keyword)
    ]
    if not supported:
        raise ValueError("quiz item expected_keywords must be supported by the cited span")
    return supported


def _validate_grounded_content(raw: RawQuizQuestion, span: RetrievedSpan) -> None:
    correct_text = _correct_option_text(raw)
    for field_name, value in [
        ("correct option", correct_text),
        ("expected_answer", raw.expected_answer),
        ("rationale", raw.rationale),
    ]:
        if not answer_grounded_in_spans(value, [span]):
            raise ValueError(f"quiz item {field_name} must be grounded in the cited span")

    span_terms = normalized_terms(span.text)
    prompt_terms = normalized_terms(raw.prompt)
    unsupported_prompt_terms = prompt_terms - span_terms - GENERIC_PROMPT_TERMS
    if unsupported_prompt_terms:
        raise ValueError("quiz item prompt includes terms unsupported by the cited span")


def _validate_option_ids(raw: RawQuizQuestion) -> None:
    option_ids = [option.option_id for option in raw.options]
    if option_ids != ["A", "B", "C", "D"]:
        raise ValueError("quiz item options must use IDs A, B, C, and D")


def generate_quiz_question(
    provider: Any,
    span: RetrievedSpan,
    *,
    question_id: str,
) -> QuizQuestion:
    raw_response = provider.generate(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_TEMPLATE.format(
                    citation_id=span.citation_id,
                    title=span.title,
                    span_text=span.text,
                ),
            },
        ],
        json_mode=True,
        max_tokens=512,
        temperature=0.0,
    )
    try:
        if not isinstance(raw_response, str) or not raw_response.strip():
            raise ValueError("empty completion")
        raw = RawQuizQuestion.model_validate(json.loads(raw_response))
        _validate_option_ids(raw)
        _validate_grounded_content(raw, span)
        keywords = _supported_keywords(raw, span)
        return QuizQuestion(
            question_id=question_id,
            prompt=raw.prompt,
            options=raw.options,
            correct_option_id=raw.correct_option_id,
            expected_answer=raw.expected_answer,
            rationale=raw.rationale,
            citation_id=span.citation_id,
            expected_keywords=keywords,
        )
    except (json.JSONDecodeError, TypeError, ValidationError, ValueError) as exc:
        raise ValueError("invalid quiz item") from exc
