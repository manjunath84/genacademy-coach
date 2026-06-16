import importlib.util
from pathlib import Path


def load_script(path: str):
    spec = importlib.util.spec_from_file_location(Path(path).stem, Path(path).resolve())
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_print_trace_formats_jsonl(tmp_path, capsys):
    path = tmp_path / "abc.jsonl"
    path.write_text(
        '{"turn": 1, "next_action": "drill", "strategy": "analogy", '
        '"evidence_score": 0.91, "evidence_band": "proceed", '
        '"retrieved_citation_ids": ["note/a::0"], '
        '"learner_message": "hello"}\n',
        encoding="utf-8",
    )
    module = load_script("scripts/print_trace.py")

    module.print_trace(path)

    out = capsys.readouterr().out
    assert "turn 1" in out
    assert "drill" in out
    assert "evidence=0.91 proceed" in out
    assert "note/a::0" in out
