from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from genacademy_coach.teach_types import CheckItem, RetrievedSpan

SYSTEM_PROMPT = "You write short grounded understanding checks. Reply only with JSON."
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
    return CheckItem(
        question=parsed.question,
        expected_answer=parsed.expected_answer,
        expected_keywords=parsed.expected_keywords,
        citation_id=span.citation_id,
    )
