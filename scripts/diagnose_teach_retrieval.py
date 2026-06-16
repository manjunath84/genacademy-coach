from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

from genacademy_rag.core.types import RetrievedChunk

from genacademy_coach.foundation import (
    Foundation,
    reorder_spans,
    select_retrieved_spans,
    source_priority_map,
)
from genacademy_coach.grounding import evidence_band
from genacademy_coach.settings import CoachSettings


def load_scenarios(settings: CoachSettings, *, split: str, limit: int) -> list[dict[str, str]]:
    script_path = Path(__file__).with_name("eval_teach_loop.py")
    spec = importlib.util.spec_from_file_location("eval_teach_loop", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load eval script at {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_scenarios(settings, split=split, limit=limit)


def source_counts(values: list[Any]) -> dict[str, int]:
    counts = Counter(value or "unknown" for value in values)
    return dict(sorted(counts.items()))


def aggregate_source_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(row[key])
    return dict(sorted(counts.items()))


def summarize_scores(scores: list[float]) -> dict[str, float | int]:
    ordered = sorted(scores)
    if not ordered:
        return {
            "n": 0,
            "min": 0.0,
            "p50_nearest_rank": 0.0,
            "max": 0.0,
            "gte_040": 0,
            "gte_050": 0,
            "gte_055": 0,
            "gte_060": 0,
        }
    p50_index = max(0, ((len(ordered) + 1) // 2) - 1)
    return {
        "n": len(ordered),
        "min": round(ordered[0], 4),
        "p50_nearest_rank": round(ordered[p50_index], 4),
        "max": round(ordered[-1], 4),
        "gte_040": sum(score >= 0.40 for score in ordered),
        "gte_050": sum(score >= 0.50 for score in ordered),
        "gte_055": sum(score >= 0.55 for score in ordered),
        "gte_060": sum(score >= 0.60 for score in ordered),
    }


def row_from_retrieved(item: RetrievedChunk) -> dict[str, Any]:
    return {
        "chunk_id": item.chunk.chunk_id,
        "score": item.score,
        "source_type": item.chunk.citation.source_type,
    }


def top_by_score(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max(
        rows,
        key=lambda item: (float(item.get("score", 0.0)), str(item.get("chunk_id", ""))),
        default=None,
    )


def scenario_retrieval_diagnostic(
    *,
    settings: CoachSettings,
    retriever: Any,
    scenario: dict[str, str],
) -> dict[str, Any]:
    raw = retriever.retrieve(scenario["question_text"])
    raw_rows = [row_from_retrieved(item) for item in raw]
    priority = source_priority_map(settings.source_priority)
    priority_ordered = reorder_spans(raw_rows, priority)
    selected = select_retrieved_spans(
        raw_rows,
        priority,
        limit=settings.retrieval_top_k,
    )
    raw_top = top_by_score(raw_rows)
    priority_top = priority_ordered[0] if priority_ordered else None
    raw_top_score = float(raw_top["score"]) if raw_top is not None else 0.0
    priority_top_score = float(priority_top["score"]) if priority_top is not None else 0.0
    selected_top_score = max((float(item["score"]) for item in selected), default=0.0)
    return {
        "scenario_id": scenario["scenario_id"],
        "item_id": scenario["item_id"],
        "source_file": scenario["source_file"],
        "split": scenario["split"],
        "question_word_count": len(scenario["question_text"].split()),
        "raw_count": len(raw),
        "raw_top_score": raw_top_score,
        "raw_band": evidence_band(
            raw_top_score,
            stop_threshold=settings.stop_threshold,
            confirm_threshold=settings.confirm_threshold,
        ),
        "raw_source_types": source_counts(
            [item.get("source_type") for item in raw_rows]
        ),
        "priority_top_score": priority_top_score,
        "priority_top_source_type": (
            priority_top.get("source_type") or "unknown"
            if priority_top is not None
            else None
        ),
        "source_priority_would_drop_top_score": bool(
            raw_top is not None
            and priority_top is not None
            and raw_top["chunk_id"] != priority_top["chunk_id"]
        ),
        "raw_minus_priority_top_score": round(raw_top_score - priority_top_score, 4),
        "selected_count": len(selected),
        "selected_top_score": selected_top_score,
        "selected_band": evidence_band(
            selected_top_score,
            stop_threshold=settings.stop_threshold,
            confirm_threshold=settings.confirm_threshold,
        ),
        "selected_source_types": source_counts(
            [item.get("source_type") for item in selected]
        ),
    }


def build_payload(
    *,
    settings: CoachSettings,
    foundation: Foundation,
    split: str,
    limit: int,
) -> dict[str, Any]:
    scenarios = load_scenarios(settings, split=split, limit=limit)
    retriever = foundation.retriever()
    results = [
        scenario_retrieval_diagnostic(
            settings=settings,
            retriever=retriever,
            scenario=scenario,
        )
        for scenario in scenarios
    ]
    raw_scores = [float(row["raw_top_score"]) for row in results]
    selected_scores = [float(row["selected_top_score"]) for row in results]
    return {
        "split": split,
        "n": len(results),
        "collection": settings.course_collection,
        "stop_threshold": settings.stop_threshold,
        "confirm_threshold": settings.confirm_threshold,
        "retrieval_top_k": settings.retrieval_top_k,
        "retrieval_candidate_k": settings.retrieval_candidate_k,
        "raw_score_summary": summarize_scores(raw_scores),
        "selected_score_summary": summarize_scores(selected_scores),
        "raw_source_type_counts": aggregate_source_counts(results, "raw_source_types"),
        "selected_source_type_counts": aggregate_source_counts(
            results,
            "selected_source_types",
        ),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="dev", choices=["seed", "dev"])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json-out", type=str)
    args = parser.parse_args()

    settings = CoachSettings.from_env()
    payload = build_payload(
        settings=settings,
        foundation=Foundation.build(settings),
        split=args.split,
        limit=args.limit,
    )
    output = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        path = Path(args.json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
