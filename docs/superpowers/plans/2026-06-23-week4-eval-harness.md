# Week-4 Local Deterministic Eval Harness — Implementation Plan (Plan 1 of 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a runnable, local-only deterministic eval harness for the teach-loop agent — a labeled golden dataset, token/latency instrumentation on the agent boundary, and a scoring runner that emits per-metric precision/recall/F1 paired with cost/latency — so a baseline can be measured.

**Architecture:** Three slices over the existing core. (1) Golden dataset = a JSONL of hand-labeled cases + a separate manifest, validated by a pydantic loader and the extended leak guard. (2) Instrumentation = capture tokens at the `AgentPort` boundary and wall-clock latency in `CoachSession`, written into new optional `TraceTurn` fields. (3) Scoring = a pure `eval_metrics` module + a **core** `eval_runner` (importable/testable) reused by a thin `scripts/run_golden_eval.py` CLI; the deterministic grounded grader stays the per-turn correctness signal and `expected_next_action` is the per-case golden gate. No web imports, no `langgraph.*`, frozen `test` untouched, cloud-safe rule machine-checked.

**Tech Stack:** Python 3.12 (pyproject `requires-python >=3.12`, ruff `target-version = py312`), pydantic v2, pytest, `langchain` 1.3.7 / `langchain_core` 1.4.2 (`usage_metadata` verified: dict with `input_tokens`/`output_tokens`/`total_tokens`), the Week-2 `genacademy_rag` foundation, existing `genacademy_coach` core.

## Global Constraints

- **Design source:** `docs/superpowers/specs/2026-06-23-week4-eval-execution-design.md`; framework: `docs/week4-eval-plan.md`; egress: `docs/decisions.md` AD-12.
- **Pure core / thin view:** no web-framework imports in `src/genacademy_coach/**`. CLI lives in `scripts/`; reusable logic lives in core (because `scripts/` is **not** reliably importable — the existing `scripts/eval_teach_loop.py` is loaded in tests via `importlib`, confirming scripts are not on the import path).
- **No `langgraph.*` imports.** Instrumentation uses stdlib `time` + dict reads of `usage_metadata` only.
- **Reuse, do not rebuild:** reuse `grounding.py` grader (per-turn correctness signal), the `eval_teach_loop.py` 3-turn scenario pattern, `eval/non_private_negative_controls.json`. No new grader/embedder/threshold scheme.
- **Frozen `test` is sacred:** golden `split` ∈ {seed, dev, synthetic, negative_control} — **never `test`**. `eval/split_manifest.json` rows stay byte-stable.
- **Cloud-safe rule (AD-12):** real seed/dev student questions are **real learner questions → `cloud_safe=false`** (no inline text; referenced by `source_ref`, resolved locally at run time, redacted from artifacts). Synthetic-from-seed + the 10 controls are `cloud_safe=true` with a required `cloud_safe_reason`. Nothing in Plan 1 uploads anywhere (that is Plan 2).
- **Scope (handout-grounded):** ~30 in-corpus teachable cases (≈16 happy / 9 edge / 5 known-failure) + the 10 negative controls; real-seed-leaning, pure-LLM-generated < 20%.
- **Recorded tool names** (for `expected_tools` / tool_f1): `retrieve_course_corpus`, `generate_check_item`, `grade_understanding`, `update_profile`, `escalate_to_mentor`.
- **Bands (verbatim):** STOP < 0.40 · CONFIRM 0.40–0.85 · PROCEED > 0.85.
- **Commit** after each task; co-author trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## File Structure

- Create `src/genacademy_coach/eval_golden.py` — `GoldenCase` model + `load_golden_cases(path)`.
- Create `src/genacademy_coach/eval_scenarios.py` — scenario loaders moved out of the script (importable).
- Create `src/genacademy_coach/eval_metrics.py` — pure metric math + `PriceTable` + `aggregate`.
- Create `src/genacademy_coach/eval_runner.py` — `score_golden_case`, `run_golden_eval`, `resolve_query`.
- Create `scripts/run_golden_eval.py` — thin CLI calling `eval_runner`.
- Create `eval/golden/golden_cases.jsonl`, `eval/golden/golden_manifest.json` — data.
- Create `tests/conftest.py` — shared fakes (`FakeFoundation`, `make_fake_session`).
- Modify `src/genacademy_coach/teach_types.py` — add `TokenUsage`; optional token/latency fields on `TraceTurn`.
- Modify `src/genacademy_coach/teach_session.py` — `AgentPort.last_usage`, `_sum_usage`, latency capture.
- Modify `scripts/eval_teach_loop.py` — re-import the moved loaders from `eval_scenarios` (back-compat).
- Modify `scripts/check_eval_leak.py` — scan `golden_cases.jsonl`.
- Tests: `tests/test_eval_golden.py`, `tests/test_eval_scenarios.py`, `tests/test_eval_metrics.py`, `tests/test_teach_instrumentation.py`, `tests/test_eval_runner.py`, `tests/test_eval_golden_leak.py`.

---

### Task 1: Golden case schema + JSONL loader

**Files:** Create `src/genacademy_coach/eval_golden.py`; Test `tests/test_eval_golden.py`.
**Interfaces:** Produces `GoldenCase` and `load_golden_cases(path) -> list[GoldenCase]`. `source_ref` format is `"scenario:<scenario_id>"` (a seed/dev scenario id from `eval_scenarios.load_scenarios`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eval_golden.py
import json
import pytest
from genacademy_coach.eval_golden import GoldenCase, load_golden_cases

def _row(**over):
    base = dict(
        case_id="happy_001", query_type="happy", concept="tokenization",
        expected_citation_span_id="doc::3", target_check_id="chk1",
        expected_next_action="advance",
        expected_tools=["retrieve_course_corpus", "generate_check_item", "grade_understanding"],
        refusal_expected=False, strategy_changed_on_stumble=True,
        split="seed", cloud_safe=True, cloud_safe_reason="synthetic, no private text",
        user_query="What is a token?", initial_wrong_answer="a whole word",
        expected_answer="a sub-word piece", expected_check_keywords=["sub-word"],
    )
    base.update(over)
    return base

def test_cloud_safe_requires_reason():
    with pytest.raises(ValueError):
        GoldenCase(**_row(cloud_safe=True, cloud_safe_reason=""))

def test_test_split_rejected():
    with pytest.raises(ValueError):
        GoldenCase(**_row(split="test"))

def test_non_cloud_safe_forbids_inline_text_and_needs_source_ref():
    with pytest.raises(ValueError):
        GoldenCase(**_row(cloud_safe=False, cloud_safe_reason=None,
                          user_query=None, initial_wrong_answer=None, expected_answer="x"))
    ok = GoldenCase(**_row(cloud_safe=False, cloud_safe_reason=None, user_query=None,
                           initial_wrong_answer=None, expected_answer=None,
                           source_ref="scenario:3df14f64046e6250:000"))
    assert ok.source_ref.startswith("scenario:")

def test_loader_reads_jsonl(tmp_path):
    p = tmp_path / "g.jsonl"
    p.write_text(json.dumps(_row()) + "\n" + json.dumps(_row(case_id="happy_002")) + "\n")
    assert [c.case_id for c in load_golden_cases(p)] == ["happy_001", "happy_002"]
```

- [ ] **Step 2: Run test to verify it fails** — `pytest tests/test_eval_golden.py -q` → FAIL (module missing).

- [ ] **Step 3: Write minimal implementation**

```python
# src/genacademy_coach/eval_golden.py
from __future__ import annotations
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator
from genacademy_coach.teach_types import NextAction

QueryType = Literal["happy", "edge", "known_failure", "adversarial"]
GoldenSplit = Literal["seed", "dev", "synthetic", "negative_control"]  # never "test"

class GoldenCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    query_type: QueryType
    concept: str
    expected_citation_span_id: str | None = None
    target_check_id: str | None = None
    expected_next_action: NextAction
    expected_tools: list[str]
    refusal_expected: bool = False
    strategy_changed_on_stumble: bool = False
    split: GoldenSplit
    cloud_safe: bool
    cloud_safe_reason: str | None = None
    user_query: str | None = None
    initial_wrong_answer: str | None = None
    expected_answer: str | None = None          # inline (cloud-safe only); drives the "correct" turn
    expected_check_keywords: list[str] = []      # short golden labels
    source_ref: str | None = None                # "scenario:<scenario_id>" for cloud_safe=false

    @model_validator(mode="after")
    def _check_cloud_safe(self) -> "GoldenCase":
        if self.cloud_safe:
            if not (self.cloud_safe_reason and self.cloud_safe_reason.strip()):
                raise ValueError(f"{self.case_id}: cloud_safe=true requires cloud_safe_reason")
        else:
            if any([self.user_query, self.initial_wrong_answer, self.expected_answer]):
                raise ValueError(f"{self.case_id}: cloud_safe=false must not carry inline text")
            if not self.source_ref:
                raise ValueError(f"{self.case_id}: cloud_safe=false requires source_ref")
        if not self.refusal_expected and not self.expected_check_keywords:
            raise ValueError(f"{self.case_id}: teachable case requires expected_check_keywords")
        return self

def load_golden_cases(path: Path) -> list[GoldenCase]:
    rows: list[GoldenCase] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(GoldenCase.model_validate_json(line))
    return rows
```

- [ ] **Step 4: Run test** — `pytest tests/test_eval_golden.py -q` → PASS.
- [ ] **Step 5: Commit** — `git add src/genacademy_coach/eval_golden.py tests/test_eval_golden.py && git commit -m "feat(eval): golden case schema + JSONL loader with cloud-safe validation"`

---

### Task 2: Extract scenario loaders to core (`eval_scenarios.py`)

**Files:** Create `src/genacademy_coach/eval_scenarios.py`; Modify `scripts/eval_teach_loop.py`; Test `tests/test_eval_scenarios.py`.
**Interfaces:** Produces `load_manifest_items`, `extract_questions`, `question_records_for_item`, `load_scenarios`, `QUESTION_PREFIX_RE` — moved verbatim from the script so both the legacy script and `eval_runner` import them.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eval_scenarios.py
from genacademy_coach.eval_scenarios import extract_questions, question_records_for_item

def test_extract_questions_numbered():
    assert extract_questions("1. What is attention?\n2. Why cite?") == ["What is attention?", "Why cite?"]

def test_question_records_reads_runtime_source(tmp_path):
    d = tmp_path / "eq"; d.mkdir()
    (d / "q.md").write_text("1. What is attention?\n")
    rows = question_records_for_item(d, {"id": "i", "split": "dev", "source_file": "q.md"})
    assert rows[0]["scenario_id"] == "i:000" and rows[0]["question_text"] == "What is attention?"
```

- [ ] **Step 2: Run test** — `pytest tests/test_eval_scenarios.py -q` → FAIL (module missing).

- [ ] **Step 3: Move the functions**

Cut `QUESTION_PREFIX_RE`, `load_manifest_items`, `extract_questions`, `question_records_for_item`, `load_scenarios` from `scripts/eval_teach_loop.py` into `src/genacademy_coach/eval_scenarios.py` (they already import only `json`, `re`, `Path`, and `genacademy_coach.eval_io.read_eval_text` + `CoachSettings`). In `scripts/eval_teach_loop.py`, replace them with:
```python
from genacademy_coach.eval_scenarios import (
    QUESTION_PREFIX_RE, extract_questions, load_manifest_items,
    load_scenarios, question_records_for_item,
)
```
(`module.load_manifest_items`/etc. still resolve in `tests/test_eval_teach_loop.py`'s `importlib`-loaded module, since they are imported into the script namespace.)

- [ ] **Step 4: Run tests** — `pytest tests/test_eval_scenarios.py tests/test_eval_teach_loop.py -q` → PASS (new + legacy unaffected).
- [ ] **Step 5: Commit** — `git add src/genacademy_coach/eval_scenarios.py scripts/eval_teach_loop.py tests/test_eval_scenarios.py && git commit -m "refactor(eval): extract scenario loaders to importable core module"`

---

### Task 3: Author the golden dataset + manifest

**Files:** Create `eval/golden/golden_cases.jsonl`, `eval/golden/golden_manifest.json`.
**Interfaces:** Consumes `load_golden_cases` (T1), `eval_scenarios.load_scenarios` (T2), `eval/non_private_negative_controls.json`.

- [ ] **Step 1: Enumerate real seed/dev scenarios (for source_ref + labels)**

Run: `python -c "from genacademy_coach.settings import CoachSettings; from genacademy_coach.eval_scenarios import load_scenarios; s=CoachSettings.from_env(); [print(x['scenario_id'], x['question_text'][:80]) for x in load_scenarios(s, split='seed', limit=999)+load_scenarios(s, split='dev', limit=999)]"`
Expected: real seed/dev student questions + their `scenario_id`s (local-only; do not paste into committed files).

- [ ] **Step 2: Author cases**

Write `eval/golden/golden_cases.jsonl`, one `GoldenCase` per line:
- **Real seed/dev rows → `cloud_safe=false`**, `user_query`/`initial_wrong_answer`/`expected_answer` omitted, `source_ref="scenario:<scenario_id>"`, with `expected_citation_span_id` (from `scripts/diagnose_teach_retrieval.py` on that question), `expected_next_action`, `expected_tools`, `expected_check_keywords` (short labels are fine to commit).
- **Synthetic-from-seed rows → `cloud_safe=true`** (paraphrased, hand-labeled) with inline `user_query`/`expected_answer` + `cloud_safe_reason="synthetic paraphrase, no private text"`.
- **10 controls → `cloud_safe=true`**, `query_type="adversarial"`, `refusal_expected=true`, `expected_next_action="refuse_escalate"`, `expected_tools=["retrieve_course_corpus","escalate_to_mentor"]`, `cloud_safe_reason="out-of-domain control, no private text"`.
- Mix ≈ 50/30/15/5 across happy/edge/known_failure/adversarial; pure-LLM-generated < 20%.
- **Every teachable (non-refusal) case requires `expected_check_keywords`** (short golden labels, committable): the runner builds the simulated correct answer from them when a row has no cloud-safe `expected_answer`, so task-completion never depends on a runtime-generated check.

- [ ] **Step 3: Manifest** — write `eval/golden/golden_manifest.json` (`version`, `seed`, `counts_by_query_type`, `cloud_safe_count`, `created`) with counts matching the file.

- [ ] **Step 4: Validate** — `python -c "from genacademy_coach.eval_golden import load_golden_cases; from collections import Counter; c=load_golden_cases('eval/golden/golden_cases.jsonl'); print(len(c), Counter(x.query_type for x in c)); assert all(x.split!='test' for x in c)"` → total 30–50; balance ≈ target; no test rows.

- [ ] **Step 5: Commit** — `git add eval/golden/ && git commit -m "feat(eval): hand-labeled golden dataset (~30 in-corpus + 10 controls)"`

---

### Task 4: Extend the leak guard to scan the golden dataset

**Files:** Modify `scripts/check_eval_leak.py`; Test `tests/test_eval_golden_leak.py`.
**Interfaces:** Consumes the `test` needles/phrases already built in `check_eval_leak.main`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eval_golden_leak.py
import json
from scripts.check_eval_leak import scan_golden_cases  # loaded via importlib in CI; see note

def _write(tmp_path, rows):
    p = tmp_path / "golden_cases.jsonl"; p.write_text("\n".join(json.dumps(r) for r in rows) + "\n"); return p

def test_rejects_test_split(tmp_path):
    p = _write(tmp_path, [{"case_id":"x","split":"test","cloud_safe":True,"cloud_safe_reason":"r"}])
    assert any("test split" in o for o in scan_golden_cases(p, test_needles=set(), test_phrases={}))

def test_flags_test_needle_in_inline_text(tmp_path):
    p = _write(tmp_path, [{"case_id":"x","split":"seed","cloud_safe":True,"cloud_safe_reason":"r","user_query":"has SECRET_ID"}])
    assert any("SECRET_ID" in o for o in scan_golden_cases(p, test_needles={"SECRET_ID"}, test_phrases={}))

def test_clean_golden_passes(tmp_path):
    p = _write(tmp_path, [{"case_id":"x","split":"seed","cloud_safe":True,"cloud_safe_reason":"r","user_query":"what is a token"}])
    assert scan_golden_cases(p, test_needles={"SECRET_ID"}, test_phrases={}) == []
```
(If `from scripts.check_eval_leak import ...` fails to import, load it via the `importlib` pattern in `tests/test_eval_teach_loop.py::load_eval_module`.)

- [ ] **Step 2: Run test** → FAIL (`scan_golden_cases` undefined).

- [ ] **Step 3: Implement** — add `scan_golden_cases(path, *, test_needles, test_phrases)` to `scripts/check_eval_leak.py` returning offenders for: `split=="test"`; `cloud_safe=True` with blank `cloud_safe_reason`; `cloud_safe=False` carrying inline text; any `test_needle` in inline fields; any normalized `test_phrase` in inline fields. Call it from `main` over `settings.eval_dir / "golden" / "golden_cases.jsonl"` and `offenders.extend(...)` before the final raise.

- [ ] **Step 4: Run** — `pytest tests/test_eval_golden_leak.py -q && python scripts/check_eval_leak.py` → unit PASS; guard prints no-leak (now covering golden).
- [ ] **Step 5: Commit** — `git add scripts/check_eval_leak.py tests/test_eval_golden_leak.py && git commit -m "feat(eval): leak guard scans golden dataset for test/cloud-safe violations"`

---

### Task 5: `TokenUsage` type + optional `TraceTurn` fields

**Files:** Modify `src/genacademy_coach/teach_types.py`; Test `tests/test_teach_types.py` (append).
**Interfaces:** Produces `TokenUsage(input_tokens, output_tokens, total_tokens)`; `TraceTurn` gains defaulted `input_tokens`, `output_tokens`, `total_tokens`, `latency_ms`.

- [ ] **Step 1: Failing test**
```python
# tests/test_teach_types.py (append)
from genacademy_coach.teach_types import TokenUsage, TraceTurn
def test_token_usage_defaults_zero():
    assert TokenUsage().input_tokens == 0 and TokenUsage().total_tokens == 0
def test_trace_turn_token_latency_defaults():
    t = TraceTurn(session_id="s", turn=1, topic_hash="h", learner_input_hash="h",
                  next_action="advance", strategy="summary", evidence_score=0.5,
                  evidence_band="confirm", retrieved_citation_ids=[], tool_calls=[])
    assert (t.input_tokens, t.output_tokens, t.total_tokens, t.latency_ms) == (0, 0, 0, 0.0)
```
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — add `class TokenUsage(BaseModel)` with three int fields defaulting 0; add to `TraceTurn` (after `tool_calls`): `input_tokens: int = 0`, `output_tokens: int = 0`, `total_tokens: int = 0`, `latency_ms: float = 0.0`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `git add src/genacademy_coach/teach_types.py tests/test_teach_types.py && git commit -m "feat(eval): TokenUsage type + optional token/latency fields on TraceTurn"`

---

### Task 6: `AgentPort.last_usage` — token capture at the boundary

**Files:** Modify `src/genacademy_coach/teach_session.py`; Test `tests/test_teach_instrumentation.py`.
**Interfaces:** Consumes `TokenUsage` (T5). Produces `_sum_usage(messages) -> TokenUsage`; `AgentPort.last_usage: TokenUsage`.

- [ ] **Step 1: Failing test**
```python
# tests/test_teach_instrumentation.py
from langchain_core.messages import AIMessage
from genacademy_coach.teach_types import TokenUsage, CoachAgentResponse
from genacademy_coach.teach_session import _sum_usage, StaticAgentPort

def test_sum_usage_sums_messages():
    msgs = [AIMessage(content="a", usage_metadata={"input_tokens":3,"output_tokens":5,"total_tokens":8}),
            AIMessage(content="b", usage_metadata={"input_tokens":2,"output_tokens":1,"total_tokens":3})]
    u = _sum_usage(msgs)
    assert (u.input_tokens, u.output_tokens, u.total_tokens) == (5, 6, 11)

def test_static_port_reports_zero_usage():
    port = StaticAgentPort(CoachAgentResponse(learner_message="x", observation="o",
                          next_action="advance", strategy="summary", citation_ids=[]))
    assert isinstance(port.last_usage, TokenUsage) and port.last_usage.total_tokens == 0
```
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — import `TokenUsage`; add `_sum_usage` (iterate messages, sum `getattr(m,"usage_metadata",None)` keys with `or 0`). `AgentPort` Protocol: declare `last_usage: TokenUsage`. `StaticAgentPort.__init__`: `self.last_usage = TokenUsage()`. `LangChainAgentPort.__init__`: `self.last_usage = TokenUsage()`; in `invoke`, reset `self.last_usage = TokenUsage()` first, then after `result = self._agent.invoke(...)` set `self.last_usage = _sum_usage(result.get("messages", []))`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `git add src/genacademy_coach/teach_session.py tests/test_teach_instrumentation.py && git commit -m "feat(eval): capture token usage at the AgentPort boundary"`

---

### Task 7: Shared test fakes + latency capture threaded into the trace

**Files:** Create `tests/conftest.py`; Modify `src/genacademy_coach/teach_session.py`; Test `tests/test_teach_instrumentation.py` (append).
**Interfaces:** Consumes `_sum_usage`, `port.last_usage` (T6). Produces `tests/conftest.py` fixtures (`fake_settings`, `fake_foundation`, `make_session`) reused by Task 9; `TraceTurn` rows carrying real `latency_ms` + token counts.

- [ ] **Step 1: Create shared fakes** — `tests/conftest.py` modeled on `tests/test_teach_session.py` (`FakeSettings`, `FakeFoundation`) and the `FakeSession` in `tests/test_eval_teach_loop.py`:
```python
# tests/conftest.py
from pathlib import Path
from types import SimpleNamespace
import pytest
from genacademy_coach.teach_types import CoachAgentResponse, RetrievedSpan, CheckItem, UnderstandingGrade

class _FakeFoundation:
    provider = object()
    def __init__(self, rows=None): self._rows = rows or []
    def retrieve(self, query: str): return list(self._rows)

@pytest.fixture
def fake_settings(tmp_path):
    return SimpleNamespace(trace_dir=tmp_path/"traces", review_queue_path=tmp_path/"rq.jsonl",
                           stop_threshold=0.40, confirm_threshold=0.85, max_teach_turns=4)

@pytest.fixture
def fake_foundation():
    return _FakeFoundation(rows=[{"chunk_id":"note::0","doc_id":"note","text":"Attention focuses context.",
                                  "score":0.91,"title":"a.md","source_type":"note","page_or_section":None}])
```
Add a `FakePort` exposing a settable `last_usage` and a canned `CoachAgentResponse`, plus a `make_session` helper that wires `CoachSession` with the `fake_settings`/`fake_foundation`/`FakePort`.

- [ ] **Step 2: Failing test** — assert the trace carries usage threaded from a nonzero-usage port (fails before wiring, since `_write_result` ignores usage):
```python
# tests/test_teach_instrumentation.py (append)
from genacademy_coach.trace import load_trace
from genacademy_coach.teach_types import TokenUsage

def test_trace_records_latency_and_threaded_tokens(make_session):
    session, trace_dir = make_session(last_usage=TokenUsage(input_tokens=11, output_tokens=7, total_tokens=18))
    session.start()
    rows = load_trace(trace_dir / f"{session.session_id}.jsonl")
    assert rows[-1].input_tokens == 11 and rows[-1].total_tokens == 18
    assert rows[-1].latency_ms > 0.0
```

- [ ] **Step 3: Run** → FAIL (token fields default 0; latency 0.0 before wiring).

- [ ] **Step 4: Implement** — in `teach_session.py`: `import time`; in `_invoke_agent` wrap the port call (`start=time.perf_counter()` … `latency_ms=(time.perf_counter()-start)*1000.0`) on both success and `AgentResponseError` branches; turn-budget early return passes `latency_ms=0.0`. Add params `latency_ms: float = 0.0, usage: TokenUsage | None = None` to `_write_result`; set `usage = usage or TokenUsage()`; pass `input_tokens=usage.input_tokens, output_tokens=usage.output_tokens, total_tokens=usage.total_tokens, latency_ms=latency_ms` into the `TraceTurn(...)`. Pass `getattr(self.agent_port, "last_usage", None) or TokenUsage()` (defensive — existing custom fake ports may only implement `invoke`, e.g. in `tests/test_teach_session.py`) + measured `latency_ms` from `_invoke_agent`.

- [ ] **Step 5: Run + regressions** — `pytest tests/test_teach_instrumentation.py tests/test_teach_session.py -q` → PASS, no regressions.
- [ ] **Step 6: Commit** — `git add tests/conftest.py src/genacademy_coach/teach_session.py tests/test_teach_instrumentation.py && git commit -m "feat(eval): record per-turn latency and threaded token usage in the trace"`

---

### Task 8: Pure `eval_metrics` module + `PriceTable` + `aggregate`

**Files:** Create `src/genacademy_coach/eval_metrics.py`; Test `tests/test_eval_metrics.py`.
**Interfaces:** Produces `precision_recall_f1`, `citation_prf`, `tool_match`, `recall_at_k`, `refusal_outcome`, `PriceTable`, `aggregate`. **p50/p95 are computed in `aggregate` across the flattened per-turn latency distribution — never from a single case.**

- [ ] **Step 1: Failing test**
```python
# tests/test_eval_metrics.py
from genacademy_coach.eval_metrics import (
    precision_recall_f1, citation_prf, tool_match, recall_at_k, refusal_outcome, PriceTable, aggregate)

def test_prf_basic():
    p,r,f = precision_recall_f1(tp=8, fp=2, fn=2); assert (round(p,2),round(r,2),round(f,2))==(0.8,0.8,0.8)
def test_citation_prf_sets():
    p,r,f = citation_prf(predicted={"a","b"}, expected={"a"}); assert round(p,2)==0.5 and r==1.0
def test_tool_match_ordered():
    m = tool_match(actual=["retrieve_course_corpus","grade_understanding"],
                   expected=["retrieve_course_corpus","grade_understanding"])
    assert m["f1"]==1.0 and m["ordered_ok"] is True
def test_recall_at_k():
    assert recall_at_k(["x","y","z"], "y", k=5) and not recall_at_k(["x","y","z"], "q", k=2)
def test_refusal_outcome():
    assert refusal_outcome(refusal_expected=True, actual_next_action="refuse_escalate")=="tp"
    assert refusal_outcome(refusal_expected=False, actual_next_action="refuse_escalate")=="fp"
def test_price_table_cost():
    assert PriceTable(prices={"m": (1e-6, 2e-6)}).cost("m", input_tokens=1000, output_tokens=1000)==0.003
def test_aggregate_computes_p95_across_turns():
    rows = [{"task_completion_pass": True, "refusal_expected": False, "turn_latencies_ms":[10.0,20.0],
             "input_tokens":100,"output_tokens":50,"model_id":"m"}]
    out = aggregate(rows, price_table=PriceTable(prices={"m": (1e-6, 2e-6)}))
    assert "latency_p95_ms" in out and "task_completion" in out and out["cost_usd"] >= 0.0
```
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — the pure functions (set-based `citation_prf`; `tool_match` returns precision/recall/f1 + `ordered_ok`; `recall_at_k`; `refusal_outcome` → tp/fp/fn/tn; `PriceTable.cost`). `aggregate(rows, *, price_table)` rolls per-metric tp/fp/fn into P/R/F1, flattens `turn_latencies_ms` across rows and computes p50/p95 via a sorted-index percentile helper (`_pct(sorted_vals, q)` guarding empty/singleton), sums tokens and `cost_usd` via `price_table`, and reports class balance.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `git add src/genacademy_coach/eval_metrics.py tests/test_eval_metrics.py && git commit -m "feat(eval): pure metrics module (P/R/F1, citation_f1, tool_f1, recall@5, cost, p95)"`

---

### Task 9: Core `eval_runner` + thin CLI

**Files:** Create `src/genacademy_coach/eval_runner.py`, `scripts/run_golden_eval.py`; Test `tests/test_eval_runner.py`.
**Interfaces:** Consumes `load_golden_cases` (T1), `eval_scenarios.load_scenarios` (T2), `eval_metrics` (T8), `grounding.grade_understanding`, `CoachSession`/`foundation.retrieve`. Produces `resolve_query(case, scenario_index)`, `score_golden_case(...)`, `run_golden_eval(...)`.

- [ ] **Step 1: Failing test** (uses `tests/conftest.py` fakes + a `FakeSession` like `test_eval_teach_loop.py`):
```python
# tests/test_eval_runner.py
from genacademy_coach.eval_golden import GoldenCase
from genacademy_coach.eval_runner import score_golden_case, resolve_query

def test_resolve_query_uses_inline_for_cloud_safe():
    c = GoldenCase(case_id="c", query_type="happy", concept="t", expected_next_action="advance",
                   expected_tools=["retrieve_course_corpus"], split="synthetic", cloud_safe=True,
                   cloud_safe_reason="syn", user_query="what is a token")
    assert resolve_query(c, scenario_index={}) == "what is a token"

def test_resolve_query_resolves_source_ref_for_non_cloud_safe():
    c = GoldenCase(case_id="c", query_type="happy", concept="t", expected_next_action="advance",
                   expected_tools=["retrieve_course_corpus"], split="seed", cloud_safe=False,
                   source_ref="scenario:i:000")
    assert resolve_query(c, scenario_index={"i:000": "real private question"}) == "real private question"

def test_score_golden_case_emits_redacted_metric_row(fake_settings, fake_foundation):
    case = GoldenCase(case_id="happy_001", query_type="happy", concept="tokenization",
        expected_citation_span_id="note::0", expected_next_action="advance",
        expected_tools=["retrieve_course_corpus","generate_check_item","grade_understanding"],
        refusal_expected=False, split="seed", cloud_safe=False, source_ref="scenario:i:000")
    row = score_golden_case(settings=fake_settings, foundation=fake_foundation, case=case,
                            scenario_index={"i:000":"what is a token"}, session_factory=FakeSession)
    for k in ("task_completion_pass","citation_f1","tool_f1","retrieval_recall_at_5",
              "refusal_outcome","turn_latencies_ms","input_tokens","output_tokens","model_id"):
        assert k in row
    assert "user_query" not in row and "answer_text" not in row  # non-cloud-safe redaction
```
(Define a local `FakeSession` in the test like `tests/test_eval_teach_loop.py:122`, returning canned `start()`/`respond()` results and a `runtime` with `last_spans`/`current_check`/`last_grade`/`tool_calls`.)

- [ ] **Step 2: Run** → FAIL (module missing).

- [ ] **Step 3: Implement** `src/genacademy_coach/eval_runner.py`:
  - `resolve_query(case, scenario_index)`: `case.user_query` if `case.cloud_safe` else `scenario_index[case.source_ref.split(":",1)[1]]`.
  - `score_golden_case(*, settings, foundation, case, scenario_index, session_factory=CoachSession)`: drive the 3-turn pattern using `resolve_query(case, scenario_index)` as the topic and, for the "correct" turn, **`case.expected_answer` (cloud-safe) else `" ".join(case.expected_check_keywords)`** (golden labels — committable, works for non-cloud-safe; the runtime-generated check is NOT the golden answer source). Read the trace (`load_trace`) for `actual_tools`, `turn_latencies_ms`, summed tokens; set `model_id = (getattr(foundation, "rag_settings", None) and foundation.rag_settings.gen_model) or DEFAULT_NEBIUS_MODEL` (import `DEFAULT_NEBIUS_MODEL` from `teach_agent`); compute `citation_f1=citation_prf(predicted, {case.expected_citation_span_id})`, `tool_f1=tool_match(actual, case.expected_tools)["f1"]`, `retrieval_recall_at_5=recall_at_k([r["chunk_id"] for r in foundation.retrieve(query)][:5], case.expected_citation_span_id)`, `refusal_outcome=refusal_outcome(refusal_expected=case.refusal_expected, actual_next_action=final_action)`, and **`task_completion_pass = (final_action == case.expected_next_action) and (case.refusal_expected or grade_correct)`** (grounded grader's `grade_correct` for teachable cases). Emit redacted fields incl. `model_id`, `input_tokens`, `output_tokens` (ids/scores/metrics only); include `answer_text`/`user_query` **only** when `case.cloud_safe`.
  - `run_golden_eval(*, settings, foundation, cases, tag, price_table)`: build `scenario_index` once via `eval_scenarios.load_scenarios(settings, split="seed"/"dev")`; map `score_golden_case`; `aggregate(rows, price_table=...)`; write `eval/runs/golden-<tag>-<YYYYMMDD>.json` (`sort_keys=True`).
  - `scripts/run_golden_eval.py`: `load_local_env`-style dotenv, argparse `--tag`/`--limit`, build `CoachSettings`/`Foundation`; build `PriceTable` keyed by the gen `model_id` (`foundation.rag_settings.gen_model`) using the **verified Nebius per-token price** for that model (AGENTS.md §4 — confirm the number at build); call `run_golden_eval`, print summary.

- [ ] **Step 4: Run + real dry-run** — `pytest tests/test_eval_runner.py -q` → PASS; then `python scripts/run_golden_eval.py --tag baseline --limit 3` → writes `eval/runs/golden-baseline-<date>.json` with per-metric P/R/F1 + p95 + cost.
- [ ] **Step 5: Commit** — `git add src/genacademy_coach/eval_runner.py scripts/run_golden_eval.py tests/test_eval_runner.py && git commit -m "feat(eval): golden-set runner (core) emitting per-metric P/R/F1 + cost/latency"`

---

## Final verification (evidence before done — gate #3)

- [ ] `ruff check .` clean.
- [ ] `pytest -q` green (show output).
- [ ] `python scripts/check_eval_leak.py` prints the no-leak message (now covering golden).
- [ ] `python scripts/run_golden_eval.py --tag baseline` writes a run artifact with all metric keys; non-cloud-safe rows carry no inline text.

## Self-Review

- **Spec coverage:** Stage 1 → Tasks 1,3,4; Stage 2 → Tasks 5–7; Stage 3 → Tasks 2,8,9. Fork 1 = Tasks 5–7. Fork 2 = Tasks 1,3,4. Fork 3 = Tasks 2,8,9. Fork 4 = Plan 2.
- **Codex FAIL fixes:** P1#1 (source_ref) → `resolve_query` + `eval_scenarios` extraction (T2/T9); P1#2 (golden gate) → `task_completion_pass` on golden `expected_next_action` + grounded `grade_correct` (T9); P1#3 (fixtures/imports) → core `eval_runner` + `tests/conftest.py` (T7/T9); P2#4 → fail-first token-threading test (T7); P2#5 → p50/p95 in `aggregate` across `turn_latencies_ms` (T8); P2#6 → Python 3.12.
- **Codex round-2 fixes:** golden answer source = `expected_check_keywords` (validator-required for teachable, used to build the correct turn; no runtime-check dependency) (T1/T3/T9); per-row `model_id` from `foundation.rag_settings.gen_model or DEFAULT_NEBIUS_MODEL` → `PriceTable` cost (T8/T9); defensive `getattr(port, "last_usage", TokenUsage())` so existing fake ports keep working (T7).
- **Type consistency:** `TokenUsage` (T5) → T6/T7; `GoldenCase` (T1) → T3/T4/T9; `eval_metrics` names (T8) → T9; `eval_scenarios` (T2) → T9; tool names match `teach_tools.py`.
- **Reuse vs rebuild:** grounded grader, scenario loaders, and the 3-turn pattern are reused, not rebuilt; the legacy `eval_teach_loop.py` keeps working via re-import.

## Execution Handoff

Per the standing flow (Codex-review the plan → on PASS, merge → build), this revised plan goes back to Codex; on PASS + merge, Stage 1 (Task 1) starts. Recommended executor: **Inline Execution** (this session, checkpoints per task) given the tight deadline and the tightly-coupled instrumentation edits.
