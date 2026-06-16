# Teach Loop Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox
> (`- [ ]`) syntax for tracking.

**Goal:** Build the MVP adaptive teach loop: retrieve citeable course evidence, explain a concept,
check understanding, re-explain differently when the learner stumbles, refuse/escalate when unsupported,
and emit a runtime-decision trace.

**Architecture:** Keep the teach-loop core framework-light and testable. LangChain `create_agent` is the
agent boundary; Week-2 `genacademy-rag` remains the retrieval/ingest/provider foundation through
`Foundation`. Python enforces grounding, citation presence, deterministic grading, trace writes, review
queue writes, turn limits, and retrieval-derived evidence scores/bands; the model chooses
`observation`, `next_action`, and `strategy` through structured output. The agent never returns a
confidence score.

**Tech Stack:** Python 3.12, `uv`, pytest, ruff, Pydantic, LangChain `create_agent`, `langchain-openai`
`ChatOpenAI`, Week-2 `genacademy-rag` provider/retriever/store/chunker.

---

## Reference Calls Re-Checked

Use these exact current library surfaces in implementation:

- LangChain agent creation:

```python
from langchain.agents import create_agent

agent = create_agent(
    model=model,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
)
```

Source: Context7 query over LangChain Python docs, `https://docs.langchain.com/oss/python/langchain/quickstart`.

- LangChain structured output:

```python
from pydantic import BaseModel
from langchain.agents import create_agent

class Answer(BaseModel):
    summary: str
    source_count: int

agent = create_agent("openai:gpt-5.4", tools=tools, response_format=Answer)
result = agent.invoke({"messages": [{"role": "user", "content": "Summarize AI trends"}]})
result["structured_response"]
```

For tool-strategy structured output:

```python
from langchain.agents.structured_output import ToolStrategy

agent = create_agent(
    model="gpt-5.4",
    tools=tools,
    response_format=ToolStrategy(ProductReview),
)
```

Source: Context7 query over LangChain Python structured-output docs,
`https://docs.langchain.com/oss/python/langchain/structured-output`.

- OpenAI-compatible LangChain model:

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="Qwen/Qwen3-30B-A3B-Instruct-2507",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key="not-needed",
    base_url="https://api.tokenfactory.nebius.com/v1/",
)
```

Source: LangChain `ChatOpenAI` reference,
`https://reference.langchain.com/python/integrations/langchain_openai/ChatOpenAI/`.

## Scope

In scope:

- One text-first teach loop.
- One source-prioritized course retriever over the already-ingested `coach_course` collection.
- Within-session learner profile only.
- Grounded explanation, check item, deterministic grading, re-explain/drill/refuse/stop branch.
- Local JSON trace plus CLI pretty print.
- Review queue JSONL escalation.
- Local demo/eval commands that do not commit private eval text.

Out of scope:

- Web UI, FastAPI, auth, admin upload, voice, quiz mode, mock interview mode.
- Direct `langgraph.*` imports.
- New chunker, embedder, vector schema, provider wrapper, or eval harness.
- Answering from model priors.

## Pass 5 Review Fixes Applied

- B1: Structured agent output no longer accepts `confidence`; traces and escalation rows use Python
  `evidence_score` / `evidence_band` derived from retrieved spans.
- B2: `scripts/eval_teach_loop.py` is a teach-loop scenario runner, not a retrieval-only shell. It
  expands private held-out files into local per-question scenarios, runs `CoachSession`, and reports only
  IDs, booleans, scores, actions, and citation IDs.
- B3: The session runner carries previous strategy, last check, and last grade across turns; the demo and
  eval require `re_explain_differently` with a different strategy after the controlled wrong answer.
- I1: `trace_dir` is explicitly placed before defaulted dataclass fields in `CoachSettings`.

## File Structure

- Modify `pyproject.toml` - add only teach-loop dependencies: `langchain>=1.1`,
  `langchain-openai>=1.0`, `pydantic>=2`.
- Modify `src/genacademy_coach/settings.py` - add trace directory, evidence thresholds, and turn
  budget settings.
- Create `src/genacademy_coach/teach_types.py` - Pydantic/dataclass state and schema types shared by
  core, tools, and agent output.
- Create `src/genacademy_coach/grounding.py` - evidence bands, citation checks, deterministic
  understanding grade.
- Create `src/genacademy_coach/check_items.py` - grounded check-item generation through the inherited
  Week-2 provider.
- Create `src/genacademy_coach/trace.py` - append-only local runtime trace writer and loader.
- Create `src/genacademy_coach/escalation.py` - review-queue JSONL writes.
- Create `src/genacademy_coach/teach_tools.py` - LangChain tools closed over a session runtime.
- Create `src/genacademy_coach/teach_agent.py` - LangChain `create_agent` boundary and model wiring.
- Create `src/genacademy_coach/teach_session.py` - pure session runner that invokes an agent port,
  validates output, updates state, and returns learner-visible turns.
- Create `scripts/run_teach_demo.py` - CLI for one local teach-loop demo.
- Create `scripts/print_trace.py` - CLI pretty printer for a trace file.
- Create `src/genacademy_coach/eval_io.py` - private held-out eval text readers shared by leak check
  and local eval; this avoids importing from `scripts.*`.
- Modify `scripts/check_eval_leak.py` - import `read_eval_text` from the shared eval I/O helper.
- Create `scripts/eval_teach_loop.py` - local eval runner over seed/dev/test manifest splits without
  committing private question text; expands held-out files into per-question scenarios at runtime and
  runs `CoachSession`.
- Create focused tests under `tests/`.

---

### Task 1: Teach-Loop Dependencies and Settings

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/genacademy_coach/settings.py`
- Test: `tests/test_teach_settings.py`

- [ ] **Step 1: Write the settings test**

Create `tests/test_teach_settings.py`:

```python
from genacademy_coach.settings import CoachSettings


def test_teach_loop_settings_default_under_repo_root(tmp_path, monkeypatch):
    monkeypatch.setenv("GENACADEMY_COACH_ROOT", str(tmp_path))
    monkeypatch.delenv("GENACADEMY_COACH_TRACE_DIR", raising=False)
    monkeypatch.delenv("GENACADEMY_COACH_STOP_THRESHOLD", raising=False)
    monkeypatch.delenv("GENACADEMY_COACH_CONFIRM_THRESHOLD", raising=False)
    monkeypatch.delenv("GENACADEMY_COACH_MAX_TURNS", raising=False)

    settings = CoachSettings.from_env()

    assert settings.trace_dir == tmp_path / "traces"
    assert settings.stop_threshold == 0.60
    assert settings.confirm_threshold == 0.85
    assert settings.max_teach_turns == 4


def test_teach_loop_settings_can_be_overridden(tmp_path, monkeypatch):
    monkeypatch.setenv("GENACADEMY_COACH_ROOT", str(tmp_path))
    monkeypatch.setenv("GENACADEMY_COACH_TRACE_DIR", str(tmp_path / "tmp-traces"))
    monkeypatch.setenv("GENACADEMY_COACH_STOP_THRESHOLD", "0.55")
    monkeypatch.setenv("GENACADEMY_COACH_CONFIRM_THRESHOLD", "0.82")
    monkeypatch.setenv("GENACADEMY_COACH_MAX_TURNS", "3")

    settings = CoachSettings.from_env()

    assert settings.trace_dir == tmp_path / "tmp-traces"
    assert settings.stop_threshold == 0.55
    assert settings.confirm_threshold == 0.82
    assert settings.max_teach_turns == 3
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
uv run pytest tests/test_teach_settings.py -q
```

Expected: fails because `CoachSettings` does not yet expose the teach-loop settings.

- [ ] **Step 3: Add dependencies**

Modify `pyproject.toml` dependencies to:

```toml
dependencies = [
    "genacademy-rag",
    "langchain>=1.1",
    "langchain-openai>=1.0",
    "pydantic>=2",
    "python-docx",
    "python-pptx",
]
```

- [ ] **Step 4: Add settings fields**

In `src/genacademy_coach/settings.py`, add fields to the `CoachSettings` dataclass:

```python
    trace_dir: Path
    course_collection: str = "coach_course"
    retrieval_top_k: int = 5
    retrieval_candidate_k: int = 20
    source_priority: tuple[str, ...] = DEFAULT_SOURCE_PRIORITY
    stop_threshold: float = 0.60
    confirm_threshold: float = 0.85
    max_teach_turns: int = 4
```

Place `trace_dir` after `review_queue_path` and before the first defaulted field (`course_collection`)
so the frozen dataclass keeps all non-default fields before defaulted fields. Update `from_env()` to pass:

```python
            trace_dir=Path(
                os.environ.get("GENACADEMY_COACH_TRACE_DIR", repo_root / "traces")
            ).resolve(),
            stop_threshold=float(os.environ.get("GENACADEMY_COACH_STOP_THRESHOLD", "0.60")),
            confirm_threshold=float(os.environ.get("GENACADEMY_COACH_CONFIRM_THRESHOLD", "0.85")),
            max_teach_turns=int(os.environ.get("GENACADEMY_COACH_MAX_TURNS", "4")),
```

- [ ] **Step 5: Lock dependencies**

Run:

```bash
uv lock
```

Expected: `uv.lock` updates with LangChain, `langchain-openai`, and Pydantic dependencies.

- [ ] **Step 6: Run the settings tests**

Run:

```bash
uv run pytest tests/test_teach_settings.py -q
uv run ruff check pyproject.toml src/genacademy_coach/settings.py tests/test_teach_settings.py
```

Expected: tests pass; ruff reports no errors.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock src/genacademy_coach/settings.py tests/test_teach_settings.py
git commit -m "chore: add teach loop settings"
```

---

### Task 2: Teach-Loop Types

**Files:**
- Create: `src/genacademy_coach/teach_types.py`
- Test: `tests/test_teach_types.py`

- [ ] **Step 1: Write type tests**

Create `tests/test_teach_types.py`:

```python
from pydantic import ValidationError

from genacademy_coach.teach_types import (
    CheckItem,
    CoachAgentResponse,
    LearnerProfile,
    RetrievedSpan,
)


def test_profile_defaults_are_within_session_only():
    profile = LearnerProfile(style="analogy", track_lens="code_heavy")

    assert profile.style == "analogy"
    assert profile.track_lens == "code_heavy"
    assert profile.known == []
    assert profile.struggled == []
    assert profile.turn_count == 0


def test_agent_response_rejects_unsupported_next_action():
    try:
        CoachAgentResponse(
            learner_message="hello",
            observation="learner asked an unsupported action",
            next_action="invent_answer",
            strategy="analogy",
            citation_ids=[],
        )
    except ValidationError as exc:
        assert "next_action" in str(exc)
    else:
        raise AssertionError("unsupported next_action should fail validation")


def test_retrieved_span_citation_id_is_stable():
    span = RetrievedSpan(
        chunk_id="note/a::0",
        doc_id="note/a",
        text="Attention routes focus.",
        score=0.91,
        title="attention.md",
        source_type="note",
        page_or_section="section-1",
    )

    assert span.citation_id == "note/a::0"


def test_check_item_keeps_expected_keywords_lowercase():
    item = CheckItem(
        question="What does attention do?",
        expected_answer="It focuses relevant context.",
        expected_keywords=["Focus", "Context"],
        citation_id="note/a::0",
    )

    assert item.expected_keywords == ["focus", "context"]


def test_agent_response_rejects_llm_confidence_field():
    try:
        CoachAgentResponse(
            learner_message="hello",
            observation="retrieved one citeable span",
            next_action="drill",
            strategy="analogy",
            citation_ids=[],
            confidence=0.9,
        )
    except ValidationError as exc:
        assert "confidence" in str(exc)
    else:
        raise AssertionError("agent confidence must not be accepted")
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
uv run pytest tests/test_teach_types.py -q
```

Expected: fails because `teach_types.py` does not exist.

- [ ] **Step 3: Implement shared types**

Create `src/genacademy_coach/teach_types.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EvidenceBand = Literal["stop", "confirm", "proceed"]
NextAction = Literal[
    "advance",
    "re_explain_differently",
    "drill",
    "refuse_escalate",
    "stop",
]
Strategy = Literal[
    "analogy",
    "step_by_step",
    "contrastive_example",
    "code_walkthrough",
    "workflow_map",
    "short_drill",
    "refusal",
    "summary",
]


class RetrievedSpan(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    score: float
    title: str
    source_type: str
    page_or_section: str | None = None

    @property
    def citation_id(self) -> str:
        return self.chunk_id


class CheckItem(BaseModel):
    question: str
    expected_answer: str
    expected_keywords: list[str] = Field(min_length=1)
    citation_id: str

    @field_validator("expected_keywords")
    @classmethod
    def normalize_keywords(cls, value: list[str]) -> list[str]:
        return [item.strip().lower() for item in value if item.strip()]


class UnderstandingGrade(BaseModel):
    correct: bool
    matched_keywords: list[str]
    missing_keywords: list[str]
    citation_id: str


class LearnerProfile(BaseModel):
    style: Literal["concise", "analogy", "step_by_step"] = "analogy"
    track_lens: Literal["low_code_no_code", "code_heavy", "bridge"] = "code_heavy"
    bridge_from: str | None = None
    known: list[str] = Field(default_factory=list)
    struggled: list[str] = Field(default_factory=list)
    previous_strategies: list[Strategy] = Field(default_factory=list)
    last_grade_correct: bool | None = None
    turn_count: int = 0


class CoachAgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_message: str
    observation: str
    next_action: NextAction
    strategy: Strategy
    citation_ids: list[str] = Field(default_factory=list)
    check_question: str | None = None


class TraceTurn(BaseModel):
    session_id: str
    turn: int
    learner_input: str
    observation: str
    next_action: NextAction
    strategy: Strategy
    evidence_score: float
    evidence_band: EvidenceBand
    faithfulness_ok: bool | None = None
    retrieved_citation_ids: list[str]
    tool_calls: list[str]
    learner_message: str


class TeachSessionResult(BaseModel):
    session_id: str
    profile: LearnerProfile
    response: CoachAgentResponse
    trace_path: str
```

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_teach_types.py -q
uv run ruff check src/genacademy_coach/teach_types.py tests/test_teach_types.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/teach_types.py tests/test_teach_types.py
git commit -m "feat: define teach loop schemas"
```

---

### Task 3: Grounding and Deterministic Understanding Grade

**Files:**
- Create: `src/genacademy_coach/grounding.py`
- Test: `tests/test_grounding.py`

- [ ] **Step 1: Write grounding tests**

Create `tests/test_grounding.py`:

```python
from genacademy_coach.grounding import (
    answer_grounded_in_spans,
    evidence_band,
    evidence_score,
    grade_understanding,
    require_citeable_spans,
)
from genacademy_coach.teach_types import CheckItem, RetrievedSpan


def span(score: float = 0.9, text: str = "Attention focuses relevant context.") -> RetrievedSpan:
    return RetrievedSpan(
        chunk_id="note/attention::0",
        doc_id="note/attention",
        text=text,
        score=score,
        title="attention.md",
        source_type="note",
    )


def test_evidence_band_uses_configured_thresholds():
    assert evidence_band(0.50, stop_threshold=0.60, confirm_threshold=0.85) == "stop"
    assert evidence_band(0.70, stop_threshold=0.60, confirm_threshold=0.85) == "confirm"
    assert evidence_band(0.91, stop_threshold=0.60, confirm_threshold=0.85) == "proceed"


def test_evidence_score_uses_top_retrieval_score():
    assert evidence_score([span(0.50), span(0.91)]) == 0.91
    assert evidence_score([]) == 0.0


def test_require_citeable_spans_needs_score_and_text():
    assert require_citeable_spans([span(0.91)], stop_threshold=0.60) == [span(0.91)]
    assert require_citeable_spans([span(0.50)], stop_threshold=0.60) == []
    assert require_citeable_spans([span(0.95, text="  ")], stop_threshold=0.60) == []


def test_grade_understanding_is_keyword_based_and_citation_bound():
    item = CheckItem(
        question="What does attention do?",
        expected_answer="It focuses relevant context.",
        expected_keywords=["focuses", "context"],
        citation_id="note/attention::0",
    )

    grade = grade_understanding("It focuses context for the model.", item)

    assert grade.correct is True
    assert grade.matched_keywords == ["focuses", "context"]
    assert grade.missing_keywords == []
    assert grade.citation_id == "note/attention::0"


def test_grade_understanding_matches_multi_word_keywords():
    item = CheckItem(
        question="What does attention do?",
        expected_answer="It focuses relevant context.",
        expected_keywords=["relevant context"],
        citation_id="note/attention::0",
    )

    grade = grade_understanding("It helps focus on relevant context.", item)

    assert grade.correct is True
    assert grade.matched_keywords == ["relevant context"]


def test_grade_understanding_reports_missing_keywords():
    item = CheckItem(
        question="What does attention do?",
        expected_answer="It focuses relevant context.",
        expected_keywords=["focuses", "context"],
        citation_id="note/attention::0",
    )

    grade = grade_understanding("It helps the model.", item)

    assert grade.correct is False
    assert grade.missing_keywords == ["focuses", "context"]


def test_answer_grounded_in_spans_reuses_week2_faithfulness_fallback():
    assert answer_grounded_in_spans("Attention focuses relevant context.", [span()])
    assert not answer_grounded_in_spans("Attention stores long term customer profiles.", [span()])
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
uv run pytest tests/test_grounding.py -q
```

Expected: fails because `grounding.py` does not exist.

- [ ] **Step 3: Implement grounding**

Create `src/genacademy_coach/grounding.py`:

```python
from __future__ import annotations

import re

from genacademy_rag.core.types import Chunk, Citation, RetrievedChunk
from genacademy_rag.eval.faithfulness_eval import citation_grounding_score

from genacademy_coach.teach_types import CheckItem, EvidenceBand, RetrievedSpan, UnderstandingGrade

WORD_RE = re.compile(r"[a-z0-9]+")
CITATION_MARKER_RE = re.compile(r"\[[^\]]+\]")


def normalized_terms(text: str) -> set[str]:
    return set(WORD_RE.findall(text.lower()))


def normalized_phrase(text: str) -> str:
    return " ".join(WORD_RE.findall(text.lower()))


def keyword_present(answer: str, keyword: str) -> bool:
    normalized_answer = f" {normalized_phrase(answer)} "
    normalized_keyword = normalized_phrase(keyword)
    return bool(normalized_keyword) and f" {normalized_keyword} " in normalized_answer


def evidence_score(spans: list[RetrievedSpan]) -> float:
    return max((span.score for span in spans), default=0.0)


def evidence_band(
    score: float,
    *,
    stop_threshold: float,
    confirm_threshold: float,
) -> EvidenceBand:
    if score < stop_threshold:
        return "stop"
    if score < confirm_threshold:
        return "confirm"
    return "proceed"


def require_citeable_spans(
    spans: list[RetrievedSpan],
    *,
    stop_threshold: float,
) -> list[RetrievedSpan]:
    return [
        span
        for span in spans
        if span.score >= stop_threshold and bool(span.text.strip()) and bool(span.citation_id)
    ]


def grade_understanding(answer: str, item: CheckItem) -> UnderstandingGrade:
    matched = [keyword for keyword in item.expected_keywords if keyword_present(answer, keyword)]
    missing = [keyword for keyword in item.expected_keywords if not keyword_present(answer, keyword)]
    return UnderstandingGrade(
        correct=not missing,
        matched_keywords=matched,
        missing_keywords=missing,
        citation_id=item.citation_id,
    )


def _ordinal_from_chunk_id(chunk_id: str) -> int:
    tail = chunk_id.rsplit("::", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def _to_week2_retrieved(span: RetrievedSpan) -> RetrievedChunk:
    citation = Citation(
        doc_id=span.doc_id,
        title=span.title,
        source_type=span.source_type,
        page_or_section=span.page_or_section,
    )
    return RetrievedChunk(
        chunk=Chunk(
            chunk_id=span.chunk_id,
            doc_id=span.doc_id,
            ordinal=_ordinal_from_chunk_id(span.chunk_id),
            text=span.text,
            citation=citation,
        ),
        score=span.score,
    )


def answer_grounded_in_spans(answer: str, spans: list[RetrievedSpan]) -> bool:
    cleaned = CITATION_MARKER_RE.sub("", answer)
    return citation_grounding_score(cleaned, [_to_week2_retrieved(span) for span in spans])
```

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_grounding.py -q
uv run ruff check src/genacademy_coach/grounding.py tests/test_grounding.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/grounding.py tests/test_grounding.py
git commit -m "feat: add grounded understanding checks"
```

---

### Task 4: Trace and Escalation Artifacts

**Files:**
- Create: `src/genacademy_coach/trace.py`
- Create: `src/genacademy_coach/escalation.py`
- Test: `tests/test_trace_and_escalation.py`

- [ ] **Step 1: Write artifact tests**

Create `tests/test_trace_and_escalation.py`:

```python
import json

from genacademy_coach.escalation import append_review_queue
from genacademy_coach.teach_types import TraceTurn
from genacademy_coach.trace import TraceWriter, load_trace


def sample_turn(session_id: str = "session-1") -> TraceTurn:
    return TraceTurn(
        session_id=session_id,
        turn=1,
        learner_input="I do not get attention",
        observation="retrieved citeable span and learner needs first explanation",
        next_action="drill",
        strategy="analogy",
        evidence_score=0.91,
        evidence_band="proceed",
        faithfulness_ok=True,
        retrieved_citation_ids=["note/attention::0"],
        tool_calls=["retrieve_course_corpus", "generate_check_item"],
        learner_message=(
            "Attention is like a spotlight that highlights relevant context. "
            "[note/attention::0]"
        ),
    )


def test_trace_writer_appends_json_turns(tmp_path):
    writer = TraceWriter(tmp_path)
    first = writer.append(sample_turn("abc"))
    second = writer.append(sample_turn("abc"))

    assert first == second
    rows = load_trace(first)
    assert len(rows) == 2
    assert rows[0].next_action == "drill"


def test_append_review_queue_writes_jsonl(tmp_path):
    path = tmp_path / "review_queue.jsonl"

    append_review_queue(
        path,
        session_id="abc",
        topic="attention",
        reason="no supporting span",
        score=0.41,
        citation_ids=[],
    )

    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["session_id"] == "abc"
    assert row["reason"] == "no supporting span"
    assert row["citation_ids"] == []
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
uv run pytest tests/test_trace_and_escalation.py -q
```

Expected: fails because the artifact modules do not exist.

- [ ] **Step 3: Implement trace writer**

Create `src/genacademy_coach/trace.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from genacademy_coach.teach_types import TraceTurn


class TraceWriter:
    def __init__(self, trace_dir: Path):
        self._trace_dir = trace_dir

    def append(self, turn: TraceTurn) -> Path:
        self._trace_dir.mkdir(parents=True, exist_ok=True)
        path = self._trace_dir / f"{turn.session_id}.jsonl"
        payload = turn.model_dump(mode="json")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
        return path


def load_trace(path: Path) -> list[TraceTurn]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(TraceTurn.model_validate_json(line))
    return rows
```

- [ ] **Step 4: Implement escalation writer**

Create `src/genacademy_coach/escalation.py`:

```python
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def append_review_queue(
    path: Path,
    *,
    session_id: str,
    topic: str,
    reason: str,
    score: float | None,
    citation_ids: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "session_id": session_id,
        "topic": topic,
        "reason": reason,
        "score": score,
        "citation_ids": citation_ids,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")
```

- [ ] **Step 5: Run tests**

Run:

```bash
uv run pytest tests/test_trace_and_escalation.py -q
uv run ruff check src/genacademy_coach/trace.py src/genacademy_coach/escalation.py tests/test_trace_and_escalation.py
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/genacademy_coach/trace.py src/genacademy_coach/escalation.py tests/test_trace_and_escalation.py
git commit -m "feat: add trace and escalation artifacts"
```

---

### Task 5: Grounded Check-Item Generation

**Files:**
- Create: `src/genacademy_coach/check_items.py`
- Test: `tests/test_check_items.py`

- [ ] **Step 1: Write check-item tests**

Create `tests/test_check_items.py`:

```python
import json

import pytest

from genacademy_coach.check_items import generate_check_item
from genacademy_coach.teach_types import RetrievedSpan


class FakeProvider:
    def __init__(self, payload: dict[str, object]):
        self.payload = payload
        self.calls = []

    def generate(self, messages: list[dict], **kwargs) -> str:
        self.calls.append((messages, kwargs))
        return json.dumps(self.payload)


def span() -> RetrievedSpan:
    return RetrievedSpan(
        chunk_id="note/attention::0",
        doc_id="note/attention",
        text="Attention lets the model focus on the most relevant context.",
        score=0.91,
        title="attention.md",
        source_type="note",
    )


def test_generate_check_item_uses_week2_provider_json_mode():
    provider = FakeProvider(
        {
            "question": "What does attention help the model do?",
            "expected_answer": "Focus on relevant context.",
            "expected_keywords": ["focus", "context"],
        }
    )

    item = generate_check_item(provider, span())

    assert item.citation_id == "note/attention::0"
    assert item.expected_keywords == ["focus", "context"]
    assert provider.calls[0][1]["json_mode"] is True


def test_generate_check_item_rejects_empty_keywords():
    provider = FakeProvider(
        {
            "question": "What does attention help the model do?",
            "expected_answer": "Focus on relevant context.",
            "expected_keywords": [],
        }
    )

    with pytest.raises(ValueError, match="expected_keywords"):
        generate_check_item(provider, span())
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
uv run pytest tests/test_check_items.py -q
```

Expected: fails because `check_items.py` does not exist.

- [ ] **Step 3: Implement check-item generation**

Create `src/genacademy_coach/check_items.py`:

```python
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from genacademy_coach.teach_types import CheckItem, RetrievedSpan

SYSTEM_PROMPT = "You write short grounded understanding checks. Reply only with JSON."
USER_TEMPLATE = """Use only the cited course span below.

Citation ID: {citation_id}
Title: {title}
Span:
{span_text}

Create one short free-answer check question. Return exactly this JSON object shape:
{{
  "question": "What does attention help the model do?",
  "expected_answer": "It helps the model focus on relevant context.",
  "expected_keywords": ["focus", "context"]
}}

Use 2-4 expected_keywords. Each keyword must be a literal term or short phrase supported by the span.
"""


class RawCheckItem(BaseModel):
    question: str
    expected_answer: str
    expected_keywords: list[str] = Field(min_length=1)


def generate_check_item(provider: Any, span: RetrievedSpan) -> CheckItem:
    raw = provider.generate(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_TEMPLATE.format(
                    citation_id=span.citation_id,
                    title=span.title,
                    span_text=span.text,
                ),
            },
        ],
        json_mode=True,
        max_tokens=256,
        temperature=0.0,
    )
    parsed = RawCheckItem.model_validate(json.loads(raw))
    return CheckItem(
        question=parsed.question,
        expected_answer=parsed.expected_answer,
        expected_keywords=parsed.expected_keywords,
        citation_id=span.citation_id,
    )
```

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_check_items.py -q
uv run ruff check src/genacademy_coach/check_items.py tests/test_check_items.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/check_items.py tests/test_check_items.py
git commit -m "feat: generate grounded check items"
```

---

### Task 6: Teach Runtime Tools

**Files:**
- Create: `src/genacademy_coach/teach_tools.py`
- Test: `tests/test_teach_tools.py`

- [ ] **Step 1: Write tool tests**

Create `tests/test_teach_tools.py`:

```python
import json
from pathlib import Path

from genacademy_coach.teach_tools import TeachRuntime, build_teach_tools
from genacademy_coach.teach_types import CheckItem, LearnerProfile


class FakeFoundation:
    provider = object()

    def retrieve(self, query: str):
        assert query == "attention"
        return [
            {
                "chunk_id": "note/attention::0",
                "doc_id": "note/attention",
                "text": "Attention focuses relevant context.",
                "score": 0.91,
                "title": "attention.md",
                "source_type": "note",
                "page_or_section": None,
            }
        ]


def test_retrieve_tool_records_last_spans(tmp_path):
    runtime = TeachRuntime(
        session_id="abc",
        topic="attention",
        profile=LearnerProfile(),
        foundation=FakeFoundation(),
        stop_threshold=0.60,
        confirm_threshold=0.85,
        review_queue_path=tmp_path / "review_queue.jsonl",
    )
    tools = build_teach_tools(runtime)
    retrieve_tool = next(tool for tool in tools if tool.name == "retrieve_course_corpus")

    payload = retrieve_tool.invoke({"query": "attention"})
    rows = json.loads(payload)

    assert rows[0]["citation_id"] == "note/attention::0"
    assert runtime.last_spans[0].score == 0.91


def test_grade_tool_uses_current_check_item(tmp_path):
    runtime = TeachRuntime(
        session_id="abc",
        topic="attention",
        profile=LearnerProfile(),
        foundation=FakeFoundation(),
        stop_threshold=0.60,
        confirm_threshold=0.85,
        review_queue_path=tmp_path / "review_queue.jsonl",
    )
    runtime.current_check = CheckItem(
        question="What does attention do?",
        expected_answer="Focuses context.",
        expected_keywords=["focuses", "context"],
        citation_id="note/attention::0",
    )
    grade_tool = next(tool for tool in build_teach_tools(runtime) if tool.name == "grade_understanding")

    payload = grade_tool.invoke({"answer": "It focuses context."})
    row = json.loads(payload)

    assert row["correct"] is True
    assert runtime.last_grade is not None
    assert runtime.last_grade.correct is True


def test_escalation_tool_writes_review_queue(tmp_path):
    runtime = TeachRuntime(
        session_id="abc",
        topic="attention",
        profile=LearnerProfile(),
        foundation=FakeFoundation(),
        stop_threshold=0.60,
        confirm_threshold=0.85,
        review_queue_path=tmp_path / "review_queue.jsonl",
    )
    escalate_tool = next(tool for tool in build_teach_tools(runtime) if tool.name == "escalate_to_mentor")

    runtime.last_spans = []
    payload = escalate_tool.invoke({"reason": "no supporting span"})

    assert json.loads(payload)["queued"] is True
    assert "no supporting span" in (tmp_path / "review_queue.jsonl").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
uv run pytest tests/test_teach_tools.py -q
```

Expected: fails because `teach_tools.py` does not exist.

- [ ] **Step 3: Implement tool runtime**

Create `src/genacademy_coach/teach_tools.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain.tools import tool

from genacademy_coach.check_items import generate_check_item
from genacademy_coach.escalation import append_review_queue
from genacademy_coach.grounding import (
    evidence_band,
    evidence_score,
    grade_understanding as grade_answer_understanding,
    require_citeable_spans,
)
from genacademy_coach.teach_types import (
    CheckItem,
    LearnerProfile,
    RetrievedSpan,
    UnderstandingGrade,
)


@dataclass
class TeachRuntime:
    session_id: str
    topic: str
    profile: LearnerProfile
    foundation: Any
    stop_threshold: float
    confirm_threshold: float
    review_queue_path: Path
    last_spans: list[RetrievedSpan] = field(default_factory=list)
    current_check: CheckItem | None = None
    last_grade: UnderstandingGrade | None = None
    tool_calls: list[str] = field(default_factory=list)

    def record_tool(self, name: str) -> None:
        self.tool_calls.append(name)

    def current_evidence_score(self) -> float:
        return evidence_score(self.last_spans)

    def current_evidence_band(self) -> str:
        return evidence_band(
            self.current_evidence_score(),
            stop_threshold=self.stop_threshold,
            confirm_threshold=self.confirm_threshold,
        )


def _span_from_row(row: dict[str, Any]) -> RetrievedSpan:
    return RetrievedSpan(
        chunk_id=str(row["chunk_id"]),
        doc_id=str(row["doc_id"]),
        text=str(row["text"]),
        score=float(row["score"]),
        title=str(row["title"]),
        source_type=str(row["source_type"]),
        page_or_section=row.get("page_or_section"),
    )


def build_teach_tools(runtime: TeachRuntime):
    @tool
    def retrieve_course_corpus(query: str) -> str:
        """Retrieve citeable Gen Academy course spans for the learner's current topic."""
        runtime.record_tool("retrieve_course_corpus")
        spans = [_span_from_row(row) for row in runtime.foundation.retrieve(query)]
        runtime.last_spans = require_citeable_spans(
            spans,
            stop_threshold=runtime.stop_threshold,
        )
        rows = [
            {
                "citation_id": span.citation_id,
                "title": span.title,
                "source_type": span.source_type,
                "score": span.score,
                "evidence_band": runtime.current_evidence_band(),
                "text": span.text,
            }
            for span in runtime.last_spans
        ]
        return json.dumps(rows, sort_keys=True)

    @tool
    def generate_check_item_for_span(citation_id: str) -> str:
        """Generate a short grounded check question for a retrieved citation ID."""
        runtime.record_tool("generate_check_item")
        span_by_id = {span.citation_id: span for span in runtime.last_spans}
        if citation_id not in span_by_id:
            return json.dumps({"error": f"unknown citation_id: {citation_id}"})
        runtime.current_check = generate_check_item(runtime.foundation.provider, span_by_id[citation_id])
        return runtime.current_check.model_dump_json()

    @tool
    def grade_understanding(answer: str) -> str:
        """Grade the learner answer against the current grounded check item."""
        runtime.record_tool("grade_understanding")
        if runtime.current_check is None:
            return json.dumps({"error": "no current check item"})
        runtime.last_grade = grade_answer_understanding(answer, runtime.current_check)
        runtime.profile.last_grade_correct = runtime.last_grade.correct
        return runtime.last_grade.model_dump_json()

    @tool
    def update_profile(known: list[str], struggled: list[str]) -> str:
        """Update the within-session learner profile with concepts known or struggled with."""
        runtime.record_tool("update_profile")
        runtime.profile.known = sorted(set([*runtime.profile.known, *known]))
        runtime.profile.struggled = sorted(set([*runtime.profile.struggled, *struggled]))
        return runtime.profile.model_dump_json()

    @tool
    def escalate_to_mentor(reason: str) -> str:
        """Queue a mentor review when the tutor cannot cite a safe answer."""
        runtime.record_tool("escalate_to_mentor")
        append_review_queue(
            runtime.review_queue_path,
            session_id=runtime.session_id,
            topic=runtime.topic,
            reason=reason,
            score=runtime.current_evidence_score(),
            citation_ids=[span.citation_id for span in runtime.last_spans],
        )
        return json.dumps({"queued": True, "reason": reason}, sort_keys=True)

    return [
        retrieve_course_corpus,
        generate_check_item_for_span,
        grade_understanding,
        update_profile,
        escalate_to_mentor,
    ]
```

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_teach_tools.py -q
uv run ruff check src/genacademy_coach/teach_tools.py tests/test_teach_tools.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/teach_tools.py tests/test_teach_tools.py
git commit -m "feat: expose teach loop tools"
```

---

### Task 7: LangChain Agent Boundary

**Files:**
- Create: `src/genacademy_coach/teach_agent.py`
- Test: `tests/test_teach_agent.py`
- Modify: `tests/test_guardrails.py`

- [ ] **Step 1: Write agent-boundary tests**

Create `tests/test_teach_agent.py`:

```python
from genacademy_coach.teach_agent import SYSTEM_PROMPT, build_langchain_model


class FakeRagSettings:
    gen_model = "Qwen/Qwen3-30B-A3B-Instruct-2507"
    gen_api_key = "secret"
    gen_base_url = "https://api.tokenfactory.nebius.com/v1/"


class FakeFoundation:
    rag_settings = FakeRagSettings()


def test_system_prompt_requires_grounding_and_trace_action():
    assert "retrieved citation" in SYSTEM_PROMPT
    assert "next_action" in SYSTEM_PROMPT
    assert "do not answer from model priors" in SYSTEM_PROMPT.lower()
    assert "evidence score" in SYSTEM_PROMPT.lower()
    assert "do not return confidence" in SYSTEM_PROMPT.lower()


def test_build_langchain_model_uses_week2_generation_settings():
    model = build_langchain_model(FakeFoundation())

    assert model.model_name == "Qwen/Qwen3-30B-A3B-Instruct-2507"
    assert str(model.openai_api_base).rstrip("/") == "https://api.tokenfactory.nebius.com/v1"


def test_build_langchain_model_falls_back_when_week2_model_is_empty():
    class EmptyModelRagSettings(FakeRagSettings):
        gen_model = ""

    class EmptyModelFoundation:
        rag_settings = EmptyModelRagSettings()

    model = build_langchain_model(EmptyModelFoundation())

    assert model.model_name == "Qwen/Qwen3-30B-A3B-Instruct-2507"
```

Modify `tests/test_guardrails.py` to keep direct LangGraph imports blocked:

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


def test_teach_agent_uses_create_agent_boundary():
    text = Path("src/genacademy_coach/teach_agent.py").read_text(encoding="utf-8")

    assert "from langchain.agents import create_agent" in text
    assert "create_agent(" in text
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
uv run pytest tests/test_teach_agent.py tests/test_guardrails.py -q
```

Expected: fails because `teach_agent.py` does not exist.

- [ ] **Step 3: Implement LangChain boundary**

Create `src/genacademy_coach/teach_agent.py`:

```python
from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI

from genacademy_coach.teach_tools import TeachRuntime, build_teach_tools
from genacademy_coach.teach_types import CoachAgentResponse

DEFAULT_NEBIUS_MODEL = "Qwen/Qwen3-30B-A3B-Instruct-2507"

SYSTEM_PROMPT = """You are GenAcademy Coach, an adaptive grounded course tutor.

Rules:
- Use retrieve_course_corpus before teaching any course concept.
- Teach only from retrieved citation text.
- Every learner-visible factual claim must be supported by a retrieved citation.
- If no retrieved citation supports the topic, call escalate_to_mentor and refuse.
- Do not answer from model priors.
- Generate or use one grounded check question before grading understanding.
- Treat tool-returned retrieval scores as the only evidence score. Do not return confidence.
- Choose next_action at runtime from: advance, re_explain_differently, drill, refuse_escalate, stop.
- Choose a strategy that is different from the failed previous explanation when the learner stumbles.
- Explain the observation that drove the decision: retrieval result, learner answer grade, prior
  strategy, and profile state.
- Return structured output with learner_message, observation, next_action, strategy, citation_ids, and
  optional check_question.
"""


def build_langchain_model(foundation: Any) -> ChatOpenAI:
    settings = foundation.rag_settings
    model_name = settings.gen_model or DEFAULT_NEBIUS_MODEL
    return ChatOpenAI(
        model=model_name,
        temperature=0,
        max_tokens=700,
        timeout=60,
        max_retries=2,
        api_key=settings.gen_api_key or "not-needed",
        base_url=settings.gen_base_url,
    )


def build_coach_agent(runtime: TeachRuntime, *, model: Any | None = None):
    active_model = model or build_langchain_model(runtime.foundation)
    return create_agent(
        model=active_model,
        tools=build_teach_tools(runtime),
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(CoachAgentResponse),
    )
```

Implementation delta to keep in the PR description: Week-2
`provider.generate(messages, json_mode=True, max_tokens=256, temperature=0.0)` is still reused for
grounded check-item generation and all embedding/retrieval machinery. The LangChain agent model uses the
same Week-2 `RagSettings.gen_model`, `gen_base_url`, and `gen_api_key` because `create_agent` requires a
LangChain chat model object for tool calling and structured output; this is not a new Coach provider
wrapper.

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_teach_agent.py tests/test_guardrails.py -q
uv run ruff check src/genacademy_coach/teach_agent.py tests/test_teach_agent.py tests/test_guardrails.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/teach_agent.py tests/test_teach_agent.py tests/test_guardrails.py
git commit -m "feat: add langchain teach agent boundary"
```

---

### Task 8: Session Runner

**Files:**
- Create: `src/genacademy_coach/teach_session.py`
- Test: `tests/test_teach_session.py`

- [ ] **Step 1: Write session-runner tests**

Create `tests/test_teach_session.py`:

```python
from pathlib import Path

from genacademy_coach.teach_session import AgentResponseError, CoachSession, StaticAgentPort
from genacademy_coach.teach_types import CheckItem, CoachAgentResponse, LearnerProfile, RetrievedSpan
from genacademy_coach.trace import load_trace


class FakeSettings:
    trace_dir: Path
    review_queue_path: Path
    stop_threshold = 0.60
    confirm_threshold = 0.85

    def __init__(self, root: Path, max_teach_turns: int = 4):
        self.trace_dir = root / "traces"
        self.review_queue_path = root / "review_queue.jsonl"
        self.max_teach_turns = max_teach_turns


class FakeFoundation:
    provider = object()

    def retrieve(self, query: str):
        return []


def cited_span() -> RetrievedSpan:
    return RetrievedSpan(
        chunk_id="note/attention::0",
        doc_id="note/attention",
        text="Attention highlights relevant context.",
        score=0.91,
        title="attention.md",
        source_type="note",
    )


def test_session_start_writes_trace_with_retrieval_evidence(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention is like a spotlight. [note/attention::0]",
            observation="retrieved a citeable attention span and learner needs an explanation",
            next_action="drill",
            strategy="analogy",
            citation_ids=["note/attention::0"],
            check_question="What does attention help with?",
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]

    result = session.start()

    assert result.response.next_action == "drill"
    assert (tmp_path / "traces" / "abc.jsonl").exists()
    assert result.profile.turn_count == 1
    rows = load_trace(Path(result.trace_path))
    assert rows[0].evidence_score == 0.91
    assert rows[0].evidence_band == "proceed"


def test_session_rejects_citation_id_not_seen_in_retrieval(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention is useful. [note/made-up::0]",
            observation="agent cited an id that was not retrieved",
            next_action="advance",
            strategy="summary",
            citation_ids=["note/made-up::0"],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]

    result = session.start()

    assert result.response.next_action == "refuse_escalate"
    assert "could not verify" in result.response.learner_message.lower()


def test_session_rejects_uncited_agent_answer(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention is useful.",
            observation="agent answered without retrieved citations",
            next_action="advance",
            strategy="summary",
            citation_ids=[],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )

    result = session.start()

    assert result.response.next_action == "refuse_escalate"
    assert "could not verify" in result.response.learner_message.lower()
    assert (tmp_path / "review_queue.jsonl").exists()


def test_session_uses_current_check_question_not_agent_desync(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention highlights relevant context. [note/attention::0]",
            observation="agent displayed a different check question than the grounded tool item",
            next_action="drill",
            strategy="analogy",
            citation_ids=["note/attention::0"],
            check_question="Made up check?",
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]
    session.runtime.current_check = CheckItem(
        question="What does attention help with?",
        expected_answer="It helps focus relevant context.",
        expected_keywords=["relevant context"],
        citation_id="note/attention::0",
    )

    result = session.start()

    assert result.response.check_question == "What does attention help with?"


def test_session_rejects_re_explain_with_same_strategy(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Trying the same analogy again. [note/attention::0]",
            observation="learner stumbled but strategy did not change",
            next_action="re_explain_differently",
            strategy="analogy",
            citation_ids=["note/attention::0"],
        )
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(previous_strategies=["analogy"]),
        agent_port=agent,
    )
    session.runtime.last_spans = [cited_span()]

    result = session.respond("It just memorizes tokens.")

    assert result.response.next_action == "refuse_escalate"
    assert "different strategy" in result.response.learner_message.lower()


def test_session_refuses_when_agent_port_fails_structured_output(tmp_path):
    class FailingAgent:
        def invoke(self, messages):
            raise AgentResponseError("missing structured_response")

    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=FailingAgent(),
    )

    result = session.start()

    assert result.response.next_action == "refuse_escalate"
    assert "structured output" in result.response.learner_message.lower()


def test_session_stops_at_turn_budget_without_agent_call(tmp_path):
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path, max_teach_turns=0),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=StaticAgentPort(
            CoachAgentResponse(
                learner_message="should not be used",
                observation="should not be used",
                next_action="advance",
                strategy="summary",
                citation_ids=[],
            )
        ),
    )

    result = session.start()

    assert result.response.next_action == "stop"
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
uv run pytest tests/test_teach_session.py -q
```

Expected: fails because `teach_session.py` does not exist.

- [ ] **Step 3: Implement session runner**

Create `src/genacademy_coach/teach_session.py`:

```python
from __future__ import annotations

from typing import Any, Protocol

from pydantic import ValidationError

from genacademy_coach.escalation import append_review_queue
from genacademy_coach.grounding import answer_grounded_in_spans
from genacademy_coach.teach_agent import build_coach_agent
from genacademy_coach.teach_tools import TeachRuntime
from genacademy_coach.teach_types import (
    CoachAgentResponse,
    LearnerProfile,
    TeachSessionResult,
    TraceTurn,
)
from genacademy_coach.trace import TraceWriter


class AgentResponseError(RuntimeError):
    pass


class AgentPort(Protocol):
    def invoke(self, messages: list[dict[str, str]]) -> CoachAgentResponse: ...


class StaticAgentPort:
    def __init__(self, *responses: CoachAgentResponse):
        self._responses = list(responses)
        self._initial_count = len(self._responses)

    def invoke(self, messages: list[dict[str, str]]) -> CoachAgentResponse:
        if not self._responses:
            raise AgentResponseError(
                f"static agent responses exhausted after {self._initial_count} configured turns"
            )
        return self._responses.pop(0)


class LangChainAgentPort:
    def __init__(self, runtime: TeachRuntime, *, model: Any | None = None):
        self._agent = build_coach_agent(runtime, model=model)

    def invoke(self, messages: list[dict[str, str]]) -> CoachAgentResponse:
        result = self._agent.invoke({"messages": messages})
        structured = result.get("structured_response")
        if structured is None:
            raise AgentResponseError("missing structured_response")
        try:
            return CoachAgentResponse.model_validate(structured)
        except ValidationError as exc:
            raise AgentResponseError("invalid structured_response") from exc


class CoachSession:
    def __init__(
        self,
        *,
        session_id: str,
        topic: str,
        settings: Any,
        foundation: Any,
        profile: LearnerProfile,
        agent_port: AgentPort | None = None,
    ):
        self.session_id = session_id
        self.topic = topic
        self.settings = settings
        self.foundation = foundation
        self.profile = profile
        self.runtime = TeachRuntime(
            session_id=session_id,
            topic=topic,
            profile=profile,
            foundation=foundation,
            stop_threshold=settings.stop_threshold,
            confirm_threshold=settings.confirm_threshold,
            review_queue_path=settings.review_queue_path,
        )
        self.agent_port = agent_port or LangChainAgentPort(self.runtime)
        self.trace_writer = TraceWriter(settings.trace_dir)

    def start(self) -> TeachSessionResult:
        return self._invoke_agent(f"Teach me this Gen Academy concept: {self.topic}")

    def respond(self, learner_answer: str) -> TeachSessionResult:
        return self._invoke_agent(f"Learner answer to current check: {learner_answer}")

    def _invoke_agent(self, learner_input: str) -> TeachSessionResult:
        if self.profile.turn_count >= self.settings.max_teach_turns:
            return self._write_result(
                learner_input,
                CoachAgentResponse(
                    learner_message="We have reached the turn limit for this teach loop.",
                    observation="turn budget reached before invoking the agent",
                    next_action="stop",
                    strategy="summary",
                    citation_ids=[],
                ),
            )

        previous_strategy = (
            self.profile.previous_strategies[-1] if self.profile.previous_strategies else None
        )
        self.profile.turn_count += 1
        current_check = (
            self.runtime.current_check.model_dump_json()
            if self.runtime.current_check is not None
            else "none"
        )
        last_grade = (
            self.runtime.last_grade.model_dump_json()
            if self.runtime.last_grade is not None
            else "none"
        )
        try:
            response = self.agent_port.invoke(
                [
                    {
                        "role": "user",
                        "content": (
                            f"Session topic: {self.topic}\n"
                            f"Profile: {self.profile.model_dump_json()}\n"
                            f"Previous strategy: {previous_strategy}\n"
                            f"Current check: {current_check}\n"
                            f"Last grade: {last_grade}\n"
                            f"Learner input: {learner_input}"
                        ),
                    }
                ]
            )
        except AgentResponseError:
            response = self._refusal_response(
                "agent failed to return structured output",
                "I could not get a valid structured output from the tutor agent, so I am "
                "escalating this instead of guessing.",
            )
        response = self._enforce_grounding(response, previous_strategy=previous_strategy)
        if response.next_action not in {"refuse_escalate", "stop"}:
            self.profile.previous_strategies.append(response.strategy)
        return self._write_result(learner_input, response)

    def _write_result(
        self,
        learner_input: str,
        response: CoachAgentResponse,
    ) -> TeachSessionResult:
        cited_spans = [
            span for span in self.runtime.last_spans if span.citation_id in response.citation_ids
        ]
        faithfulness_ok = (
            None
            if response.next_action in {"refuse_escalate", "stop"} or not cited_spans
            else answer_grounded_in_spans(response.learner_message, cited_spans)
        )
        trace_path = self.trace_writer.append(
            TraceTurn(
                session_id=self.session_id,
                turn=self.profile.turn_count,
                learner_input=learner_input,
                observation=response.observation,
                next_action=response.next_action,
                strategy=response.strategy,
                evidence_score=self.runtime.current_evidence_score(),
                evidence_band=self.runtime.current_evidence_band(),
                faithfulness_ok=faithfulness_ok,
                retrieved_citation_ids=[span.citation_id for span in self.runtime.last_spans],
                tool_calls=list(self.runtime.tool_calls),
                learner_message=response.learner_message,
            )
        )
        self.runtime.tool_calls.clear()
        return TeachSessionResult(
            session_id=self.session_id,
            profile=self.profile,
            response=response,
            trace_path=str(trace_path),
        )

    def _enforce_grounding(
        self,
        response: CoachAgentResponse,
        *,
        previous_strategy: str | None,
    ) -> CoachAgentResponse:
        if response.next_action in {"refuse_escalate", "stop"}:
            return response
        if (
            response.next_action == "re_explain_differently"
            and previous_strategy is not None
            and response.strategy == previous_strategy
        ):
            return self._refusal_response(
                "agent chose re_explain_differently without changing strategy",
                "I could not produce a different strategy for the re-explanation, so I am "
                "escalating this instead of repeating the same approach.",
            )
        if self.runtime.current_check is not None:
            response = response.model_copy(
                update={"check_question": self.runtime.current_check.question}
            )
        elif response.check_question is not None:
            return self._refusal_response(
                "agent displayed a check question that was not generated by the grounded tool",
                "I could not verify the check question against a retrieved course span, so I am "
                "escalating this instead of asking it.",
            )
        retrieved_ids = {span.citation_id for span in self.runtime.last_spans}
        if response.citation_ids and set(response.citation_ids).issubset(retrieved_ids):
            return response
        return self._refusal_response(
            "agent response had no retrieved citation_ids",
            "I could not verify that answer against a retrieved course citation, so I am "
            "escalating this to a mentor instead of guessing.",
            citation_ids=response.citation_ids,
        )

    def _refusal_response(
        self,
        reason: str,
        learner_message: str,
        *,
        citation_ids: list[str] | None = None,
    ) -> CoachAgentResponse:
        cited = citation_ids or []
        append_review_queue(
            self.settings.review_queue_path,
            session_id=self.session_id,
            topic=self.topic,
            reason=reason,
            score=self.runtime.current_evidence_score(),
            citation_ids=cited,
        )
        return CoachAgentResponse(
            learner_message=learner_message,
            observation=reason,
            next_action="refuse_escalate",
            strategy="refusal",
            citation_ids=[],
        )
```

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_teach_session.py -q
uv run ruff check src/genacademy_coach/teach_session.py tests/test_teach_session.py
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/teach_session.py tests/test_teach_session.py
git commit -m "feat: run grounded teach sessions"
```

---

### Task 9: Demo and Trace CLIs

**Files:**
- Create: `scripts/run_teach_demo.py`
- Create: `scripts/print_trace.py`
- Test: `tests/test_teach_cli.py`

- [ ] **Step 1: Write CLI tests**

Create `tests/test_teach_cli.py`:

```python
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
    assert "note/a::0" in out
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
uv run pytest tests/test_teach_cli.py -q
```

Expected: fails because CLI scripts do not exist.

- [ ] **Step 3: Implement trace printer**

Create `scripts/print_trace.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path


def print_trace(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        citations = ", ".join(row.get("retrieved_citation_ids", [])) or "none"
        print(
            f"turn {row['turn']}: {row['next_action']} / {row['strategy']} "
            f"evidence={row['evidence_score']:.2f} {row['evidence_band']} citations={citations}"
        )
        print(f"  {row['learner_message']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace_path", type=Path)
    args = parser.parse_args()
    print_trace(args.trace_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Implement demo runner**

Create `scripts/run_teach_demo.py`:

```python
from __future__ import annotations

import argparse
import uuid

from genacademy_coach.foundation import Foundation
from genacademy_coach.settings import CoachSettings
from genacademy_coach.teach_session import CoachSession
from genacademy_coach.teach_types import LearnerProfile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--style", default="analogy", choices=["concise", "analogy", "step_by_step"])
    parser.add_argument(
        "--track-lens",
        default="code_heavy",
        choices=["low_code_no_code", "code_heavy", "bridge"],
    )
    parser.add_argument("--learner-answer")
    parser.add_argument("--session-id", default=None)
    args = parser.parse_args()

    settings = CoachSettings.from_env()
    foundation = Foundation.build(settings)
    session = CoachSession(
        session_id=args.session_id or uuid.uuid4().hex[:12],
        topic=args.topic,
        settings=settings,
        foundation=foundation,
        profile=LearnerProfile(style=args.style, track_lens=args.track_lens),
    )
    first = session.start()
    print(first.response.learner_message)
    if first.response.check_question:
        print(f"\nCheck: {first.response.check_question}")
    if args.learner_answer:
        second = session.respond(args.learner_answer)
        print("\nAfter learner answer:")
        print(second.response.learner_message)
    print(f"\ntrace={first.trace_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests**

Run:

```bash
uv run pytest tests/test_teach_cli.py -q
uv run ruff check scripts/run_teach_demo.py scripts/print_trace.py tests/test_teach_cli.py
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/run_teach_demo.py scripts/print_trace.py tests/test_teach_cli.py
git commit -m "feat: add teach loop demo cli"
```

---

### Task 10: Local Teach-Loop Eval Runner

**Files:**
- Create: `src/genacademy_coach/eval_io.py`
- Modify: `scripts/check_eval_leak.py`
- Create: `scripts/eval_teach_loop.py`
- Test: `tests/test_eval_teach_loop.py`

- [ ] **Step 1: Write eval runner test**

Create `tests/test_eval_teach_loop.py`:

```python
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

from genacademy_coach.teach_types import (
    CheckItem,
    CoachAgentResponse,
    RetrievedSpan,
    UnderstandingGrade,
)


def load_eval_module():
    script_path = Path("scripts/eval_teach_loop.py").resolve()
    spec = importlib.util.spec_from_file_location("eval_teach_loop", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_manifest_items_filters_split(tmp_path):
    manifest = {
        "items": [
            {"id": "a", "split": "dev", "source_file": "a.md"},
            {"id": "b", "split": "test", "source_file": "b.md"},
        ]
    }
    path = tmp_path / "split_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    module = load_eval_module()

    rows = module.load_manifest_items(path, split="dev")

    assert rows == [{"id": "a", "split": "dev", "source_file": "a.md"}]


def test_question_text_for_item_reads_private_source_at_runtime(tmp_path):
    module = load_eval_module()
    eval_dir = tmp_path / "corpus" / "eval-questions"
    eval_dir.mkdir(parents=True)
    (eval_dir / "question.md").write_text(
        "\n\n1. What is attention?\n\n2. Why use citations?\n\n",
        encoding="utf-8",
    )

    rows = module.question_records_for_item(
        eval_dir,
        {"id": "item-a", "split": "dev", "source_file": "question.md"},
    )

    assert [row["scenario_id"] for row in rows] == ["item-a:000", "item-a:001"]
    assert [row["question_text"] for row in rows] == [
        "What is attention?",
        "Why use citations?",
    ]


def test_score_scenario_runs_teach_loop_instead_of_retrieval_only(tmp_path):
    module = load_eval_module()
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        '{"session_id": "item-a-000", "turn": 1, "learner_input": "teach", '
        '"observation": "retrieved span", "next_action": "drill", "strategy": "analogy", '
        '"evidence_score": 0.91, "evidence_band": "proceed", '
        '"retrieved_citation_ids": ["note/attention::0"], "tool_calls": [], '
        '"learner_message": "first"}\n'
        '{"session_id": "item-a-000", "turn": 2, "learner_input": "wrong", '
        '"observation": "learner confused attention", '
        '"next_action": "re_explain_differently", '
        '"strategy": "contrastive_example", "evidence_score": 0.91, '
        '"evidence_band": "proceed", '
        '"retrieved_citation_ids": ["note/attention::0"], "tool_calls": [], '
        '"learner_message": "second"}\n',
        encoding="utf-8",
    )
    calls = []

    class FakeSession:
        def __init__(self, **kwargs):
            self.runtime = SimpleNamespace(
                last_spans=[
                    RetrievedSpan(
                        chunk_id="note/attention::0",
                        doc_id="note/attention",
                        text="Attention focuses relevant context.",
                        score=0.91,
                        title="attention.md",
                        source_type="note",
                    )
                ],
                current_check=CheckItem(
                    question="What does attention do?",
                    expected_answer="It focuses relevant context.",
                    expected_keywords=["relevant context"],
                    citation_id="note/attention::0",
                ),
                last_grade=UnderstandingGrade(
                    correct=True,
                    matched_keywords=["relevant context"],
                    missing_keywords=[],
                    citation_id="note/attention::0",
                ),
            )

        def start(self):
            calls.append("start")
            return SimpleNamespace(
                response=CoachAgentResponse(
                    learner_message="Attention focuses context. [note/attention::0]",
                    observation="retrieved span",
                    next_action="drill",
                    strategy="analogy",
                    citation_ids=["note/attention::0"],
                    check_question="What does attention do?",
                ),
                trace_path=str(trace_path),
            )

        def respond(self, learner_answer):
            calls.append(learner_answer)
            action = "re_explain_differently" if len(calls) == 2 else "advance"
            strategy = "contrastive_example" if len(calls) == 2 else "summary"
            return SimpleNamespace(
                response=CoachAgentResponse(
                    learner_message="Grounded. [note/attention::0]",
                    observation="graded answer",
                    next_action=action,
                    strategy=strategy,
                    citation_ids=["note/attention::0"],
                ),
                trace_path=str(trace_path),
            )

    result = module.score_scenario(
        settings=SimpleNamespace(
            trace_dir=tmp_path / "traces",
            stop_threshold=0.60,
            confirm_threshold=0.85,
            review_queue_path=tmp_path / "review_queue.jsonl",
            max_teach_turns=4,
        ),
        foundation=object(),
        scenario={
            "scenario_id": "item-a:000",
            "item_id": "item-a",
            "split": "dev",
            "source_file": "question.md",
            "question_text": "What is attention?",
        },
        session_factory=FakeSession,
    )

    assert calls[0] == "start"
    assert result["passed"] is True
    assert result["scenario_id"] == "item-a:000"
    assert "question_text" not in result
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
uv run pytest tests/test_eval_teach_loop.py -q
```

Expected: fails because `eval_io.py` and `scripts/eval_teach_loop.py` do not exist.

- [ ] **Step 3: Move private eval text loading into core helper**

Create `src/genacademy_coach/eval_io.py`:

```python
from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


def read_eval_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".docx":
        doc = DocxDocument(path)
        paragraphs = [p.text for p in doc.paragraphs]
        table_cells = [
            cell.text for table in doc.tables for row in table.rows for cell in row.cells
        ]
        return "\n".join([*paragraphs, *table_cells])
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return ""
```

Modify `scripts/check_eval_leak.py` imports:

```python
import json
from collections.abc import Iterator
from pathlib import Path

from genacademy_coach.corpus import iter_indexable_files, load_corpus_document
from genacademy_coach.eval_io import read_eval_text
from genacademy_coach.eval_split import normalized_words, phrase_hashes
from genacademy_coach.settings import CoachSettings
```

Delete the old local `read_eval_text()` function and the now-unused `docx` / `pypdf` imports from
`scripts/check_eval_leak.py`.

- [ ] **Step 4: Implement local teach-loop eval runner**

Create `scripts/eval_teach_loop.py`:

```python
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from genacademy_coach.eval_io import read_eval_text
from genacademy_coach.foundation import Foundation
from genacademy_coach.settings import CoachSettings
from genacademy_coach.teach_session import CoachSession
from genacademy_coach.teach_types import LearnerProfile
from genacademy_coach.trace import load_trace

QUESTION_PREFIX_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s*")
DEFAULT_WRONG_ANSWER = "I am not sure; I think it just memorizes previous tokens."


def load_manifest_items(manifest_path: Path, *, split: str) -> list[dict[str, str]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [item for item in manifest["items"] if item["split"] == split]


def extract_questions(text: str) -> list[str]:
    rows = []
    for line in text.splitlines():
        cleaned = QUESTION_PREFIX_RE.sub("", line).strip()
        if "?" in cleaned:
            rows.append(cleaned[:500])
    if rows:
        return rows
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return [cleaned[:500]]
    return []


def question_records_for_item(
    eval_questions_dir: Path,
    item: dict[str, str],
) -> list[dict[str, str]]:
    source_path = eval_questions_dir / item["source_file"]
    questions = extract_questions(read_eval_text(source_path))
    if not questions:
        questions = [source_path.stem.replace("-", " ")]
    return [
        {
            "scenario_id": f"{item['id']}:{idx:03d}",
            "item_id": item["id"],
            "source_file": item["source_file"],
            "split": item["split"],
            "question_text": question,
        }
        for idx, question in enumerate(questions)
    ]


def load_scenarios(settings: CoachSettings, *, split: str, limit: int) -> list[dict[str, str]]:
    scenarios = []
    for item in load_manifest_items(settings.eval_manifest_path, split=split):
        scenarios.extend(question_records_for_item(settings.eval_questions_dir, item))
    return scenarios[:limit]


def _trace_has_runtime_decision(trace_path: Path) -> bool:
    rows = load_trace(trace_path)
    return any(row.next_action == "re_explain_differently" for row in rows)


def score_scenario(
    *,
    settings: CoachSettings,
    foundation: Foundation,
    scenario: dict[str, str],
    session_factory: Any = CoachSession,
    wrong_answer: str = DEFAULT_WRONG_ANSWER,
) -> dict[str, Any]:
    session = session_factory(
        session_id=scenario["scenario_id"].replace(":", "-"),
        topic=scenario["question_text"],
        settings=settings,
        foundation=foundation,
        profile=LearnerProfile(style="analogy", track_lens="code_heavy"),
    )
    first = session.start()
    first_strategy = first.response.strategy
    second = session.respond(wrong_answer)
    expected_answer = (
        session.runtime.current_check.expected_answer
        if session.runtime.current_check is not None
        else ""
    )
    final = session.respond(expected_answer) if expected_answer else second
    retrieved_ids = {span.citation_id for span in session.runtime.last_spans}
    citation_ids = final.response.citation_ids
    citations_resolve = bool(citation_ids) and set(citation_ids).issubset(retrieved_ids)
    re_explained_differently = (
        second.response.next_action == "re_explain_differently"
        and second.response.strategy != first_strategy
    )
    grade_correct = bool(session.runtime.last_grade and session.runtime.last_grade.correct)
    trace_has_decision = _trace_has_runtime_decision(Path(final.trace_path))
    passed = citations_resolve and re_explained_differently and grade_correct and trace_has_decision
    return {
        "scenario_id": scenario["scenario_id"],
        "item_id": scenario["item_id"],
        "source_file": scenario["source_file"],
        "split": scenario["split"],
        "passed": passed,
        "citations_resolve": citations_resolve,
        "re_explained_differently": re_explained_differently,
        "grade_correct": grade_correct,
        "trace_has_runtime_decision": trace_has_decision,
        "top_score": max((span.score for span in session.runtime.last_spans), default=0.0),
        "citation_ids": citation_ids,
        "final_next_action": final.response.next_action,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="dev", choices=["seed", "dev", "test"])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    settings = CoachSettings.from_env()
    scenarios = load_scenarios(settings, split=args.split, limit=args.limit)
    foundation = Foundation.build(settings)
    results = [
        score_scenario(settings=settings, foundation=foundation, scenario=scenario)
        for scenario in scenarios
    ]
    passed = sum(1 for row in results if row["passed"])
    payload = {
        "split": args.split,
        "n": len(results),
        "passed": passed,
        "pass_rate": passed / len(results) if results else 0.0,
        "results": results,
    }
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
```

This task loads private held-out question text only at local eval runtime. It expands file-granular
manifest items into per-question scenarios in memory, runs the actual `CoachSession` loop, and
prints/saves IDs, scores, booleans, actions, and citation IDs only. Do not print or commit raw private
question text.

- [ ] **Step 5: Run tests**

Run:

```bash
uv run pytest tests/test_eval_teach_loop.py -q
uv run ruff check src/genacademy_coach/eval_io.py scripts/check_eval_leak.py scripts/eval_teach_loop.py tests/test_eval_teach_loop.py
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/genacademy_coach/eval_io.py scripts/check_eval_leak.py scripts/eval_teach_loop.py tests/test_eval_teach_loop.py
git commit -m "feat: evaluate teach loop scenarios"
```

---

### Task 11: Live Verification Gate

**Files:**
- Modify: `README.md`
- Create: `docs/teach-loop-status.md`

- [ ] **Step 1: Run full static and unit verification**

Run:

```bash
uv run ruff check .
uv run pytest -q
uv run python scripts/check_eval_leak.py
```

Expected:

- ruff passes.
- pytest passes.
- leak guard passes. PDF extraction warnings are acceptable if the process exits 0.

- [ ] **Step 2: Ensure course corpus is ingested**

Run:

```bash
GENACADEMY_CHUNKER=section uv run python scripts/ingest_course_corpus.py
```

Expected: prints a line in the form
`ingested 33 docs -> 1540 chunks into collection=coach_course; extraction report=<path>` and writes
`eval/extraction_report.json`. Exact counts may change when the private corpus changes.

- [ ] **Step 3: Run the live teach-loop demo**

Run with configured generation credentials:

```bash
GENACADEMY_PROVIDER=nebius uv run python scripts/run_teach_demo.py \
  --topic "attention" \
  --style analogy \
  --track-lens code_heavy \
  --learner-answer "It is when the model remembers previous tokens."
```

Expected:

- The learner-visible answer includes at least one retrieved citation ID.
- The second turn returns `re_explain_differently`.
- The second-turn strategy differs from the first-turn strategy.
- The trace tool calls show the LangChain/Nebius agent successfully used tool calling and structured
  output through `create_agent`; if Nebius rejects tool calling or structured output, stop and switch to
  a Nebius model verified to support OpenAI-compatible tools before claiming the loop works.
- A trace path is printed.

- [ ] **Step 4: Pretty-print the trace**

Run:

```bash
uv run python scripts/print_trace.py traces/<printed-session-id>.jsonl
```

Expected: at least two turns print with `next_action`, `strategy`, `evidence=<score> <band>`, and
citation IDs. The trace must include `re_explain_differently` with a strategy different from turn 1.

- [ ] **Step 5: Run the refusal path**

Run:

```bash
GENACADEMY_PROVIDER=nebius uv run python scripts/run_teach_demo.py \
  --topic "Gen Academy cafeteria menu" \
  --style concise \
  --track-lens low_code_no_code
```

Expected:

- The answer refuses or escalates instead of inventing.
- `review_queue.jsonl` receives a line with the session ID, reason, score, and citation IDs.
- The trace shows `next_action=refuse_escalate`.

- [ ] **Step 6: Run the local teach-loop eval**

Run:

```bash
GENACADEMY_PROVIDER=nebius uv run python scripts/eval_teach_loop.py \
  --split dev \
  --limit 10 \
  --json-out eval/runs/teach-loop-dev.json
```

Expected:

- The command prints JSON with only scenario IDs, source filenames, booleans, scores, actions, and
  citation IDs.
- No raw private question text appears in stdout or `eval/runs/teach-loop-dev.json`.
- Each `passed=true` row has `citations_resolve=true`, `re_explained_differently=true`,
  `grade_correct=true`, and `trace_has_runtime_decision=true`.
- Record the real pass rate. If fewer than 8 of 10 pass, report the actual number and failure modes
  instead of rounding up or changing the test split.

- [ ] **Step 7: Record status**

Create `docs/teach-loop-status.md`:

```markdown
# Teach Loop Status

Status: implemented pending different-model / fresh-context review.

## Verification

Record the exact command output for each required gate before committing this file:

- `uv run ruff check .`
- `uv run pytest -q`
- `uv run python scripts/check_eval_leak.py`
- `GENACADEMY_CHUNKER=section uv run python scripts/ingest_course_corpus.py`
- `GENACADEMY_PROVIDER=nebius uv run python scripts/run_teach_demo.py --topic "attention" --style analogy --track-lens code_heavy --learner-answer "It is when the model remembers previous tokens."`
- `GENACADEMY_PROVIDER=nebius uv run python scripts/eval_teach_loop.py --split dev --limit 10 --json-out eval/runs/teach-loop-dev.json`
- Refusal demo review-queue line, with private content removed if necessary

## Review Notes

- Builder did not self-approve.
- Needs a different model / fresh-context review before merge.
```

Update `README.md` implementation status from foundation-only to teach-loop implemented pending review.

- [ ] **Step 8: Commit**

```bash
git add README.md docs/teach-loop-status.md
git commit -m "docs: record teach loop verification"
```

---

## Self-Review

- Spec coverage: this plan covers the MVP teach loop, one source-prioritized retriever, grounded check
  generation, deterministic grading, within-session profile, refusal/escalation, local trace, and a
  verification gate. It intentionally excludes quiz, interview, admin upload, voice, web UI, MCP/A2A,
  and direct LangGraph.
- Week-2 reuse: retrieval and ingestion remain behind `Foundation`; check-item generation uses the
  inherited Week-2 provider; the LangChain model boundary uses Week-2 generation settings and documents
  the delta required by `create_agent`.
- Held-out test set: the eval runner loads private question text only at local eval runtime, expands
  held-out files into per-question scenarios in memory, runs the actual teach loop, then reports IDs,
  source filenames, booleans, scores, actions, and citation IDs without committing or printing raw
  private text.
- Guardrails: no `langgraph.*` imports; no web-framework imports in core; refusal, citation,
  evidence-score, check-question, turn-budget, and strategy-change gates are enforced in Python;
  model-chosen `observation`, `next_action`, and `strategy` are written to trace.
- Review gate: after implementation, a different model or fresh context must review before merging.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-15-teach-loop-agent.md`. Two execution
options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast
   iteration.
2. **Inline Execution** - execute tasks in this session using executing-plans, batch execution with
   checkpoints.

Do not implement until this plan is approved.
