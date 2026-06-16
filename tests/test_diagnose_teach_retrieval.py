import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def load_script():
    script_path = Path("scripts/diagnose_teach_retrieval.py").resolve()
    spec = importlib.util.spec_from_file_location("diagnose_teach_retrieval", script_path)
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
            doc_id=f"{source_type}/doc",
            text="retrieved text",
            citation=SimpleNamespace(
                title=f"{source_type}.md",
                source_type=source_type,
                page_or_section=None,
            ),
        ),
    )


class FakeRetriever:
    def retrieve(self, query):
        assert query == "private question text"
        return [
            hit(0.72, "transcript", "transcript/doc::0"),
            hit(0.51, "handout", "handout/doc::0"),
        ]


class FakeFoundation:
    def __init__(self):
        self.calls = 0
        self._retriever = FakeRetriever()

    def retriever(self):
        self.calls += 1
        return self._retriever


def test_scenario_retrieval_diagnostic_is_redacted():
    module = load_script()

    row = module.scenario_retrieval_diagnostic(
        settings=SimpleNamespace(
            stop_threshold=0.60,
            confirm_threshold=0.85,
            retrieval_top_k=2,
            source_priority=("handout", "transcript"),
        ),
        retriever=FakeRetriever(),
        scenario={
            "scenario_id": "item-a:000",
            "item_id": "item-a",
            "source_file": "week1-chat.docx",
            "split": "dev",
            "question_text": "private question text",
        },
    )

    assert row == {
        "scenario_id": "item-a:000",
        "item_id": "item-a",
        "source_file": "week1-chat.docx",
        "split": "dev",
        "question_word_count": 3,
        "raw_count": 2,
        "raw_top_score": 0.72,
        "raw_band": "confirm",
        "raw_source_types": {"handout": 1, "transcript": 1},
        "priority_top_score": 0.51,
        "priority_top_source_type": "handout",
        "source_priority_would_drop_top_score": True,
        "raw_minus_priority_top_score": 0.21,
        "selected_count": 2,
        "selected_top_score": 0.72,
        "selected_band": "confirm",
        "selected_source_types": {"handout": 1, "transcript": 1},
    }
    assert "question_text" not in row
    assert "private question text" not in json.dumps(row)
    assert "retrieved text" not in json.dumps(row)


def test_build_payload_summarizes_scores_without_question_text(monkeypatch):
    module = load_script()

    monkeypatch.setattr(
        module,
        "load_scenarios",
        lambda settings, split, limit: [
            {
                "scenario_id": "item-a:000",
                "item_id": "item-a",
                "source_file": "week1-chat.docx",
                "split": split,
                "question_text": "private question text",
            }
        ],
    )

    foundation = FakeFoundation()
    payload = module.build_payload(
        settings=SimpleNamespace(
            course_collection="coach_course",
            stop_threshold=0.60,
            confirm_threshold=0.85,
            retrieval_top_k=5,
            retrieval_candidate_k=20,
            source_priority=("handout", "transcript"),
        ),
        foundation=foundation,
        split="dev",
        limit=1,
    )

    assert foundation.calls == 1
    assert payload["raw_score_summary"]["gte_060"] == 1
    assert payload["selected_source_type_counts"] == {"handout": 1, "transcript": 1}
    assert "question_text" not in json.dumps(payload)
    assert "private question text" not in json.dumps(payload)
    assert "retrieved text" not in json.dumps(payload)


def test_summarize_scores_inclusive_boundaries_and_empty_list():
    module = load_script()

    assert module.summarize_scores([]) == {
        "n": 0,
        "min": 0.0,
        "p50_nearest_rank": 0.0,
        "max": 0.0,
        "gte_040": 0,
        "gte_050": 0,
        "gte_055": 0,
        "gte_060": 0,
    }
    assert module.summarize_scores([0.39, 0.40, 0.50, 0.55, 0.60]) == {
        "n": 5,
        "min": 0.39,
        "p50_nearest_rank": 0.5,
        "max": 0.6,
        "gte_040": 4,
        "gte_050": 3,
        "gte_055": 2,
        "gte_060": 1,
    }
    assert module.summarize_scores([0.10, 0.20, 0.30, 0.40])[
        "p50_nearest_rank"
    ] == 0.20


def test_source_counts_normalizes_missing_source_type():
    module = load_script()

    assert module.source_counts(["handout", "", None]) == {
        "handout": 1,
        "unknown": 2,
    }


def test_main_rejects_held_out_test_split(monkeypatch):
    module = load_script()
    monkeypatch.setattr(
        sys,
        "argv",
        ["diagnose_teach_retrieval.py", "--split", "test"],
    )

    with pytest.raises(SystemExit):
        module.main()
