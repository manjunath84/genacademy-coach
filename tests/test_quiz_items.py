import json

import pytest

from genacademy_coach.quiz_items import generate_quiz_question
from genacademy_coach.teach_types import RetrievedSpan


class FakeProvider:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = []

    def generate(self, messages: list[dict], **kwargs) -> str:
        self.calls.append((messages, kwargs))
        return json.dumps(self.payload)


class EmptyProvider:
    def generate(self, _messages: list[dict], **_kwargs):
        return None


def span() -> RetrievedSpan:
    return RetrievedSpan(
        chunk_id="note/attention::0",
        doc_id="note/attention",
        text="Attention focuses relevant context for the model.",
        score=0.91,
        title="attention.md",
        source_type="note",
    )


def payload(**overrides) -> dict:
    row = {
        "prompt": "Which option is supported by the cited span?",
        "options": [
            {"option_id": "A", "text": "Attention focuses relevant context."},
            {"option_id": "B", "text": "Attention stores customer profiles."},
            {"option_id": "C", "text": "Attention removes all tools."},
            {"option_id": "D", "text": "Attention disables retrieval."},
        ],
        "correct_option_id": "A",
        "expected_answer": "Attention focuses relevant context.",
        "rationale": "The span says attention focuses relevant context.",
        "expected_keywords": ["relevant context"],
    }
    row.update(overrides)
    return row


def test_generate_quiz_question_pins_citation_to_source_span():
    provider = FakeProvider(payload())

    question = generate_quiz_question(provider, span(), question_id="q1")

    assert question.question_id == "q1"
    assert question.citation_id == "note/attention::0"
    assert question.correct_option_id == "A"
    assert provider.calls[0][1]["json_mode"] is True
    assert provider.calls[0][1]["temperature"] == 0.0


def test_generate_quiz_question_rejects_model_supplied_citation_id():
    provider = FakeProvider(payload(citation_id="made-up::0"))

    with pytest.raises(ValueError, match="invalid quiz item"):
        generate_quiz_question(provider, span(), question_id="q1")


def test_generate_quiz_question_rejects_empty_completion():
    with pytest.raises(ValueError, match="invalid quiz item"):
        generate_quiz_question(EmptyProvider(), span(), question_id="q1")


@pytest.mark.parametrize(
    "bad_payload",
    [
        payload(expected_keywords=["customer profiles"]),
        payload(
            options=[
                {"option_id": "A", "text": "Attention focuses relevant context."},
                {"option_id": "B", "text": "Attention stores customer profiles."},
                {"option_id": "C", "text": "Attention removes all tools."},
            ]
        ),
        payload(
            options=[
                {"option_id": "A", "text": "Attention focuses relevant context."},
                {"option_id": "B", "text": "Attention stores customer profiles."},
                {"option_id": "C", "text": "Attention removes all tools."},
                {"option_id": "C", "text": "Attention disables retrieval."},
            ]
        ),
        payload(
            options=[
                {"option_id": "A", "text": "Attention focuses relevant context."},
                {"option_id": "B", "text": "Attention focuses relevant context."},
                {"option_id": "C", "text": "Attention removes all tools."},
                {"option_id": "D", "text": "Attention disables retrieval."},
            ]
        ),
        payload(correct_option_id="Z"),
    ],
)
def test_generate_quiz_question_rejects_invalid_model_payloads(bad_payload):
    provider = FakeProvider(bad_payload)

    with pytest.raises(ValueError):
        generate_quiz_question(provider, span(), question_id="q1")


@pytest.mark.parametrize(
    "bad_payload",
    [
        payload(
            options=[
                {
                    "option_id": "A",
                    "text": "Attention focuses relevant context and stores customer profiles.",
                },
                {"option_id": "B", "text": "Attention stores customer profiles."},
                {"option_id": "C", "text": "Attention removes all tools."},
                {"option_id": "D", "text": "Attention disables retrieval."},
            ],
            expected_answer="Attention focuses relevant context and stores customer profiles.",
        ),
        payload(rationale="The span says attention stores customer profiles."),
        payload(prompt="Which option says attention stores customer profiles?"),
    ],
)
def test_generate_quiz_question_rejects_ungrounded_displayed_content(bad_payload):
    provider = FakeProvider(bad_payload)

    with pytest.raises(ValueError, match="invalid quiz item"):
        generate_quiz_question(provider, span(), question_id="q1")
