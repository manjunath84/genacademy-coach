# Foundation Adapter + Eval Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first executable slice of GenAcademy Coach: Python scaffold, a thin adapter over Week-2 `genacademy-rag`, text-only corpus ingestion, and eval split/leak guards.

**Architecture:** The Coach repo owns orchestration code and the local course corpus. Retrieval,
embedding, Chroma, chunking, citation metadata, provider calls, and eval machinery are reused from the
sibling Week-2 `genacademy-rag` package through a small adapter. The Week-2 repo is a code dependency
only; it does **not** contain the `genacademy-coach/corpus/` files. Generated Coach Chroma/SQLite
artifacts live under `genacademy-coach/data/` by default, not in the Week-2 repo. Source prioritization
is configurable, with a default order of slides/handouts, then notes, then transcripts. The MVP does
**not** use multimodal RAG; it extracts text from notes, transcripts, slides, handouts, PDFs, PPTX, and
DOCX, records extraction gaps, and defers OCR/vision/layout-aware retrieval unless measured failures
prove text extraction is blocking.

**Tech Stack:** Python 3.12, `uv`, pytest, ruff, Week-2 `genacademy-rag` as editable
local dependency, Chroma via Week-2, pypdf via Week-2, `python-pptx`, `python-docx`.
LangChain, `langchain-openai`, FastAPI, and Uvicorn are added only in later slices that need
agent or web runtime surfaces.

---

## Scope

This plan intentionally stops before prompt templates and before the LangChain `create_agent` teach loop. The next plan starts only after this slice proves:

- Week-2 can be imported as a local editable dependency.
- Course corpus from this repo's local `corpus/` directory can be converted into Week-2 `Document`
  objects without publishing private content.
- Course corpus from this repo can be ingested into a separate `coach_course` Chroma collection.
- Generated Chroma and SQLite artifacts are written to this repo's ignored `data/` directory unless
  explicitly overridden through Coach settings.
- Source priority can be changed through configuration without changing retrieval code.
- Held-out eval source files can be normalized, split deterministically, and leak-checked without committing private question text.
- Text extraction quality is visible enough to decide whether multimodal RAG is actually needed later.

## File Structure

- Create `pyproject.toml` - package metadata, dependencies, `uv` local source binding to Week-2.
- Create `src/genacademy_coach/__init__.py` - package marker.
- Create `src/genacademy_coach/settings.py` - local paths, collection names, and env-derived settings that do not duplicate Week-2 config.
- Create `src/genacademy_coach/foundation.py` - thin adapter around Week-2 `Settings`, `build_provider`, `ChromaStore`, `SQLiteDatastore`, `build_chunker`, `IngestPipeline`, `HybridRetriever`.
- Create `src/genacademy_coach/corpus.py` - readers for this repo's local `corpus/` files that return
  Week-2 `Document` objects with `source_type` set to `note`, `transcript`, `slide`, or `handout`.
- Create `src/genacademy_coach/eval_split.py` - deterministic eval manifest builder and filename normalization checks.
- Create `scripts/ingest_course_corpus.py` - CLI for local course-corpus ingest into `coach_course`.
- Create `scripts/split_eval.py` - CLI for private eval source split into a manifest with checksums and no text.
- Create `scripts/check_eval_leak.py` - CLI that fails if test IDs/checksums or full verbatim eval
  n-grams appear in committed prompt/demo/index config files or local indexable corpus files.
- Create tests under `tests/` matching each module above.
- Create `docs/foundation-adapter-spec.md` - human-readable audit record generated from the real Week-2 public surface.

Private corpus files under `corpus/` stay ignored. Generated Chroma/SQLite/eval run artifacts stay
ignored under this repo, primarily `data/` and `eval/`.

---

### Task 1: Python Package Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/genacademy_coach/__init__.py`
- Create: `tests/test_scaffold.py`

- [ ] **Step 1: Create `pyproject.toml`**

Use this exact package shape:

```toml
[project]
name = "genacademy-coach"
version = "0.1.0"
description = "Adaptive grounded tutor over Gen Academy course materials"
requires-python = ">=3.12"
dependencies = [
    "genacademy-rag",
    "python-docx",
    "python-pptx",
]

[build-system]
requires = ["uv_build>=0.11.17,<0.12.0"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "pytest",
    "ruff",
]

[tool.uv.sources]
genacademy-rag = { path = "../../Week2-RAG_ContextEngineering/genacademy-rag", editable = true }

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package marker**

```python
"""GenAcademy Coach package."""
```

- [ ] **Step 3: Write scaffold import test**

```python
def test_imports_week2_foundation():
    import genacademy_coach
    import genacademy_rag

    assert genacademy_coach.__doc__
    assert genacademy_rag.__name__ == "genacademy_rag"
```

- [ ] **Step 4: Lock dependencies**

Run:

```bash
uv lock
```

Expected: `uv.lock` is created and includes the local editable `genacademy-rag` source.

- [ ] **Step 5: Run scaffold checks**

Run:

```bash
uv run pytest tests/test_scaffold.py -q
uv run ruff check .
```

Expected: pytest passes; ruff reports no errors.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/genacademy_coach/__init__.py tests/test_scaffold.py
git commit -m "chore: scaffold coach package"
```

---

### Task 2: Foundation Audit Spec

**Files:**
- Create: `docs/foundation-adapter-spec.md`
- Create: `tests/test_guardrails.py`

- [ ] **Step 1: Write the adapter spec**

Create `docs/foundation-adapter-spec.md` with these concrete Week-2 calls:

```markdown
# Foundation Adapter Spec

Status: implementation-pinned after reading the Week-2 repo.

## Week-2 package

Local editable dependency: `../../Week2-RAG_ContextEngineering/genacademy-rag`.

This dependency supplies reusable code only. It does not contain the Week-3 owned course corpus. The
source documents to ingest live under this repo's ignored `corpus/` directory.

## Imports the Coach adapter may use

- `from genacademy_rag.config import Settings`
- `from genacademy_rag.core.chunker import build_chunker`
- `from genacademy_rag.core.pipeline import IngestPipeline`
- `from genacademy_rag.core.providers import build_provider`
- `from genacademy_rag.core.reranker import build_reranker`
- `from genacademy_rag.core.retriever import DEFAULT_CANDIDATE_K, HybridRetriever`
- `from genacademy_rag.core.types import Citation, Chunk, Document, RetrievedChunk`
- `from genacademy_rag.core.vectorstore import ChromaStore`
- `from genacademy_rag.data.datastore import SQLiteDatastore`

## Week-2 calls

- `Settings.from_env()` supplies provider, embedder, chunking, rerank, and top-k config.
  The Coach adapter calls it for reusable Week-2 settings, then pins the returned Chroma and SQLite
  paths to `CoachSettings.chroma_dir` and `CoachSettings.sqlite_path`.
- `build_provider(settings)` returns a provider with `embed(texts)` and `generate(messages, ...)`.
- `ChromaStore(persist_dir=coach_settings.chroma_dir, collection="coach_course")` stores course vectors.
- `SQLiteDatastore(coach_settings.sqlite_path)` stores document/chunk metadata.
- `build_chunker("section", chunk_size=..., chunk_overlap=..., section_max_chars=..., section_overlap=...)` returns the section-aware chunker.
- `IngestPipeline(chunker=..., provider=..., store=..., datastore=...)` prepares and commits Week-2 `Document` objects.
- `HybridRetriever(store=..., provider=..., all_chunks=store.get_all_chunks(), top_k=..., candidate_k=DEFAULT_CANDIDATE_K, reranker=build_reranker(settings), rerank_pool=settings.rerank_pool)` retrieves `RetrievedChunk` objects.

## Audited Week-2 path fields

- `Settings.from_env()` uses `GENACADEMY_DATA_DIR` as the default parent for `chroma_dir` and
  `sqlite_path`.
- `CoachSettings.data_dir` uses `GENACADEMY_COACH_DATA_DIR` or defaults to `genacademy-coach/data/`.
- Coach exposes one artifact relocation knob for this slice: `GENACADEMY_COACH_DATA_DIR`. Chroma and
  SQLite stay under that directory by construction.
- Week-2 also honors `GENACADEMY_CHROMA_DIR` and `GENACADEMY_SQLITE`, so the adapter must not trust
  those returned path fields. It replaces them with Coach-derived paths before constructing stores.
- `SQLiteDatastore` creates the parent directory but does not expose the SQLite path after
  construction.
- The Coach adapter must store `chroma_dir` and `sqlite_path` on `Foundation`, assert both resolve
  under `CoachSettings.data_dir`, and assert a real ingest does not write into simulated Week-2
  artifact paths. This prevents stale Week-2 environment variables from writing artifacts into the
  sibling `genacademy-rag` repo.

## Data ownership boundary

- `genacademy-rag` = reusable RAG machinery and existing Week-2 eval/demo corpus.
- `genacademy-coach/corpus/` = Week-3 owned course corpus: notes, transcripts, slides, handouts, and never-indexed eval questions.
- `genacademy-coach/data/` = generated local Coach Chroma/SQLite artifacts, ignored by git.
- The adapter converts local Coach corpus files into Week-2 `Document` objects, then passes those objects into Week-2 `IngestPipeline`.
- No code should assume Week-2 already has the Coach corpus indexed.

## Eval harness delta

Week-2's eval harness scores retrieval/faithfulness against a gold set. It does not provide the
Coach-owned held-out chat-question split, private-source manifest, or leak guard. `eval_split.py` is
additive data governance for the sacred held-out set; it is not a replacement for the Week-2 retrieval
or faithfulness evaluators.

## Coach rules

- The Coach repo must not import `langgraph.*` directly.
- The Coach repo must not rebuild the embedder, chunker, vector schema, refusal scheme, or eval harness.
- The Coach repo may create text loaders for local `.pptx` and `.docx` files because Week-2 does not provide those loaders.
- The MVP is text-only RAG. Multimodal RAG is deferred until extraction reports or eval failures show that image-only slide content blocks the teach loop.
```

- [ ] **Step 2: Add guardrail test for forbidden direct LangGraph imports**

```python
from pathlib import Path


def test_coach_code_does_not_import_langgraph_directly():
    src = Path("src/genacademy_coach")
    offenders = []
    for path in src.rglob("*.py"):
        text = path.read_text()
        if "import langgraph" in text or "from langgraph" in text:
            offenders.append(str(path))
    assert offenders == []
```

- [ ] **Step 3: Run guardrail test**

Run:

```bash
uv run pytest tests/test_guardrails.py -q
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add docs/foundation-adapter-spec.md tests/test_guardrails.py
git commit -m "docs: pin foundation adapter surface"
```

---

### Task 3: Coach Settings and Foundation Adapter

**Files:**
- Create: `src/genacademy_coach/settings.py`
- Create: `src/genacademy_coach/foundation.py`
- Create: `tests/test_foundation.py`

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path

import pytest

from genacademy_coach.foundation import reorder_spans, select_retrieved_spans, source_priority_map
from genacademy_coach.settings import CoachSettings
from genacademy_rag.core.types import Document


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
```

- [ ] **Step 2: Implement settings**

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ALLOWED_SOURCE_TYPES = frozenset({"slide", "handout", "note", "transcript"})
DEFAULT_SOURCE_PRIORITY = ("slide", "handout", "note", "transcript")
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]


def _source_priority_from_env() -> tuple[str, ...]:
    raw = os.environ.get("GENACADEMY_COACH_SOURCE_PRIORITY")
    if raw is None:
        return DEFAULT_SOURCE_PRIORITY
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    unknown = sorted(set(values) - ALLOWED_SOURCE_TYPES)
    if unknown:
        message = "unknown source_type values in GENACADEMY_COACH_SOURCE_PRIORITY: "
        raise ValueError(message + ", ".join(unknown))
    duplicates = sorted({item for item in values if values.count(item) > 1})
    if duplicates:
        message = "duplicate source_type values in GENACADEMY_COACH_SOURCE_PRIORITY: "
        raise ValueError(message + ", ".join(duplicates))
    return values or DEFAULT_SOURCE_PRIORITY


@dataclass(frozen=True)
class CoachSettings:
    repo_root: Path
    data_dir: Path
    chroma_dir: Path
    sqlite_path: Path
    corpus_dir: Path
    eval_questions_dir: Path
    eval_dir: Path
    eval_manifest_path: Path
    review_queue_path: Path
    course_collection: str = "coach_course"
    retrieval_top_k: int = 5
    retrieval_candidate_k: int = 20
    source_priority: tuple[str, ...] = DEFAULT_SOURCE_PRIORITY

    @classmethod
    def from_env(cls) -> "CoachSettings":
        repo_root = Path(os.environ.get("GENACADEMY_COACH_ROOT", DEFAULT_REPO_ROOT)).resolve()
        eval_dir = repo_root / "eval"
        data_dir = Path(os.environ.get("GENACADEMY_COACH_DATA_DIR", repo_root / "data")).resolve()
        sqlite_filename = os.environ.get(
            "GENACADEMY_COACH_SQLITE_FILENAME",
            "genacademy-coach.sqlite",
        )
        return cls(
            repo_root=repo_root,
            data_dir=data_dir,
            chroma_dir=(data_dir / "chroma").resolve(),
            sqlite_path=(data_dir / sqlite_filename).resolve(),
            corpus_dir=Path(os.environ.get("GENACADEMY_COACH_CORPUS_DIR", repo_root / "corpus")),
            eval_questions_dir=Path(
                os.environ.get(
                    "GENACADEMY_COACH_EVAL_QUESTIONS_DIR",
                    repo_root / "corpus" / "eval-questions",
                )
            ),
            eval_dir=eval_dir,
            eval_manifest_path=eval_dir / "split_manifest.json",
            review_queue_path=repo_root / "review_queue.jsonl",
            course_collection=os.environ.get("GENACADEMY_COACH_COLLECTION", "coach_course"),
            retrieval_top_k=int(os.environ.get("GENACADEMY_COACH_TOP_K", "5")),
            retrieval_candidate_k=int(os.environ.get("GENACADEMY_COACH_CANDIDATE_K", "20")),
            source_priority=_source_priority_from_env(),
        )
```

- [ ] **Step 3: Implement adapter ordering and builders**

```python
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from genacademy_rag.config import Settings as RagSettings
from genacademy_rag.core.chunker import build_chunker
from genacademy_rag.core.pipeline import IngestPipeline
from genacademy_rag.core.providers import build_provider
from genacademy_rag.core.reranker import build_reranker
from genacademy_rag.core.retriever import DEFAULT_CANDIDATE_K, HybridRetriever
from genacademy_rag.core.types import Document, RetrievedChunk
from genacademy_rag.core.vectorstore import ChromaStore
from genacademy_rag.data.datastore import SQLiteDatastore

from genacademy_coach.settings import CoachSettings


def source_priority_map(source_priority: tuple[str, ...]) -> dict[str, int]:
    return {source_type: rank for rank, source_type in enumerate(source_priority)}


def reorder_spans(spans: list[dict[str, Any]], priority: dict[str, int]) -> list[dict[str, Any]]:
    return sorted(
        spans,
        key=lambda item: (
            priority.get(str(item.get("source_type", "")), len(priority)),
            -float(item.get("score", 0.0)),
            str(item.get("chunk_id", "")),
        ),
    )


def select_retrieved_spans(
    spans: list[dict[str, Any]],
    priority: dict[str, int],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    ordered = reorder_spans(spans, priority)
    selected = ordered[:limit]
    top_scored = max(
        spans,
        key=lambda item: (float(item.get("score", 0.0)), str(item.get("chunk_id", ""))),
        default=None,
    )
    if top_scored is not None and top_scored not in selected:
        selected = [*selected[:-1], top_scored] if selected else [top_scored]
    return selected


@dataclass
class Foundation:
    rag_settings: RagSettings
    coach_settings: CoachSettings
    provider: Any
    store: ChromaStore
    datastore: SQLiteDatastore
    chroma_dir: Path
    sqlite_path: Path

    @classmethod
    def build(
        cls,
        coach_settings: CoachSettings | None = None,
        *,
        provider: Any | None = None,
    ) -> "Foundation":
        coach = coach_settings or CoachSettings.from_env()
        rag = replace(
            RagSettings.from_env(),
            chroma_dir=coach.chroma_dir,
            sqlite_path=coach.sqlite_path,
        )
        active_provider = provider or build_provider(rag)
        store = ChromaStore(persist_dir=coach.chroma_dir, collection=coach.course_collection)
        datastore = SQLiteDatastore(coach.sqlite_path)
        return cls(
            rag_settings=rag,
            coach_settings=coach,
            provider=active_provider,
            store=store,
            datastore=datastore,
            chroma_dir=coach.chroma_dir,
            sqlite_path=coach.sqlite_path,
        )

    def ingest(self, docs: list[Document]) -> int:
        chunker = build_chunker(
            "section",
            chunk_size=self.rag_settings.chunk_size,
            chunk_overlap=self.rag_settings.chunk_overlap,
            section_max_chars=self.rag_settings.section_chunk_max_chars,
            section_overlap=self.rag_settings.section_chunk_overlap,
        )
        pipe = IngestPipeline(
            chunker=chunker,
            provider=self.provider,
            store=self.store,
            datastore=self.datastore,
        )
        return pipe.ingest(docs)

    def retriever(self) -> HybridRetriever:
        return HybridRetriever(
            store=self.store,
            provider=self.provider,
            all_chunks=self.store.get_all_chunks(),
            # Over-fetch from Week-2 so Coach can apply source-priority ordering afterward.
            top_k=self.coach_settings.retrieval_candidate_k,
            candidate_k=max(DEFAULT_CANDIDATE_K, self.coach_settings.retrieval_candidate_k),
            reranker=build_reranker(self.rag_settings),
            rerank_pool=self.rag_settings.rerank_pool,
        )

    def retrieve(self, query: str) -> list[dict[str, Any]]:
        results: list[RetrievedChunk] = self.retriever().retrieve(query)
        spans = [
            {
                "chunk_id": item.chunk.chunk_id,
                "doc_id": item.chunk.doc_id,
                "text": item.chunk.text,
                "score": item.score,
                "title": item.chunk.citation.title,
                "source_type": item.chunk.citation.source_type,
                "page_or_section": item.chunk.citation.page_or_section,
            }
            for item in results
        ]
        priority = source_priority_map(self.coach_settings.source_priority)
        return select_retrieved_spans(
            spans,
            priority,
            limit=self.coach_settings.retrieval_top_k,
        )
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_foundation.py tests/test_guardrails.py -q
```

Expected: pass.

Decision recorded for source priority: this slice keeps source-type precedence as the default ordering
so slides/handouts remain primary, but reserves one final returned slot for the highest-scoring span
when it would otherwise be excluded. That avoids transcript-only starvation before we have eval evidence
to justify a stronger source-specific retrieval rule. The teach-loop plan should cache the
`HybridRetriever` instead of rebuilding the BM25 side index on every request.

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/settings.py src/genacademy_coach/foundation.py tests/test_foundation.py
git commit -m "feat: add week2 foundation adapter"
```

---

### Task 4: Text-Only Corpus Loaders and Extraction Report

**Files:**
- Create: `src/genacademy_coach/corpus.py`
- Create: `tests/test_corpus.py`

- [ ] **Step 1: Write tests for local text conversion**

```python
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches

from genacademy_coach.corpus import (
    build_doc_id,
    extraction_summary,
    load_markdown_document,
    load_pptx_document,
    source_type_for_path,
)
from genacademy_rag.core.types import Document


def test_source_type_for_path_uses_folder_priority():
    assert source_type_for_path(Path("corpus/slides/week1-session1.pptx")) == "slide"
    assert source_type_for_path(Path("corpus/handouts/agent-memory.pdf")) == "handout"
    assert source_type_for_path(Path("corpus/notes/lesson1.md")) == "note"
    assert source_type_for_path(Path("corpus/transcripts/week1-session1.md")) == "transcript"


def test_build_doc_id_is_stable_and_does_not_include_absolute_path():
    first = build_doc_id(Path("corpus/notes/lesson1.md"), b"hello")
    second = build_doc_id(Path("/tmp/elsewhere/corpus/notes/lesson1.md"), b"hello")

    assert first == second
    assert first.startswith("note/lesson1-")


def test_load_markdown_document_sets_source_type_and_title(tmp_path):
    path = tmp_path / "corpus" / "notes" / "lesson1.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Attention\n\nText.", encoding="utf-8")

    doc = load_markdown_document(path)

    assert doc.source_type == "note"
    assert doc.title == "lesson1.md"
    assert "Attention" in doc.text


def test_load_pptx_document_includes_shape_text_and_speaker_notes(tmp_path):
    path = tmp_path / "corpus" / "slides" / "week1.pptx"
    path.parent.mkdir(parents=True)
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "Retrieval planning"
    slide.notes_slide.notes_text_frame.text = "Speaker note about citations."
    prs.save(path)

    doc = load_pptx_document(path)

    assert doc.source_type == "slide"
    assert "Retrieval planning" in doc.text
    assert "Speaker note about citations" in doc.text


def test_image_only_pptx_reports_empty_text_with_shape_count(tmp_path):
    path = tmp_path / "corpus" / "slides" / "image-only.pptx"
    path.parent.mkdir(parents=True)
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1), Inches(1), Inches(2), Inches(1))
    prs.save(path)

    doc = load_pptx_document(path)
    summary = extraction_summary(doc)

    assert doc.text.strip() == ""
    assert summary["empty"] is True
    assert summary["slide_shape_count"] == 1


def test_extraction_summary_marks_empty_text():
    doc = Document(
        doc_id="note/empty",
        title="empty.md",
        source_type="note",
        text="  ",
        stored_path="corpus/notes/empty.md",
    )

    summary = extraction_summary(doc)

    assert summary["chars"] == 0
    assert summary["empty"] is True
```

- [ ] **Step 2: Implement corpus loaders**

Use text extraction only from this repo's local `corpus/` directory. Do not read corpus files from
`genacademy-rag`. Do not add OCR, image embeddings, screenshot parsing, or multimodal indexing in this
task.

```python
from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from docx import Document as DocxDocument
from pptx import Presentation

from genacademy_rag.core.loaders.pdf_loader import load_pdf_bytes
from genacademy_rag.core.types import Document


INDEXABLE_DIRS = ("notes", "transcripts", "slides", "handouts")
INDEXABLE_SUFFIXES = {".md", ".pdf", ".pptx", ".docx"}


def source_type_for_path(path: Path) -> str:
    parts = set(path.parts)
    if "slides" in parts:
        return "slide"
    if "handouts" in parts:
        return "handout"
    if "notes" in parts:
        return "note"
    if "transcripts" in parts:
        return "transcript"
    raise ValueError(f"not an indexable corpus path: {path}")


def build_doc_id(path: Path, raw_bytes: bytes) -> str:
    source_type = source_type_for_path(path)
    stem = path.stem.lower().replace("_", "-")
    digest = hashlib.sha256(raw_bytes).hexdigest()[:12]
    return f"{source_type}/{stem}-{digest}"


def load_markdown_document(path: Path) -> Document:
    raw = path.read_bytes()
    return Document(
        doc_id=build_doc_id(path, raw),
        title=path.name,
        source_type=source_type_for_path(path),
        text=raw.decode("utf-8"),
        filename=path.name,
        stored_path=str(path),
    )


def load_pdf_document(path: Path) -> Document:
    raw = path.read_bytes()
    doc = load_pdf_bytes(filename=path.name, raw_bytes=raw, stored_path=str(path))
    return replace(
        doc,
        doc_id=build_doc_id(path, raw),
        source_type=source_type_for_path(path),
        title=path.name,
    )


def _shape_alt_text(shape) -> list[str]:
    values: list[str] = []
    for node in shape.element.iter():
        if not str(node.tag).endswith("}cNvPr"):
            continue
        for key in ("title", "descr"):
            value = (node.attrib.get(key) or "").strip()
            if value:
                values.append(value)
    return values


def _shape_text(shape) -> list[str]:
    values: list[str] = []
    if getattr(shape, "has_text_frame", False):
        text = shape.text_frame.text.strip()
        if text:
            values.append(text)
    if getattr(shape, "has_table", False):
        cells = [
            cell.text.strip()
            for row in shape.table.rows
            for cell in row.cells
            if cell.text.strip()
        ]
        if cells:
            values.append("\n".join(cells))
    values.extend(_shape_alt_text(shape))
    return values


def _slide_notes_text(slide) -> str:
    try:
        return slide.notes_slide.notes_text_frame.text.strip()
    except (AttributeError, KeyError, ValueError):
        return ""


def pptx_shape_count(path: Path) -> int:
    prs = Presentation(path)
    return sum(len(slide.shapes) for slide in prs.slides)


def load_pptx_document(path: Path) -> Document:
    raw = path.read_bytes()
    prs = Presentation(path)
    parts: list[str] = []
    for idx, slide in enumerate(prs.slides, start=1):
        texts: list[str] = []
        for shape in slide.shapes:
            texts.extend(_shape_text(shape))
        notes = _slide_notes_text(slide)
        if notes:
            texts.append("## Speaker Notes\n\n" + notes)
        if texts:
            parts.append(f"# Slide {idx}\n\n" + "\n\n".join(texts))
    return Document(
        doc_id=build_doc_id(path, raw),
        title=path.name,
        source_type="slide",
        text="\n\f\n".join(parts),
        filename=path.name,
        stored_path=str(path),
    )


def load_docx_document(path: Path) -> Document:
    raw = path.read_bytes()
    parsed = DocxDocument(path)
    paragraphs = [p.text.strip() for p in parsed.paragraphs if p.text.strip()]
    return Document(
        doc_id=build_doc_id(path, raw),
        title=path.name,
        source_type=source_type_for_path(path),
        text="\n\n".join(paragraphs),
        filename=path.name,
        stored_path=str(path),
    )


def load_corpus_document(path: Path) -> Document:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return load_markdown_document(path)
    if suffix == ".pdf":
        return load_pdf_document(path)
    if suffix == ".pptx":
        return load_pptx_document(path)
    if suffix == ".docx":
        return load_docx_document(path)
    raise ValueError(f"unsupported corpus file: {path}")


def iter_indexable_files(corpus_dir: Path) -> list[Path]:
    files: list[Path] = []
    for dirname in INDEXABLE_DIRS:
        root = corpus_dir / dirname
        if not root.exists():
            continue
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in INDEXABLE_SUFFIXES
        )
    return sorted(files)


def extraction_summary(doc: Document) -> dict[str, object]:
    text = doc.text.strip()
    stored_path = Path(doc.stored_path) if doc.stored_path else None
    slide_shape_count = None
    if (
        doc.source_type == "slide"
        and stored_path is not None
        and stored_path.suffix.lower() == ".pptx"
        and stored_path.exists()
    ):
        slide_shape_count = pptx_shape_count(stored_path)
    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "source_type": doc.source_type,
        "chars": len(text),
        "empty": not bool(text),
        "slide_shape_count": slide_shape_count,
        "stored_path": doc.stored_path,
    }
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/test_corpus.py -q
```

Expected: pass.

Implementation note: `extraction_summary()` re-opens `.pptx` files to count shapes because the reused
Week-2 `Document` type has no metadata field for loader-only diagnostics. This is acceptable in the
offline ingest slice; do not change the Week-2 type to optimize it.

- [ ] **Step 4: Commit**

```bash
git add src/genacademy_coach/corpus.py tests/test_corpus.py
git commit -m "feat: load local corpus as week2 documents"
```

---

### Task 5: Eval Split Manifest and Leak Guard

**Files:**
- Create: `src/genacademy_coach/eval_split.py`
- Create: `tests/test_eval_split.py`
- Create: `scripts/split_eval.py`
- Create: `scripts/check_eval_leak.py`

- [ ] **Step 1: Write tests**

Eval source files must be kebab-cased `docx`, `pdf`, `txt`, or `md` files. Other private eval source
formats should be normalized before splitting.

```python
from pathlib import Path

import pytest

from genacademy_coach.eval_split import assert_normalized_eval_filename, ngrams, split_items


def test_rejects_case_variant_eval_filename():
    with pytest.raises(ValueError, match="lowercase kebab-case"):
        assert_normalized_eval_filename(Path("Week1_Session2_Chat_Questions.docx"))


def test_split_items_is_deterministic_and_keeps_test_frozen():
    items = [{"id": f"q{i}", "source_sha256": f"s{i}"} for i in range(100)]

    first = split_items(items, seed="genacademy-coach-v1")
    second = split_items(items, seed="genacademy-coach-v1")
    expanded = split_items(
        [*items, {"id": "q-new", "source_sha256": "s-new"}],
        seed="genacademy-coach-v1",
    )
    first_by_id = {item["id"]: item["split"] for item in first}

    assert first == second
    assert {row["split"] for row in first} == {"seed", "dev", "test"}
    assert all(
        row["split"] == first_by_id[row["id"]]
        for row in expanded
        if row["id"] in first_by_id
    )
    assert all("text" not in row for row in first)


def test_ngrams_uses_all_normalized_eight_word_phrases_without_private_manifest_text():
    text = "One two three four five six seven eight nine ten"

    phrases = ngrams(text, n=8)

    assert "one two three four five six seven eight" in phrases
    assert "two three four five six seven eight nine" in phrases
    assert "three four five six seven eight nine ten" in phrases


def test_phrase_hashes_preserve_multiple_eval_sources():
    from genacademy_coach.eval_split import phrase_hashes

    phrases = phrase_hashes(
        [
            ("first.md", "One two three four five six seven eight"),
            ("second.md", "One two three four five six seven eight"),
        ],
        n=8,
    )

    assert len(phrases["one two three four five six seven eight"]) == 2
    assert {row["source_file"] for row in phrases["one two three four five six seven eight"]} == {
        "first.md",
        "second.md",
    }
```

- [ ] **Step 2: Implement split module**

```python
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


NORMALIZED_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.(docx|pdf|txt|md)$")
WORD_RE = re.compile(r"[a-z0-9]+")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def assert_normalized_eval_filename(path: Path) -> None:
    if NORMALIZED_RE.match(path.name) is None:
        raise ValueError(
            f"{path.name!r} must be lowercase kebab-case before splitting held-out eval files"
        )


def build_file_items(eval_dir: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for path in sorted(eval_dir.iterdir()):
        if not path.is_file() or path.name.startswith(".") or path.name == "README.md":
            continue
        assert_normalized_eval_filename(path)
        digest = sha256_file(path)
        items.append(
            {
                "id": hashlib.sha256(f"{path.name}:{digest}".encode("utf-8")).hexdigest()[:16],
                "source_file": path.name,
                "source_sha256": digest,
            }
        )
    if len({item["id"] for item in items}) != len(items):
        raise ValueError("duplicate eval item IDs after hashing")
    return items


def split_items(items: list[dict[str, str]], *, seed: str) -> list[dict[str, str]]:
    rows = []
    for item in sorted(items, key=lambda row: row["id"]):
        bucket = int(hashlib.sha256(f"{seed}:{item['id']}".encode("utf-8")).hexdigest(), 16) % 100
        if bucket < 33:
            split = "test"
        elif bucket < 66:
            split = "dev"
        else:
            split = "seed"
        rows.append({**item, "split": split})
    return rows


def normalized_words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def ngrams(text: str, *, n: int = 8) -> set[str]:
    words = normalized_words(text)
    return {" ".join(words[i : i + n]) for i in range(0, max(0, len(words) - n + 1))}


def phrase_hashes(sources: list[tuple[str, str]], *, n: int = 8) -> dict[str, list[dict[str, str]]]:
    rows: dict[str, list[dict[str, str]]] = {}
    for source_file, text in sources:
        for phrase in ngrams(text, n=n):
            rows.setdefault(phrase, []).append(
                {
                    "source_file": source_file,
                    "phrase_hash": hashlib.sha256(phrase.encode("utf-8")).hexdigest()[:12],
                }
            )
    return rows


def write_manifest(eval_dir: Path, manifest_path: Path, *, seed: str) -> dict[str, object]:
    rows = split_items(build_file_items(eval_dir), seed=seed)
    manifest = {
        "version": 1,
        "seed": seed,
        "items": rows,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(payload, encoding="utf-8")
    return manifest
```

- [ ] **Step 3: Add CLIs**

`scripts/split_eval.py`:

```python
from genacademy_coach.eval_split import write_manifest
from genacademy_coach.settings import CoachSettings


def main() -> None:
    settings = CoachSettings.from_env()
    manifest = write_manifest(
        settings.eval_questions_dir,
        settings.eval_manifest_path,
        seed="genacademy-coach-v1",
    )
    print(
        f"wrote {settings.eval_manifest_path} with {len(manifest['items'])} private-source items"
    )


if __name__ == "__main__":
    main()
```

`scripts/check_eval_leak.py`:

The ID/checksum scan is CI-safe because it only needs the committed manifest. The n-gram scan is
local-authoritative because it needs ignored private eval source files; on a fresh clone or CI where
those files are absent, the script skips the phrase scan and reports that limitation.

```python
import hashlib
import json
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

from genacademy_coach.corpus import iter_indexable_files, load_corpus_document
from genacademy_coach.eval_split import normalized_words, phrase_hashes
from genacademy_coach.settings import CoachSettings


SCAN_GLOBS = [
    "AGENTS.md",
    "README.md",
    "docs/**/*.md",
    "specs/**/*.md",
    "src/**/*.py",
    "scripts/**/*.py",
]


def read_eval_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".docx":
        doc = DocxDocument(path)
        paragraphs = [p.text for p in doc.paragraphs]
        table_cells = [
            cell.text
            for table in doc.tables
            for row in table.rows
            for cell in row.cells
        ]
        return "\n".join([*paragraphs, *table_cells])
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return ""


def normalized_text(text: str) -> str:
    return " ".join(normalized_words(text))


def iter_committed_scan_texts(settings: CoachSettings):
    for pattern in SCAN_GLOBS:
        for path in settings.repo_root.glob(pattern):
            if path.is_file():
                yield path, path.read_text(encoding="utf-8", errors="ignore")


def iter_local_corpus_scan_texts(settings: CoachSettings):
    for path in iter_indexable_files(settings.corpus_dir):
        yield path, load_corpus_document(path).text


def main() -> None:
    settings = CoachSettings.from_env()
    if not settings.eval_manifest_path.exists():
        raise SystemExit(f"missing eval manifest: {settings.eval_manifest_path}")
    manifest = json.loads(settings.eval_manifest_path.read_text(encoding="utf-8"))
    test_items = [item for item in manifest["items"] if item["split"] == "test"]
    needles = {item["id"] for item in test_items} | {item["source_sha256"] for item in test_items}
    offenders: list[str] = []
    eval_phrase_sources: list[tuple[str, str]] = []
    missing_eval_sources: list[str] = []
    for item in test_items:
        eval_path = settings.eval_questions_dir / item["source_file"]
        if not eval_path.exists():
            missing_eval_sources.append(item["source_file"])
            continue
        eval_phrase_sources.append((item["source_file"], read_eval_text(eval_path)))
    test_phrase_hashes = phrase_hashes(eval_phrase_sources)
    scan_texts = list(iter_committed_scan_texts(settings))
    if test_phrase_hashes:
        scan_texts.extend(iter_local_corpus_scan_texts(settings))
    for path, text in scan_texts:
        if any(needle in text for needle in needles):
            offenders.append(str(path))
        normalized = normalized_text(text)
        for phrase, matches in test_phrase_hashes.items():
            if phrase in normalized:
                phrase_refs = ", ".join(
                    f"{match['source_file']}:{match['phrase_hash']}" for match in matches
                )
                offenders.append(f"{path} matched eval phrase {phrase_refs}")
    if offenders:
        raise SystemExit("eval test leak detected in: " + ", ".join(sorted(set(offenders))))
    if missing_eval_sources:
        print(
            "private eval sources missing; skipped local n-gram leak scan for: "
            + ", ".join(sorted(missing_eval_sources))
        )
    print(
        "no eval test IDs/checksums found in code/docs; no eval n-grams found where "
        "private eval sources were available "
        f"({len(test_items)} test items)"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_eval_split.py -q
```

Expected: pass.

- [ ] **Step 5: Run the split and leak scripts locally**

```bash
uv run python scripts/split_eval.py
uv run python scripts/check_eval_leak.py
```

Expected: manifest is written under `eval/split_manifest.json`; leak script reports no test
IDs/checksums in code/docs, and no eval n-grams in code/docs or local indexable corpus files when
private eval sources are available. On fresh clones or CI without private eval source files, the
n-gram scan is skipped and the committed ID/checksum scan remains authoritative.

- [ ] **Step 6: Commit only safe artifacts**

Commit `eval/split_manifest.json` because it contains source filenames, IDs, checksums, and split
  labels only. Do not commit private eval source file contents.

Known limitation: the local phrase scan is a simple nested string scan over eval phrases and scanned
files. That is appropriate for the current corpus size; if the corpus grows to thousands of files,
replace it with a trie or Aho-Corasick matcher before making it a mandatory CI gate.

```bash
git add src/genacademy_coach/eval_split.py tests/test_eval_split.py scripts/split_eval.py scripts/check_eval_leak.py eval/split_manifest.json
git commit -m "feat: add held-out eval split guard"
```

---

### Task 6: Course Corpus Ingest CLI

**Files:**
- Create: `scripts/ingest_course_corpus.py`
- Create: `tests/test_ingest_cli.py`

- [ ] **Step 1: Write CLI and ingest/retrieve smoke tests**

```python
from pathlib import Path

import pytest

from genacademy_coach.corpus import iter_indexable_files, load_markdown_document
from genacademy_coach.foundation import Foundation
from genacademy_coach.settings import CoachSettings
from scripts.ingest_course_corpus import refuse_empty_extractions


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
            return [
                [1.0 if "attention" in text.lower() else 0.0, 1.0]
                for text in texts
            ]

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
    report = [{"title": "image-only.pptx", "empty": True}]

    with pytest.raises(SystemExit, match="image-only.pptx"):
        refuse_empty_extractions(report)
```

- [ ] **Step 2: Implement ingest CLI**

```python
import json

from genacademy_coach.corpus import (
    extraction_summary,
    iter_indexable_files,
    load_corpus_document,
)
from genacademy_coach.foundation import Foundation
from genacademy_coach.settings import CoachSettings


def refuse_empty_extractions(report: list[dict[str, object]]) -> None:
    empty = [row for row in report if row["empty"]]
    if empty:
        titles = ", ".join(str(row["title"]) for row in empty)
        raise SystemExit(f"refusing to ingest empty extracted documents: {titles}")


def main() -> None:
    settings = CoachSettings.from_env()
    files = iter_indexable_files(settings.corpus_dir)
    docs = [load_corpus_document(path) for path in files]
    report = [extraction_summary(doc) for doc in docs]
    settings.eval_dir.mkdir(parents=True, exist_ok=True)
    extraction_path = settings.eval_dir / "extraction_report.json"
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    extraction_path.write_text(payload, encoding="utf-8")
    refuse_empty_extractions(report)
    foundation = Foundation.build(settings)
    n_chunks = foundation.ingest(docs)
    print(
        f"ingested {len(docs)} docs -> {n_chunks} chunks into "
        f"collection={settings.course_collection}; "
        f"extraction report={extraction_path}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/test_ingest_cli.py tests/test_corpus.py tests/test_foundation.py -q
```

Expected: pass.

- [ ] **Step 4: Run local ingest**

Run from `genacademy-coach` with local corpus files in this repo and the Week-2 provider/config code.
The adapter defaults Coach artifacts to `./data`; pass `GENACADEMY_COACH_DATA_DIR` explicitly if you
want a different local artifact directory:

```bash
GENACADEMY_CHUNKER=section uv run python scripts/ingest_course_corpus.py
```

Expected: prints doc/chunk counts, writes `eval/extraction_report.json`, and writes Chroma/SQLite under
this repo's ignored `data/` directory unless `GENACADEMY_COACH_DATA_DIR` was overridden. If any
slide/PDF/docx has zero extracted text, stop and inspect the report. Do **not** add multimodal RAG
here; decide whether to skip that source, improve text extraction, or create a follow-up decision.

- [ ] **Step 5: Commit safe code only**

Do not commit Chroma, SQLite, source corpus, or extraction report if it includes private filenames that should stay local.

```bash
git add scripts/ingest_course_corpus.py tests/test_ingest_cli.py
git commit -m "feat: add course corpus ingest cli"
```

---

### Task 7: Verification Gate for This Slice

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a short build-status note to README**

Append this under the status block after the slice is implemented:

```markdown
> **Implementation status:** foundation adapter + eval guard slice implemented. The teach-loop agent is still gated on an approved follow-up plan.
```

- [ ] **Step 2: Run full local verification**

Run:

```bash
uv run ruff check .
uv run pytest -q
uv run python scripts/split_eval.py
uv run python scripts/check_eval_leak.py
GENACADEMY_CHUNKER=section uv run python scripts/ingest_course_corpus.py
```

Expected:

- Ruff passes.
- Pytest passes.
- Split script writes a manifest with no private text.
- Leak script passes ID/checksum checks and full local n-gram checks where private eval sources are
  available.
- Ingest script writes an extraction report and ingests only `notes/`, `transcripts/`, `slides/`, and `handouts/`.

- [ ] **Step 3: Confirm corpus privacy**

Run:

```bash
git status --ignored --short corpus eval data chroma .chroma
git ls-files corpus
```

Expected:

- Private `.md`, `.pdf`, `.pptx`, `.docx`, Chroma, SQLite, and extraction artifacts are ignored or untracked.
- `git ls-files corpus` shows only `.gitignore`, READMEs, and `.gitkeep` files.

- [ ] **Step 4: Commit README status**

```bash
git add README.md
git commit -m "docs: record foundation slice status"
```

---

## Multimodal RAG Decision

Do **not** build multimodal RAG for the Week-3 MVP.

Reasoning:

- The judged differentiator is agentic teaching behavior: model-chosen re-explanation strategy, refusal, trace, and eval honesty.
- The current corpus has substantial text sources: notes, transcripts, handouts, slide text, and extracted PPTX text.
- Multimodal RAG would add OCR/image embedding/layout complexity before we know text retrieval is failing.
- Long-term extensibility is preserved by keeping `source_type`, `stored_path`, `page_or_section`, and extraction reports. If later eval failures trace to image-only diagrams, add a new decision and a separate layout-aware/multimodal ingestion plan.

Trigger to reopen: after Task 6, at least one high-priority teach-loop scenario fails because the needed answer exists only inside a non-extracted slide image/table/diagram, and no equivalent text exists in handouts, notes, or transcripts.

---

## Self-Review

- Spec coverage: this implements the first required build task from `docs/genacademy-rag-foundation.md` and the eval/data-split guard from `specs/roadmap.md`; it intentionally does not implement prompts or the teach loop.
- Placeholder scan: the plan contains no open-ended implementation placeholders. Deferred work is explicitly scoped as a later plan.
- Type consistency: `CoachSettings`, `Foundation`, `Document`, `RetrievedChunk`, `Citation`, `source_type`, and collection names are consistent across tasks.
- Review incorporation: the Kimchi and Claude review items are covered by artifact path containment
  tests, an ingest/retrieve smoke test, full n-gram eval leak checks, PPTX notes/alt-text extraction,
  empty extraction failure behavior, and unknown `source_type` ordering coverage.
- Review decisions recorded: source priority keeps slides/handouts primary but reserves one top-score
  slot to avoid transcript starvation; eval leak scanning includes local indexable corpus files when
  private eval sources are available.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-15-foundation-adapter-eval-guard.md`. Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach?
