# Week-4 Local Deterministic Eval Harness — Implementation Plan (Plan 1 of 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a runnable, local-only deterministic eval harness for the teach-loop agent — a labeled golden dataset, token/latency instrumentation on the agent boundary, and a scoring runner that emits per-metric precision/recall/F1 paired with cost/latency — so a baseline can be measured.

**Architecture:** Three slices over the existing core. (1) Golden dataset = a JSONL of hand-labeled cases + a separate manifest, validated by a pydantic loader and the extended leak guard. (2) Instrumentation = capture tokens at the `AgentPort` boundary and wall-clock latency in `CoachSession`, written into new optional `TraceTurn` fields. (3) Scoring = a pure `eval_metrics` module (P/R/F1, citation_f1, tool_f1, recall@5, refusal, cost) plus a thin `run_golden_eval` runner that reuses the deterministic grounded grader as the gate. No web imports, no `langgraph.*`, frozen `test` untouched, cloud-safe rule machine-checked.

**Tech Stack:** Python 3.11, pydantic v2, pytest, `langchain` 1.3.7 / `langchain_core` 1.4.2 (`usage_metadata` verified: dict with `input_tokens`/`output_tokens`/`total_tokens`), the Week-2 `genacademy_rag` foundation, existing `genacademy_coach` core.

## Global Constraints

- **Design source:** `docs/superpowers/specs/2026-06-23-week4-eval-execution-design.md`; framework: `docs/week4-eval-plan.md`; egress: `docs/decisions.md` AD-12. (Verbatim values below.)
- **Pure core / thin view:** no web-framework imports in `src/genacademy_coach/**`. Runners live in `scripts/`.
- **No `langgraph.*` imports.** Instrumentation uses stdlib `time` + dict reads of `usage_metadata` only.
- **Reuse, do not rebuild:** reuse `grounding.py` grader (the gate), the `scripts/eval_teach_loop.py` scenario-running pattern, `scripts/check_eval_leak.py`, `eval/non_private_negative_controls.json`. No new grader/embedder/threshold scheme.
- **Frozen `test` is sacred:** golden cases use `split` ∈ {seed, dev, synthetic, negative_control} — **never `test`**. `eval/split_manifest.json` rows stay byte-stable (do not edit them).
- **Cloud-safe rule (AD-12):** inline `user_query`/`initial_wrong_answer`/`answer_text` only on `cloud_safe=true` rows, each carrying a non-empty `cloud_safe_reason`. Run artifacts redact `answer_text` on non-cloud-safe rows. Nothing in this plan uploads anywhere (that is Plan 2).
- **Scope (handout-grounded):** target ~30 in-corpus teachable cases (≈16 happy / 9 edge / 5 known-failure) + the 10 negative controls; real-seed-leaning, pure-LLM-generated < 20%.
- **Recorded tool names** (for `expected_tools` / tool_f1): `retrieve_course_corpus`, `generate_check_item`, `grade_understanding`, `update_profile`, `escalate_to_mentor`.
- **Bands (verbatim):** STOP < 0.40 · CONFIRM 0.40–0.85 · PROCEED > 0.85.
- **Commit** after each task; co-author trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## File Structure

- Create `src/genacademy_coach/eval_golden.py` — `GoldenCase` pydantic model + `load_golden_cases(path)` JSONL loader/validator.
- Create `src/genacademy_coach/eval_metrics.py` — pure metric math + `PriceTable` + `aggregate`.
- Create `eval/golden/golden_cases.jsonl` — band-(a) golden inputs (data).
- Create `eval/golden/golden_manifest.json` — version, seed, class-balance counts, cloud_safe count.
- Create `scripts/run_golden_eval.py` — thin runner; emits `eval/runs/golden-<tag>-<date>.json`.
- Modify `src/genacademy_coach/teach_types.py` — add `TokenUsage`; add optional token/latency fields to `TraceTurn`.
- Modify `src/genacademy_coach/teach_session.py` — `AgentPort.last_usage`; latency capture; thread into `_write_result`.
- Modify `scripts/check_eval_leak.py` — scan `golden_cases.jsonl` (4 assertions).
- Tests: `tests/test_eval_golden.py`, `tests/test_eval_metrics.py`, `tests/test_teach_instrumentation.py`, `tests/test_run_golden_eval.py`, and extend `tests/test_*` for the leak guard.

---

### Task 1: Golden case schema + JSONL loader

**Files:**
- Create: `src/genacademy_coach/eval_golden.py`
- Test: `tests/test_eval_golden.py`

**Interfaces:**
- Produces: `GoldenCase` (pydantic model) and `load_golden_cases(path: Path) -> list[GoldenCase]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eval_golden.py
import json
from pathlib import Path
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
    )
    base.update(over)
    return base

def test_cloud_safe_requires_reason():
    with pytest.raises(ValueError):
        GoldenCase(**_row(cloud_safe=True, cloud_safe_reason=""))

def test_test_split_rejected():
    with pytest.raises(ValueError):
        GoldenCase(**_row(split="test"))

def test_non_cloud_safe_forbids_inline_text():
    with pytest.raises(ValueError):
        GoldenCase(**_row(cloud_safe=False, cloud_safe_reason=None,
                          user_query="real learner question", source_ref="seed:abc"))

def test_loader_reads_jsonl(tmp_path):
    p = tmp_path / "g.jsonl"
    p.write_text(json.dumps(_row()) + "\n" + json.dumps(_row(case_id="happy_002")) + "\n")
    cases = load_golden_cases(p)
    assert [c.case_id for c in cases] == ["happy_001", "happy_002"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_eval_golden.py -q`
Expected: FAIL (module `genacademy_coach.eval_golden` not found).

- [ ] **Step 3: Write minimal implementation**

```python
# src/genacademy_coach/eval_golden.py
from __future__ import annotations
import json
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
    source_ref: str | None = None

    @model_validator(mode="after")
    def _check_cloud_safe(self) -> "GoldenCase":
        if self.cloud_safe:
            if not (self.cloud_safe_reason and self.cloud_safe_reason.strip()):
                raise ValueError(f"{self.case_id}: cloud_safe=true requires cloud_safe_reason")
        else:
            if any([self.user_query, self.initial_wrong_answer]):
                raise ValueError(f"{self.case_id}: cloud_safe=false must not carry inline text")
            if not self.source_ref:
                raise ValueError(f"{self.case_id}: cloud_safe=false requires source_ref")
        return self

def load_golden_cases(path: Path) -> list[GoldenCase]:
    rows: list[GoldenCase] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(GoldenCase.model_validate_json(line))
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_eval_golden.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/eval_golden.py tests/test_eval_golden.py
git commit -m "feat(eval): golden case schema + JSONL loader with cloud-safe validation"
```

---

### Task 2: Author the golden dataset + manifest

**Files:**
- Create: `eval/golden/golden_cases.jsonl`, `eval/golden/golden_manifest.json`

**Interfaces:**
- Consumes: `load_golden_cases` (Task 1); the seed/dev real questions via `scripts/eval_teach_loop.py::load_scenarios`; `eval/non_private_negative_controls.json`.

This task authors **data**, validated by code. No new production code.

- [ ] **Step 1: Enumerate real seed/dev source questions**

Run: `python -c "from genacademy_coach.settings import CoachSettings; from scripts.eval_teach_loop import load_scenarios; s=CoachSettings.from_env(); [print(x['scenario_id'], x['question_text'][:80]) for x in load_scenarios(s, split='seed', limit=999)+load_scenarios(s, split='dev', limit=999)]"`
Expected: prints the real seed/dev student questions to hand-label from. (Local-only; do not paste into committed files.)

- [ ] **Step 2: Author ~30 in-corpus cases + 10 controls**

Hand-write `eval/golden/golden_cases.jsonl`, one `GoldenCase` JSON per line:
- ≈16 `happy`, 9 `edge`, 5 `known_failure` drawn from seed/dev real questions (hand-labeled) and synthetic-from-seed paraphrases. Pure-LLM-generated < 20% of total.
- 10 `adversarial`/refusal rows from `eval/non_private_negative_controls.json` (each `refusal_expected=true`, `expected_next_action="refuse_escalate"`, `expected_tools=["retrieve_course_corpus","escalate_to_mentor"]`, `cloud_safe=true`, `cloud_safe_reason="out-of-domain control, no private text"`).
- Each in-corpus row: set `expected_citation_span_id` to a real retrieved span id (use the print from Task 8 dry-run or `scripts/diagnose_teach_retrieval.py`), `expected_next_action`, `expected_tools`, `refusal_expected=false`. Rows quoting private question text verbatim → `cloud_safe=false` + `source_ref`, no inline text.

- [ ] **Step 3: Write the manifest**

```json
{
  "version": 1,
  "seed": "genacademy-coach-golden-v1",
  "counts_by_query_type": {"happy": 16, "edge": 9, "known_failure": 5, "adversarial": 10},
  "cloud_safe_count": 40,
  "created": "2026-06-23"
}
```
(Update counts to match the actual file.)

- [ ] **Step 4: Validate the dataset loads + balance holds**

Run: `python -c "from genacademy_coach.eval_golden import load_golden_cases; from collections import Counter; c=load_golden_cases('eval/golden/golden_cases.jsonl'); print(len(c)); print(Counter(x.query_type for x in c)); assert all(x.split!='test' for x in c)"`
Expected: total in 30–50; Counter roughly 50/30/15/5 + controls; no test rows.

- [ ] **Step 5: Commit**

```bash
git add eval/golden/golden_cases.jsonl eval/golden/golden_manifest.json
git commit -m "feat(eval): hand-labeled golden dataset (~30 in-corpus + 10 controls)"
```

---

### Task 3: Extend the leak guard to scan the golden dataset

**Files:**
- Modify: `scripts/check_eval_leak.py`
- Test: `tests/test_eval_golden_leak.py`

**Interfaces:**
- Consumes: `load_golden_cases` (Task 1); the test-split needles already computed in `check_eval_leak.py::main`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eval_golden_leak.py
import json
from pathlib import Path
import pytest
from scripts.check_eval_leak import scan_golden_cases

def _write(tmp_path, rows):
    p = tmp_path / "golden_cases.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return p

def test_rejects_test_split(tmp_path):
    p = _write(tmp_path, [{"case_id":"x","split":"test","cloud_safe":True,"cloud_safe_reason":"r"}])
    offenders = scan_golden_cases(p, test_needles=set(), test_phrases={})
    assert any("test split" in o for o in offenders)

def test_flags_test_needle_in_inline_text(tmp_path):
    p = _write(tmp_path, [{"case_id":"x","split":"seed","cloud_safe":True,
                           "cloud_safe_reason":"r","user_query":"contains SECRET_ID here"}])
    offenders = scan_golden_cases(p, test_needles={"SECRET_ID"}, test_phrases={})
    assert any("SECRET_ID" in o for o in offenders)

def test_clean_golden_passes(tmp_path):
    p = _write(tmp_path, [{"case_id":"x","split":"seed","cloud_safe":True,
                           "cloud_safe_reason":"r","user_query":"what is a token"}])
    assert scan_golden_cases(p, test_needles={"SECRET_ID"}, test_phrases={}) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_eval_golden_leak.py -q`
Expected: FAIL (`scan_golden_cases` undefined).

- [ ] **Step 3: Write minimal implementation**

Add to `scripts/check_eval_leak.py` (and call it from `main` over `settings.eval_dir / "golden" / "golden_cases.jsonl"` when present, extending the existing `offenders` list before the final raise):

```python
def scan_golden_cases(path, *, test_needles, test_phrases):
    import json
    from pathlib import Path
    offenders = []
    p = Path(path)
    if not p.exists():
        return offenders
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        cid = row.get("case_id", f"line{i}")
        if row.get("split") == "test":
            offenders.append(f"golden {cid}: test split not allowed in golden set")
        if row.get("cloud_safe") and not (row.get("cloud_safe_reason") or "").strip():
            offenders.append(f"golden {cid}: cloud_safe=true missing cloud_safe_reason")
        if row.get("cloud_safe") is False and (row.get("user_query") or row.get("initial_wrong_answer")):
            offenders.append(f"golden {cid}: cloud_safe=false carries inline text")
        inline = " ".join(str(row.get(k, "")) for k in ("user_query","initial_wrong_answer","answer_text"))
        for needle in test_needles:
            if needle and needle in inline:
                offenders.append(f"golden {cid}: test needle {needle} in inline text")
        norm = " ".join(inline.lower().split())
        for phrase, matches in test_phrases.items():
            if phrase in norm:
                offenders.append(f"golden {cid}: matched test phrase")
    return offenders
```

In `main`, after building `needles` and `test_phrase_hashes`, add:
`offenders.extend(scan_golden_cases(settings.eval_dir / "golden" / "golden_cases.jsonl", test_needles=needles, test_phrases=test_phrase_hashes))`

- [ ] **Step 4: Run tests (unit + real guard)**

Run: `pytest tests/test_eval_golden_leak.py -q && python scripts/check_eval_leak.py`
Expected: unit PASS; real guard prints the no-leak message (now also covering golden).

- [ ] **Step 5: Commit**

```bash
git add scripts/check_eval_leak.py tests/test_eval_golden_leak.py
git commit -m "feat(eval): leak guard scans golden dataset for test/cloud-safe violations"
```

---

### Task 4: `TokenUsage` type + optional `TraceTurn` fields

**Files:**
- Modify: `src/genacademy_coach/teach_types.py`
- Test: `tests/test_teach_types.py` (extend)

**Interfaces:**
- Produces: `TokenUsage(input_tokens, output_tokens, total_tokens)`; `TraceTurn` gains `input_tokens`, `output_tokens`, `total_tokens`, `latency_ms` (all defaulted).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_teach_types.py (append)
from genacademy_coach.teach_types import TokenUsage, TraceTurn

def test_token_usage_defaults_zero():
    assert TokenUsage().input_tokens == 0 and TokenUsage().total_tokens == 0

def test_trace_turn_token_latency_fields_default():
    t = TraceTurn(session_id="s", turn=1, topic_hash="h", learner_input_hash="h",
                  next_action="advance", strategy="summary", evidence_score=0.5,
                  evidence_band="confirm", retrieved_citation_ids=[], tool_calls=[])
    assert t.input_tokens == 0 and t.output_tokens == 0 and t.total_tokens == 0 and t.latency_ms == 0.0
    t2 = t.model_copy(update={"input_tokens": 12, "latency_ms": 34.5})
    assert t2.input_tokens == 12 and t2.latency_ms == 34.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_teach_types.py -q`
Expected: FAIL (`TokenUsage` undefined / fields missing).

- [ ] **Step 3: Write minimal implementation**

```python
# teach_types.py — add near the top-level models
class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

# in class TraceTurn, add (after tool_calls):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_teach_types.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/teach_types.py tests/test_teach_types.py
git commit -m "feat(eval): TokenUsage type + optional token/latency fields on TraceTurn"
```

---

### Task 5: `AgentPort.last_usage` — token capture at the boundary

**Files:**
- Modify: `src/genacademy_coach/teach_session.py`
- Test: `tests/test_teach_instrumentation.py`

**Interfaces:**
- Consumes: `TokenUsage` (Task 4). Produces: `AgentPort.last_usage: TokenUsage`; `_sum_usage(messages) -> TokenUsage`.

- [ ] **Step 1: Write the failing test**

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

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_teach_instrumentation.py -q`
Expected: FAIL (`_sum_usage` / `last_usage` missing).

- [ ] **Step 3: Write minimal implementation**

In `teach_session.py`: import `TokenUsage`; add `_sum_usage`; give both ports `last_usage`.

```python
def _sum_usage(messages: list[Any]) -> TokenUsage:
    inp = out = tot = 0
    for m in messages:
        um = getattr(m, "usage_metadata", None)
        if um:
            inp += um.get("input_tokens", 0) or 0
            out += um.get("output_tokens", 0) or 0
            tot += um.get("total_tokens", 0) or 0
    return TokenUsage(input_tokens=inp, output_tokens=out, total_tokens=tot)
```
- `AgentPort` Protocol: add attribute `last_usage: TokenUsage`.
- `StaticAgentPort.__init__`: `self.last_usage = TokenUsage()` (stays zero each invoke).
- `LangChainAgentPort.__init__`: `self.last_usage = TokenUsage()`. In `invoke`, set `self.last_usage = TokenUsage()` at the top, then after `result = self._agent.invoke(...)` set `self.last_usage = _sum_usage(result.get("messages", []))` before returning.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_teach_instrumentation.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/teach_session.py tests/test_teach_instrumentation.py
git commit -m "feat(eval): capture token usage at the AgentPort boundary"
```

---

### Task 6: Latency capture + thread tokens/latency into the trace

**Files:**
- Modify: `src/genacademy_coach/teach_session.py`
- Test: `tests/test_teach_instrumentation.py` (extend)

**Interfaces:**
- Consumes: `_sum_usage`, `port.last_usage` (Task 5). Produces: `TraceTurn` rows carrying `latency_ms` + token counts.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_teach_instrumentation.py (append)
from genacademy_coach.trace import load_trace

def test_trace_records_latency_and_tokens(tmp_path, monkeypatch):
    # Build a CoachSession with StaticAgentPort over a fake foundation that returns one citeable span,
    # run start(); load the written trace; assert latency_ms >= 0.0 and token fields present (0 for static).
    ...  # use existing test_teach_session.py fixtures/factory as the template
```
(Model this on the existing `tests/test_teach_session.py` setup — reuse its fake foundation + `StaticAgentPort` wiring.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_teach_instrumentation.py::test_trace_records_latency_and_tokens -q`
Expected: FAIL (TraceTurn written with default 0.0 latency before the change is wired).

- [ ] **Step 3: Write minimal implementation**

- Add `import time` to `teach_session.py`.
- In `_invoke_agent`, wrap the port call: `start = time.perf_counter()` before `self.agent_port.invoke(...)`; `latency_ms = (time.perf_counter() - start) * 1000.0` after (in both success and `AgentResponseError` branches). For the turn-budget early return, `latency_ms = 0.0`.
- Pass `latency_ms` and `self.agent_port.last_usage` through to `_write_result`; add params `latency_ms: float = 0.0, usage: TokenUsage | None = None`.
- In `_write_result`, set `usage = usage or TokenUsage()` and add to the `TraceTurn(...)` call: `input_tokens=usage.input_tokens, output_tokens=usage.output_tokens, total_tokens=usage.total_tokens, latency_ms=latency_ms`.

- [ ] **Step 4: Run tests (instrumentation + full suite for regressions)**

Run: `pytest tests/test_teach_instrumentation.py tests/test_teach_session.py -q`
Expected: PASS; no regression in existing teach-session tests.

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/teach_session.py tests/test_teach_instrumentation.py
git commit -m "feat(eval): record per-turn latency and token usage in the trace"
```

---

### Task 7: Pure `eval_metrics` module + `PriceTable`

**Files:**
- Create: `src/genacademy_coach/eval_metrics.py`
- Test: `tests/test_eval_metrics.py`

**Interfaces:**
- Produces: `precision_recall_f1`, `citation_prf`, `tool_match`, `recall_at_k`, `refusal_outcome`, `PriceTable`, `aggregate`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eval_metrics.py
from genacademy_coach.eval_metrics import (
    precision_recall_f1, citation_prf, tool_match, recall_at_k, refusal_outcome, PriceTable)

def test_prf_basic():
    p, r, f = precision_recall_f1(tp=8, fp=2, fn=2)
    assert round(p,2)==0.8 and round(r,2)==0.8 and round(f,2)==0.8

def test_citation_prf_sets():
    p, r, f = citation_prf(predicted={"a","b"}, expected={"a"})
    assert round(p,2)==0.5 and r==1.0

def test_tool_match_ordered():
    m = tool_match(actual=["retrieve_course_corpus","grade_understanding"],
                   expected=["retrieve_course_corpus","grade_understanding"])
    assert m["f1"]==1.0 and m["ordered_ok"] is True

def test_recall_at_k():
    assert recall_at_k(["x","y","z"], "y", k=5) is True
    assert recall_at_k(["x","y","z"], "q", k=2) is False

def test_refusal_outcome():
    assert refusal_outcome(refusal_expected=True, actual_next_action="refuse_escalate")=="tp"
    assert refusal_outcome(refusal_expected=False, actual_next_action="refuse_escalate")=="fp"

def test_price_table_cost():
    pt = PriceTable(prices={"m": (1e-6, 2e-6)})
    assert pt.cost("m", input_tokens=1000, output_tokens=1000) == 0.003
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_eval_metrics.py -q`
Expected: FAIL (module missing).

- [ ] **Step 3: Write minimal implementation**

```python
# src/genacademy_coach/eval_metrics.py
from __future__ import annotations
from dataclasses import dataclass

def precision_recall_f1(*, tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f

def citation_prf(*, predicted: set[str], expected: set[str]) -> tuple[float, float, float]:
    tp = len(predicted & expected); fp = len(predicted - expected); fn = len(expected - predicted)
    return precision_recall_f1(tp=tp, fp=fp, fn=fn)

def tool_match(*, actual: list[str], expected: list[str]) -> dict:
    sa, se = set(actual), set(expected)
    tp = len(sa & se); fp = len(sa - se); fn = len(se - sa)
    p, r, f = precision_recall_f1(tp=tp, fp=fp, fn=fn)
    ordered_ok = [t for t in actual if t in se] == [t for t in expected if t in sa]
    return {"precision": p, "recall": r, "f1": f, "ordered_ok": ordered_ok}

def recall_at_k(ranked_ids: list[str], expected_id: str | None, *, k: int = 5) -> bool:
    return bool(expected_id) and expected_id in ranked_ids[:k]

def refusal_outcome(*, refusal_expected: bool, actual_next_action: str) -> str:
    refused = actual_next_action == "refuse_escalate"
    if refusal_expected and refused: return "tp"
    if refusal_expected and not refused: return "fn"
    if not refusal_expected and refused: return "fp"
    return "tn"

@dataclass(frozen=True)
class PriceTable:
    prices: dict[str, tuple[float, float]]  # model_id -> (input_usd_per_token, output_usd_per_token)
    def cost(self, model_id: str, *, input_tokens: int, output_tokens: int) -> float:
        pin, pout = self.prices.get(model_id, (0.0, 0.0))
        return input_tokens * pin + output_tokens * pout
```
Add an `aggregate(rows: list[dict]) -> dict` that rolls per-metric tp/fp/fn into P/R/F1, computes latency p50/p95 (use `statistics.quantiles` or a sorted-index helper), sums cost/tokens, and reports class balance. Cover `aggregate` with one test over 3 fixture rows.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_eval_metrics.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/eval_metrics.py tests/test_eval_metrics.py
git commit -m "feat(eval): pure metrics module (P/R/F1, citation_f1, tool_f1, recall@5, cost)"
```

---

### Task 8: `run_golden_eval.py` runner + run artifact

**Files:**
- Create: `scripts/run_golden_eval.py`
- Test: `tests/test_run_golden_eval.py`

**Interfaces:**
- Consumes: `load_golden_cases` (T1), `eval_metrics` (T7), the `score_scenario` pattern in `scripts/eval_teach_loop.py`, `grounding.py` grader, `foundation.retrieve`.
- Produces: `score_golden_case(...) -> dict` (band b+c row) and `run_golden_eval(...)` writing `eval/runs/golden-<tag>-<date>.json`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_run_golden_eval.py
from genacademy_coach.eval_golden import GoldenCase
from scripts.run_golden_eval import score_golden_case

def test_score_golden_case_emits_metric_row(fake_settings, fake_foundation):
    case = GoldenCase(case_id="happy_001", query_type="happy", concept="tokenization",
        expected_citation_span_id="doc::3", target_check_id="chk1", expected_next_action="advance",
        expected_tools=["retrieve_course_corpus","generate_check_item","grade_understanding"],
        refusal_expected=False, strategy_changed_on_stumble=True, split="seed",
        cloud_safe=True, cloud_safe_reason="synthetic", user_query="what is a token")
    row = score_golden_case(settings=fake_settings, foundation=fake_foundation, case=case,
                            session_factory=FakeSession)  # reuse test_eval_teach_loop fakes
    for key in ("task_completion_pass","citation_f1","tool_f1","retrieval_recall_at_5",
                "refusal_outcome","latency_p95_ms","input_tokens","output_tokens","cost_usd"):
        assert key in row
    # non-cloud-safe redaction:
    assert "answer_text" in row  # present (case is cloud_safe)
```
(Reuse the fakes from `tests/test_eval_teach_loop.py` for `fake_settings`/`fake_foundation`/`FakeSession`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_run_golden_eval.py -q`
Expected: FAIL (module missing).

- [ ] **Step 3: Write minimal implementation**

Build `scripts/run_golden_eval.py`:
- `score_golden_case`: reuse the `eval_teach_loop.score_scenario` 3-turn pattern (start → wrong → expected). Capture actual tool sequence from the trace (`load_trace` → `tool_calls`), `actual_next_action`, predicted `citation_ids`, `evidence_score`/`band`, summed `latency_ms`/tokens from the trace turns. For recall@5, call `foundation.retrieve(case.user_query)` and take the top-5 `chunk_id`s. Compute: `task_completion_pass` (grounded grader correct on the expected-answer turn), `citation_prf(predicted, {expected_citation_span_id})`, `tool_match(actual, expected_tools)`, `recall_at_k(top5, expected_citation_span_id)`, `refusal_outcome(...)`. Redact: include `answer_text` only when `case.cloud_safe`.
- `run_golden_eval(settings, foundation, cases, tag)`: map `score_golden_case` over cases, `eval_metrics.aggregate(rows)`, write `eval/runs/golden-<tag>-<YYYYMMDD>.json` (`sort_keys=True`), print the summary.
- `main()`: argparse `--tag` (default `baseline`), `--limit`; `load_local_env()` (reuse from `eval_teach_loop`).

- [ ] **Step 4: Run tests + a real dry-run**

Run: `pytest tests/test_run_golden_eval.py -q`
Expected: PASS.
Run (real, local, needs the index + provider): `python scripts/run_golden_eval.py --tag baseline --limit 3`
Expected: writes `eval/runs/golden-baseline-<date>.json` with per-metric P/R/F1 + latency p95 + cost.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_golden_eval.py tests/test_run_golden_eval.py
git commit -m "feat(eval): golden-set runner emitting per-metric P/R/F1 + cost/latency"
```

---

## Final verification (evidence before done — gate #3)

- [ ] `ruff check .` clean.
- [ ] `pytest -q` green (show output).
- [ ] `python scripts/check_eval_leak.py` prints the no-leak message (now covering golden).
- [ ] `python scripts/run_golden_eval.py --tag baseline` writes a run artifact with all metric keys.

## Self-Review

- **Spec coverage:** Stage 1 → Tasks 1–3; Stage 2 → Tasks 4–6; Stage 3 → Tasks 7–8. Fork 1 (instrumentation seam) = Tasks 4–6. Fork 2 (format) = Tasks 1–3. Fork 3 (scoring) = Tasks 7–8. Fork 4 (judge) is Plan 2.
- **Type consistency:** `TokenUsage` defined T4, consumed T5/T6; `GoldenCase` T1 → T2/T3/T8; `eval_metrics` names T7 → T8; tool names match `teach_tools.py`.
- **Placeholders:** Task 6/Task 8 test bodies reference existing fixtures (`tests/test_teach_session.py`, `tests/test_eval_teach_loop.py`) rather than restating them — the implementer copies those fakes; this is intentional reuse, not a TBD.

## Execution Handoff

Two execution options:
1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks.
2. **Inline Execution** — execute tasks in this session with checkpoints.

Per the standing flow (Codex-review the plan → build), this plan goes to a Codex review first; on PASS + merge, Stage 1 (Task 1) starts.
