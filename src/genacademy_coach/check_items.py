from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from genacademy_coach.grounding import keyword_present
from genacademy_coach.teach_types import CheckItem, RetrievedSpan

SYSTEM_PROMPT = "You write short grounded understanding checks. Reply only with JSON."
WORD_RE = re.compile(r"[a-z0-9]+")
KEYWORD_STOP_WORDS = frozenset(
    {
        "about",
        "does",
        "from",
        "help",
        "helps",
        "into",
        "that",
        "their",
        "this",
        "what",
        "with",
    }
)
USER_TEMPLATE = """Use only the cited course span below.

Citation ID: {citation_id}
Title: {title}
Span:
{span_text}

Create one short free-answer check question. Return exactly this JSON object shape:
{{
  "question": "What does attention help the model do?",
  "expected_answer": "It helps the model focus on relevant context.",
  "expected_keywords": ["focus", "context"]
}}

Use 2-4 expected_keywords. Each keyword must be a literal term or short phrase supported by
the span.
"""


class RawCheckItem(BaseModel):
    question: str
    expected_answer: str
    expected_keywords: list[str] = Field(min_length=1)


def keywords_for_expected_answer(
    *,
    expected_answer: str,
    expected_keywords: list[str],
    span_text: str,
) -> list[str]:
    matched = [
        keyword for keyword in expected_keywords if keyword_present(expected_answer, keyword)
    ]
    if len(matched) >= 2:
        return matched

    derived = _derive_supported_keywords(expected_answer=expected_answer, span_text=span_text)
    if len(derived) >= 2:
        return derived
    if matched:
        return matched
    if derived:
        return derived
    raise ValueError("expected_answer must contain at least one supported keyword")


def _derive_supported_keywords(*, expected_answer: str, span_text: str) -> list[str]:
    span_terms = set(WORD_RE.findall(span_text.lower()))
    derived = []
    for term in WORD_RE.findall(expected_answer.lower()):
        if len(term) < 4 or term in KEYWORD_STOP_WORDS:
            continue
        if span_terms and term not in span_terms:
            continue
        if term not in derived:
            derived.append(term)
        if len(derived) == 4:
            break
    return derived


def generate_check_item(provider: Any, span: RetrievedSpan) -> CheckItem:
    raw = provider.generate(
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
        max_tokens=256,
        temperature=0.0,
    )
    parsed = RawCheckItem.model_validate(json.loads(raw))
    expected_keywords = keywords_for_expected_answer(
        expected_answer=parsed.expected_answer,
        expected_keywords=parsed.expected_keywords,
        span_text=span.text,
    )
    return CheckItem(
        question=parsed.question,
        expected_answer=parsed.expected_answer,
        expected_keywords=expected_keywords,
        citation_id=span.citation_id,
    )
