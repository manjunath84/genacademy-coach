from pathlib import Path
from typing import get_args

import pytest

from genacademy_coach.escalation import append_review_queue
from genacademy_coach.privacy import topic_hash
from genacademy_coach.teach_session import (
    FALLBACK_STRATEGIES,
    AgentResponseError,
    CoachSession,
    LangChainAgentPort,
    StaticAgentPort,
    _grounded_excerpt,
)
from genacademy_coach.teach_types import (
    CheckItem,
    CoachAgentResponse,
    LearnerProfile,
    RetrievedSpan,
    Strategy,
    UnderstandingGrade,
)
from genacademy_coach.trace import load_trace


class FakeSettings:
    trace_dir: Path
    review_queue_path: Path
    stop_threshold = 0.60
    confirm_threshold = 0.85

    def __init__(self, root: Path, max_teach_turns: int = 4):
        self.trace_dir = root / "traces"
        self.review_queue_path = root / "review_queue.jsonl"
        self.max_teach_turns = max_teach_turns


class FakeFoundation:
    provider = object()

    def retrieve(self, query: str):
        return []


def cited_span() -> RetrievedSpan:
    return RetrievedSpan(
        chunk_id="note/attention::0",
        doc_id="note/attention",
        text="Attention highlights relevant context.",
        score=0.91,
        title="attention.md",
        source_type="note",
    )


def other_span() -> RetrievedSpan:
    return RetrievedSpan(
        chunk_id="note/tools::0",
        doc_id="note/tools",
        text="Tools let an agent act outside the model.",
        score=0.88,
        title="tools.md",
        source_type="note",
    )


def check_item() -> CheckItem:
    return CheckItem(
        question="What does attention help with?",
        expected_answer="It helps focus relevant context.",
        expected_keywords=["relevant context"],
        citation_id="note/attention::0",
    )


def test_fallback_strategies_are_valid_strategy_literals():
    assert set(FALLBACK_STRATEGIES).issubset(set(get_args(Strategy)))


def test_grounded_excerpt_bounds_and_normalizes_whitespace():
    span = cited_span().model_copy(update={"text": ("  word\t\n" * 200).strip()})

    excerpt = _grounded_excerpt(span)

    assert len(excerpt) <= 700
    assert "\n" not in excerpt
    assert "\t" not in excerpt
    assert "  " not in excerpt


def test_session_start_writes_trace_with_retrieval_evidence(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention highlights relevant context. [note/attention::0]",
            observation="retrieved a citeable attention span and learner needs an explanation",
            next_action="drill",
            strategy="analogy",
            citation_ids=["note/attention::0"],
            check_question="What does attention help with?",
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]
    session.runtime.current_check = check_item()

    result = session.start()

    assert result.response.next_action == "drill"
    assert (tmp_path / "traces" / "abc.jsonl").exists()
    assert result.profile.turn_count == 1
    rows = load_trace(Path(result.trace_path))
    assert rows[0].evidence_score == 0.91
    assert rows[0].evidence_band == "proceed"


def test_teach_trace_contains_hashes_and_no_raw_private_text(tmp_path):
    private_topic = "PRIVATE RAW TOPIC"
    private_answer = "PRIVATE LEARNER ANSWER"
    private_message = "PRIVATE GENERATED TUTOR MESSAGE"
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention highlights relevant context. [note/attention::0]",
            observation=private_message,
            next_action="drill",
            strategy="analogy",
            citation_ids=["note/attention::0"],
        ),
        CoachAgentResponse(
            learner_message="Attention highlights relevant context. [note/attention::0]",
            observation=private_message,
            next_action="re_explain_differently",
            strategy="contrastive_example",
            citation_ids=["note/attention::0"],
        ),
    )
    session = CoachSession(
        session_id="abc",
        topic=private_topic,
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(previous_strategies=["analogy"]),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]
    session.start()

    result = session.respond(private_answer)

    serialized = Path(result.trace_path).read_text(encoding="utf-8")
    rows = [row.model_dump() for row in load_trace(Path(result.trace_path))]
    assert all("topic_hash" in row for row in rows)
    assert all("learner_input_hash" in row for row in rows)
    assert private_topic not in serialized
    assert private_answer not in serialized
    assert private_message not in serialized
    assert '"learner_input":' not in serialized
    assert "learner_message" not in serialized


def test_session_rejects_citation_id_not_seen_in_retrieval(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention is useful. [note/made-up::0]",
            observation="agent cited an id that was not retrieved",
            next_action="advance",
            strategy="summary",
            citation_ids=["note/made-up::0"],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]

    result = session.start()

    assert result.response.next_action == "refuse_escalate"
    assert "could not verify" in result.response.learner_message.lower()


def test_session_rejects_uncited_agent_answer(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention is useful.",
            observation="agent answered without retrieved citations",
            next_action="advance",
            strategy="summary",
            citation_ids=[],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )

    result = session.start()

    assert result.response.next_action == "refuse_escalate"
    assert "could not verify" in result.response.learner_message.lower()
    assert (tmp_path / "review_queue.jsonl").exists()


def test_session_uses_current_check_question_not_agent_desync(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention highlights relevant context. [note/attention::0]",
            observation="agent displayed a different check question than the grounded tool item",
            next_action="drill",
            strategy="analogy",
            citation_ids=["note/attention::0"],
            check_question="Made up check?",
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]
    session.runtime.current_check = check_item()

    result = session.start()

    assert result.response.check_question == "What does attention help with?"


def test_session_appends_missing_visible_citation_id(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention highlights relevant context.",
            observation="agent cited retrieved span in metadata but not visible text",
            next_action="drill",
            strategy="analogy",
            citation_ids=["note/attention::0"],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]

    result = session.start()

    assert "[note/attention::0]" in result.response.learner_message


def test_session_rejects_unfaithful_cited_answer(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention stores long term customer profiles. [note/attention::0]",
            observation="agent used retrieved citation id for unsupported text",
            next_action="advance",
            strategy="summary",
            citation_ids=["note/attention::0"],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]

    result = session.start()

    assert result.response.next_action == "refuse_escalate"
    assert "retrieved course citation text" in result.response.learner_message.lower()
    rows = load_trace(Path(result.trace_path))
    assert rows[0].faithfulness_ok is False


def test_session_uses_grounded_teach_fallback_for_initial_unfaithful_explanation(
    tmp_path,
):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention stores long term customer profiles. [note/attention::0]",
            observation="agent tried to teach with unsupported text",
            next_action="drill",
            strategy="analogy",
            citation_ids=["note/attention::0"],
            check_question="Made up check?",
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]
    session.runtime.current_check = check_item()

    result = session.start()

    assert result.response.next_action == "drill"
    assert result.response.strategy == "analogy"
    assert result.response._decision_source == "python safety gate"
    assert result.response.citation_ids == ["note/attention::0"]
    assert result.response.check_question == "What does attention help with?"
    assert "Attention highlights relevant context" in result.response.learner_message
    assert not (tmp_path / "review_queue.jsonl").exists()
    rows = load_trace(Path(result.trace_path))
    assert rows[0].faithfulness_ok is True


def test_session_refuses_initial_unfaithful_cited_answer_without_grounded_check(
    tmp_path,
):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention stores long term customer profiles. [note/attention::0]",
            observation="agent tried to teach with unsupported text",
            next_action="drill",
            strategy="analogy",
            citation_ids=["note/attention::0"],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]

    result = session.start()

    assert result.response.next_action == "refuse_escalate"
    assert result.response._decision_source == "python safety gate"
    assert "retrieved course citation text" in result.response.learner_message.lower()
    assert (tmp_path / "review_queue.jsonl").exists()


def test_session_does_not_coerce_initial_reexplain_into_drill(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention stores long term customer profiles. [note/attention::0]",
            observation="agent picked a re-explanation without a learner stumble",
            next_action="re_explain_differently",
            strategy="contrastive_example",
            citation_ids=["note/attention::0"],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]
    session.runtime.current_check = check_item()

    result = session.start()

    assert result.response.next_action == "refuse_escalate"
    assert result.response.next_action != "drill"
    assert (tmp_path / "review_queue.jsonl").exists()


def test_grounded_teach_fallback_uses_span_that_matches_current_check(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Tools store long term customer profiles. [note/tools::0]",
            observation="agent cited a different retrieved span than the check item",
            next_action="drill",
            strategy="analogy",
            citation_ids=["note/tools::0"],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [other_span(), cited_span()]
    session.runtime.current_check = check_item()

    result = session.start()

    assert result.response.next_action == "drill"
    assert result.response.citation_ids == ["note/attention::0"]
    assert "Attention highlights relevant context" in result.response.learner_message
    assert "Tools let an agent act" not in result.response.learner_message
    assert result.response.check_question == "What does attention help with?"


def test_grounded_teach_fallback_refuses_when_check_span_not_retrieved(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Customer profiles persist long term. [note/tools::0]",
            observation="agent cited a span but the active check citation was not retrieved",
            next_action="drill",
            strategy="analogy",
            citation_ids=["note/tools::0"],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [other_span()]
    session.runtime.current_check = check_item()

    result = session.start()

    queue_text = (tmp_path / "review_queue.jsonl").read_text(encoding="utf-8")
    assert result.response.next_action == "refuse_escalate"
    assert result.response.observation == (
        "grounded check citation was not present in retrieved spans"
    )
    assert "note/tools::0" in queue_text
    assert "grounded check citation was not present in retrieved spans" in queue_text


def test_session_uses_grounded_reexplain_fallback_after_wrong_answer(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention highlights relevant context. [note/attention::0]",
            observation="retrieved a citeable attention span",
            next_action="drill",
            strategy="analogy",
            citation_ids=["note/attention::0"],
        ),
        CoachAgentResponse(
            learner_message="Attention stores long term customer profiles. [note/attention::0]",
            observation="learner stumbled but agent produced unsupported text",
            next_action="re_explain_differently",
            strategy="analogy",
            citation_ids=["note/attention::0"],
        ),
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]
    session.runtime.current_check = check_item()
    session.start()
    session.runtime.last_grade = UnderstandingGrade(
        correct=False,
        matched_keywords=[],
        missing_keywords=["relevant context"],
        citation_id="note/attention::0",
    )

    result = session.respond("It stores profiles.")

    assert result.response.next_action == "re_explain_differently"
    assert result.response._decision_source == "python safety gate"
    assert result.response.strategy != "analogy"
    assert result.response.citation_ids == ["note/attention::0"]
    assert "Attention highlights relevant context" in result.response.learner_message
    rows = load_trace(Path(result.trace_path))
    assert rows[-1].faithfulness_ok is True


def test_session_uses_grounded_advance_fallback_after_correct_answer(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention stores long term customer profiles. [note/attention::0]",
            observation="learner answered correctly but agent produced unsupported text",
            next_action="advance",
            strategy="summary",
            citation_ids=["note/attention::0"],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(previous_strategies=["analogy"]),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]
    session.runtime.last_grade = UnderstandingGrade(
        correct=True,
        matched_keywords=["relevant context"],
        missing_keywords=[],
        citation_id="note/attention::0",
    )

    result = session.respond("It helps with relevant context.")

    assert result.response.next_action == "advance"
    assert result.response._decision_source == "python safety gate"
    assert result.response.citation_ids == ["note/attention::0"]
    assert "Attention highlights relevant context" in result.response.learner_message
    rows = load_trace(Path(result.trace_path))
    assert rows[-1].faithfulness_ok is True


def test_session_grades_current_check_answer_before_agent_decides(tmp_path):
    class CapturingAgent:
        def __init__(self):
            self.messages = []

        def invoke(self, messages):
            self.messages.append(messages)
            return CoachAgentResponse(
                learner_message="Attention highlights relevant context. [note/attention::0]",
                observation="learner answered the grounded check correctly",
                next_action="advance",
                strategy="summary",
                citation_ids=["note/attention::0"],
            )

    agent = CapturingAgent()
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(previous_strategies=["analogy"]),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]
    session.runtime.current_check = check_item()

    result = session.respond("It helps focus relevant context.")

    assert result.response.next_action == "advance"
    assert session.runtime.last_grade is not None
    assert session.runtime.last_grade.correct is True
    assert '"correct":true' in agent.messages[0][0]["content"]


def test_session_preserves_boundary_grade_when_agent_switches_check_in_turn(tmp_path):
    class SwitchingCheckAgent:
        def __init__(self):
            self.runtime = None

        def invoke(self, messages):
            assert self.runtime is not None
            assert '"correct":true' in messages[0]["content"]
            self.runtime.current_check = CheckItem(
                question="What do tools let an agent do?",
                expected_answer="Tools let an agent act outside the model.",
                expected_keywords=["agent act"],
                citation_id="note/tools::0",
            )
            self.runtime.grade_locked = False
            self.runtime.last_grade = UnderstandingGrade(
                correct=False,
                matched_keywords=[],
                missing_keywords=["agent act"],
                citation_id="note/tools::0",
            )
            self.runtime.profile.last_grade_correct = False
            self.runtime.record_tool("generate_check_item")
            self.runtime.record_tool("grade_understanding")
            return CoachAgentResponse(
                learner_message="Attention highlights relevant context. [note/attention::0]",
                observation="agent generated the next check before finishing this response",
                next_action="advance",
                strategy="summary",
                citation_ids=["note/attention::0"],
            )

    agent = SwitchingCheckAgent()
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(previous_strategies=["analogy"]),
        agent_port=agent,
    )
    agent.runtime = session.runtime
    session.runtime.last_spans = [cited_span(), other_span()]
    session.runtime.current_check = check_item()

    result = session.respond("It helps focus relevant context.")

    assert result.response.next_action == "advance"
    assert session.runtime.last_grade is not None
    assert session.runtime.last_grade.correct is True
    assert session.runtime.last_grade.citation_id == "note/attention::0"
    assert session.profile.last_grade_correct is True


def test_session_preserves_incorrect_boundary_grade_when_agent_switches_check_in_turn(
    tmp_path,
):
    class SwitchingCheckAgent:
        def __init__(self):
            self.runtime = None

        def invoke(self, messages):
            assert self.runtime is not None
            assert '"correct":false' in messages[0]["content"]
            self.runtime.current_check = CheckItem(
                question="What do tools let an agent do?",
                expected_answer="Tools let an agent act outside the model.",
                expected_keywords=["agent act"],
                citation_id="note/tools::0",
            )
            self.runtime.grade_locked = False
            self.runtime.last_grade = UnderstandingGrade(
                correct=True,
                matched_keywords=["agent act"],
                missing_keywords=[],
                citation_id="note/tools::0",
            )
            self.runtime.profile.last_grade_correct = True
            self.runtime.record_tool("generate_check_item")
            self.runtime.record_tool("grade_understanding")
            return CoachAgentResponse(
                learner_message="Attention highlights relevant context. [note/attention::0]",
                observation="agent generated the next check before finishing this response",
                next_action="advance",
                strategy="summary",
                citation_ids=["note/attention::0"],
            )

    agent = SwitchingCheckAgent()
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(previous_strategies=["analogy"]),
        agent_port=agent,
    )
    agent.runtime = session.runtime
    session.runtime.last_spans = [cited_span(), other_span()]
    session.runtime.current_check = check_item()

    result = session.respond("It stores customer profiles.")

    assert result.response.next_action == "re_explain_differently"
    assert session.runtime.last_grade is not None
    assert session.runtime.last_grade.correct is False
    assert session.runtime.last_grade.citation_id == "note/attention::0"
    assert session.profile.last_grade_correct is False


@pytest.mark.parametrize("agent_action", ["refuse_escalate", "stop"])
def test_session_uses_grounded_advance_after_correct_answer_when_agent_skips_citations(
    tmp_path,
    agent_action,
):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="I cannot verify this.",
            observation="agent tried to end without citing the retrieved span",
            next_action=agent_action,
            strategy="refusal" if agent_action == "refuse_escalate" else "summary",
            citation_ids=[],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(previous_strategies=["analogy", "contrastive_example"]),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]
    session.runtime.current_check = check_item()

    result = session.respond("It helps focus relevant context.")

    assert session.runtime.last_grade is not None
    assert session.runtime.last_grade.correct is True
    assert result.response.next_action == "advance"
    assert result.response.citation_ids == ["note/attention::0"]
    rows = load_trace(Path(result.trace_path))
    assert rows[-1].next_action == "advance"


@pytest.mark.parametrize("agent_action", ["advance", "stop", "refuse_escalate"])
def test_session_forces_reexplain_after_wrong_answer_when_agent_skips_stumble_action(
    tmp_path,
    agent_action,
):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention highlights relevant context. [note/attention::0]",
            observation="agent did not react to the incorrect grade",
            next_action=agent_action,
            strategy="summary",
            citation_ids=["note/attention::0"],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(previous_strategies=["analogy"]),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]
    session.runtime.current_check = check_item()

    result = session.respond("It stores long term customer profiles.")

    assert session.runtime.last_grade is not None
    assert session.runtime.last_grade.correct is False
    assert result.response.next_action == "re_explain_differently"
    assert result.response.strategy != "analogy"
    assert result.response.citation_ids == ["note/attention::0"]
    rows = load_trace(Path(result.trace_path))
    assert rows[-1].next_action == "re_explain_differently"


def test_session_rejects_re_explain_with_same_strategy(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Trying the same analogy again. [note/attention::0]",
            observation="learner stumbled but strategy did not change",
            next_action="re_explain_differently",
            strategy="analogy",
            citation_ids=["note/attention::0"],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(previous_strategies=["analogy"]),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]

    result = session.respond("It just memorizes tokens.")

    assert result.response.next_action == "refuse_escalate"
    assert "different strategy" in result.response.learner_message.lower()


def test_session_refuses_when_agent_port_fails_structured_output(tmp_path):
    class FailingAgent:
        def invoke(self, messages):
            raise AgentResponseError("missing structured_response")

    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=FailingAgent(),
    )

    result = session.start()

    assert result.response.next_action == "refuse_escalate"
    assert "structured output" in result.response.learner_message.lower()


def test_session_does_not_duplicate_review_queue_after_tool_escalation(tmp_path):
    class EscalatedThenFailingAgent:
        def __init__(self):
            self.runtime = None

        def invoke(self, messages):
            assert self.runtime is not None
            append_review_queue(
                self.runtime.review_queue_path,
                session_id=self.runtime.session_id,
                topic_hash=topic_hash(self.runtime.topic),
                reason="tool escalation",
                score=self.runtime.current_evidence_score(),
                citation_ids=[],
            )
            self.runtime.escalation_queued = True
            self.runtime.record_tool("escalate_to_mentor")
            raise AgentResponseError("missing structured_response")

    agent = EscalatedThenFailingAgent()
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    agent.runtime = session.runtime

    result = session.start()

    assert result.response.next_action == "refuse_escalate"
    rows = (tmp_path / "review_queue.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    assert "tool escalation" in rows[0]


def test_static_agent_message_identifies_exhaustion():
    with pytest.raises(AgentResponseError, match="exhausted after 0 configured turns"):
        StaticAgentPort().invoke([])


def test_langchain_agent_port_validates_structured_response():
    port = LangChainAgentPort.__new__(LangChainAgentPort)

    class FakeAgent:
        def invoke(self, payload):
            return {
                "structured_response": {
                    "learner_message": "Grounded. [note/attention::0]",
                    "observation": "ok",
                    "next_action": "advance",
                    "strategy": "summary",
                    "citation_ids": ["note/attention::0"],
                }
            }

    port._agent = FakeAgent()

    response = port.invoke([{"role": "user", "content": "hello"}])

    assert response.next_action == "advance"
    assert response.strategy == "summary"


def test_langchain_agent_port_rejects_missing_structured_response():
    port = LangChainAgentPort.__new__(LangChainAgentPort)

    class FakeAgent:
        def invoke(self, payload):
            return {}

    port._agent = FakeAgent()

    with pytest.raises(AgentResponseError, match="missing structured_response"):
        port.invoke([{"role": "user", "content": "hello"}])


def test_langchain_agent_port_rejects_invalid_structured_response():
    port = LangChainAgentPort.__new__(LangChainAgentPort)

    class FakeAgent:
        def invoke(self, payload):
            return {"structured_response": {"confidence": 0.9}}

    port._agent = FakeAgent()

    with pytest.raises(AgentResponseError, match="invalid structured_response"):
        port.invoke([{"role": "user", "content": "hello"}])


def test_session_stops_at_turn_budget_without_agent_call(tmp_path):
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path, max_teach_turns=0),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=StaticAgentPort(
            CoachAgentResponse(
                learner_message="should not be used",
                observation="should not be used",
                next_action="advance",
                strategy="summary",
                citation_ids=[],
            )
        ),
    )

    result = session.start()

    assert result.response.next_action == "stop"
    assert result.response._decision_source == "python safety gate"
