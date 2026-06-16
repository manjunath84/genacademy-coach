from pydantic import ValidationError

from genacademy_coach.teach_types import (
    CheckItem,
    CoachAgentResponse,
    LearnerProfile,
    RetrievedSpan,
)


def test_profile_defaults_are_within_session_only():
    profile = LearnerProfile(style="analogy", track_lens="code_heavy")

    assert profile.style == "analogy"
    assert profile.track_lens == "code_heavy"
    assert profile.known == []
    assert profile.struggled == []
    assert profile.previous_strategies == []
    assert profile.turn_count == 0


def test_agent_response_rejects_unsupported_next_action():
    try:
        CoachAgentResponse(
            learner_message="hello",
            observation="learner asked an unsupported action",
            next_action="invent_answer",
            strategy="analogy",
            citation_ids=[],
        )
    except ValidationError as exc:
        assert "next_action" in str(exc)
    else:
        raise AssertionError("unsupported next_action should fail validation")


def test_retrieved_span_citation_id_is_stable():
    span = RetrievedSpan(
        chunk_id="note/a::0",
        doc_id="note/a",
        text="Attention routes focus.",
        score=0.91,
        title="attention.md",
        source_type="note",
        page_or_section="section-1",
    )

    assert span.citation_id == "note/a::0"


def test_check_item_keeps_expected_keywords_lowercase():
    item = CheckItem(
        question="What does attention do?",
        expected_answer="It focuses relevant context.",
        expected_keywords=["Focus", "Context"],
        citation_id="note/a::0",
    )

    assert item.expected_keywords == ["focus", "context"]


def test_agent_response_rejects_llm_confidence_field():
    try:
        CoachAgentResponse(
            learner_message="hello",
            observation="retrieved one citeable span",
            next_action="drill",
            strategy="analogy",
            citation_ids=[],
            confidence=0.9,
        )
    except ValidationError as exc:
        assert "confidence" in str(exc)
    else:
        raise AssertionError("agent confidence must not be accepted")
