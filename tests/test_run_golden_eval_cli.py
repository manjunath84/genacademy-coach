import importlib.util
from pathlib import Path


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
