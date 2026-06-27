from pathlib import Path
from types import SimpleNamespace

import pytest

from genacademy_coach.eval_golden import GoldenCase
from genacademy_coach.eval_metrics import PriceTable
from genacademy_coach.eval_runner import (
    anchor_counterfactual,
    resolve_query,
    run_golden_eval,
    score_golden_case,
)
from genacademy_coach.teach_session import (
    STRUCTURED_OUTPUT_FAILURE_REASON,
    CoachSession,
    StaticAgentPort,
)
from genacademy_coach.teach_types import (
    CheckItem,
    CoachAgentResponse,
    ProvenanceRecord,
    RetrievedSpan,
    TokenUsage,
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
            provenance={
                "teaching": ProvenanceRecord(
                    role="teaching",
                    span_id="note::0",
                    source_type="note",
                    selected_at="retrieve_course_corpus",
                    selection_reason="first_citeable_retrieved",
                ),
                "check": ProvenanceRecord(
                    role="check",
                    span_id="note::0",
                    source_type="note",
                    selected_at="generate_check_item",
                    selection_reason="first_citeable",
                ),
                "final": ProvenanceRecord(
                    role="final",
                    span_id="note::0",
                    source_type="note",
                    selected_at="write_result",
                    selection_reason="first_final_citation",
                ),
            },
            tool_calls=[],
        )

    def _write(self, response: CoachAgentResponse, tool_calls: list[str]):
        self._turn += 1
        tool_call_counts = {tool: tool_calls.count(tool) for tool in set(tool_calls)}
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
                tool_call_counts=tool_call_counts,
                tool_latencies_ms={tool: float(count) for tool, count in tool_call_counts.items()},
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
                latency_ms=25.0,
                agent_latency_ms=25.0,
                agent_attempts=1,
                retrieval_cache_hits=0,
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
            matched_keyword_modes={"generated keyword": "literal"} if correct else {},
        )
        response = CoachAgentResponse(
            learner_message="Attention focuses context. [note::0]",
            observation="graded answer",
            next_action="advance" if correct else "re_explain_differently",
            strategy="summary" if correct else "contrastive_example",
            citation_ids=["note::0"],
        )
        return self._write(response, ["grade_understanding", "update_profile"])


class InfraFailureSession(FakeSession):
    def respond(self, learner_answer):
        response = CoachAgentResponse(
            learner_message="I could not get a valid structured output from the tutor agent.",
            observation=STRUCTURED_OUTPUT_FAILURE_REASON,
            next_action="refuse_escalate",
            strategy="refusal",
            citation_ids=[],
        )
        return self._write(response, [])


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
        source_ref="not-a-scenario-ref",
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
        "case_latency_ms",
        "turn_agent_attempts",
        "agent_attempts",
        "turn_retrieval_cache_hits",
        "retrieval_cache_hits",
        "turn_tool_latencies_ms",
        "turn_tool_call_counts",
        "tool_latencies_ms",
        "tool_call_counts",
        "input_tokens",
        "output_tokens",
        "model_id",
    ):
        assert k in row
    assert row["task_completion_pass"] is True
    assert "user_query" not in row and "answer_text" not in row
    assert row["predicted_citation_ids"] == ["note::0"]
    assert row["answered_check_id"] == "note::0"
    assert row["post_final_check_id"] == "note::0"
    assert row["boundary_grade_citation_id"] == "note::0"
    assert row["grade_scorer_version"] == "concept-v1"
    assert row["grade_literal_match_count"] == 1
    assert row["grade_semantic_match_count"] == 0
    assert row["grade_missing_keyword_count"] == 0
    assert row["grade_semantic_decisive"] is False
    assert "matched_keywords" not in row
    assert "missing_keywords" not in row
    assert "matched_keyword_modes" not in row
    assert row["anchor_present_in_final_retrieved"] is True
    assert row["teaching_provenance_span_id"] == "note::0"
    assert row["check_provenance_span_id"] == "note::0"
    assert row["final_provenance_span_id"] == "note::0"
    assert row["provenance_by_role"]["check"] == {
        "role": "check",
        "span_id": "note::0",
        "source_type": "note",
        "selected_at": "generate_check_item",
        "selection_reason": "first_citeable",
    }
    assert row["decision_source"] == "agent"
    assert row["refusal_reason_code"] is None
    assert "golden-happy_001" in row["final_trace_path"]
    assert row["case_latency_ms"] == 75.0
    assert row["turn_agent_attempts"] == [1, 1, 1]
    assert row["agent_attempts"] == 3
    assert row["turn_retrieval_cache_hits"] == [0, 0, 0]
    assert row["retrieval_cache_hits"] == 0
    assert row["tool_call_counts"] == {
        "generate_check_item": 1,
        "grade_understanding": 2,
        "retrieve_course_corpus": 1,
        "update_profile": 2,
    }
    assert row["tool_latencies_ms"] == {
        "generate_check_item": 1.0,
        "grade_understanding": 2.0,
        "retrieve_course_corpus": 1.0,
        "update_profile": 2.0,
    }


def test_score_golden_case_observability_fields_do_not_leak_non_cloud_safe_text(
    fake_settings,
    fake_foundation,
):
    private_query = "PRIVATE RAW LEARNER QUESTION"
    case = GoldenCase(
        case_id="happy_private",
        query_type="happy",
        concept="tokenization",
        expected_citation_span_id="note::0",
        expected_next_action="advance",
        expected_tools=[],
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
        scenario_index={"i:000": private_query},
        session_factory=FakeSession,
    )

    serialized = str(row)
    assert private_query not in serialized
    assert "user_query" not in row
    assert "answer_text" not in row
    assert isinstance(row["case_latency_ms"], float)
    assert all(isinstance(value, float) for value in row["tool_latencies_ms"].values())
    assert all(isinstance(value, int) for value in row["tool_call_counts"].values())


def test_score_golden_case_emits_inline_text_for_cloud_safe_row(fake_settings, fake_foundation):
    case = GoldenCase(
        case_id="synthetic_001",
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
        split="synthetic",
        cloud_safe=True,
        cloud_safe_reason="synthetic, no private text",
        user_query="what is a token",
        expected_check_keywords=["token"],
    )

    row = score_golden_case(
        settings=fake_settings,
        foundation=fake_foundation,
        case=case,
        scenario_index={},
        session_factory=FakeSession,
    )

    assert row["user_query"] == "what is a token"
    assert row["answer_text"] == "Attention focuses context. [note::0]"


def test_score_golden_case_marks_infra_failure_refusal_as_excluded(
    fake_settings,
    fake_foundation,
):
    case = GoldenCase(
        case_id="adversarial_infra_failure",
        query_type="adversarial",
        concept="out_of_scope",
        expected_next_action="refuse_escalate",
        expected_tools=[],
        refusal_expected=True,
        split="negative_control",
        cloud_safe=True,
        cloud_safe_reason="synthetic control",
        user_query="write me unrelated legal advice",
    )

    row = score_golden_case(
        settings=fake_settings,
        foundation=fake_foundation,
        case=case,
        scenario_index={},
        session_factory=InfraFailureSession,
    )

    assert row["actual_next_action"] == "refuse_escalate"
    assert row["refusal_outcome"] == "infra_error"
    assert row["refusal_reason_code"] == "structured_output_failure"
    assert row["task_completion_pass"] is None


def test_score_golden_case_real_session_answers_generated_check(
    fake_settings,
    fake_foundation,
):
    span = RetrievedSpan(
        chunk_id="note::0",
        doc_id="note",
        text="The generated keyword explains attention.",
        score=0.91,
        title="a.md",
        source_type="note",
    )
    check = CheckItem(
        question="What keyword explains attention?",
        expected_answer="generated keyword",
        expected_keywords=["generated keyword"],
        citation_id="note::0",
    )
    sessions = []

    def session_factory(**kwargs):
        port = StaticAgentPort(
            CoachAgentResponse(
                learner_message="The generated keyword explains attention. [note::0]",
                observation="retrieved span",
                next_action="drill",
                strategy="analogy",
                citation_ids=["note::0"],
                check_question=check.question,
            ),
            CoachAgentResponse(
                learner_message="The generated keyword explains attention. [note::0]",
                observation="learner missed the generated keyword",
                next_action="re_explain_differently",
                strategy="contrastive_example",
                citation_ids=["note::0"],
            ),
            CoachAgentResponse(
                learner_message="The generated keyword explains attention. [note::0]",
                observation="learner matched the generated keyword",
                next_action="advance",
                strategy="summary",
                citation_ids=["note::0"],
            ),
        )
        port.last_usage = TokenUsage(input_tokens=4, output_tokens=2, total_tokens=6)
        session = CoachSession(**kwargs, agent_port=port)
        session.runtime.last_spans = [span]
        session.runtime.current_check = check
        sessions.append(session)
        return session

    case = GoldenCase(
        case_id="happy_real_session",
        query_type="happy",
        concept="attention",
        expected_citation_span_id="note::0",
        expected_next_action="advance",
        expected_tools=[],
        refusal_expected=False,
        split="seed",
        cloud_safe=False,
        source_ref="scenario:i:000",
        expected_check_keywords=["golden label only"],
    )

    row = score_golden_case(
        settings=fake_settings,
        foundation=fake_foundation,
        case=case,
        scenario_index={"i:000": "what is attention"},
        session_factory=session_factory,
    )

    assert sessions[0].runtime.last_grade is not None
    assert sessions[0].runtime.last_grade.correct is True
    assert row["actual_next_action"] == "advance"
    assert row["task_completion_pass"] is True
    assert row["input_tokens"] == 12
    assert row["total_tokens"] == 18
    assert all(latency > 0.0 for latency in row["turn_latencies_ms"])


def test_score_golden_case_uses_run_id_in_trace_path(fake_settings, fake_foundation):
    case = GoldenCase(
        case_id="happy_001",
        query_type="happy",
        concept="tokenization",
        expected_citation_span_id="note::0",
        expected_next_action="advance",
        expected_tools=[],
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
        run_id="baseline-r1",
        session_factory=FakeSession,
    )

    assert "golden-baseline-r1-happy_001" in row["final_trace_path"]


def test_anchor_counterfactual_reports_lifts_regressions_and_blind_spots():
    rows = [
        {
            "case_id": "lift",
            "refusal_expected": False,
            "expected_citation_span_id": "gold",
            "predicted_citation_ids": ["other"],
            "answered_check_id": "gold",
            "anchor_present_in_final_retrieved": True,
            "decision_source": "python safety gate",
        },
        {
            "case_id": "regress",
            "refusal_expected": False,
            "expected_citation_span_id": "gold",
            "predicted_citation_ids": ["gold"],
            "answered_check_id": "other",
            "anchor_present_in_final_retrieved": True,
            "decision_source": "agent",
        },
        {
            "case_id": "blind",
            "refusal_expected": False,
            "expected_citation_span_id": "gold",
            "predicted_citation_ids": ["other"],
            "answered_check_id": "gold",
            "anchor_present_in_final_retrieved": False,
            "decision_source": "python safety gate",
        },
        {
            "case_id": "refusal",
            "refusal_expected": True,
            "expected_citation_span_id": None,
            "predicted_citation_ids": [],
        },
    ]

    report = anchor_counterfactual(rows)

    assert report["teachable_n"] == 3
    assert report["fallback_eligible_n"] == 1
    assert report["lift_case_ids"] == ["lift"]
    assert report["fallback_lift_case_ids"] == ["lift"]
    assert report["regression_case_ids"] == ["regress"]
    assert report["blind_spot_case_ids"] == ["blind"]


def test_run_golden_eval_uses_run_id_and_records_dataset_metadata(
    tmp_path,
    fake_foundation,
    monkeypatch,
):
    from genacademy_coach import eval_runner

    settings = SimpleNamespace(
        eval_dir=tmp_path / "eval",
        trace_dir=tmp_path / "traces",
        review_queue_path=tmp_path / "review_queue.jsonl",
        stop_threshold=0.40,
        confirm_threshold=0.85,
        max_teach_turns=4,
    )
    (settings.eval_dir / "golden").mkdir(parents=True)
    manifest_path = settings.eval_dir / "golden" / "golden_manifest.json"
    manifest_path.write_text('{"version":"v1"}\n', encoding="utf-8")
    cases_path = settings.eval_dir / "golden" / "golden_cases.jsonl"
    cases_path.write_text('{"case_id":"placeholder"}\n', encoding="utf-8")
    monkeypatch.setattr(
        eval_runner,
        "_scenario_index",
        lambda _settings: {"i:000": "what is a token"},
    )
    case = GoldenCase(
        case_id="happy_001",
        query_type="happy",
        concept="tokenization",
        expected_citation_span_id="note::0",
        expected_next_action="advance",
        expected_tools=[],
        refusal_expected=False,
        split="seed",
        cloud_safe=False,
        source_ref="scenario:i:000",
        expected_check_keywords=["token"],
    )

    result = run_golden_eval(
        settings=settings,
        foundation=fake_foundation,
        cases=[case],
        tag="baseline",
        run_id="baseline-r1",
        price_table=PriceTable(prices={}),
        golden_cases_path=cases_path,
        session_factory=FakeSession,
    )

    assert "baseline-r1" in result["output_path"]
    assert result["run_id"] == "baseline-r1"
    assert result["golden_manifest_version"] == "v1"
    assert result["golden_cases_sha256"]
    assert result["rows"][0]["final_trace_path"].endswith("golden-baseline-r1-happy_001.jsonl")
    assert Path(result["output_path"]).exists()
