from types import SimpleNamespace

import pytest

from genacademy_coach.eval_golden import GoldenCase
from genacademy_coach.eval_runner import resolve_query, score_golden_case
from genacademy_coach.teach_types import (
    CheckItem,
    CoachAgentResponse,
    RetrievedSpan,
    TraceTurn,
    UnderstandingGrade,
)
from genacademy_coach.trace import TraceWriter


class FakeSession:
    def __init__(self, **kwargs):
        self.session_id = kwargs["session_id"]
        self.settings = kwargs["settings"]
        self._turn = 0
        self.runtime = SimpleNamespace(
            last_spans=[
                RetrievedSpan(
                    chunk_id="note::0",
                    doc_id="note",
                    text="Attention focuses context.",
                    score=0.91,
                    title="a.md",
                    source_type="note",
                )
            ],
            current_check=CheckItem(
                question="What does attention do?",
                expected_answer="It includes the generated keyword.",
                expected_keywords=["generated keyword"],
                citation_id="note::0",
            ),
            last_grade=UnderstandingGrade(
                correct=True,
                matched_keywords=["generated keyword"],
                missing_keywords=[],
                citation_id="note::0",
            ),
            tool_calls=[],
        )

    def _write(self, response: CoachAgentResponse, tool_calls: list[str]):
        self._turn += 1
        path = TraceWriter(self.settings.trace_dir).append(
            TraceTurn(
                session_id=self.session_id,
                turn=self._turn,
                topic_hash="topic",
                learner_input_hash=f"input-{self._turn}",
                next_action=response.next_action,
                strategy=response.strategy,
                evidence_score=0.91,
                evidence_band="proceed",
                retrieved_citation_ids=["note::0"],
                tool_calls=tool_calls,
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
                latency_ms=25.0,
            )
        )
        return SimpleNamespace(response=response, trace_path=str(path))

    def start(self):
        response = CoachAgentResponse(
            learner_message="Attention focuses context. [note::0]",
            observation="retrieved span",
            next_action="drill",
            strategy="analogy",
            citation_ids=["note::0"],
            check_question="What does attention do?",
        )
        return self._write(response, ["retrieve_course_corpus", "generate_check_item"])

    def respond(self, learner_answer):
        correct = "generated keyword" in learner_answer
        self.runtime.last_grade = UnderstandingGrade(
            correct=correct,
            matched_keywords=["generated keyword"] if correct else [],
            missing_keywords=[] if correct else ["generated keyword"],
            citation_id="note::0",
        )
        response = CoachAgentResponse(
            learner_message="Attention focuses context. [note::0]",
            observation="graded answer",
            next_action="advance" if correct else "re_explain_differently",
            strategy="summary" if correct else "contrastive_example",
            citation_ids=["note::0"],
        )
        return self._write(response, ["grade_understanding", "update_profile"])


def test_resolve_query_uses_inline_for_cloud_safe():
    c = GoldenCase(
        case_id="c",
        query_type="happy",
        concept="t",
        expected_next_action="advance",
        expected_tools=["retrieve_course_corpus"],
        split="synthetic",
        cloud_safe=True,
        cloud_safe_reason="syn",
        user_query="what is a token",
        expected_check_keywords=["token"],
    )
    assert resolve_query(c, scenario_index={}) == "what is a token"


def test_resolve_query_resolves_source_ref_for_non_cloud_safe():
    c = GoldenCase(
        case_id="c",
        query_type="happy",
        concept="t",
        expected_next_action="advance",
        expected_tools=["retrieve_course_corpus"],
        split="seed",
        cloud_safe=False,
        source_ref="scenario:i:000",
        expected_check_keywords=["token"],
    )
    assert (
        resolve_query(c, scenario_index={"i:000": "real private question"})
        == "real private question"
    )


def test_resolve_query_raises_clear_error_without_parseable_source_ref():
    c = GoldenCase(
        case_id="c",
        query_type="happy",
        concept="t",
        expected_next_action="advance",
        expected_tools=["retrieve_course_corpus"],
        split="synthetic",
        cloud_safe=True,
        cloud_safe_reason="syn",
        expected_check_keywords=["token"],
    )
    with pytest.raises(ValueError, match="no inline user_query and no parseable source_ref"):
        resolve_query(c, scenario_index={})


def test_resolve_query_raises_clear_error_for_unknown_source_ref():
    c = GoldenCase(
        case_id="c",
        query_type="happy",
        concept="t",
        expected_next_action="advance",
        expected_tools=["retrieve_course_corpus"],
        split="seed",
        cloud_safe=False,
        source_ref="scenario:i:000",
        expected_check_keywords=["token"],
    )
    with pytest.raises(ValueError, match="source_ref scenario i:000 not found"):
        resolve_query(c, scenario_index={})


def test_score_golden_case_emits_redacted_metric_row(fake_settings, fake_foundation):
    case = GoldenCase(
        case_id="happy_001",
        query_type="happy",
        concept="tokenization",
        expected_citation_span_id="note::0",
        expected_next_action="advance",
        expected_tools=[
            "retrieve_course_corpus",
            "generate_check_item",
            "grade_understanding",
        ],
        refusal_expected=False,
        split="seed",
        cloud_safe=False,
        source_ref="scenario:i:000",
        expected_check_keywords=["token"],
    )
    row = score_golden_case(
        settings=fake_settings,
        foundation=fake_foundation,
        case=case,
        scenario_index={"i:000": "what is a token"},
        session_factory=FakeSession,
    )
    for k in (
        "task_completion_pass",
        "citation_f1",
        "tool_f1",
        "retrieval_recall_at_5",
        "refusal_outcome",
        "turn_latencies_ms",
        "input_tokens",
        "output_tokens",
        "model_id",
    ):
        assert k in row
    assert row["task_completion_pass"] is True
    assert "user_query" not in row and "answer_text" not in row
