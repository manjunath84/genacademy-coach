import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def load_script():
    script_path = Path("scripts/calibrate_teach_threshold.py").resolve()
    spec = importlib.util.spec_from_file_location("calibrate_teach_threshold", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hit(score, source_type, chunk_id):
    return SimpleNamespace(
        score=score,
        chunk=SimpleNamespace(
            chunk_id=chunk_id,
            text="retrieved text",
            citation=SimpleNamespace(source_type=source_type),
        ),
    )


class FakeRetriever:
    def retrieve(self, query):
        scores = {
            "private seed question": 0.55,
            "private dev question": 0.41,
            "public unrelated control": 0.39,
        }
        return [hit(scores[query], "transcript", f"{query}::0")]


class FakeFoundation:
    def __init__(self):
        self.calls = 0
        self._retriever = FakeRetriever()

    def retriever(self):
        self.calls += 1
        return self._retriever


def test_build_payload_recommends_lowest_threshold_that_blocks_controls(
    tmp_path,
    monkeypatch,
):
    module = load_script()
    controls_path = tmp_path / "negative-controls.json"
    controls_path.write_text(
        json.dumps(
            [
                {
                    "id": "neg_public_001",
                    "category": "public",
                    "query": "public unrelated control",
                }
            ]
        ),
        encoding="utf-8",
    )

    def fake_scenarios(settings, *, split, limit):
        query = "private seed question" if split == "seed" else "private dev question"
        return [
            {
                "scenario_id": f"{split}:000",
                "item_id": split,
                "source_file": f"{split}.docx",
                "split": split,
                "question_text": query,
            }
        ]

    monkeypatch.setattr(module, "load_scenarios", fake_scenarios)
    foundation = FakeFoundation()
    payload = module.build_payload(
        settings=SimpleNamespace(
            course_collection="coach_course",
            stop_threshold=0.60,
            confirm_threshold=0.85,
            retrieval_top_k=5,
            retrieval_candidate_k=20,
        ),
        foundation=foundation,
        seed_limit=1,
        dev_limit=1,
        negative_controls_path=controls_path,
        thresholds=(0.39, 0.40, 0.41),
    )

    serialized = json.dumps(payload)
    assert foundation.calls == 1
    assert payload["recommended_stop_threshold"] == 0.40
    assert payload["threshold_candidates"] == [
        {
            "threshold": 0.39,
            "positive_at_or_above": 2,
            "positive_total": 2,
            "seed_at_or_above": 1,
            "seed_total": 1,
            "dev_at_or_above": 1,
            "dev_total": 1,
            "negative_controls_at_or_above": 1,
            "negative_controls_total": 1,
            "all_negative_controls_stop": False,
        },
        {
            "threshold": 0.40,
            "positive_at_or_above": 2,
            "positive_total": 2,
            "seed_at_or_above": 1,
            "seed_total": 1,
            "dev_at_or_above": 1,
            "dev_total": 1,
            "negative_controls_at_or_above": 0,
            "negative_controls_total": 1,
            "all_negative_controls_stop": True,
        },
        {
            "threshold": 0.41,
            "positive_at_or_above": 2,
            "positive_total": 2,
            "seed_at_or_above": 1,
            "seed_total": 1,
            "dev_at_or_above": 1,
            "dev_total": 1,
            "negative_controls_at_or_above": 0,
            "negative_controls_total": 1,
            "all_negative_controls_stop": True,
        },
    ]
    assert "private seed question" not in serialized
    assert "private dev question" not in serialized
    assert "public unrelated control" not in serialized
    assert "retrieved text" not in serialized


def test_parse_thresholds_sorts_deduplicates_and_rejects_empty():
    module = load_script()

    assert module.parse_thresholds("0.42,0.40,0.42") == (0.4, 0.42)
    with pytest.raises(ValueError):
        module.parse_thresholds(" , ")


def test_load_negative_controls_validates_required_fields(tmp_path):
    module = load_script()
    path = tmp_path / "negative-controls.json"

    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty JSON list"):
        module.load_negative_controls(path)

    path.write_text(json.dumps([{"id": "missing-query", "category": "public"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="id, category, and query"):
        module.load_negative_controls(path)
