from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

FORBIDDEN_OUTPUT_KEYS = {
    "user_query",
    "answer_text",
    "predicted_text",
    "final_text",
    "assistant_text",
    "tutor_text",
    "retrieved_span",
    "retrieved_span_text",
    "raw_span",
    "raw_prompt",
    "system_prompt",
    "trace",
    "trace_id",
    "trace_json",
    "langsmith_url",
    "langsmith_experiment_url",
}


def citation_source_type(citation_id: str | None) -> str:
    if not citation_id or "/" not in citation_id:
        return "unknown"
    return citation_id.split("/", 1)[0] or "unknown"


def citation_source_family(citation_id: str | None) -> str:
    if not citation_id:
        return ""
    return citation_id.split("::", 1)[0]


def _nonempty_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value or "").strip()]


def _source_types(ids: list[str]) -> list[str]:
    return sorted({citation_source_type(citation_id) for citation_id in ids})


def _source_families(ids: list[str]) -> list[str]:
    return sorted(
        {family for citation_id in ids if (family := citation_source_family(citation_id))}
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def review_bucket(row: dict[str, Any]) -> str:
    expected_id = str(row.get("expected_citation_span_id") or "")
    predicted_ids = _nonempty_strings(row.get("predicted_citation_ids"))
    retrieved_ids = _nonempty_strings(row.get("retrieved_citation_ids"))
    predicted_set = set(predicted_ids)
    retrieved_set = set(retrieved_ids)
    expected_family = citation_source_family(expected_id)
    predicted_families = set(_source_families(predicted_ids))

    if expected_id and expected_id in predicted_set and len(predicted_set) > 1:
        return "expected_exact_plus_extra_citations"
    if not predicted_set and row.get("actual_next_action") == "refuse_escalate":
        return "refused_no_final_citation"
    if expected_id and expected_id in retrieved_set and expected_family in predicted_families:
        return "expected_retrieved_predicted_same_source_family"
    if expected_id and expected_id in retrieved_set and predicted_set:
        return "expected_retrieved_predicted_other_source"
    if expected_id and expected_id not in retrieved_set and row.get("retrieval_recall_at_5"):
        return "expected_missing_from_final_trace_but_seen_in_ranked_retrieval"
    if expected_id and expected_id not in retrieved_set:
        return "expected_not_in_final_retrieved"
    return "other_citation_mismatch"


def audit_row(row: dict[str, Any]) -> dict[str, Any]:
    expected_id = str(row.get("expected_citation_span_id") or "")
    predicted_ids = _nonempty_strings(row.get("predicted_citation_ids"))
    retrieved_ids = _nonempty_strings(row.get("retrieved_citation_ids"))
    expected_family = citation_source_family(expected_id)
    predicted_families = set(_source_families(predicted_ids))

    return {
        "case_id": str(row.get("case_id") or ""),
        "query_type": str(row.get("query_type") or "unknown"),
        "split": str(row.get("split") or "unknown"),
        "cloud_safe": bool(row.get("cloud_safe")),
        "expected_citation_span_id": expected_id or None,
        "expected_source_type": citation_source_type(expected_id),
        "expected_source_family": expected_family or None,
        "predicted_citation_ids": predicted_ids,
        "predicted_source_types": _source_types(predicted_ids),
        "predicted_source_families": _source_families(predicted_ids),
        "retrieved_citation_ids": retrieved_ids,
        "retrieved_source_types": _source_types(retrieved_ids),
        "answered_check_id": row.get("answered_check_id"),
        "post_final_check_id": row.get("post_final_check_id"),
        "boundary_grade_citation_id": row.get("boundary_grade_citation_id"),
        "anchor_present_in_final_retrieved": bool(row.get("anchor_present_in_final_retrieved")),
        "expected_exact_predicted": bool(expected_id and expected_id in set(predicted_ids)),
        "expected_exact_retrieved": bool(expected_id and expected_id in set(retrieved_ids)),
        "predicted_same_source_family": bool(
            expected_family and expected_family in predicted_families
        ),
        "citation_precision": float(row.get("citation_precision") or 0.0),
        "citation_recall": float(row.get("citation_recall") or 0.0),
        "citation_f1": float(row.get("citation_f1") or 0.0),
        "retrieval_recall_at_5": bool(row.get("retrieval_recall_at_5")),
        "evidence_band": str(row.get("evidence_band") or "unknown"),
        "evidence_score": float(row.get("evidence_score") or 0.0),
        "faithfulness_ok": row.get("faithfulness_ok"),
        "actual_next_action": str(row.get("actual_next_action") or "unknown"),
        "decision_source": str(row.get("decision_source") or "unknown"),
        "refusal_reason_code": row.get("refusal_reason_code"),
        "review_bucket": review_bucket(row),
        "citation_miss_category": None,
    }


def _exact_or_family_flags(row: dict[str, Any]) -> tuple[bool, bool]:
    expected_id = str(row.get("expected_citation_span_id") or "")
    predicted_ids = _nonempty_strings(row.get("predicted_citation_ids"))
    expected_family = citation_source_family(expected_id)
    predicted_families = set(_source_families(predicted_ids))
    exact = bool(expected_id and expected_id in set(predicted_ids))
    same_family = bool(expected_family and expected_family in predicted_families)
    return exact, same_family


def _assert_public_safe(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_OUTPUT_KEYS:
                raise ValueError(f"forbidden audit output key at {path}.{key}: {key}")
            _assert_public_safe(child, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _assert_public_safe(child, f"{path}[{index}]")
        return
    if isinstance(value, str) and "smith.langchain.com" in value:
        raise ValueError(f"forbidden private LangSmith URL at {path}")


def build_audit(run_payload: dict[str, Any], *, source_path: Path) -> dict[str, Any]:
    rows = [row for row in run_payload.get("rows", []) if isinstance(row, dict)]
    test_rows = [str(row.get("case_id") or "") for row in rows if row.get("split") == "test"]
    if test_rows:
        raise ValueError("refusing to audit frozen test rows: " + ", ".join(test_rows))

    teachable = [row for row in rows if not row.get("refusal_expected")]
    misses = [row for row in teachable if float(row.get("citation_f1") or 0.0) < 1.0]
    audit_rows = [audit_row(row) for row in misses]
    bucket_counts = Counter(row["review_bucket"] for row in audit_rows)
    query_type_counts = Counter(row["query_type"] for row in audit_rows)
    expected_source_type_counts = Counter(row["expected_source_type"] for row in audit_rows)

    current_f1 = [float(row.get("citation_f1") or 0.0) for row in teachable]
    exact_or_extra_ceiling: list[float] = []
    same_family_ceiling: list[float] = []
    for row in teachable:
        row_f1 = float(row.get("citation_f1") or 0.0)
        exact, same_family = _exact_or_family_flags(row)
        exact_or_extra_ceiling.append(1.0 if exact else row_f1)
        same_family_ceiling.append(1.0 if exact or same_family else row_f1)

    payload = {
        "schema_version": 1,
        "source_run_file": source_path.name,
        "source_run_tag": run_payload.get("tag"),
        "source_run_id": run_payload.get("run_id"),
        "golden_manifest_version": run_payload.get("golden_manifest_version"),
        "golden_cases_sha256": run_payload.get("golden_cases_sha256"),
        "n_rows": len(rows),
        "teachable_rows": len(teachable),
        "citation_miss_rows": len(audit_rows),
        "test_rows": 0,
        "current_teachable_citation_f1_mean": _mean(current_f1),
        "heuristic_exact_or_extra_ceiling_f1": _mean(exact_or_extra_ceiling),
        "heuristic_same_source_family_ceiling_f1": _mean(same_family_ceiling),
        "review_bucket_counts": dict(sorted(bucket_counts.items())),
        "miss_query_type_counts": dict(sorted(query_type_counts.items())),
        "miss_expected_source_type_counts": dict(sorted(expected_source_type_counts.items())),
        "rows": audit_rows,
        "notes": [
            "Rows are public-safe review candidates, not final human citation labels.",
            "citation_miss_category is intentionally null until a reviewer inspects support.",
            (
                "Heuristic ceilings are not product deltas; they estimate "
                "label/source-family ambiguity."
            ),
        ],
    }
    _assert_public_safe(payload)
    return payload


def load_run(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
        raise ValueError(f"{path}: expected a golden run object with a rows array")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a public-safe citation provenance audit from a redacted golden run."
    )
    parser.add_argument("run_json", type=Path)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    run_path = args.run_json
    payload = build_audit(load_run(run_path), source_path=run_path)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
