import json
from pathlib import Path

from genacademy_coach.quiz_session import (
    NO_CITEABLE_QUIZ_CORPUS,
    NO_GROUNDED_QUIZ_ITEMS,
    QuizSession,
)
from genacademy_coach.quiz_types import QuizQuestion, QuizTraceRow


class FakeSettings:
    stop_threshold = 0.60
    confirm_threshold = 0.85

    def __init__(self, root: Path):
        self.trace_dir = root / "traces"
        self.review_queue_path = root / "review_queue.jsonl"


class FakeProvider:
    pass


class FakeFoundation:
    provider = FakeProvider()

    def __init__(self, rows, *, expected_query: str = "agent harness"):
        self.rows = rows
        self.expected_query = expected_query

    def retrieve(self, query: str):
        assert query == self.expected_query
        return self.rows


def span_row(**overrides):
    row = {
        "chunk_id": "note/attention::0",
        "doc_id": "note/attention",
        "text": "Attention focuses relevant context.",
        "score": 0.91,
        "title": "attention.md",
        "source_type": "note",
        "page_or_section": None,
    }
    row.update(overrides)
    return row


def quiz_question(question_id: str, citation_id: str = "note/attention::0") -> QuizQuestion:
    return QuizQuestion(
        question_id=question_id,
        prompt="Which option is supported?",
        options=[
            {"option_id": "A", "text": "Attention focuses relevant context."},
            {"option_id": "B", "text": "Attention stores profiles."},
            {"option_id": "C", "text": "Attention disables tools."},
            {"option_id": "D", "text": "Attention deletes context."},
        ],
        correct_option_id="A",
        expected_answer="Attention focuses relevant context.",
        rationale="The span says attention focuses relevant context.",
        citation_id=citation_id,
        expected_keywords=["relevant context"],
    )


def test_quiz_session_refuses_low_retrieval_and_writes_review_queue(tmp_path):
    session = QuizSession(
        session_id="quiz-1",
        topic="agent harness",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation([span_row(score=0.2)]),
    )

    result = session.run()

    assert result.refusal_reason == NO_CITEABLE_QUIZ_CORPUS
    review_row = json.loads((tmp_path / "review_queue.jsonl").read_text(encoding="utf-8"))
    assert review_row["reason"] == NO_CITEABLE_QUIZ_CORPUS
    trace_row = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    assert trace_row["refusal_reason"] == NO_CITEABLE_QUIZ_CORPUS
    assert trace_row["evidence_score"] == 0.2
    assert trace_row["evidence_band"] == "stop"


def test_quiz_session_generates_cited_questions_and_grades_answers(tmp_path, monkeypatch):
    def fake_generate(_provider, span, *, question_id):
        return quiz_question(question_id, citation_id=span.citation_id)

    monkeypatch.setattr("genacademy_coach.quiz_session.generate_quiz_question", fake_generate)
    session = QuizSession(
        session_id="quiz-1",
        topic="agent harness",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation([span_row()]),
        question_count=1,
    )

    result = session.run(["A"])

    assert result.score == 1
    assert result.grades[0].correct is True
    assert result.questions[0].citation_id == "note/attention::0"
    trace_row = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    assert trace_row["citation_ids"] == ["note/attention::0"]
    assert trace_row["selected_option_ids"] == ["A"]
    assert trace_row["evidence_band"] == "proceed"
    assert "Attention focuses relevant context" not in Path(result.trace_path).read_text(
        encoding="utf-8"
    )


def test_quiz_session_accepts_transcript_spans_through_same_citation_path(
    tmp_path,
    monkeypatch,
):
    def fake_generate(_provider, span, *, question_id):
        return quiz_question(question_id, citation_id=span.citation_id)

    monkeypatch.setattr("genacademy_coach.quiz_session.generate_quiz_question", fake_generate)
    session = QuizSession(
        session_id="quiz-1",
        topic="agent harness",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(
            [span_row(chunk_id="transcript/session2::3", source_type="transcript")]
        ),
        question_count=1,
    )

    result = session.run()

    assert result.questions[0].citation_id == "transcript/session2::3"


def test_quiz_session_trace_omits_raw_private_topic(tmp_path, monkeypatch):
    private_topic = "PRIVATE EVAL QUESTION TEXT"

    def fake_generate(_provider, span, *, question_id):
        return quiz_question(question_id, citation_id=span.citation_id)

    monkeypatch.setattr("genacademy_coach.quiz_session.generate_quiz_question", fake_generate)
    session = QuizSession(
        session_id="quiz-1",
        topic=private_topic,
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation([span_row()], expected_query=private_topic),
        question_count=1,
    )

    result = session.run()
    serialized = Path(result.trace_path).read_text(encoding="utf-8")
    trace_row = json.loads(serialized)

    assert private_topic not in serialized
    assert "topic" not in trace_row
    assert "topic_hash" in trace_row


def test_quiz_session_trace_omits_raw_quiz_content(tmp_path, monkeypatch):
    private_values = [
        "PRIVATE QUIZ PROMPT",
        "PRIVATE OPTION TEXT",
        "PRIVATE EXPECTED ANSWER",
        "PRIVATE RATIONALE",
        "PRIVATE KEYWORD",
        "PRIVATE SPAN TEXT",
    ]

    def fake_generate(_provider, span, *, question_id):
        return QuizQuestion(
            question_id=question_id,
            prompt=private_values[0],
            options=[
                {"option_id": "A", "text": private_values[1]},
                {"option_id": "B", "text": "Wrong option B"},
                {"option_id": "C", "text": "Wrong option C"},
                {"option_id": "D", "text": "Wrong option D"},
            ],
            correct_option_id="A",
            expected_answer=private_values[2],
            rationale=private_values[3],
            citation_id=span.citation_id,
            expected_keywords=[private_values[4]],
        )

    monkeypatch.setattr("genacademy_coach.quiz_session.generate_quiz_question", fake_generate)
    session = QuizSession(
        session_id="quiz-1",
        topic="agent harness",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation([span_row(text=private_values[5])]),
        question_count=1,
    )

    result = session.run(["A"])
    serialized = Path(result.trace_path).read_text(encoding="utf-8")

    for private_value in private_values:
        assert private_value not in serialized
    trace_row = json.loads(serialized)
    assert set(trace_row) == set(QuizTraceRow.model_fields)


def test_quiz_session_refuses_when_all_generated_items_are_invalid(tmp_path, monkeypatch):
    def fake_generate(_provider, _span, *, question_id):
        raise ValueError(f"bad item {question_id}")

    monkeypatch.setattr("genacademy_coach.quiz_session.generate_quiz_question", fake_generate)
    session = QuizSession(
        session_id="quiz-1",
        topic="agent harness",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation([span_row()]),
    )

    result = session.run()

    assert result.refusal_reason == NO_GROUNDED_QUIZ_ITEMS
    assert result.questions == []
    review_row = json.loads((tmp_path / "review_queue.jsonl").read_text(encoding="utf-8"))
    assert review_row["reason"] == NO_GROUNDED_QUIZ_ITEMS


def test_quiz_session_refuses_partial_generation_instead_of_grading_mismatch(
    tmp_path,
    monkeypatch,
):
    def fake_generate(_provider, span, *, question_id):
        if span.citation_id == "note/attention::0":
            return quiz_question(question_id, citation_id=span.citation_id)
        raise ValueError("bad item")

    monkeypatch.setattr("genacademy_coach.quiz_session.generate_quiz_question", fake_generate)
    session = QuizSession(
        session_id="quiz-1",
        topic="agent harness",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(
            [
                span_row(chunk_id="note/attention::0"),
                span_row(chunk_id="note/tools::0", text="Tools let agents act."),
            ]
        ),
        question_count=2,
    )

    result = session.run(["A", "B"])

    assert result.refusal_reason == NO_GROUNDED_QUIZ_ITEMS
    assert result.grades == []
