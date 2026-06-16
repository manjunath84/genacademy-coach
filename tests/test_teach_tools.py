import json

from genacademy_coach.teach_tools import TeachRuntime, build_teach_tools
from genacademy_coach.teach_types import CheckItem, LearnerProfile, UnderstandingGrade


class FakeFoundation:
    provider = object()

    def retrieve(self, query: str):
        assert query == "attention"
        return [
            {
                "chunk_id": "note/attention::0",
                "doc_id": "note/attention",
                "text": "Attention focuses relevant context.",
                "score": 0.91,
                "title": "attention.md",
                "source_type": "note",
                "page_or_section": None,
            }
        ]


class SequentialFoundation:
    provider = object()

    def __init__(self):
        self.calls = 0

    def retrieve(self, query: str):
        self.calls += 1
        if self.calls == 1:
            return [
                {
                    "chunk_id": "note/attention::0",
                    "doc_id": "note/attention",
                    "text": "Attention focuses relevant context.",
                    "score": 0.91,
                    "title": "attention.md",
                    "source_type": "note",
                    "page_or_section": None,
                }
            ]
        return [
            {
                "chunk_id": "note/noisy::0",
                "doc_id": "note/noisy",
                "text": "Noisy low-confidence text.",
                "score": 0.21,
                "title": "noisy.md",
                "source_type": "note",
                "page_or_section": None,
            }
        ]


def runtime(tmp_path) -> TeachRuntime:
    return TeachRuntime(
        session_id="abc",
        topic="attention",
        profile=LearnerProfile(),
        foundation=FakeFoundation(),
        stop_threshold=0.60,
        confirm_threshold=0.85,
        review_queue_path=tmp_path / "review_queue.jsonl",
    )


def test_retrieve_tool_records_last_spans(tmp_path):
    active_runtime = runtime(tmp_path)
    tools = build_teach_tools(active_runtime)
    retrieve_tool = next(tool for tool in tools if tool.name == "retrieve_course_corpus")

    payload = retrieve_tool.invoke({"query": "attention"})
    rows = json.loads(payload)

    assert rows[0]["citation_id"] == "note/attention::0"
    assert rows[0]["evidence_band"] == "proceed"
    assert active_runtime.last_spans[0].score == 0.91


def test_retrieve_tool_keeps_previous_citeable_spans_on_later_retrieval_miss(tmp_path):
    active_runtime = runtime(tmp_path)
    active_runtime.foundation = SequentialFoundation()
    retrieve_tool = next(
        tool for tool in build_teach_tools(active_runtime) if tool.name == "retrieve_course_corpus"
    )

    first_payload = retrieve_tool.invoke({"query": "attention"})
    second_payload = retrieve_tool.invoke({"query": "bad query"})

    assert json.loads(first_payload)[0]["citation_id"] == "note/attention::0"
    assert json.loads(second_payload) == []
    assert active_runtime.last_spans[0].citation_id == "note/attention::0"


def test_grade_tool_uses_current_check_item(tmp_path):
    active_runtime = runtime(tmp_path)
    active_runtime.current_check = CheckItem(
        question="What does attention do?",
        expected_answer="Focuses context.",
        expected_keywords=["focuses", "context"],
        citation_id="note/attention::0",
    )
    grade_tool = next(
        tool for tool in build_teach_tools(active_runtime) if tool.name == "grade_understanding"
    )

    payload = grade_tool.invoke({"answer": "It focuses context."})
    row = json.loads(payload)

    assert row["correct"] is True
    assert active_runtime.last_grade is not None
    assert active_runtime.last_grade.correct is True


def test_grade_tool_preserves_locked_boundary_grade(tmp_path):
    active_runtime = runtime(tmp_path)
    active_runtime.current_check = CheckItem(
        question="What does attention do?",
        expected_answer="Focuses context.",
        expected_keywords=["focuses", "context"],
        citation_id="note/attention::0",
    )
    active_runtime.last_grade = UnderstandingGrade(
        correct=True,
        matched_keywords=["focuses", "context"],
        missing_keywords=[],
        citation_id="note/attention::0",
    )
    active_runtime.grade_locked = True
    grade_tool = next(
        tool for tool in build_teach_tools(active_runtime) if tool.name == "grade_understanding"
    )

    payload = grade_tool.invoke({"answer": "It stores customer profiles."})
    row = json.loads(payload)

    assert row["correct"] is True
    assert active_runtime.last_grade.correct is True


def test_escalation_tool_writes_review_queue(tmp_path):
    active_runtime = runtime(tmp_path)
    active_runtime.last_spans = []
    escalate_tool = next(
        tool for tool in build_teach_tools(active_runtime) if tool.name == "escalate_to_mentor"
    )

    payload = escalate_tool.invoke({"reason": "no supporting span"})

    assert json.loads(payload)["queued"] is True
    assert "no supporting span" in (tmp_path / "review_queue.jsonl").read_text(encoding="utf-8")


def test_escalation_tool_is_idempotent_within_turn(tmp_path):
    active_runtime = runtime(tmp_path)
    escalate_tool = next(
        tool for tool in build_teach_tools(active_runtime) if tool.name == "escalate_to_mentor"
    )

    escalate_tool.invoke({"reason": "first"})
    escalate_tool.invoke({"reason": "second"})

    rows = (tmp_path / "review_queue.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    assert "first" in rows[0]
