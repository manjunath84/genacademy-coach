import importlib.util
from pathlib import Path

import pytest

from genacademy_coach.corpus import iter_indexable_files, load_markdown_document
from genacademy_coach.foundation import Foundation
from genacademy_coach.settings import CoachSettings


def load_ingest_cli_module():
    script_path = Path("scripts/ingest_course_corpus.py").resolve()
    spec = importlib.util.spec_from_file_location("ingest_course_corpus", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_iter_indexable_files_ignores_eval_questions(tmp_path):
    corpus = tmp_path / "corpus"
    (corpus / "notes").mkdir(parents=True)
    (corpus / "eval-questions").mkdir(parents=True)
    (corpus / "notes" / "lesson.md").write_text("lesson", encoding="utf-8")
    (corpus / "eval-questions" / "week1-chat.md").write_text("private", encoding="utf-8")

    files = iter_indexable_files(corpus)

    assert files == [corpus / "notes" / "lesson.md"]


def test_ingest_and_retrieve_smoke_uses_week2_pipeline(tmp_path, monkeypatch):
    class FakeProvider:
        def embed(self, texts: list[str]) -> list[list[float]]:
            return [[1.0 if "attention" in text.lower() else 0.0, 1.0] for text in texts]

        def generate(self, messages: list[dict], **kwargs) -> str:
            return "{}"

    corpus = tmp_path / "corpus"
    note = corpus / "notes" / "attention.md"
    note.parent.mkdir(parents=True)
    note.write_text("# Attention\n\nAttention controls retrieval focus.", encoding="utf-8")
    monkeypatch.setenv("GENACADEMY_COACH_ROOT", str(tmp_path))
    monkeypatch.setenv("GENACADEMY_COACH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("GENACADEMY_DATA_DIR", str(tmp_path / "week2" / "data"))
    settings = CoachSettings.from_env()
    foundation = Foundation.build(settings, provider=FakeProvider())

    n_chunks = foundation.ingest([load_markdown_document(note)])
    results = foundation.retrieve("attention")

    assert n_chunks >= 1
    assert results
    assert results[0]["source_type"] == "note"
    assert Path(foundation.chroma_dir).resolve().is_relative_to(settings.data_dir)
    assert Path(foundation.sqlite_path).resolve().is_relative_to(settings.data_dir)


def test_refuse_empty_extractions_blocks_zero_text_documents():
    module = load_ingest_cli_module()
    report = [{"title": "image-only.pptx", "empty": True}]

    with pytest.raises(SystemExit, match="image-only.pptx"):
        module.refuse_empty_extractions(report)
