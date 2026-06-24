from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any


def precision_recall_f1(*, tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def citation_prf(
    predicted: set[str] | list[str] | tuple[str, ...],
    expected: set[str] | list[str] | tuple[str, ...],
) -> tuple[float, float, float]:
    predicted_set = {item for item in predicted if item}
    expected_set = {item for item in expected if item}
    if not predicted_set and not expected_set:
        return 1.0, 1.0, 1.0
    tp = len(predicted_set & expected_set)
    fp = len(predicted_set - expected_set)
    fn = len(expected_set - predicted_set)
    return precision_recall_f1(tp=tp, fp=fp, fn=fn)


def tool_match(actual: list[str], expected: list[str]) -> dict[str, float]:
    # Tool coverage is scored over the *set* of unique tools, not the per-call multiset:
    # the runner flattens tool calls across all turns, so repeated/retried calls would
    # otherwise read as false positives. Sequence order is not scored.
    actual_set = set(actual)
    expected_set = set(expected)
    if not actual_set and not expected_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    tp = len(actual_set & expected_set)
    fp = len(actual_set - expected_set)
    fn = len(expected_set - actual_set)
    precision, recall, f1 = precision_recall_f1(tp=tp, fp=fp, fn=fn)
    return {"precision": precision, "recall": recall, "f1": f1}


def recall_at_k(ranked_ids: list[str], expected_id: str | None, *, k: int = 5) -> bool:
    return bool(expected_id and expected_id in ranked_ids[:k])


def refusal_outcome(*, refusal_expected: bool, actual_next_action: str) -> str:
    refused = actual_next_action == "refuse_escalate"
    if refusal_expected and refused:
        return "tp"
    if refusal_expected and not refused:
        return "fn"
    if not refusal_expected and refused:
        return "fp"
    return "tn"


@dataclass(frozen=True)
class PriceTable:
    prices: dict[str, tuple[float, float]]

    def cost(self, model_id: str, *, input_tokens: int, output_tokens: int) -> float:
        input_price, output_price = self.prices.get(model_id, (0.0, 0.0))
        return (input_tokens * input_price) + (output_tokens * output_price)


def _pct(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    index = max(0, min(len(sorted_vals) - 1, math.ceil(q * len(sorted_vals)) - 1))
    return sorted_vals[index]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _prf_dict(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision, recall, f1 = precision_recall_f1(tp=tp, fp=fp, fn=fn)
    return {"precision": precision, "recall": recall, "f1": f1}


def _pass_rate(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    passed = sum(1 for row in rows if row.get("task_completion_pass") is True)
    failed = sum(1 for row in rows if row.get("task_completion_pass") is False)
    total = passed + failed
    return {"pass_rate": passed / total if total else 0.0, "passed": passed, "n": total}


def aggregate(rows: list[dict[str, Any]], *, price_table: PriceTable) -> dict[str, Any]:
    teachable = [row for row in rows if not row.get("refusal_expected")]
    refusal_rows = [row for row in rows if row.get("refusal_expected")]

    refusal_counts = Counter(str(row.get("refusal_outcome", "tn")) for row in rows)
    latencies = sorted(
        float(value)
        for row in rows
        for value in row.get("turn_latencies_ms", [])
    )
    input_tokens = sum(int(row.get("input_tokens") or 0) for row in rows)
    output_tokens = sum(int(row.get("output_tokens") or 0) for row in rows)
    total_tokens = sum(
        int(row.get("total_tokens") or 0)
        or int(row.get("input_tokens") or 0) + int(row.get("output_tokens") or 0)
        for row in rows
    )
    cost_usd = sum(
        price_table.cost(
            str(row.get("model_id") or ""),
            input_tokens=int(row.get("input_tokens") or 0),
            output_tokens=int(row.get("output_tokens") or 0),
        )
        for row in rows
    )

    citation_precision = [
        float(row["citation_precision"]) for row in teachable if "citation_precision" in row
    ]
    citation_recall = [
        float(row["citation_recall"]) for row in teachable if "citation_recall" in row
    ]
    citation_f1 = [
        float(row["citation_f1"]) for row in teachable if "citation_f1" in row
    ]
    tool_f1 = [float(row["tool_f1"]) for row in teachable if "tool_f1" in row]
    retrieval = [
        1.0 if row.get("retrieval_recall_at_5") else 0.0
        for row in teachable
        if "retrieval_recall_at_5" in row
    ]

    return {
        "n": len(rows),
        "class_balance": dict(
            sorted(Counter(row.get("query_type", "unknown") for row in rows).items())
        ),
        "segment_counts": {
            "teachable": len(teachable),
            "refusal_expected": len(refusal_rows),
        },
        "task_completion": {
            **_pass_rate(rows),
            "by_segment": {
                "teachable": _pass_rate(teachable),
                "refusal_expected": _pass_rate(refusal_rows),
            },
        },
        "citation": {
            "precision": _mean(citation_precision or citation_f1),
            "recall": _mean(citation_recall or citation_f1),
            "f1": _mean(citation_f1),
        },
        "citation_f1": _mean(citation_f1),
        "tool": {"f1": _mean(tool_f1)},
        "tool_f1": _mean(tool_f1),
        "retrieval_recall_at_5": _mean(retrieval),
        "refusal": _prf_dict(
            refusal_counts["tp"],
            refusal_counts["fp"],
            refusal_counts["fn"],
        ),
        "latency_p50_ms": _pct(latencies, 0.50),
        "latency_p95_ms": _pct(latencies, 0.95),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
    }
