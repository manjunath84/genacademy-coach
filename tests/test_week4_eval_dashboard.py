import importlib.util
from pathlib import Path

import pytest


def load_dashboard_module():
    script_path = Path("scripts/build_week4_eval_dashboard.py").resolve()
    spec = importlib.util.spec_from_file_location("build_week4_eval_dashboard", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def minimal_snapshot():
    return {
        "schema_version": 1,
        "title": "Week-4 Eval Dashboard",
        "provenance": {
            "snapshot_date": "2026-06-25",
            "generator_git_sha": "test-sha",
            "baseline_artifact": "golden-baseline-20260624.json",
            "current_run_ids": [
                "current-main-full-langsmith-r1",
                "current-main-full-langsmith-r2",
                "current-main-full-langsmith-r3",
            ],
            "dataset_version": "2026-06-24-plan1",
            "dataset_version_note": (
                "40-case golden; 16 happy / 9 edge / 5 known_failure / 10 adversarial"
            ),
            "model_id": "Qwen/Qwen3-30B-A3B-Instruct-2507",
            "thresholds": {"stop": 0.40, "confirm_upper": 0.85},
            "source_handoff_doc": "docs/week4-eval-progress-handoff.md",
            "privacy_reviewed": True,
            "redaction_policy": (
                "Committed dashboard data contains only aggregate metrics and synthetic case IDs."
            ),
        },
        "hero": {
            "verdict": (
                "Citation F1 +0.150 and turn p95 -27%; refusal precision and task "
                "completion regressed slightly."
            ),
            "primary_question": "Did Week-4 improvements help without breaking refusal safety?",
        },
        "class_balance": {"happy": 16, "edge": 9, "known_failure": 5, "adversarial": 10},
        "evaluator_types": [
            {
                "label": "Code-based checks",
                "summary": (
                    "Deterministic checks for task completion, citations, tools, retrieval, "
                    "refusal, latency, tokens, cost, and privacy guards."
                ),
            },
            {
                "label": "Trajectory eval",
                "summary": (
                    "Path-level scoring over retrieval, tools, action, citations, "
                    "advance/re-explain/refuse behavior, and trace evidence."
                ),
            },
            {
                "label": "Human review",
                "summary": (
                    "Reviewer inspection of report, dashboard, and sampled trace evidence."
                ),
            },
        ],
        "baseline": {"label": "baseline", "task_completion_rate": 0.947, "citation_f1": 0.444},
        "current_mean": {
            "label": "current mean",
            "task_completion_rate": 0.933,
            "citation_f1": 0.594,
        },
        "kpis": [
            {
                "id": "citation_f1",
                "label": "Citation F1",
                "baseline": "0.444",
                "current": "0.594",
                "delta": "+0.150",
                "status": "win",
                "note": "Below 0.90 plan pass bar.",
            }
        ],
        "metric_deltas": [
            {
                "metric": "Citation F1",
                "baseline": "0.444",
                "current": "0.594",
                "delta": "+0.150",
                "status": "win",
                "note": "Below 0.90 plan pass bar.",
            }
        ],
        "runs": [
            {
                "run_id": "r1",
                "citation_f1": 0.539,
                "refusal_precision": 0.769,
                "turn_p95_ms": 8102,
                "task_completion_rate": 0.925,
            },
            {
                "run_id": "r2",
                "citation_f1": 0.667,
                "refusal_precision": 0.833,
                "turn_p95_ms": 8356,
                "task_completion_rate": 0.950,
            },
            {
                "run_id": "r3",
                "citation_f1": 0.578,
                "refusal_precision": 0.769,
                "turn_p95_ms": 8368,
                "task_completion_rate": 0.925,
            },
        ],
        "tool_latency": [
            {"tool": "generate_check_item", "total_ms_per_run": 49793, "share": 0.66},
            {"tool": "retrieve_course_corpus", "total_ms_per_run": 27046, "share": 0.34},
        ],
        "improvement_levers": [
            {
                "lever": "Tool design + prompt engineering",
                "change": "Preferred check-span selection.",
                "cluster": "Citation mismatch (dominant cluster)",
                "predicted_impact": "Hold or improve citation F1 above the 0.50 floor",
                "measured": "Citation F1 0.444 -> 0.594 (+0.150).",
                "status": "win",
            },
            {
                "lever": "Guardrail / anchoring attempt (rejected)",
                "change": "Broad citation fallback to anchor final answers.",
                "cluster": "Citation mismatch",
                "predicted_impact": "citation F1 +0.10 to +0.20",
                "measured": "-0.044 (0.444 -> 0.400); not shipped.",
                "status": "risk",
            },
        ],
        "production_monitoring": [
            {
                "signal": "Quality drift",
                "metric": "Citation F1 & task-completion (7-day rolling)",
                "threshold": "Alert if either drops > 10% vs trailing baseline",
                "rationale": "Catches retrieval/citation regressions before learners feel them.",
            },
            {
                "signal": "Cost spike",
                "metric": "p95 tokens & cost per turn (24h)",
                "threshold": "Alert if > 25% over budget",
                "rationale": "Usually signals a tool-loop or retrieval blow-up.",
            },
            {
                "signal": "Latency regression",
                "metric": "Turn p95 latency",
                "threshold": "Alert if > 10s SLA on > 5% of runs",
                "rationale": "Protects the interactive teach loop.",
            },
            {
                "signal": "Guardrail trips",
                "metric": "Refusal + escalation rate",
                "threshold": "Alert if > 2x trailing baseline",
                "rationale": (
                    "Over-conservative refusal is our dominant failure mode — watch it live."
                ),
            },
            {
                "signal": "Tool failure",
                "metric": "Per-tool error rate: retrieve / generate_check / grade (1h)",
                "threshold": "Alert if any single tool > 5%",
                "rationale": (
                    "Flags external-dependency outage or structured-output regression."
                ),
            },
        ],
        "per_scenario": [
            {
                "scenario_type": "happy",
                "support": 16,
                "task_pass": "93.8%",
                "citation_f1": "0.576",
                "false_refusals": "happy_014 (3/3)",
                "status": "caveat",
            },
            {
                "scenario_type": "adversarial",
                "support": 10,
                "task_pass": "100.0%",
                "citation_f1": "n/a (refusal)",
                "false_refusals": "none",
                "status": "win",
            },
        ],
        "failure_distribution": [
            {
                "category": "Citation-span mismatch",
                "case_runs": 31,
                "distinct_cases": 18,
                "kind": "Citation quality",
                "status": "caveat",
            },
            {
                "category": "Over-conservative refusal",
                "case_runs": 8,
                "distinct_cases": 3,
                "kind": "Task failure",
                "status": "risk",
            },
        ],
        "open_axial": [
            {
                "case": "known_failure_001",
                "open_code": "Below STOP threshold.",
                "axial_code": "Over-conservative refusal",
            },
        ],
        "guardrails": [
            {
                "label": "Refusal recall",
                "value": "1.000",
                "status": "held",
                "note": "Safety held.",
            },
            {
                "label": "Retrieval recall@5",
                "value": "1.000",
                "status": "held",
                "note": "Retrieval held.",
            },
        ],
        "remaining_failures": [
            {
                "case_id": "happy_014",
                "summary": "Stable false refusal",
                "status": "open",
                "status_label": "open",
            }
        ],
        "perspectives": {
            "user": "The tutor is faster and cites better.",
            "builder": "Retrieval is healthy; remaining work is post-retrieval behavior.",
        },
        "notes": [
            "Cost delta vs baseline is not meaningful because baseline pricing env vars were unset."
        ],
    }


def test_validate_public_snapshot_accepts_clean_data():
    module = load_dashboard_module()
    module.validate_public_snapshot(minimal_snapshot())


@pytest.mark.parametrize(
    "bad_key",
    ["user_query", "answer_text", "trace_id", "retrieved_span_text", "langsmith_url"],
)
def test_validate_public_snapshot_rejects_forbidden_exact_keys(bad_key):
    module = load_dashboard_module()
    data = minimal_snapshot()
    data[bad_key] = "private"
    with pytest.raises(ValueError, match=bad_key):
        module.validate_public_snapshot(data)


def test_validate_public_snapshot_rejects_forbidden_key_pattern():
    module = load_dashboard_module()
    data = minimal_snapshot()
    data["nested"] = {"learner_text": "private"}
    with pytest.raises(ValueError, match="learner_text"):
        module.validate_public_snapshot(data)


def test_validate_public_snapshot_rejects_langsmith_url_values():
    module = load_dashboard_module()
    data = minimal_snapshot()
    data["notes"].append("https://smith.langchain.com/o/private")
    with pytest.raises(ValueError, match="smith.langchain.com"):
        module.validate_public_snapshot(data)


def test_render_dashboard_includes_honest_verdict_and_footer():
    module = load_dashboard_module()
    html = module.render_dashboard(minimal_snapshot())
    assert "Citation F1 +0.150" in html
    assert "refusal precision" in html
    assert "snapshot_date" in html
    assert "2026-06-24-plan1" in html
    assert "docs/week4-eval-progress-handoff.md" in html
    assert "langsmith.com" not in html
    assert "user_query" not in html
    assert "answer_text" not in html
    assert "trace_id" not in html


def test_render_dashboard_includes_evaluator_types():
    module = load_dashboard_module()
    html = module.render_dashboard(minimal_snapshot())
    assert "Evaluator Types" in html
    assert "Code-based checks" in html
    assert "Trajectory eval" in html
    assert "Human review" in html
    assert "future offline audit" in html


def test_render_dashboard_moves_scenario_breakdown_near_top():
    module = load_dashboard_module()
    html = module.render_dashboard(minimal_snapshot())
    assert html.index("Evaluator Types") < html.index("Per-Scenario Breakdown")
    assert html.index("Per-Scenario Breakdown") < html.index("Baseline vs Current Mean")


def test_render_dashboard_includes_improvement_levers():
    module = load_dashboard_module()
    html = module.render_dashboard(minimal_snapshot())
    assert "Improvement Levers" in html
    assert "Tool design + prompt engineering" in html
    assert "Predicted" in html
    assert "Levers deliberately not pulled" in html
    assert "retrieval recall@5 was already 1.000" in html


def test_render_dashboard_includes_failure_analysis():
    module = load_dashboard_module()
    html = module.render_dashboard(minimal_snapshot())
    assert "Per-Scenario Breakdown" in html
    assert "Failure And Quality-Issue Distribution" in html
    assert "Open-Code To Axial-Code" in html
    assert "Over-conservative refusal" in html


def test_render_dashboard_includes_production_monitoring():
    module = load_dashboard_module()
    html = module.render_dashboard(minimal_snapshot())
    assert "Production Monitoring" in html
    assert "Over-conservative refusal" in html


def test_improvement_levers_keys_pass_public_snapshot_validation():
    module = load_dashboard_module()
    # The lever section must not trip the forbidden-key privacy guard.
    module.validate_public_snapshot(minimal_snapshot())


def test_write_private_appendix_noops_without_localdocs(tmp_path):
    module = load_dashboard_module()
    written = module.write_private_appendix(minimal_snapshot(), repo_root=tmp_path)
    assert written is None
