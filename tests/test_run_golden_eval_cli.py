import importlib.util
from pathlib import Path
from types import SimpleNamespace


def load_cli_module():
    script_path = Path("scripts/run_golden_eval.py").resolve()
    spec = importlib.util.spec_from_file_location("run_golden_eval", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_warns_when_price_env_vars_are_unset(monkeypatch, capsys):
    monkeypatch.delenv("GENACADEMY_NEBIUS_INPUT_USD_PER_1M", raising=False)
    monkeypatch.delenv("GENACADEMY_NEBIUS_OUTPUT_USD_PER_1M", raising=False)
    module = load_cli_module()

    price_table = module.price_table_for_model("m")
    module.warn_if_zero_prices(price_table)

    assert "cost_usd will be 0" in capsys.readouterr().err


def test_select_cases_filters_cloud_safe_before_limit(capsys):
    module = load_cli_module()
    cases = [
        SimpleNamespace(case_id="private_001", split="seed", cloud_safe=False),
        SimpleNamespace(case_id="safe_001", split="negative_control", cloud_safe=True),
        SimpleNamespace(case_id="safe_002", split="negative_control", cloud_safe=True),
    ]

    selected = module.select_cases(cases, cloud_safe_only=True, limit=1)

    assert [case.case_id for case in selected] == ["safe_001"]
    err = capsys.readouterr().err
    assert "cloud-safe golden eval enabled" in err
    assert "cases=2" in err


def test_select_cases_rejects_zero_cloud_safe():
    module = load_cli_module()
    cases = [SimpleNamespace(case_id="private_001", split="seed", cloud_safe=False)]

    try:
        module.select_cases(cases, cloud_safe_only=True)
    except SystemExit as exc:
        assert "--cloud-safe-only selected 0 golden cases" in str(exc)
    else:
        raise AssertionError("cloud-safe filtering must reject empty selections")


def test_select_cases_rejects_empty_after_limit():
    module = load_cli_module()
    cases = [SimpleNamespace(case_id="safe_001", split="negative_control", cloud_safe=True)]

    try:
        module.select_cases(cases, cloud_safe_only=True, limit=0)
    except SystemExit as exc:
        assert "selected 0 golden cases" in str(exc)
    else:
        raise AssertionError("empty golden selections must be rejected")


def test_langsmith_preflight_is_noop_when_tracing_disabled(monkeypatch):
    module = load_cli_module()
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)

    module.validate_langsmith_eval_egress(
        [SimpleNamespace(case_id="c", split="seed", cloud_safe=False)]
    )


def test_langsmith_preflight_requires_approved_project(monkeypatch):
    module = load_cli_module()
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_PROJECT", "wrong")
    monkeypatch.setenv("GENACADEMY_LANGSMITH_EVAL_EGRESS_OK", "true")

    try:
        module.validate_langsmith_eval_egress(
            [SimpleNamespace(case_id="c", split="seed", cloud_safe=False)]
        )
    except SystemExit as exc:
        assert "genacademy-coach-week4-eval" in str(exc)
    else:
        raise AssertionError("tracing must require the approved private project")


def test_langsmith_preflight_requires_explicit_egress_ack(monkeypatch):
    module = load_cli_module()
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_PROJECT", "genacademy-coach-week4-eval")
    monkeypatch.delenv("GENACADEMY_LANGSMITH_EVAL_EGRESS_OK", raising=False)

    try:
        module.validate_langsmith_eval_egress(
            [SimpleNamespace(case_id="c", split="seed", cloud_safe=False)]
        )
    except SystemExit as exc:
        assert "GENACADEMY_LANGSMITH_EVAL_EGRESS_OK" in str(exc)
    else:
        raise AssertionError("tracing must require explicit egress acknowledgement")


def test_langsmith_preflight_rejects_test_cases(monkeypatch):
    module = load_cli_module()
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_PROJECT", "genacademy-coach-week4-eval")
    monkeypatch.setenv("GENACADEMY_LANGSMITH_EVAL_EGRESS_OK", "true")

    try:
        module.validate_langsmith_eval_egress(
            [SimpleNamespace(case_id="test_001", split="test", cloud_safe=False)]
        )
    except SystemExit as exc:
        assert "frozen test cases" in str(exc)
    else:
        raise AssertionError("tracing must reject frozen test cases")


def test_langsmith_preflight_prints_approved_summary(monkeypatch, capsys):
    module = load_cli_module()
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_PROJECT", "genacademy-coach-week4-eval")
    monkeypatch.setenv("GENACADEMY_LANGSMITH_EVAL_EGRESS_OK", "true")

    module.validate_langsmith_eval_egress(
        [
            SimpleNamespace(case_id="seed_001", split="seed", cloud_safe=False),
            SimpleNamespace(case_id="control_001", split="negative_control", cloud_safe=True),
        ]
    )

    err = capsys.readouterr().err
    assert "LangSmith eval tracing enabled" in err
    assert "cases=2" in err
    assert "cloud_safe=1" in err
