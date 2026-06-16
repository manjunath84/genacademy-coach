import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from genacademy_coach.grounding import evidence_band
from genacademy_coach.teach_types import (
    CheckItem,
    CoachAgentResponse,
    RetrievedSpan,
    UnderstandingGrade,
)


def load_eval_module():
    script_path = Path("scripts/eval_teach_loop.py").resolve()
    spec = importlib.util.spec_from_file_location("eval_teach_loop", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def diagnostic_row(**overrides):
    row = {
        "scenario_id": "item-a:000",
        "item_id": "item-a",
        "source_file": "week1-chat.docx",
        "passed": True,
        "citations_resolve": True,
        "re_explained_differently": True,
        "grade_correct": True,
        "trace_has_runtime_decision": True,
        "teachable": True,
        "safe_refusal": False,
        "top_score": 0.72,
        "retrieved_count": 1,
        "retrieved_source_types": {"handout": 1},
        "citation_ids": ["handout/attention::0"],
        "final_next_action": "advance",
    }
    row.update(overrides)
    return row


def test_load_manifest_items_filters_split(tmp_path):
    manifest = {
        "items": [
            {"id": "a", "split": "dev", "source_file": "a.md"},
            {"id": "b", "split": "test", "source_file": "b.md"},
        ]
    }
    path = tmp_path / "split_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    module = load_eval_module()

    rows = module.load_manifest_items(path, split="dev")

    assert rows == [{"id": "a", "split": "dev", "source_file": "a.md"}]


def test_question_text_for_item_reads_private_source_at_runtime(tmp_path):
    module = load_eval_module()
    eval_dir = tmp_path / "corpus" / "eval-questions"
    eval_dir.mkdir(parents=True)
    (eval_dir / "question.md").write_text(
        "\n\n1. What is attention?\n\n2. Why use citations?\n\n",
        encoding="utf-8",
    )

    rows = module.question_records_for_item(
        eval_dir,
        {"id": "item-a", "split": "dev", "source_file": "question.md"},
    )

    assert [row["scenario_id"] for row in rows] == ["item-a:000", "item-a:001"]
    assert [row["question_text"] for row in rows] == [
        "What is attention?",
        "Why use citations?",
    ]


def test_reset_scenario_trace_removes_previous_eval_rows(tmp_path):
    module = load_eval_module()
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    trace_path = trace_dir / "item-a-000.jsonl"
    trace_path.write_text('{"turn": 1}\n', encoding="utf-8")

    module.reset_scenario_trace(
        SimpleNamespace(trace_dir=trace_dir),
        module.scenario_session_id({"scenario_id": "item-a:000"}),
    )

    assert not trace_path.exists()


def test_score_scenario_runs_teach_loop_instead_of_retrieval_only(tmp_path):
    module = load_eval_module()
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        '{"session_id": "item-a-000", "turn": 1, "learner_input": "teach", '
        '"observation": "retrieved span", "next_action": "drill", "strategy": "analogy", '
        '"evidence_score": 0.91, "evidence_band": "proceed", '
        '"retrieved_citation_ids": ["note/attention::0"], "tool_calls": [], '
        '"learner_message": "first"}\n'
        '{"session_id": "item-a-000", "turn": 2, "learner_input": "wrong", '
        '"observation": "learner confused attention", '
        '"next_action": "re_explain_differently", '
        '"strategy": "contrastive_example", "evidence_score": 0.91, '
        '"evidence_band": "proceed", '
        '"retrieved_citation_ids": ["note/attention::0"], "tool_calls": [], '
        '"learner_message": "second"}\n',
        encoding="utf-8",
    )
    calls = []

    class FakeSession:
        def __init__(self, **kwargs):
            self.runtime = SimpleNamespace(
                last_spans=[
                    RetrievedSpan(
                        chunk_id="note/attention::0",
                        doc_id="note/attention",
                        text="Attention focuses relevant context.",
                        score=0.91,
                        title="attention.md",
                        source_type="note",
                    )
                ],
                current_check=CheckItem(
                    question="What does attention do?",
                    expected_answer="It focuses relevant context.",
                    expected_keywords=["relevant context"],
                    citation_id="note/attention::0",
                ),
                last_grade=UnderstandingGrade(
                    correct=True,
                    matched_keywords=["relevant context"],
                    missing_keywords=[],
                    citation_id="note/attention::0",
                ),
            )

        def start(self):
            calls.append("start")
            return SimpleNamespace(
                response=CoachAgentResponse(
                    learner_message="Attention focuses context. [note/attention::0]",
                    observation="retrieved span",
                    next_action="drill",
                    strategy="analogy",
                    citation_ids=["note/attention::0"],
                    check_question="What does attention do?",
                ),
                trace_path=str(trace_path),
            )

        def respond(self, learner_answer):
            calls.append(learner_answer)
            action = "re_explain_differently" if len(calls) == 2 else "advance"
            strategy = "contrastive_example" if len(calls) == 2 else "summary"
            return SimpleNamespace(
                response=CoachAgentResponse(
                    learner_message="Grounded. [note/attention::0]",
                    observation="graded answer",
                    next_action=action,
                    strategy=strategy,
                    citation_ids=["note/attention::0"],
                ),
                trace_path=str(trace_path),
            )

    result = module.score_scenario(
        settings=SimpleNamespace(
            trace_dir=tmp_path / "traces",
            stop_threshold=0.60,
            confirm_threshold=0.85,
            review_queue_path=tmp_path / "review_queue.jsonl",
            max_teach_turns=4,
        ),
        foundation=object(),
        scenario={
            "scenario_id": "item-a:000",
            "item_id": "item-a",
            "split": "dev",
            "source_file": "question.md",
            "question_text": "What is attention?",
        },
        session_factory=FakeSession,
    )

    assert calls[0] == "start"
    assert result["passed"] is True
    assert result["teachable"] is True
    assert result["safe_refusal"] is False
    assert result["scenario_id"] == "item-a:000"
    assert result["retrieved_count"] == 1
    assert result["retrieved_source_types"] == {"note": 1}
    assert result["diagnostic_reasons"] == []
    assert "question_text" not in result


def test_build_diagnostics_reports_redacted_low_retrieval_and_source_coverage():
    module = load_eval_module()
    results = [
        {
            "scenario_id": "item-a:000",
            "item_id": "item-a",
            "source_file": "week1-chat.docx",
            "passed": False,
            "citations_resolve": False,
            "re_explained_differently": False,
            "grade_correct": False,
            "trace_has_runtime_decision": False,
            "teachable": False,
            "safe_refusal": True,
            "top_score": 0.0,
            "retrieved_count": 0,
            "retrieved_source_types": {},
            "citation_ids": [],
            "final_next_action": "refuse_escalate",
            "question_text": "private text must not appear",
        },
        {
            "scenario_id": "item-a:001",
            "item_id": "item-a",
            "source_file": "week1-chat.docx",
            "passed": False,
            "citations_resolve": False,
            "re_explained_differently": False,
            "grade_correct": True,
            "trace_has_runtime_decision": True,
            "teachable": True,
            "safe_refusal": False,
            "top_score": 0.72,
            "retrieved_count": 2,
            "retrieved_source_types": {"handout": 1, "note": 1},
            "citation_ids": [],
            "final_next_action": "advance",
        },
        {
            "scenario_id": "item-b:000",
            "item_id": "item-b",
            "source_file": "week2-chat.pdf",
            "passed": True,
            "citations_resolve": True,
            "re_explained_differently": True,
            "grade_correct": True,
            "trace_has_runtime_decision": True,
            "teachable": True,
            "safe_refusal": False,
            "top_score": 0.91,
            "retrieved_count": 1,
            "retrieved_source_types": {"slide": 1},
            "citation_ids": ["slide/attention::0"],
            "final_next_action": "advance",
        },
    ]
    for row in results:
        row["diagnostic_reasons"] = module.diagnostic_reasons(row)

    diagnostics = module.build_diagnostics(
        results,
        stop_threshold=0.60,
        confirm_threshold=0.85,
    )

    assert diagnostics["score_band_counts"] == {
        "stop": 1,
        "confirm": 1,
        "proceed": 1,
    }
    assert diagnostics["retrieval_coverage"] == {
        "scenarios_with_spans": 2,
        "scenarios_without_spans": 1,
    }
    assert diagnostics["retrieved_source_type_counts"] == {
        "handout": 1,
        "note": 1,
        "slide": 1,
    }
    assert diagnostics["diagnostic_reason_counts"] == {
        "citation_ids_not_resolved": 1,
        "missing_strategy_change": 1,
        "safe_low_retrieval_refusal": 1,
    }
    assert diagnostics["low_retrieval_by_eval_source_file"] == {"week1-chat.docx": 1}
    assert diagnostics["low_retrieval_scenarios"] == [
        {
            "scenario_id": "item-a:000",
            "item_id": "item-a",
            "source_file": "week1-chat.docx",
            "top_score": 0.0,
            "retrieved_count": 0,
            "retrieved_source_types": {},
            "final_next_action": "refuse_escalate",
            "safe_refusal": True,
            "diagnostic_reasons": ["safe_low_retrieval_refusal"],
        }
    ]
    assert diagnostics["teachable_failures"][0]["scenario_id"] == "item-a:001"
    assert "question_text" not in diagnostics["low_retrieval_scenarios"][0]


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        (
            diagnostic_row(
                passed=False,
                teachable=False,
                safe_refusal=True,
                top_score=0.0,
                retrieved_count=0,
                retrieved_source_types={},
                citation_ids=[],
                final_next_action="refuse_escalate",
            ),
            ["safe_low_retrieval_refusal"],
        ),
        (
            diagnostic_row(passed=False, teachable=False, top_score=0.0),
            ["low_retrieval_not_refused"],
        ),
        (
            diagnostic_row(passed=False, citations_resolve=False, citation_ids=[]),
            ["citation_ids_not_resolved"],
        ),
        (
            diagnostic_row(passed=False, re_explained_differently=False),
            ["missing_strategy_change"],
        ),
        (
            diagnostic_row(passed=False, grade_correct=False),
            ["grade_not_correct"],
        ),
        (
            diagnostic_row(passed=False, trace_has_runtime_decision=False),
            ["missing_runtime_decision_trace"],
        ),
        (
            diagnostic_row(passed=False),
            ["unknown_eval_failure"],
        ),
    ],
)
def test_diagnostic_reasons_covers_reason_taxonomy(row, expected):
    module = load_eval_module()

    assert module.diagnostic_reasons(row) == expected


def test_build_diagnostics_uses_canonical_evidence_band_boundaries():
    module = load_eval_module()
    rows = [
        diagnostic_row(scenario_id="item-a:000", top_score=0.59),
        diagnostic_row(scenario_id="item-a:001", top_score=0.60),
        diagnostic_row(scenario_id="item-a:002", top_score=0.85),
    ]
    for row in rows:
        row["diagnostic_reasons"] = module.diagnostic_reasons(row)

    diagnostics = module.build_diagnostics(
        rows,
        stop_threshold=0.60,
        confirm_threshold=0.85,
    )

    expected_counts = {"stop": 0, "confirm": 0, "proceed": 0}
    for row in rows:
        band = evidence_band(
            row["top_score"],
            stop_threshold=0.60,
            confirm_threshold=0.85,
        )
        expected_counts[band] += 1
    assert diagnostics["score_band_counts"] == expected_counts
    assert [row["scenario_id"] for row in diagnostics["low_retrieval_scenarios"]] == [
        "item-a:000"
    ]
