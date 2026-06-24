from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from genacademy_coach.eval_scenarios import (
    QUESTION_PREFIX_RE,
    extract_questions,
    load_manifest_items,
    load_scenarios,
    question_records_for_item,
)
from genacademy_coach.foundation import Foundation
from genacademy_coach.grounding import evidence_band, evidence_score
from genacademy_coach.settings import CoachSettings
from genacademy_coach.teach_session import CoachSession
from genacademy_coach.teach_types import LearnerProfile, RetrievedSpan
from genacademy_coach.trace import load_trace

DEFAULT_WRONG_ANSWER = "I am not sure; I think it just memorizes previous tokens."

__all__ = [
    "QUESTION_PREFIX_RE",
    "extract_questions",
    "load_manifest_items",
    "load_scenarios",
    "question_records_for_item",
]


def load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_path, override=False)


def _trace_has_runtime_decision(trace_path: Path) -> bool:
    rows = load_trace(trace_path)
    return any(row.next_action == "re_explain_differently" for row in rows)


def scenario_session_id(scenario: dict[str, str]) -> str:
    return scenario["scenario_id"].replace(":", "-")


def reset_scenario_trace(settings: CoachSettings, session_id: str) -> None:
    trace_path = settings.trace_dir / f"{session_id}.jsonl"
    if trace_path.exists():
        trace_path.unlink()


def count_source_types(spans: list[RetrievedSpan]) -> dict[str, int]:
    counts = Counter(span.source_type or "unknown" for span in spans)
    return {source_type: counts[source_type] for source_type in sorted(counts)}


def diagnostic_reasons(row: dict[str, Any]) -> list[str]:
    if row["safe_refusal"]:
        return ["safe_low_retrieval_refusal"]

    reasons = []
    if not row["teachable"]:
        reasons.append("low_retrieval_not_refused")
    if row["teachable"] and not row["citations_resolve"]:
        reasons.append("citation_ids_not_resolved")
    if row["teachable"] and not row["re_explained_differently"]:
        reasons.append("missing_strategy_change")
    if row["teachable"] and not row["grade_correct"]:
        reasons.append("grade_not_correct")
    if row["teachable"] and not row["trace_has_runtime_decision"]:
        reasons.append("missing_runtime_decision_trace")
    if not reasons and not row["passed"]:
        # Defensive for externally assembled rows; score_scenario classifies normal failures above.
        reasons.append("unknown_eval_failure")
    return reasons


def diagnostic_scenario(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario_id": row["scenario_id"],
        "item_id": row["item_id"],
        "source_file": row["source_file"],
        "top_score": row["top_score"],
        "retrieved_count": row["retrieved_count"],
        "retrieved_source_types": row["retrieved_source_types"],
        "final_next_action": row["final_next_action"],
        "safe_refusal": row["safe_refusal"],
        "diagnostic_reasons": row["diagnostic_reasons"],
    }


def build_diagnostics(
    results: list[dict[str, Any]],
    *,
    stop_threshold: float,
    confirm_threshold: float,
) -> dict[str, Any]:
    band_counts = {"stop": 0, "confirm": 0, "proceed": 0}
    next_action_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    eval_source_counts: Counter[str] = Counter()
    low_retrieval_by_source: Counter[str] = Counter()
    retrieved_source_counts: Counter[str] = Counter()
    low_retrieval_scenarios = []
    teachable_failures = []

    for row in results:
        band = evidence_band(
            float(row["top_score"]),
            stop_threshold=stop_threshold,
            confirm_threshold=confirm_threshold,
        )
        band_counts[band] += 1
        next_action_counts[str(row["final_next_action"] or "unknown")] += 1
        eval_source_counts[str(row["source_file"])] += 1
        if band == "stop":
            low_retrieval_by_source[str(row["source_file"])] += 1
            low_retrieval_scenarios.append(diagnostic_scenario(row))
        if row["teachable"] and not row["passed"]:
            teachable_failures.append(diagnostic_scenario(row))
        reason_counts.update(row["diagnostic_reasons"])
        retrieved_source_counts.update(row["retrieved_source_types"])

    return {
        "score_band_counts": band_counts,
        "next_action_counts": dict(sorted(next_action_counts.items())),
        "diagnostic_reason_counts": dict(sorted(reason_counts.items())),
        "eval_source_file_counts": dict(sorted(eval_source_counts.items())),
        "low_retrieval_by_eval_source_file": dict(
            sorted(low_retrieval_by_source.items())
        ),
        "retrieved_source_type_counts": dict(sorted(retrieved_source_counts.items())),
        "retrieval_coverage": {
            "scenarios_with_spans": sum(1 for row in results if row["retrieved_count"]),
            "scenarios_without_spans": sum(
                1 for row in results if not row["retrieved_count"]
            ),
        },
        "low_retrieval_scenarios": low_retrieval_scenarios,
        "teachable_failures": teachable_failures,
    }


def score_scenario(
    *,
    settings: CoachSettings,
    foundation: Foundation,
    scenario: dict[str, str],
    session_factory: Any = CoachSession,
    wrong_answer: str = DEFAULT_WRONG_ANSWER,
) -> dict[str, Any]:
    session_id = scenario_session_id(scenario)
    reset_scenario_trace(settings, session_id)
    session = session_factory(
        session_id=session_id,
        topic=scenario["question_text"],
        settings=settings,
        foundation=foundation,
        profile=LearnerProfile(style="analogy", track_lens="code_heavy"),
    )
    first = session.start()
    first_strategy = first.response.strategy
    second = session.respond(wrong_answer)
    expected_answer = (
        session.runtime.current_check.expected_answer
        if session.runtime.current_check is not None
        else ""
    )
    final = session.respond(expected_answer) if expected_answer else second
    retrieved_ids = {span.citation_id for span in session.runtime.last_spans}
    retrieved_source_types = count_source_types(session.runtime.last_spans)
    citation_ids = final.response.citation_ids
    top_score = evidence_score(session.runtime.last_spans)
    final_next_action = final.response.next_action
    citations_resolve = bool(citation_ids) and set(citation_ids).issubset(retrieved_ids)
    re_explained_differently = (
        second.response.next_action == "re_explain_differently"
        and second.response.strategy != first_strategy
    )
    grade_correct = bool(session.runtime.last_grade and session.runtime.last_grade.correct)
    trace_has_decision = _trace_has_runtime_decision(Path(final.trace_path))
    teachable = top_score >= settings.stop_threshold
    safe_refusal = not teachable and final_next_action == "refuse_escalate"
    passed = citations_resolve and re_explained_differently and grade_correct and trace_has_decision
    row = {
        "scenario_id": scenario["scenario_id"],
        "item_id": scenario["item_id"],
        "source_file": scenario["source_file"],
        "split": scenario["split"],
        "passed": passed,
        "citations_resolve": citations_resolve,
        "re_explained_differently": re_explained_differently,
        "grade_correct": grade_correct,
        "trace_has_runtime_decision": trace_has_decision,
        "teachable": teachable,
        "safe_refusal": safe_refusal,
        "top_score": top_score,
        "retrieved_count": len(session.runtime.last_spans),
        "retrieved_source_types": retrieved_source_types,
        "citation_ids": citation_ids,
        "final_next_action": final_next_action,
    }
    row["diagnostic_reasons"] = diagnostic_reasons(row)
    return row


def main() -> None:
    load_local_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="dev", choices=["seed", "dev", "test"])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    settings = CoachSettings.from_env()
    scenarios = load_scenarios(settings, split=args.split, limit=args.limit)
    foundation = Foundation.build(settings)
    results = [
        score_scenario(settings=settings, foundation=foundation, scenario=scenario)
        for scenario in scenarios
    ]
    passed = sum(1 for row in results if row["passed"])
    teachable = [row for row in results if row["teachable"]]
    teachable_passed = sum(1 for row in teachable if row["passed"])
    safe_refusals = sum(1 for row in results if row["safe_refusal"])
    payload = {
        "split": args.split,
        "n": len(results),
        "passed": passed,
        "pass_rate": passed / len(results) if results else 0.0,
        "teachable_n": len(teachable),
        "teachable_passed": teachable_passed,
        "teachable_pass_rate": teachable_passed / len(teachable) if teachable else 0.0,
        "safe_refusals": safe_refusals,
        "diagnostics": build_diagnostics(
            results,
            stop_threshold=settings.stop_threshold,
            confirm_threshold=settings.confirm_threshold,
        ),
        "results": results,
    }
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
