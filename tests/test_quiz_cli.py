import importlib.util
from pathlib import Path

import pytest


def load_script():
    script_path = Path("scripts/run_quiz_demo.py").resolve()
    spec = importlib.util.spec_from_file_location("run_quiz_demo", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_answers_normalizes_comma_separated_ids():
    module = load_script()

    assert module.parse_answers("a, B,c ") == ["A", "B", "C"]
    assert module.parse_answers(None) is None


def test_validate_answer_count_reports_mismatch():
    module = load_script()

    with pytest.raises(ValueError, match="expected 3 answers, received 2"):
        module.validate_answer_count(["A", "B"], 3)


def test_validate_answers_reports_unknown_option_id():
    module = load_script()

    with pytest.raises(ValueError, match="answers must use option IDs A, B, C, or D"):
        module.validate_answers(["A", "Z"], 2)
