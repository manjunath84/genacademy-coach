import pytest

from genacademy_coach.eval_metrics import (
    PriceTable,
    aggregate,
    citation_prf,
    precision_recall_f1,
    recall_at_k,
    refusal_outcome,
    tool_match,
)


def test_prf_basic():
    p, r, f = precision_recall_f1(tp=8, fp=2, fn=2)
    assert (round(p, 2), round(r, 2), round(f, 2)) == (0.8, 0.8, 0.8)


def test_citation_prf_sets():
    p, r, f = citation_prf(predicted={"a", "b"}, expected={"a"})
    assert round(p, 2) == 0.5 and r == 1.0


def test_tool_match_exact_set():
    m = tool_match(
        actual=["retrieve_course_corpus", "grade_understanding"],
        expected=["retrieve_course_corpus", "grade_understanding"],
    )
    assert m["precision"] == 1.0 and m["recall"] == 1.0 and m["f1"] == 1.0
    assert "ordered_ok" not in m


def test_tool_match_ignores_repeated_actual_calls_for_f1():
    m = tool_match(
        actual=[
            "retrieve_course_corpus",
            "retrieve_course_corpus",
            "grade_understanding",
        ],
        expected=["retrieve_course_corpus", "grade_understanding"],
    )
    assert m["f1"] == 1.0


def test_recall_at_k():
    assert recall_at_k(["x", "y", "z"], "y", k=5) and not recall_at_k(["x", "y", "z"], "q", k=2)


def test_refusal_outcome():
    assert refusal_outcome(refusal_expected=True, actual_next_action="refuse_escalate") == "tp"
    assert refusal_outcome(refusal_expected=False, actual_next_action="refuse_escalate") == "fp"


def test_refusal_outcome_excludes_infrastructure_errors():
    assert (
        refusal_outcome(
            refusal_expected=True,
            actual_next_action="refuse_escalate",
            infrastructure_error=True,
        )
        == "infra_error"
    )


def test_price_table_cost():
    assert PriceTable(prices={"m": (1e-6, 2e-6)}).cost(
        "m", input_tokens=1000, output_tokens=1000
    ) == pytest.approx(0.003)


def test_aggregate_computes_p95_across_turns():
    rows = [
        {
            "task_completion_pass": True,
            "refusal_expected": False,
            "case_id": "case-1",
            "turn_latencies_ms": [10.0, 20.0],
            "case_latency_ms": 35.0,
            "tool_call_counts": {
                "retrieve_course_corpus": 1,
                "generate_check_item": 1,
            },
            "tool_latencies_ms": {
                "retrieve_course_corpus": 2.0,
                "generate_check_item": 20.0,
            },
            "input_tokens": 100,
            "output_tokens": 50,
            "model_id": "m",
        },
        {
            "task_completion_pass": False,
            "refusal_expected": False,
            "case_id": "case-2",
            "turn_latencies_ms": [30.0],
            "tool_call_counts": {"retrieve_course_corpus": 2},
            "tool_latencies_ms": {"retrieve_course_corpus": 5.0},
            "input_tokens": 0,
            "output_tokens": 0,
            "model_id": "m",
        },
    ]
    out = aggregate(rows, price_table=PriceTable(prices={"m": (1e-6, 2e-6)}))
    assert out["task_completion"]["pass_rate"] == 0.5
    assert out["task_completion"]["passed"] == 1 and out["task_completion"]["n"] == 2
    assert out["task_completion"]["by_segment"]["teachable"] == {
        "pass_rate": 0.5,
        "passed": 1,
        "n": 2,
    }
    assert out["task_completion"]["by_segment"]["refusal_expected"] == {
        "pass_rate": 0.0,
        "passed": 0,
        "n": 0,
    }
    assert "task_completion_f1" not in out
    assert "latency_p95_ms" in out and out["cost_usd"] >= 0.0
    assert out["latency_p95_ms"] == 30.0
    assert out["turn_latency_p95_ms"] == 30.0
    assert out["case_latency_p50_ms"] == 30.0
    assert out["case_latency_p95_ms"] == 35.0
    assert out["avg_tool_calls_per_case"] == 2.0
    assert out["tool_call_counts"] == {
        "generate_check_item": 1,
        "retrieve_course_corpus": 3,
    }
    assert out["total_tool_latencies_ms"] == {
        "generate_check_item": 20.0,
        "retrieve_course_corpus": 7.0,
    }
    assert out["max_repeated_tool_count"] == 2
    assert out["max_repeated_tool_count_by_case"] == {
        "case-1": 1,
        "case-2": 2,
    }


def test_aggregate_quality_means_exclude_refusal_controls():
    rows = [
        {
            "task_completion_pass": True,
            "refusal_expected": False,
            "citation_precision": 0.5,
            "citation_recall": 0.5,
            "citation_f1": 0.5,
            "tool_f1": 0.5,
            "retrieval_recall_at_5": True,
            "turn_latencies_ms": [],
            "model_id": "m",
        },
        {
            "task_completion_pass": True,
            "refusal_expected": True,
            "citation_precision": 1.0,
            "citation_recall": 1.0,
            "citation_f1": 1.0,
            "tool_f1": 0.0,
            "retrieval_recall_at_5": False,
            "refusal_outcome": "tp",
            "turn_latencies_ms": [],
            "model_id": "m",
        },
    ]
    out = aggregate(rows, price_table=PriceTable(prices={"m": (0.0, 0.0)}))
    assert out["segment_counts"] == {"teachable": 1, "refusal_expected": 1}
    assert out["citation_f1"] == 0.5
    assert out["tool_f1"] == 0.5
    assert out["retrieval_recall_at_5"] == 1.0
    assert out["task_completion"]["pass_rate"] == 1.0
    assert out["task_completion"]["by_segment"]["teachable"] == {
        "pass_rate": 1.0,
        "passed": 1,
        "n": 1,
    }
    assert out["task_completion"]["by_segment"]["refusal_expected"] == {
        "pass_rate": 1.0,
        "passed": 1,
        "n": 1,
    }


def test_aggregate_excludes_infra_errors_from_refusal_and_completion():
    rows = [
        {
            "query_type": "adversarial",
            "refusal_expected": True,
            "refusal_outcome": "tp",
            "task_completion_pass": True,
            "turn_latencies_ms": [],
            "model_id": "m",
        },
        {
            "query_type": "adversarial",
            "refusal_expected": True,
            "refusal_outcome": "infra_error",
            "task_completion_pass": None,
            "turn_latencies_ms": [],
            "model_id": "m",
        },
    ]

    out = aggregate(rows, price_table=PriceTable(prices={"m": (0.0, 0.0)}))

    assert out["n"] == 2
    assert out["class_balance"] == {"adversarial": 2}
    assert out["refusal"] == {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    assert out["task_completion"] == {
        "pass_rate": 1.0,
        "passed": 1,
        "n": 1,
        "by_segment": {
            "teachable": {"pass_rate": 0.0, "passed": 0, "n": 0},
            "refusal_expected": {"pass_rate": 1.0, "passed": 1, "n": 1},
        },
    }
