import importlib.util
import json
from pathlib import Path


def load_leak_module():
    script_path = Path("scripts/check_eval_leak.py").resolve()
    spec = importlib.util.spec_from_file_location("check_eval_leak", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(tmp_path, rows):
    p = tmp_path / "golden_cases.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return p


def test_rejects_test_split(tmp_path):
    p = _write(
        tmp_path,
        [{"case_id": "x", "split": "test", "cloud_safe": True, "cloud_safe_reason": "r"}],
    )
    module = load_leak_module()
    assert any(
        "test split" in o
        for o in module.scan_golden_cases(p, test_needles=set(), test_phrases={})
    )


def test_flags_test_needle_in_inline_text(tmp_path):
    p = _write(
        tmp_path,
        [
            {
                "case_id": "x",
                "split": "seed",
                "cloud_safe": True,
                "cloud_safe_reason": "r",
                "user_query": "has SECRET_ID",
            }
        ],
    )
    module = load_leak_module()
    assert any(
        "SECRET_ID" in o
        for o in module.scan_golden_cases(p, test_needles={"SECRET_ID"}, test_phrases={})
    )


def test_flags_non_cloud_safe_inline_text(tmp_path):
    p = _write(
        tmp_path,
        [
            {
                "case_id": "x",
                "split": "seed",
                "cloud_safe": False,
                "source_ref": "scenario:i:000",
                "user_query": "private learner wording",
            }
        ],
    )
    module = load_leak_module()

    assert any(
        "cloud_safe=false carries inline text" in o
        for o in module.scan_golden_cases(p, test_needles=set(), test_phrases={})
    )


def test_flags_test_phrase_in_inline_text(tmp_path):
    phrase = "alpha beta gamma delta epsilon zeta eta theta"
    p = _write(
        tmp_path,
        [
            {
                "case_id": "x",
                "split": "synthetic",
                "cloud_safe": True,
                "cloud_safe_reason": "synthetic",
                "user_query": f"Please explain {phrase}.",
            }
        ],
    )
    module = load_leak_module()

    offenders = module.scan_golden_cases(
        p,
        test_needles=set(),
        test_phrases={
            phrase: [{"source_file": "private.txt", "phrase_hash": "abc123"}],
        },
    )

    assert any("matched eval phrase private.txt:abc123" in o for o in offenders)


def test_empty_eval_text_is_reported_as_unscanned(tmp_path, monkeypatch):
    module = load_leak_module()
    eval_path = tmp_path / "private.pdf"
    eval_path.write_bytes(b"%PDF-empty")
    monkeypatch.setattr(module, "read_eval_text", lambda path: "")

    sources, unscanned = module.collect_eval_phrase_sources(
        tmp_path,
        [{"source_file": "private.pdf"}],
    )

    assert sources == []
    assert unscanned == ["private.pdf (no extractable text)"]


def test_clean_golden_passes(tmp_path):
    p = _write(
        tmp_path,
        [
            {
                "case_id": "x",
                "split": "seed",
                "cloud_safe": True,
                "cloud_safe_reason": "r",
                "user_query": "what is a token",
            }
        ],
    )
    module = load_leak_module()
    assert module.scan_golden_cases(p, test_needles={"SECRET_ID"}, test_phrases={}) == []
