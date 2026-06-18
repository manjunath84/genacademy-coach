import json

from pydantic import ValidationError

from genacademy_coach.escalation import append_review_queue
from genacademy_coach.privacy import learner_input_hash, topic_hash
from genacademy_coach.teach_types import TraceTurn
from genacademy_coach.trace import TraceWriter, load_trace


def sample_turn(session_id: str = "session-1") -> TraceTurn:
    return TraceTurn(
        session_id=session_id,
        turn=1,
        topic_hash=topic_hash("attention"),
        learner_input_hash=learner_input_hash("I do not get attention"),
        next_action="drill",
        strategy="analogy",
        evidence_score=0.91,
        evidence_band="proceed",
        faithfulness_ok=True,
        retrieved_citation_ids=["note/attention::0"],
        tool_calls=["retrieve_course_corpus", "generate_check_item"],
    )


def test_trace_writer_appends_json_turns(tmp_path):
    writer = TraceWriter(tmp_path)
    first = writer.append(sample_turn("abc"))
    second = writer.append(sample_turn("abc"))

    assert first == second
    rows = load_trace(first)
    assert len(rows) == 2
    assert rows[0].next_action == "drill"
    serialized = first.read_text(encoding="utf-8")
    assert "I do not get attention" not in serialized
    assert '"learner_input":' not in serialized
    assert "learner_message" not in serialized


def test_trace_turn_rejects_raw_private_fields():
    try:
        TraceTurn(
            session_id="abc",
            turn=1,
            topic_hash=topic_hash("attention"),
            learner_input_hash=learner_input_hash("answer"),
            next_action="drill",
            strategy="analogy",
            evidence_score=0.91,
            evidence_band="proceed",
            faithfulness_ok=True,
            retrieved_citation_ids=["note/attention::0"],
            tool_calls=["retrieve_course_corpus"],
            learner_message="PRIVATE GENERATED TEXT",
        )
    except ValidationError as exc:
        assert "learner_message" in str(exc)
    else:
        raise AssertionError("raw trace fields must be rejected")


def test_append_review_queue_writes_jsonl(tmp_path):
    path = tmp_path / "review_queue.jsonl"

    append_review_queue(
        path,
        session_id="abc",
        topic_hash=topic_hash("attention"),
        reason="no supporting span",
        score=0.41,
        citation_ids=[],
    )

    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["session_id"] == "abc"
    assert row["topic_hash"] == topic_hash("attention")
    assert "topic" not in row
    assert row["reason"] == "no supporting span"
    assert row["citation_ids"] == []
