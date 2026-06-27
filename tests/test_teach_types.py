from pydantic import ValidationError

from genacademy_coach.teach_types import (
    CheckItem,
    CoachAgentResponse,
    LearnerProfile,
    ProvenanceRecord,
    RetrievedSpan,
    TokenUsage,
    TraceTurn,
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


def test_retrieved_span_source_label_is_camera_friendly_for_slides():
    span = RetrievedSpan(
        chunk_id="slide/week1-session1-82cf85861f9f::36",
        doc_id="slide/week1-session1",
        text="Agent harnesses use tool checks.",
        score=0.91,
        title="week1-session1.pptx",
        source_type="slide",
        page_or_section="36",
    )

    assert span.source_label == "Week 1 Session 1 (slide 36)"
    assert "82cf85861f9f" not in span.source_label
    assert "slide/week1-session1" not in span.source_label


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


def test_token_usage_defaults_zero():
    assert TokenUsage().input_tokens == 0 and TokenUsage().total_tokens == 0


def test_provenance_record_serializes_safe_metadata_only():
    record = ProvenanceRecord(
        role="check",
        span_id="slide/week2-session1::3",
        source_type="slide",
        selected_at="generate_check_item",
        selection_reason="preferred_slide",
    )

    assert record.model_dump() == {
        "role": "check",
        "span_id": "slide/week2-session1::3",
        "source_type": "slide",
        "selected_at": "generate_check_item",
        "selection_reason": "preferred_slide",
    }


def test_trace_turn_accepts_role_keyed_provenance():
    turn = TraceTurn(
        session_id="s",
        turn=1,
        topic_hash="topic-hash",
        learner_input_hash="input-hash",
        next_action="drill",
        strategy="analogy",
        evidence_score=0.91,
        evidence_band="proceed",
        retrieved_citation_ids=["slide/week2-session1::3"],
        tool_calls=[],
        provenance={
            "check": ProvenanceRecord(
                role="check",
                span_id="slide/week2-session1::3",
                source_type="slide",
                selected_at="generate_check_item",
                selection_reason="preferred_slide",
            )
        },
    )

    assert turn.provenance["check"].span_id == "slide/week2-session1::3"


def test_trace_turn_token_latency_defaults():
    t = TraceTurn(
        session_id="s",
        turn=1,
        topic_hash="h",
        learner_input_hash="h",
        next_action="advance",
        strategy="summary",
        evidence_score=0.5,
        evidence_band="confirm",
        retrieved_citation_ids=[],
        tool_calls=[],
    )
    assert (t.input_tokens, t.output_tokens, t.total_tokens, t.latency_ms) == (0, 0, 0, 0.0)
    assert t.agent_latency_ms == 0.0
    assert t.agent_attempts == 0
    assert t.retrieval_cache_hits == 0
    assert t.tool_latencies_ms == {}
    assert t.tool_call_counts == {}
    assert t.provenance == {}
