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


def test_tool_match_ordered():
    m = tool_match(
        actual=["retrieve_course_corpus", "grade_understanding"],
        expected=["retrieve_course_corpus", "grade_understanding"],
    )
    assert m["f1"] == 1.0 and m["ordered_ok"] is True


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


def test_price_table_cost():
    assert PriceTable(prices={"m": (1e-6, 2e-6)}).cost(
        "m", input_tokens=1000, output_tokens=1000
    ) == 0.003


def test_aggregate_computes_p95_across_turns():
    rows = [
        {
            "task_completion_pass": True,
            "refusal_expected": False,
            "turn_latencies_ms": [10.0, 20.0],
            "input_tokens": 100,
            "output_tokens": 50,
            "model_id": "m",
        },
        {
            "task_completion_pass": False,
            "refusal_expected": False,
            "turn_latencies_ms": [30.0],
            "input_tokens": 0,
            "output_tokens": 0,
            "model_id": "m",
        },
    ]
    out = aggregate(rows, price_table=PriceTable(prices={"m": (1e-6, 2e-6)}))
    assert out["task_completion"] == {"pass_rate": 0.5, "passed": 1, "n": 2}
    assert "task_completion_f1" not in out
    assert "latency_p95_ms" in out and out["cost_usd"] >= 0.0
