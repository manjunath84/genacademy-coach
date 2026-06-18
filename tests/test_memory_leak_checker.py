import importlib.util
import json
from pathlib import Path

import pytest

from genacademy_coach.eval_split import phrase_hashes


def load_script():
    path = Path("scripts/check_memory_leak.py").resolve()
    spec = importlib.util.spec_from_file_location("check_memory_leak", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"topic": "PRIVATE RAW TOPIC"}, "forbidden memory key topic"),
        ({"answer": "PRIVATE LEARNER ANSWER"}, "forbidden memory key answer"),
    ],
)
def test_memory_leak_checker_fails_on_raw_topic_or_answer(tmp_path, payload, expected):
    module = load_script()
    path = write_jsonl(tmp_path / "memory-bad.jsonl", payload)

    offenders = module.scan_memory_artifacts([path])

    assert expected in offenders[0]


@pytest.mark.parametrize("source_name", ["corpus.md", "eval.md"])
def test_memory_leak_checker_fails_on_private_text_overlap(tmp_path, source_name):
    module = load_script()
    private_text = "alpha beta gamma delta epsilon zeta eta theta iota"
    private_phrases = phrase_hashes([(source_name, private_text)])
    path = write_jsonl(
        tmp_path / "memory-bad.jsonl",
        {"safe_payload": "alpha beta gamma delta epsilon zeta eta theta"},
    )

    offenders = module.scan_memory_artifacts([path], private_phrases=private_phrases)

    assert offenders
    assert "matched private phrase" in offenders[0]
    assert source_name in offenders[0]


def test_memory_leak_checker_passes_safe_memory_trace(tmp_path):
    module = load_script()
    path = write_jsonl(
        tmp_path / "memory-safe.jsonl",
        {
            "session_id": "s1",
            "user_id_hash": "userhash",
            "topic_hash": "abc123def456",
            "event": "write",
            "provider": "fake",
            "wrote_count": 1,
        },
    )

    assert module.scan_memory_artifacts([path]) == []
