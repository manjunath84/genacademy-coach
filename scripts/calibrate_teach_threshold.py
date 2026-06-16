from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

from genacademy_rag.core.types import RetrievedChunk

from genacademy_coach.foundation import Foundation
from genacademy_coach.grounding import evidence_band
from genacademy_coach.settings import CoachSettings

DEFAULT_NEGATIVE_CONTROLS_PATH = (
    Path(__file__).resolve().parents[1] / "eval" / "non_private_negative_controls.json"
)
DEFAULT_THRESHOLDS = tuple(round(value / 100, 2) for value in range(40, 61))


def load_diagnostics_module() -> Any:
    script_path = Path(__file__).with_name("diagnose_teach_retrieval.py")
    spec = importlib.util.spec_from_file_location("diagnose_teach_retrieval", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load diagnostic script at {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DIAGNOSTICS = load_diagnostics_module()


def load_scenarios(settings: CoachSettings, *, split: str, limit: int) -> list[dict[str, str]]:
    return DIAGNOSTICS.load_scenarios(settings, split=split, limit=limit)


def source_counts(values: list[Any]) -> dict[str, int]:
    return DIAGNOSTICS.source_counts(values)


def summarize_scores(scores: list[float]) -> dict[str, float | int]:
    return DIAGNOSTICS.summarize_scores(scores)


def load_negative_controls(path: Path) -> list[dict[str, str]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("negative controls file must contain a non-empty JSON list")

    controls = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"negative control at index {idx} must be an object")
        control_id = str(row.get("id", "")).strip()
        category = str(row.get("category", "")).strip()
        query = str(row.get("query", "")).strip()
        if not control_id or not category or not query:
            raise ValueError(
                "negative controls require non-empty id, category, and query fields"
            )
        controls.append({"id": control_id, "category": category, "query": query})
    return controls


def parse_thresholds(raw: str) -> tuple[float, ...]:
    values = tuple(round(float(item.strip()), 4) for item in raw.split(",") if item.strip())
    if not values:
        raise ValueError("at least one threshold candidate is required")
    return tuple(sorted(set(values)))


def row_from_retrieved(item: RetrievedChunk) -> dict[str, Any]:
    return {
        "chunk_id": item.chunk.chunk_id,
        "score": item.score,
        "source_type": item.chunk.citation.source_type,
    }


def top_score(rows: list[dict[str, Any]]) -> float:
    top = max(
        rows,
        key=lambda item: (float(item.get("score", 0.0)), str(item.get("chunk_id", ""))),
        default=None,
    )
    return float(top["score"]) if top is not None else 0.0


def score_query(
    *,
    retriever: Any,
    query: str,
    settings: CoachSettings,
) -> dict[str, Any]:
    raw = retriever.retrieve(query)
    rows = [row_from_retrieved(item) for item in raw]
    score = top_score(rows)
    return {
        "raw_count": len(raw),
        "raw_top_score": score,
        "raw_band": evidence_band(
            score,
            stop_threshold=settings.stop_threshold,
            confirm_threshold=settings.confirm_threshold,
        ),
        "raw_source_types": source_counts([row.get("source_type") for row in rows]),
    }


def score_positive_scenarios(
    *,
    retriever: Any,
    settings: CoachSettings,
    split: str,
    limit: int,
) -> list[dict[str, Any]]:
    results = []
    for scenario in load_scenarios(settings, split=split, limit=limit):
        row = score_query(
            retriever=retriever,
            query=scenario["question_text"],
            settings=settings,
        )
        results.append(
            {
                "kind": "positive",
                "split": split,
                "scenario_id": scenario["scenario_id"],
                "item_id": scenario["item_id"],
                "source_file": scenario["source_file"],
                "question_word_count": len(scenario["question_text"].split()),
                **row,
            }
        )
    return results


def score_negative_controls(
    *,
    retriever: Any,
    settings: CoachSettings,
    controls: list[dict[str, str]],
) -> list[dict[str, Any]]:
    results = []
    for control in controls:
        row = score_query(
            retriever=retriever,
            query=control["query"],
            settings=settings,
        )
        results.append(
            {
                "kind": "negative_control",
                "control_id": control["id"],
                "category": control["category"],
                "query_word_count": len(control["query"].split()),
                **row,
            }
        )
    return results


def threshold_row(
    *,
    threshold: float,
    positives: list[dict[str, Any]],
    negatives: list[dict[str, Any]],
) -> dict[str, Any]:
    seed = [row for row in positives if row["split"] == "seed"]
    dev = [row for row in positives if row["split"] == "dev"]
    negative_at_or_above = [
        row for row in negatives if float(row["raw_top_score"]) >= threshold
    ]
    positive_at_or_above = [
        row for row in positives if float(row["raw_top_score"]) >= threshold
    ]
    return {
        "threshold": threshold,
        "positive_at_or_above": len(positive_at_or_above),
        "positive_total": len(positives),
        "seed_at_or_above": sum(float(row["raw_top_score"]) >= threshold for row in seed),
        "seed_total": len(seed),
        "dev_at_or_above": sum(float(row["raw_top_score"]) >= threshold for row in dev),
        "dev_total": len(dev),
        "negative_controls_at_or_above": len(negative_at_or_above),
        "negative_controls_total": len(negatives),
        "all_negative_controls_stop": not negative_at_or_above,
    }


def recommend_threshold(rows: list[dict[str, Any]]) -> float | None:
    safe_rows = [row for row in rows if row["all_negative_controls_stop"]]
    if not safe_rows:
        return None
    return float(min(safe_rows, key=lambda row: row["threshold"])["threshold"])


def score_summary(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    return summarize_scores([float(row["raw_top_score"]) for row in rows])


def category_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(row["category"]) for row in rows)
    return dict(sorted(counts.items()))


def build_payload(
    *,
    settings: CoachSettings,
    foundation: Foundation,
    seed_limit: int,
    dev_limit: int,
    negative_controls_path: Path,
    thresholds: tuple[float, ...],
) -> dict[str, Any]:
    controls = load_negative_controls(negative_controls_path)
    retriever = foundation.retriever()
    seed = score_positive_scenarios(
        retriever=retriever,
        settings=settings,
        split="seed",
        limit=seed_limit,
    )
    dev = score_positive_scenarios(
        retriever=retriever,
        settings=settings,
        split="dev",
        limit=dev_limit,
    )
    negatives = score_negative_controls(
        retriever=retriever,
        settings=settings,
        controls=controls,
    )
    positives = [*seed, *dev]
    table = [
        threshold_row(threshold=threshold, positives=positives, negatives=negatives)
        for threshold in thresholds
    ]
    recommended = recommend_threshold(table)
    negative_scores = [float(row["raw_top_score"]) for row in negatives]
    return {
        "collection": settings.course_collection,
        "current_stop_threshold": settings.stop_threshold,
        "confirm_threshold": settings.confirm_threshold,
        "retrieval_candidate_k": settings.retrieval_candidate_k,
        "retrieval_top_k": settings.retrieval_top_k,
        "negative_controls_path": str(negative_controls_path),
        "negative_control_category_counts": category_counts(negatives),
        "positive_score_summary": score_summary(positives),
        "seed_score_summary": score_summary(seed),
        "dev_score_summary": score_summary(dev),
        "negative_control_score_summary": score_summary(negatives),
        "negative_control_max_score": max(negative_scores, default=0.0),
        "recommended_stop_threshold": recommended,
        "threshold_candidates": table,
        "positive_results": positives,
        "negative_control_results": negatives,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-limit", type=int, default=20)
    parser.add_argument("--dev-limit", type=int, default=10)
    parser.add_argument("--negative-controls", type=Path, default=DEFAULT_NEGATIVE_CONTROLS_PATH)
    parser.add_argument(
        "--thresholds",
        default=",".join(str(item) for item in DEFAULT_THRESHOLDS),
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    settings = CoachSettings.from_env()
    payload = build_payload(
        settings=settings,
        foundation=Foundation.build(settings),
        seed_limit=args.seed_limit,
        dev_limit=args.dev_limit,
        negative_controls_path=args.negative_controls,
        thresholds=parse_thresholds(args.thresholds),
    )
    output = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
