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
            {"tool": "generate_check_item", "mean_ms": 49793, "share": 0.66},
            {"tool": "retrieve_course_corpus", "mean_ms": 27046, "share": 0.34},
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
    assert "docs/week4-eval-progress-handoff.md" in html
    assert "langsmith.com" not in html
    assert "user_query" not in html
    assert "answer_text" not in html
    assert "trace_id" not in html


def test_write_private_appendix_noops_without_localdocs(tmp_path):
    module = load_dashboard_module()
    written = module.write_private_appendix(minimal_snapshot(), repo_root=tmp_path)
    assert written is None
