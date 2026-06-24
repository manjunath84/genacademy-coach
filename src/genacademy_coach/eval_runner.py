from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from genacademy_coach.eval_golden import GoldenCase
from genacademy_coach.eval_metrics import (
    PriceTable,
    aggregate,
    citation_prf,
    recall_at_k,
    refusal_outcome,
    tool_match,
)
from genacademy_coach.eval_scenarios import load_scenarios
from genacademy_coach.teach_agent import DEFAULT_NEBIUS_MODEL
from genacademy_coach.teach_session import CoachSession
from genacademy_coach.teach_types import LearnerProfile
from genacademy_coach.trace import load_trace

DEFAULT_WRONG_ANSWER = "I am not sure; I think it just memorizes previous tokens."


def resolve_query(case: GoldenCase, scenario_index: dict[str, str]) -> str:
    if case.cloud_safe and case.user_query:
        return case.user_query
    source_ref = case.source_ref or ""
    if ":" not in source_ref:
        raise ValueError(
            f"{case.case_id}: cannot resolve query "
            "(no inline user_query and no parseable source_ref)"
        )
    scenario_id = source_ref.split(":", 1)[1]
    if scenario_id not in scenario_index:
        raise ValueError(
            f"{case.case_id}: source_ref scenario {scenario_id} not found in seed/dev scenarios"
        )
    return scenario_index[scenario_id]


def _model_id(foundation: Any) -> str:
    rag_settings = getattr(foundation, "rag_settings", None)
    return (getattr(rag_settings, "gen_model", None) if rag_settings is not None else None) or (
        DEFAULT_NEBIUS_MODEL
    )


def _reset_trace(settings: Any, session_id: str) -> None:
    trace_path = Path(settings.trace_dir) / f"{session_id}.jsonl"
    if trace_path.exists():
        trace_path.unlink()


def _trace_rows(trace_path: str | Path):
    path = Path(trace_path)
    return load_trace(path) if path.exists() else []


def _ranked_retrieval_ids(foundation: Any, query: str) -> list[str]:
    return [str(row.get("chunk_id", "")) for row in foundation.retrieve(query)]


def score_golden_case(
    *,
    settings: Any,
    foundation: Any,
    case: GoldenCase,
    scenario_index: dict[str, str],
    session_factory: Any = CoachSession,
) -> dict[str, Any]:
    query = resolve_query(case, scenario_index)
    session_id = f"golden-{case.case_id}"
    _reset_trace(settings, session_id)
    session = session_factory(
        session_id=session_id,
        topic=query,
        settings=settings,
        foundation=foundation,
        profile=LearnerProfile(style="analogy", track_lens="code_heavy"),
    )
    session.start()
    second = session.respond(case.initial_wrong_answer or DEFAULT_WRONG_ANSWER)
    if case.expected_answer:
        correct_answer = case.expected_answer
    elif session.runtime.current_check is not None:
        correct_answer = session.runtime.current_check.expected_answer
    else:
        correct_answer = " ".join(case.expected_check_keywords)
    final = session.respond(correct_answer) if correct_answer else second

    rows = _trace_rows(final.trace_path)
    actual_tools = [tool for row in rows for tool in row.tool_calls]
    turn_latencies_ms = [row.latency_ms for row in rows]
    input_tokens = sum(row.input_tokens for row in rows)
    output_tokens = sum(row.output_tokens for row in rows)
    total_tokens = sum(row.total_tokens for row in rows)
    final_trace = rows[-1] if rows else None

    predicted_citations = set(final.response.citation_ids)
    expected_citations = (
        {case.expected_citation_span_id} if case.expected_citation_span_id else set()
    )
    citation_precision, citation_recall, citation_f1 = citation_prf(
        predicted_citations,
        expected_citations,
    )
    tool_scores = tool_match(actual_tools, case.expected_tools)
    ranked_ids = _ranked_retrieval_ids(foundation, query)
    final_action = final.response.next_action
    refusal = refusal_outcome(
        refusal_expected=case.refusal_expected,
        actual_next_action=final_action,
    )
    grade_correct = bool(
        getattr(session.runtime, "last_grade", None)
        and session.runtime.last_grade.correct
    )
    task_completion_pass = (final_action == case.expected_next_action) and (
        case.refusal_expected or grade_correct
    )

    row: dict[str, Any] = {
        "case_id": case.case_id,
        "query_type": case.query_type,
        "concept": case.concept,
        "split": case.split,
        "cloud_safe": case.cloud_safe,
        "refusal_expected": case.refusal_expected,
        "expected_next_action": case.expected_next_action,
        "actual_next_action": final_action,
        "actual_strategy": final.response.strategy,
        "actual_tools": actual_tools,
        "expected_tools": case.expected_tools,
        "retrieved_citation_ids": list(final_trace.retrieved_citation_ids) if final_trace else [],
        "expected_citation_span_id": case.expected_citation_span_id,
        "evidence_score": final_trace.evidence_score if final_trace else 0.0,
        "evidence_band": final_trace.evidence_band if final_trace else "stop",
        "faithfulness_ok": final_trace.faithfulness_ok if final_trace else None,
        "turns_used": len(rows),
        "turn_latencies_ms": turn_latencies_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "model_id": _model_id(foundation),
        "task_completion_pass": task_completion_pass,
        "grade_correct": grade_correct,
        "citation_precision": citation_precision,
        "citation_recall": citation_recall,
        "citation_f1": citation_f1,
        "tool_precision": float(tool_scores["precision"]),
        "tool_recall": float(tool_scores["recall"]),
        "tool_f1": float(tool_scores["f1"]),
        "retrieval_recall_at_5": recall_at_k(
            ranked_ids,
            case.expected_citation_span_id,
            k=5,
        ),
        "refusal_outcome": refusal,
    }
    if case.cloud_safe:
        row["user_query"] = query
        row["answer_text"] = final.response.learner_message
    return row


def _scenario_index(settings: Any) -> dict[str, str]:
    scenarios = []
    for split in ("seed", "dev"):
        scenarios.extend(load_scenarios(settings, split=split, limit=9999))
    return {row["scenario_id"]: row["question_text"] for row in scenarios}


def run_golden_eval(
    *,
    settings: Any,
    foundation: Any,
    cases: list[GoldenCase],
    tag: str,
    price_table: PriceTable,
) -> dict[str, Any]:
    scenario_index = _scenario_index(settings)
    rows = [
        score_golden_case(
            settings=settings,
            foundation=foundation,
            case=case,
            scenario_index=scenario_index,
        )
        for case in cases
    ]
    metrics = aggregate(rows, price_table=price_table)
    output_path = Path(settings.eval_dir) / "runs" / f"golden-{tag}-{date.today():%Y%m%d}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created": datetime.now(UTC).isoformat(),
        "tag": tag,
        "n": len(rows),
        "metrics": metrics,
        "rows": rows,
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**payload, "output_path": str(output_path)}
