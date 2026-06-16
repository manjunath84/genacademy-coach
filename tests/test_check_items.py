import json

import pytest

from genacademy_coach.check_items import generate_check_item
from genacademy_coach.grounding import grade_understanding
from genacademy_coach.teach_types import RetrievedSpan


class FakeProvider:
    def __init__(self, payload: dict[str, object]):
        self.payload = payload
        self.calls = []

    def generate(self, messages: list[dict], **kwargs) -> str:
        self.calls.append((messages, kwargs))
        return json.dumps(self.payload)


def span() -> RetrievedSpan:
    return RetrievedSpan(
        chunk_id="note/attention::0",
        doc_id="note/attention",
        text="Attention lets the model focus on the most relevant context.",
        score=0.91,
        title="attention.md",
        source_type="note",
    )


def test_generate_check_item_uses_week2_provider_json_mode():
    provider = FakeProvider(
        {
            "question": "What does attention help the model do?",
            "expected_answer": "Focus on relevant context.",
            "expected_keywords": ["focus", "context"],
        }
    )

    item = generate_check_item(provider, span())

    assert item.citation_id == "note/attention::0"
    assert item.expected_keywords == ["focus", "context"]
    assert provider.calls[0][1]["json_mode"] is True


def test_generate_check_item_rejects_empty_keywords():
    provider = FakeProvider(
        {
            "question": "What does attention help the model do?",
            "expected_answer": "Focus on relevant context.",
            "expected_keywords": [],
        }
    )

    with pytest.raises(ValueError, match="expected_keywords"):
        generate_check_item(provider, span())


def test_generate_check_item_filters_keywords_missing_from_expected_answer():
    provider = FakeProvider(
        {
            "question": "What does attention help the model do?",
            "expected_answer": "Focus on relevant context.",
            "expected_keywords": ["focus", "token prediction", "context"],
        }
    )

    item = generate_check_item(provider, span())

    assert item.expected_keywords == ["focus", "context"]
    assert grade_understanding(item.expected_answer, item).correct is True


def test_generate_check_item_derives_keywords_when_provider_keywords_do_not_match_answer():
    provider = FakeProvider(
        {
            "question": "What does attention help the model do?",
            "expected_answer": "Focus on relevant context.",
            "expected_keywords": ["token prediction"],
        }
    )

    item = generate_check_item(provider, span())

    assert item.expected_keywords == ["focus", "relevant", "context"]
    assert grade_understanding(item.expected_answer, item).correct is True
