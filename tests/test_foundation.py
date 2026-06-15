from pathlib import Path

import pytest
from genacademy_rag.core.types import Document

from genacademy_coach.foundation import reorder_spans, select_retrieved_spans, source_priority_map
from genacademy_coach.settings import CoachSettings


def test_default_settings_use_course_collection_and_eval_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("GENACADEMY_COACH_ROOT", str(tmp_path))
    monkeypatch.delenv("GENACADEMY_COACH_DATA_DIR", raising=False)
    monkeypatch.delenv("GENACADEMY_DATA_DIR", raising=False)
    settings = CoachSettings.from_env()

    assert settings.course_collection == "coach_course"
    assert settings.eval_manifest_path.as_posix().endswith("eval/split_manifest.json")
    assert settings.review_queue_path.as_posix().endswith("review_queue.jsonl")
    assert settings.data_dir == tmp_path / "data"
    assert settings.chroma_dir == tmp_path / "data" / "chroma"
    assert settings.sqlite_path == tmp_path / "data" / "genacademy-coach.sqlite"
    assert settings.source_priority == ("slide", "handout", "note", "transcript")


def test_data_dir_can_be_overridden_without_using_week2_artifact_paths(tmp_path, monkeypatch):
    artifact_dir = tmp_path / "coach-artifacts"
    monkeypatch.setenv("GENACADEMY_COACH_ROOT", str(tmp_path))
    monkeypatch.setenv("GENACADEMY_COACH_DATA_DIR", str(artifact_dir))
    monkeypatch.setenv("GENACADEMY_DATA_DIR", str(tmp_path / "week2" / "data"))
    monkeypatch.setenv("GENACADEMY_CHROMA_DIR", str(tmp_path / "week2" / "chroma"))
    monkeypatch.setenv("GENACADEMY_SQLITE", str(tmp_path / "week2" / "genacademy.sqlite"))

    settings = CoachSettings.from_env()

    assert settings.data_dir == artifact_dir
    assert settings.chroma_dir == artifact_dir / "chroma"
    assert settings.sqlite_path == artifact_dir / "genacademy-coach.sqlite"


def test_source_priority_can_be_overridden_without_code_changes(monkeypatch):
    monkeypatch.setenv("GENACADEMY_COACH_SOURCE_PRIORITY", "handout,note,slide,transcript")
    settings = CoachSettings.from_env()

    assert settings.source_priority == ("handout", "note", "slide", "transcript")


def test_source_priority_rejects_typos(monkeypatch):
    monkeypatch.setenv("GENACADEMY_COACH_SOURCE_PRIORITY", "slides,handout")

    with pytest.raises(ValueError, match="unknown source_type"):
        CoachSettings.from_env()


def test_source_priority_rejects_duplicate_values(monkeypatch):
    monkeypatch.setenv("GENACADEMY_COACH_SOURCE_PRIORITY", "slide,slide,note")

    with pytest.raises(ValueError, match="duplicate source_type"):
        CoachSettings.from_env()


def test_source_priority_prefers_configured_sources_without_hiding_scores():
    spans = [
        {"source_type": "transcript", "score": 0.92, "chunk_id": "t"},
        {"source_type": "slide", "score": 0.81, "chunk_id": "s"},
        {"source_type": "handout", "score": 0.79, "chunk_id": "h"},
    ]

    priority = source_priority_map(("handout", "slide", "note", "transcript"))
    ordered = reorder_spans(spans, priority)

    assert [item["chunk_id"] for item in ordered] == ["h", "s", "t"]
    assert priority["handout"] < priority["transcript"]


def test_source_priority_keeps_unknown_sources_last():
    spans = [
        {"source_type": "worksheet", "score": 0.99, "chunk_id": "u"},
        {"source_type": "slide", "score": 0.25, "chunk_id": "s"},
    ]
    priority = source_priority_map(tuple(f"future-{idx}" for idx in range(10)) + ("slide",))

    ordered = reorder_spans(spans, priority)

    assert [item["chunk_id"] for item in ordered] == ["s", "u"]
    assert ordered[-1]["source_type"] == "worksheet"


def test_retrieval_selection_reserves_one_slot_for_highest_score():
    spans = [
        {"source_type": "slide", "score": 0.20, "chunk_id": "s"},
        {"source_type": "handout", "score": 0.30, "chunk_id": "h"},
        {"source_type": "transcript", "score": 0.99, "chunk_id": "t"},
    ]
    priority = source_priority_map(("slide", "handout", "note", "transcript"))

    selected = select_retrieved_spans(spans, priority, limit=2)

    assert [item["chunk_id"] for item in selected] == ["s", "t"]


def test_all_artifact_paths_are_under_data_dir(tmp_path, monkeypatch):
    from genacademy_coach.foundation import Foundation

    class FakeProvider:
        def embed(self, texts: list[str]) -> list[list[float]]:
            return [[1.0] for _text in texts]

        def generate(self, messages: list[dict], **kwargs) -> str:
            return "{}"

    monkeypatch.setenv("GENACADEMY_COACH_ROOT", str(tmp_path))
    monkeypatch.setenv("GENACADEMY_COACH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("GENACADEMY_DATA_DIR", str(tmp_path / "week2" / "data"))
    monkeypatch.setenv("GENACADEMY_CHROMA_DIR", str(tmp_path / "week2" / "chroma"))
    monkeypatch.setenv("GENACADEMY_SQLITE", str(tmp_path / "week2" / "genacademy.sqlite"))
    settings = CoachSettings.from_env()

    foundation = Foundation.build(settings, provider=FakeProvider())
    n_chunks = foundation.ingest(
        [
            Document(
                doc_id="note/path-test",
                title="Path Test",
                source_type="note",
                text="Artifact containment test text.",
                stored_path="corpus/notes/path-test.md",
            )
        ]
    )

    assert n_chunks >= 1
    assert Path(foundation.chroma_dir).resolve().is_relative_to(settings.data_dir)
    assert Path(foundation.sqlite_path).resolve().is_relative_to(settings.data_dir)
    assert Path(foundation.rag_settings.chroma_dir).resolve().is_relative_to(settings.data_dir)
    assert Path(foundation.rag_settings.sqlite_path).resolve().is_relative_to(settings.data_dir)
    assert not any((tmp_path / "week2").rglob("*"))
