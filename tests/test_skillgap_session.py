import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from genacademy_coach.quiz_trace import QuizTraceWriter
from genacademy_coach.quiz_types import QuizTraceRow
from genacademy_coach.skillgap_session import NO_CITEABLE_SKILL_GAP_REVIEW, SkillGapSession
from genacademy_coach.skillgap_types import SkillGapTraceRow
from genacademy_coach.teach_types import TraceTurn
from genacademy_coach.trace import TraceWriter


class FakeSettings:
    stop_threshold = 0.60
    confirm_threshold = 0.85

    def __init__(self, root: Path):
        self.trace_dir = root / "traces"
        self.review_queue_path = root / "review_queue.jsonl"


class FakeFoundation:
    def __init__(self, rows_by_query: dict[str, list[dict]]):
        self.rows_by_query = rows_by_query
        self.queries: list[str] = []

    def retrieve(self, query: str):
        self.queries.append(query)
        return self.rows_by_query.get(query, [])


def span_row(**overrides):
    row = {
        "chunk_id": "handout/review::0",
        "doc_id": "handout/review",
        "text": "PRIVATE SPAN TEXT: review how agent tools are checked.",
        "score": 0.91,
        "title": "Agent Field Guide",
        "source_type": "handout",
        "page_or_section": "p.1",
    }
    row.update(overrides)
    return row


def write_teach_trace(root: Path, session_id: str = "teach-1") -> None:
    TraceWriter(root / "traces").append(
        TraceTurn(
            session_id=session_id,
            turn=1,
            learner_input="PRIVATE LEARNER ANSWER",
            observation="PRIVATE OBSERVATION",
            next_action="re_explain_differently",
            strategy="contrastive_example",
            evidence_score=0.72,
            evidence_band="confirm",
            faithfulness_ok=True,
            retrieved_citation_ids=["note/agent-harness::0"],
            tool_calls=["retrieve_course_corpus"],
            learner_message="PRIVATE GENERATED TEACHER MESSAGE",
        )
    )


def write_quiz_trace(root: Path, session_id: str = "quiz-1") -> None:
    QuizTraceWriter(root / "traces").append(
        QuizTraceRow(
            session_id=session_id,
            topic_hash="abc123",
            evidence_score=0.91,
            evidence_band="proceed",
            citation_ids=["note/agent-harness::0", "note/tools::0"],
            question_ids=["q1", "q2"],
            selected_option_ids=["B", "A"],
            correctness=[False, True],
            actions=["retrieve_course_corpus", "generate_quiz_items", "grade_quiz"],
        )
    )


def test_skillgap_ranks_gaps_and_writes_cited_redacted_trace(tmp_path):
    write_teach_trace(tmp_path)
    write_quiz_trace(tmp_path)
    foundation = FakeFoundation(
        {
            "note/agent-harness::0": [span_row(chunk_id="handout/review::0")],
            "note/tools::0": [span_row(chunk_id="handout/tools::0", score=0.88)],
        }
    )
    session = SkillGapSession(
        session_id="skillgap-1",
        source_session_ids=["teach-1", "quiz-1"],
        settings=FakeSettings(tmp_path),
        foundation=foundation,
    )

    result = session.run()

    assert [item.gap_id for item in result.items][:2] == [
        "note/agent-harness::0",
        "note/tools::0",
    ]
    first = result.items[0]
    assert first.priority_score > result.items[1].priority_score
    assert first.next_action == "review_next"
    assert first.citation_ids == ["handout/review::0"]
    assert "Agent Field Guide" in first.review_next
    assert "p.1" in first.review_next
    assert foundation.queries[:2] == ["note/agent-harness::0", "note/tools::0"]

    serialized = Path(result.trace_path).read_text(encoding="utf-8")
    for private_value in [
        "PRIVATE LEARNER ANSWER",
        "PRIVATE OBSERVATION",
        "PRIVATE GENERATED TEACHER MESSAGE",
        "PRIVATE SPAN TEXT",
    ]:
        assert private_value not in serialized
    rows = [json.loads(line) for line in serialized.splitlines()]
    assert set(rows[0]) == set(SkillGapTraceRow.model_fields)
    assert rows[0]["topic_hash"] == "abc123"
    assert rows[0]["quiz_correct"] == 0
    assert rows[0]["quiz_total"] == 1
    assert rows[0]["struggle_count"] == 1


def test_skillgap_refuses_gap_without_citeable_review_span(tmp_path):
    write_teach_trace(tmp_path)
    foundation = FakeFoundation({"note/agent-harness::0": [span_row(score=0.2)]})
    settings = FakeSettings(tmp_path)
    session = SkillGapSession(
        session_id="skillgap-1",
        source_session_ids=["teach-1"],
        settings=settings,
        foundation=foundation,
    )

    result = session.run()

    assert result.items[0].next_action == "refuse_escalate"
    assert result.items[0].escalated is True
    assert result.items[0].reason_code == NO_CITEABLE_SKILL_GAP_REVIEW
    review_row = json.loads(settings.review_queue_path.read_text(encoding="utf-8"))
    assert review_row["reason"] == NO_CITEABLE_SKILL_GAP_REVIEW
    trace_row = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    assert trace_row["evidence_score"] == 0.2
    assert trace_row["evidence_band"] == "stop"


def test_review_queue_reason_is_not_serialized_as_gap_id(tmp_path):
    settings = FakeSettings(tmp_path)
    settings.review_queue_path.parent.mkdir(parents=True, exist_ok=True)
    settings.review_queue_path.write_text(
        json.dumps(
            {
                "session_id": "teach-1",
                "topic": "PRIVATE TOPIC",
                "reason": "PRIVATE REVIEW REASON",
                "score": 0.1,
                "citation_ids": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    session = SkillGapSession(
        session_id="skillgap-1",
        source_session_ids=["teach-1"],
        settings=settings,
        foundation=FakeFoundation({}),
    )

    result = session.run()

    serialized = Path(result.trace_path).read_text(encoding="utf-8")
    assert "PRIVATE REVIEW REASON" not in serialized
    assert "PRIVATE TOPIC" not in serialized
    assert result.items[0].gap_id.startswith("review:teach-1:")


def test_skillgap_rejects_unsafe_session_ids(tmp_path):
    with pytest.raises(ValueError, match="session id may only contain"):
        SkillGapSession(
            session_id="skillgap-1",
            source_session_ids=["../private"],
            settings=FakeSettings(tmp_path),
            foundation=FakeFoundation({}),
        )


def test_skillgap_trace_row_is_allow_list():
    with pytest.raises(ValidationError):
        SkillGapTraceRow(
            session_id="skillgap-1",
            topic_hash="abc123",
            gap_id="gap-1",
            source_session_ids=["teach-1"],
            evidence_score=0.91,
            evidence_band="proceed",
            citation_ids=["note/a::0"],
            quiz_correct=0,
            quiz_total=1,
            struggle_count=1,
            refusal_count=0,
            next_action="review_next",
            escalated=False,
            reason_code=None,
            raw_topic="PRIVATE TOPIC",
        )
