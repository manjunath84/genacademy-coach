import json

from genacademy_coach.teach_tools import TeachRuntime, build_teach_tools
from genacademy_coach.teach_types import (
    CheckItem,
    LearnerProfile,
    RetrievedSpan,
    UnderstandingGrade,
)


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


class MissThenHitFoundation:
    provider = object()

    def __init__(self):
        self.calls = 0

    def retrieve(self, query: str):
        self.calls += 1
        if self.calls == 1:
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


class MixedSourceFoundation:
    provider = object()

    def retrieve(self, query: str):
        assert query == "attention"
        return [
            {
                "chunk_id": "note/attention::0",
                "doc_id": "note/attention",
                "text": "Attention focuses relevant context.",
                "score": 0.95,
                "title": "attention.md",
                "source_type": "note",
                "page_or_section": None,
            },
            {
                "chunk_id": "handout/attention::2",
                "doc_id": "handout/attention",
                "text": "Attention helps select relevant context.",
                "score": 0.93,
                "title": "attention.pdf",
                "source_type": "handout",
                "page_or_section": "2",
            },
            {
                "chunk_id": "slide/attention::1",
                "doc_id": "slide/attention",
                "text": "Attention highlights the relevant context window.",
                "score": 0.91,
                "title": "attention.pdf",
                "source_type": "slide",
                "page_or_section": "1",
            },
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
    assert rows[0]["preferred_for_check"] is True
    assert active_runtime.last_spans[0].score == 0.91
    assert active_runtime.tool_call_counts == {"retrieve_course_corpus": 1}
    assert active_runtime.tool_latencies_ms["retrieve_course_corpus"] >= 0.0


def test_retrieve_tool_marks_slide_or_handout_as_preferred_check_span(tmp_path):
    active_runtime = runtime(tmp_path)
    active_runtime.foundation = MixedSourceFoundation()
    retrieve_tool = next(
        tool for tool in build_teach_tools(active_runtime) if tool.name == "retrieve_course_corpus"
    )

    payload = retrieve_tool.invoke({"query": "attention"})
    rows = json.loads(payload)

    assert rows[0]["citation_id"] == "note/attention::0"
    assert rows[0]["preferred_for_check"] is False
    assert rows[1]["citation_id"] == "handout/attention::2"
    assert rows[1]["preferred_for_check"] is False
    assert rows[2]["citation_id"] == "slide/attention::1"
    assert rows[2]["preferred_for_check"] is True


def test_retrieve_tool_reuses_current_turn_citeable_spans_without_second_foundation_call(
    tmp_path,
):
    active_runtime = runtime(tmp_path)
    active_runtime.foundation = SequentialFoundation()
    retrieve_tool = next(
        tool for tool in build_teach_tools(active_runtime) if tool.name == "retrieve_course_corpus"
    )

    first_payload = retrieve_tool.invoke({"query": "attention"})
    second_payload = retrieve_tool.invoke({"query": "bad query"})

    assert json.loads(first_payload)[0]["citation_id"] == "note/attention::0"
    assert json.loads(second_payload)[0]["citation_id"] == "note/attention::0"
    assert active_runtime.last_spans[0].citation_id == "note/attention::0"
    assert active_runtime.foundation.calls == 1
    assert active_runtime.tool_call_counts == {"retrieve_course_corpus": 2}


def test_retrieve_tool_allows_second_lookup_when_first_lookup_has_no_citeable_spans(
    tmp_path,
):
    active_runtime = runtime(tmp_path)
    active_runtime.foundation = MissThenHitFoundation()
    retrieve_tool = next(
        tool for tool in build_teach_tools(active_runtime) if tool.name == "retrieve_course_corpus"
    )

    first_payload = retrieve_tool.invoke({"query": "bad query"})
    second_payload = retrieve_tool.invoke({"query": "attention"})

    assert json.loads(first_payload) == []
    assert json.loads(second_payload)[0]["citation_id"] == "note/attention::0"
    assert active_runtime.foundation.calls == 2


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
    assert active_runtime.tool_call_counts == {"grade_understanding": 1}
    assert active_runtime.tool_latencies_ms["grade_understanding"] >= 0.0


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


def test_generate_check_unlocks_stale_boundary_grade(tmp_path, monkeypatch):
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
    active_runtime.last_spans = [
        RetrievedSpan(
            chunk_id="note/tools::0",
            doc_id="note/tools",
            text="Tools let an agent act outside the model.",
            score=0.91,
            title="tools.md",
            source_type="note",
        )
    ]

    def fake_generate_check_item(_provider, span):
        return CheckItem(
            question="What do tools let an agent do?",
            expected_answer="Tools let an agent act outside the model.",
            expected_keywords=["agent act"],
            citation_id=span.citation_id,
        )

    monkeypatch.setattr(
        "genacademy_coach.teach_tools.generate_check_item",
        fake_generate_check_item,
    )
    tools = build_teach_tools(active_runtime)
    generate_tool = next(tool for tool in tools if tool.name == "generate_check_item_for_span")
    grade_tool = next(tool for tool in tools if tool.name == "grade_understanding")

    generated = json.loads(generate_tool.invoke({"citation_id": "note/tools::0"}))
    payload = grade_tool.invoke({"answer": "It lets the agent act."})
    row = json.loads(payload)

    assert generated["citation_id"] == "note/tools::0"
    assert active_runtime.grade_locked is False
    assert row["citation_id"] == "note/tools::0"
    assert row["correct"] is True
    assert active_runtime.tool_call_counts == {
        "generate_check_item": 1,
        "grade_understanding": 1,
    }
    assert active_runtime.tool_latencies_ms["generate_check_item"] >= 0.0


def test_generate_check_reuses_current_check_for_same_citation_without_provider_call(
    tmp_path,
    monkeypatch,
):
    active_runtime = runtime(tmp_path)
    active_runtime.current_check = CheckItem(
        question="What does attention do?",
        expected_answer="Focuses context.",
        expected_keywords=["focuses", "context"],
        citation_id="note/attention::0",
    )
    active_runtime.grade_locked = True
    active_runtime.last_spans = [
        RetrievedSpan(
            chunk_id="note/attention::0",
            doc_id="note/attention",
            text="Attention focuses relevant context.",
            score=0.91,
            title="attention.md",
            source_type="note",
        )
    ]

    def fail_generate_check_item(_provider, _span):
        raise AssertionError("provider should not be called for current check")

    monkeypatch.setattr(
        "genacademy_coach.teach_tools.generate_check_item",
        fail_generate_check_item,
    )
    generate_tool = next(
        tool for tool in build_teach_tools(active_runtime)
        if tool.name == "generate_check_item_for_span"
    )

    generated = json.loads(generate_tool.invoke({"citation_id": "note/attention::0"}))

    assert generated["citation_id"] == "note/attention::0"
    assert active_runtime.grade_locked is True
    assert active_runtime.tool_call_counts == {"generate_check_item": 1}


def test_escalation_tool_writes_review_queue(tmp_path):
    active_runtime = runtime(tmp_path)
    active_runtime.last_spans = []
    escalate_tool = next(
        tool for tool in build_teach_tools(active_runtime) if tool.name == "escalate_to_mentor"
    )

    payload = escalate_tool.invoke({"reason": "no supporting span"})

    assert json.loads(payload)["queued"] is True
    row = json.loads((tmp_path / "review_queue.jsonl").read_text(encoding="utf-8"))
    assert row["reason"] == "no supporting span"
    assert "topic_hash" in row
    assert "topic" not in row
    assert active_runtime.tool_call_counts == {"escalate_to_mentor": 1}
    assert active_runtime.tool_latencies_ms["escalate_to_mentor"] >= 0.0


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
    assert active_runtime.tool_call_counts == {"escalate_to_mentor": 2}
