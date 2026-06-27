# Role-Keyed Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox
> (`- [ ]`) syntax for tracking.

**Goal:** Add role-keyed citation provenance and deterministic check-span selection so Teach evals can
distinguish teaching, check, final, and future recovery evidence without guessing from scattered fields.

**Architecture:** Keep the current LangChain `create_agent` teach loop and existing tool surface. Add a
small typed provenance record in the pure core, store provenance on `TeachRuntime`, write it into redacted
trace rows, and expose backward-compatible eval fields plus new per-role IDs. Enforce check-span
selection in Python: slide first, then handout, then first citeable span.

**Tech Stack:** Python 3.12, Pydantic models in `teach_types.py`, existing `TeachRuntime`, existing
trace/eval runner, pytest, ruff. No direct `langgraph.*` imports. No frozen `test` split use.

---

## Context

PR #51 added a public-safe citation audit. The audit found:

- 14 teachable citation miss rows in the inspected current-main run.
- Current teachable citation F1: `0.5777777777777777`.
- Heuristic same-source-family ceiling: `0.7333333333333333`.
- Retrieval recall@5 stayed healthy, so the next fix is post-retrieval provenance and check-span
  selection, not retrieval expansion.

This plan is product behavior work. Do not start it until reviewed and approved.

## Scope

### In Scope

- Add typed role-keyed provenance records for `teaching`, `check`, `final`, and deferred `recovery`.
- Record provenance when evidence is selected, not by parsing generated text later.
- Enforce deterministic check-span selection: first citeable `slide`, then first citeable `handout`,
  then first citeable span.
- Add redacted provenance to trace rows and eval rows.
- Preserve existing eval fields: `answered_check_id`, `post_final_check_id`,
  `boundary_grade_citation_id`, `predicted_citation_ids`.
- Add tests for runtime provenance, deterministic check selection, trace redaction, and eval output.

### Out Of Scope

- Golden label changes.
- Metric/scorer-definition changes.
- Turn-2 recovery loop.
- False-refusal threshold changes.
- Semantic grading.
- Memory-personalized recovery.
- Any frozen `test` split use.
- Direct `langgraph.*` imports.

## Planned Files

- Modify `src/genacademy_coach/teach_types.py`
  - Add `ProvenanceRole` and `ProvenanceRecord`.
  - Add `provenance` field to `TraceTurn`.
- Modify `src/genacademy_coach/teach_tools.py`
  - Add role-keyed provenance storage and helper methods to `TeachRuntime`.
  - Replace citation-id-only preferred check helper with deterministic span selection.
  - Enforce preferred check-span selection inside `generate_check_item_for_span`.
- Modify `src/genacademy_coach/teach_agent.py`
  - Update prompt text so the model knows the runtime enforces preferred check-span selection.
- Modify `src/genacademy_coach/teach_session.py`
  - Record `final` provenance for finalized cited responses.
  - Include runtime provenance in trace rows.
- Modify `src/genacademy_coach/eval_runner.py`
  - Emit `provenance_by_role`, `teaching_provenance_span_id`, `check_provenance_span_id`,
    `final_provenance_span_id`.
  - Keep old fields unchanged.
- Modify `tests/test_teach_types.py`
  - Test provenance model validation and trace serialization.
- Modify `tests/test_teach_tools.py`
  - Test deterministic check-span selection and provenance recording.
- Modify `tests/test_teach_session.py`
  - Test trace provenance is redacted and final provenance follows finalized citation.
- Modify `tests/test_eval_runner.py`
  - Test eval rows include new provenance fields without leaking private text.

## Data Shape

Add this model in `src/genacademy_coach/teach_types.py`:

```python
ProvenanceRole = Literal["teaching", "check", "final", "recovery"]


class ProvenanceRecord(BaseModel):
    role: ProvenanceRole
    span_id: str
    source_type: str
    selected_at: str
    selection_reason: str
```

Trace rows will carry:

```python
provenance: dict[ProvenanceRole, ProvenanceRecord] = Field(default_factory=dict)
```

Committed traces still must not include raw learner text, tutor prose, retrieved span text, private URLs,
or secrets. The provenance record contains IDs and source metadata only.

Each role stores one primary span. For multi-citation final responses, `final` records the first
retrieved citation used by the finalized answer; the full citation list remains in
`predicted_citation_ids` and `response.citation_ids`. This is intentional for the first slice: one
primary span per role is enough to debug provenance drift without changing the scorer or widening trace
payloads.

## Task 0: Capture Pre-Change Golden Metrics

**Files:**
- No source changes.

- [ ] **Step 1: Run current local golden baseline before product code changes**

Run this before implementing Tasks 1-6:

```bash
uv run python scripts/run_golden_eval.py \
  --tag provenance-before \
  --run-id provenance-before
```

Expected:

- A local ignored file appears under `eval/runs/`.
- No frozen `test` split rows are used.
- Record the output path, `metrics.citation_f1`, `metrics.task_completion.pass_rate`,
  `metrics.refusal.precision`, and `metrics.refusal.recall` in the PR body or implementation handoff.

If provider credentials or the local index are unavailable, stop and record the blocker before coding.
Do not silently replace this with the frozen `test` split or a synthetic-only run.

## Task 1: Add Provenance Types

**Files:**
- Modify: `src/genacademy_coach/teach_types.py`
- Modify: `tests/test_teach_types.py`

- [ ] **Step 1: Write failing tests for provenance records**

Add to `tests/test_teach_types.py`:

```python
from genacademy_coach.teach_types import ProvenanceRecord, TraceTurn


def test_provenance_record_serializes_safe_metadata_only():
    record = ProvenanceRecord(
        role="check",
        span_id="slide/week2-session1::3",
        source_type="slide",
        selected_at="generate_check_item",
        selection_reason="preferred_slide",
    )

    assert record.model_dump() == {
        "role": "check",
        "span_id": "slide/week2-session1::3",
        "source_type": "slide",
        "selected_at": "generate_check_item",
        "selection_reason": "preferred_slide",
    }


def test_trace_turn_accepts_role_keyed_provenance():
    turn = TraceTurn(
        session_id="s",
        turn=1,
        topic_hash="topic-hash",
        learner_input_hash="input-hash",
        next_action="drill",
        strategy="analogy",
        evidence_score=0.91,
        evidence_band="proceed",
        retrieved_citation_ids=["slide/week2-session1::3"],
        tool_calls=[],
        provenance={
            "check": ProvenanceRecord(
                role="check",
                span_id="slide/week2-session1::3",
                source_type="slide",
                selected_at="generate_check_item",
                selection_reason="preferred_slide",
            )
        },
    )

    assert turn.provenance["check"].span_id == "slide/week2-session1::3"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest -q tests/test_teach_types.py::test_provenance_record_is_public_safe_metadata tests/test_teach_types.py::test_trace_turn_accepts_role_keyed_provenance
```

Expected: fail because `ProvenanceRecord` does not exist.

- [ ] **Step 3: Add models**

In `src/genacademy_coach/teach_types.py`, update imports and add:

```python
ProvenanceRole = Literal["teaching", "check", "final", "recovery"]


class ProvenanceRecord(BaseModel):
    role: ProvenanceRole
    span_id: str
    source_type: str
    selected_at: str
    selection_reason: str
```

Add to `TraceTurn`:

```python
    provenance: dict[ProvenanceRole, ProvenanceRecord] = Field(default_factory=dict)
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
uv run pytest -q tests/test_teach_types.py::test_provenance_record_is_public_safe_metadata tests/test_teach_types.py::test_trace_turn_accepts_role_keyed_provenance
```

Expected: pass.

## Task 2: Add Runtime Provenance Helpers

**Files:**
- Modify: `src/genacademy_coach/teach_tools.py`
- Modify: `tests/test_teach_tools.py`

- [ ] **Step 1: Write failing test for runtime provenance helpers**

Add to `tests/test_teach_tools.py`:

```python
def test_runtime_records_role_keyed_provenance(tmp_path):
    active_runtime = runtime(tmp_path)
    span = RetrievedSpan(
        chunk_id="slide/attention::1",
        doc_id="slide/attention",
        text="Attention highlights relevant context.",
        score=0.91,
        title="attention.pdf",
        source_type="slide",
        page_or_section="1",
    )

    active_runtime.record_provenance(
        role="check",
        span=span,
        selected_at="generate_check_item",
        selection_reason="preferred_slide",
    )

    record = active_runtime.provenance["check"]
    assert record.role == "check"
    assert record.span_id == "slide/attention::1"
    assert record.source_type == "slide"
    assert record.selected_at == "generate_check_item"
    assert record.selection_reason == "preferred_slide"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run pytest -q tests/test_teach_tools.py::test_runtime_records_role_keyed_provenance
```

Expected: fail because `TeachRuntime.record_provenance` does not exist.

- [ ] **Step 3: Add runtime field and helper**

In `src/genacademy_coach/teach_tools.py`, import:

```python
    ProvenanceRecord,
    ProvenanceRole,
```

Add to `TeachRuntime`:

```python
    provenance: dict[ProvenanceRole, ProvenanceRecord] = field(default_factory=dict)
```

Add method:

```python
    def record_provenance(
        self,
        *,
        role: ProvenanceRole,
        span: RetrievedSpan,
        selected_at: str,
        selection_reason: str,
    ) -> None:
        self.provenance[role] = ProvenanceRecord(
            role=role,
            span_id=span.citation_id,
            source_type=span.source_type,
            selected_at=selected_at,
            selection_reason=selection_reason,
        )
```

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
uv run pytest -q tests/test_teach_tools.py::test_runtime_records_role_keyed_provenance
```

Expected: pass.

## Task 3: Enforce Deterministic Check-Span Selection

**Files:**
- Modify: `src/genacademy_coach/teach_agent.py`
- Modify: `src/genacademy_coach/teach_tools.py`
- Modify: `tests/test_teach_tools.py`

- [ ] **Step 1: Write failing test for enforced preferred span**

Add to `tests/test_teach_tools.py`:

```python
def test_generate_check_uses_preferred_slide_even_when_agent_requests_note(
    tmp_path,
    monkeypatch,
):
    active_runtime = runtime(tmp_path)
    active_runtime.last_spans = [
        RetrievedSpan(
            chunk_id="note/attention::0",
            doc_id="note/attention",
            text="Attention focuses relevant context.",
            score=0.95,
            title="attention.md",
            source_type="note",
        ),
        RetrievedSpan(
            chunk_id="handout/attention::2",
            doc_id="handout/attention",
            text="Attention helps select relevant context.",
            score=0.93,
            title="attention.pdf",
            source_type="handout",
            page_or_section="2",
        ),
        RetrievedSpan(
            chunk_id="slide/attention::1",
            doc_id="slide/attention",
            text="Attention highlights the relevant context window.",
            score=0.91,
            title="attention.pdf",
            source_type="slide",
            page_or_section="1",
        ),
    ]

    def fake_generate_check_item(_provider, span):
        return CheckItem(
            question="What does attention highlight?",
            expected_answer="Attention highlights the relevant context window.",
            expected_keywords=["relevant context"],
            citation_id=span.citation_id,
        )

    monkeypatch.setattr(
        "genacademy_coach.teach_tools.generate_check_item",
        fake_generate_check_item,
    )
    generate_tool = next(
        tool for tool in build_teach_tools(active_runtime)
        if tool.name == "generate_check_item_for_span"
    )

    generated = json.loads(generate_tool.invoke({"citation_id": "note/attention::0"}))

    assert generated["citation_id"] == "slide/attention::1"
    assert active_runtime.current_check is not None
    assert active_runtime.current_check.citation_id == "slide/attention::1"
    assert active_runtime.provenance["check"].span_id == "slide/attention::1"
    assert active_runtime.provenance["check"].selection_reason == "preferred_slide"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run pytest -q tests/test_teach_tools.py::test_generate_check_uses_preferred_slide_even_when_agent_requests_note
```

Expected: fail because current behavior uses the requested note span.

- [ ] **Step 3: Replace preferred ID helper with preferred span helper**

In `src/genacademy_coach/teach_tools.py`, replace `_preferred_check_citation_id` with:

```python
def _preferred_check_span(spans: list[RetrievedSpan]) -> tuple[RetrievedSpan | None, str]:
    for span in spans:
        if span.source_type == "slide":
            return span, "preferred_slide"
    for span in spans:
        if span.source_type == "handout":
            return span, "preferred_handout"
    if spans:
        return spans[0], "first_citeable"
    return None, "no_citeable_span"
```

Update `_retrieval_rows`:

```python
    preferred_check_span, _ = _preferred_check_span(spans)
    preferred_check_id = (
        preferred_check_span.citation_id if preferred_check_span is not None else None
    )
```

- [ ] **Step 4: Enforce preferred span in check generation**

Inside `generate_check_item_for_span`, keep unknown-ID rejection, then select the preferred span. This
means the `citation_id` parameter remains a validation gate proving the agent requested a retrieved
span, while Python still enforces the preferred citeable span for the generated check:

```python
            span_by_id = {span.citation_id: span for span in runtime.last_spans}
            if citation_id not in span_by_id:
                return json.dumps({"error": f"unknown citation_id: {citation_id}"})
            selected_span, selection_reason = _preferred_check_span(runtime.last_spans)
            if selected_span is None:
                return json.dumps({"error": "no citeable span available"})
            if (
                runtime.current_check is not None
                and runtime.current_check.citation_id == selected_span.citation_id
            ):
                runtime.record_provenance(
                    role="check",
                    span=selected_span,
                    selected_at="generate_check_item",
                    selection_reason=selection_reason,
                )
                return runtime.current_check.model_dump_json()
            runtime.current_check = generate_check_item(
                runtime.foundation.provider,
                selected_span,
            )
            runtime.record_provenance(
                role="check",
                span=selected_span,
                selected_at="generate_check_item",
                selection_reason=selection_reason,
            )
            runtime.grade_locked = False
            return runtime.current_check.model_dump_json()
```

- [ ] **Step 5: Update tool documentation and agent prompt**

In `src/genacademy_coach/teach_tools.py`, update the tool docstring:

```python
    @tool
    def generate_check_item_for_span(citation_id: str) -> str:
        """Generate a check for the runtime-preferred retrieved span.

        The citation_id must be a retrieved span ID, but the runtime enforces check-span
        selection in this order: slide, handout, first citeable span.
        """
```

In `src/genacademy_coach/teach_agent.py`, update the check-span instruction so it no longer implies
the model has final authority over span choice:

```python
- When calling generate_check_item_for_span, pass a retrieved citation_id. The runtime will enforce
  the preferred check span in this order: slide, handout, then first citeable span.
```

- [ ] **Step 6: Run teach-tools and agent prompt tests**

Run:

```bash
uv run pytest -q tests/test_teach_tools.py tests/test_teach_agent.py
```

Expected: pass.

## Task 4: Record Teaching And Final Provenance

**Files:**
- Modify: `src/genacademy_coach/teach_tools.py`
- Modify: `src/genacademy_coach/teach_session.py`
- Modify: `tests/test_teach_session.py`

- [ ] **Step 1: Record teaching provenance on successful retrieval**

In `retrieve_course_corpus`, immediately after `runtime.last_spans = citeable_spans`, add:

```python
                runtime.record_provenance(
                    role="teaching",
                    span=citeable_spans[0],
                    selected_at="retrieve_course_corpus",
                    selection_reason="first_citeable_retrieved",
                )
```

- [ ] **Step 2: Write failing test for trace provenance**

Add to `tests/test_teach_session.py`:

```python
def test_session_trace_records_role_keyed_provenance(tmp_path):
    agent = StaticAgentPort(
        CoachAgentResponse(
            learner_message="Attention highlights relevant context. [note/attention::0]",
            observation="retrieved a citeable attention span",
            next_action="advance",
            strategy="summary",
            citation_ids=["note/attention::0"],
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
    session.runtime.record_provenance(
        role="teaching",
        span=cited_span(),
        selected_at="retrieve_course_corpus",
        selection_reason="first_citeable_retrieved",
    )

    result = session.start()

    rows = load_trace(Path(result.trace_path))
    assert rows[0].provenance["teaching"].span_id == "note/attention::0"
    assert rows[0].provenance["final"].span_id == "note/attention::0"
    serialized = Path(result.trace_path).read_text(encoding="utf-8")
    assert "Attention highlights relevant context." not in serialized
    assert "learner_message" not in serialized
```

- [ ] **Step 3: Run test to verify failure**

Run:

```bash
uv run pytest -q tests/test_teach_session.py::test_session_trace_records_role_keyed_provenance
```

Expected: fail because traces do not include provenance and final provenance is not recorded.

- [ ] **Step 4: Add final provenance helper**

In `CoachSession`, add:

```python
    def _record_final_provenance(self, response: CoachAgentResponse) -> None:
        if response.next_action in {"refuse_escalate", "stop"}:
            return
        retrieved_by_id = {span.citation_id: span for span in self.runtime.last_spans}
        for citation_id in response.citation_ids:
            span = retrieved_by_id.get(citation_id)
            if span is not None:
                self.runtime.record_provenance(
                    role="final",
                    span=span,
                    selected_at="write_result",
                    selection_reason="first_final_citation",
                )
                return
```

At the start of `_write_result`, after `usage = usage or TokenUsage()`, call:

```python
        self._record_final_provenance(response)
```

- [ ] **Step 5: Include provenance in trace**

In `_write_result`, add this field to `TraceTurn(...)`:

```python
                provenance=dict(self.runtime.provenance),
```

- [ ] **Step 6: Run teach-session tests**

Run:

```bash
uv run pytest -q tests/test_teach_session.py
```

Expected: pass.

## Task 5: Add Eval Provenance Fields

**Files:**
- Modify: `src/genacademy_coach/eval_runner.py`
- Modify: `tests/test_eval_runner.py`

- [ ] **Step 1: Write failing test for eval provenance fields**

In `tests/test_eval_runner.py`, extend `test_score_golden_case_emits_redacted_metric_row` with:

```python
    assert "provenance_by_role" in row
    assert row["teaching_provenance_span_id"] == "note::0"
    assert row["check_provenance_span_id"] == "note::0"
    assert row["final_provenance_span_id"] == "note::0"
```

Update `FakeSession` in the same test file so its runtime has:

```python
        self.runtime.provenance = {
            "teaching": ProvenanceRecord(
                role="teaching",
                span_id="note::0",
                source_type="note",
                selected_at="retrieve_course_corpus",
                selection_reason="first_citeable_retrieved",
            ),
            "check": ProvenanceRecord(
                role="check",
                span_id="note::0",
                source_type="note",
                selected_at="generate_check_item",
                selection_reason="first_citeable",
            ),
            "final": ProvenanceRecord(
                role="final",
                span_id="note::0",
                source_type="note",
                selected_at="write_result",
                selection_reason="first_final_citation",
            ),
        }
```

Add import:

```python
from genacademy_coach.teach_types import ProvenanceRecord
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run pytest -q tests/test_eval_runner.py::test_score_golden_case_emits_redacted_metric_row
```

Expected: fail because eval rows do not include provenance fields.

- [ ] **Step 3: Add redacted eval fields**

In `score_golden_case`, before the `row` dict:

```python
    provenance_by_role = {
        role: record.model_dump()
        for role, record in getattr(session.runtime, "provenance", {}).items()
    }
```

Add to `row`:

```python
        "provenance_by_role": provenance_by_role,
        "teaching_provenance_span_id": (
            provenance_by_role.get("teaching", {}).get("span_id")
        ),
        "check_provenance_span_id": provenance_by_role.get("check", {}).get("span_id"),
        "final_provenance_span_id": provenance_by_role.get("final", {}).get("span_id"),
```

- [ ] **Step 4: Run eval-runner tests**

Run:

```bash
uv run pytest -q tests/test_eval_runner.py
```

Expected: pass.

## Task 6: Keep Audit Backward Compatible And Provenance-Aware

**Files:**
- Modify: `scripts/audit_citation_provenance.py`
- Modify: `tests/test_audit_citation_provenance.py`

- [ ] **Step 1: Write failing test for provenance-aware audit rows**

Add to `tests/test_audit_citation_provenance.py`:

```python
def test_audit_row_includes_optional_role_provenance_ids():
    module = load_audit_module()

    audited = module.audit_row(
        row(
            provenance_by_role={
                "check": {
                    "role": "check",
                    "span_id": "slide/week2-session1::3",
                    "source_type": "slide",
                    "selected_at": "generate_check_item",
                    "selection_reason": "preferred_slide",
                },
                "final": {
                    "role": "final",
                    "span_id": "slide/week2-session1::4",
                    "source_type": "slide",
                    "selected_at": "write_result",
                    "selection_reason": "first_final_citation",
                },
            }
        )
    )

    assert audited["check_provenance_span_id"] == "slide/week2-session1::3"
    assert audited["final_provenance_span_id"] == "slide/week2-session1::4"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run pytest -q tests/test_audit_citation_provenance.py::test_audit_row_includes_optional_role_provenance_ids
```

Expected: fail because audit rows do not include optional provenance IDs.

- [ ] **Step 3: Add optional provenance ID projection**

In `audit_row`, before returning:

```python
    provenance_by_role = row.get("provenance_by_role") or {}
    check_provenance = (
        provenance_by_role.get("check", {}) if isinstance(provenance_by_role, dict) else {}
    )
    final_provenance = (
        provenance_by_role.get("final", {}) if isinstance(provenance_by_role, dict) else {}
    )
```

Add fields:

```python
        "check_provenance_span_id": check_provenance.get("span_id"),
        "final_provenance_span_id": final_provenance.get("span_id"),
```

- [ ] **Step 4: Run audit tests**

Run:

```bash
uv run pytest -q tests/test_audit_citation_provenance.py
```

Expected: pass.

## Task 7: Verification And Review Prep

**Files:**
- No new source files.

- [ ] **Step 1: Run focused tests**

Run:

```bash
uv run pytest -q \
  tests/test_teach_types.py \
  tests/test_teach_tools.py \
  tests/test_teach_session.py \
  tests/test_eval_runner.py \
  tests/test_audit_citation_provenance.py
```

Expected: all pass.

- [ ] **Step 2: Run full static and test gates**

Run:

```bash
uv run ruff check .
uv run pytest -q
uv run python scripts/check_eval_leak.py
uv run python scripts/check_memory_leak.py
```

Expected:

- Ruff passes.
- Pytest passes.
- Eval leak checker reports no eval test IDs/checksums and no eval n-grams found where private eval
  sources are available.
- Memory leak checker reports no raw memory leaks.

- [ ] **Step 3: Run post-change local golden eval and compare against Task 0**

Run:

```bash
uv run python scripts/run_golden_eval.py \
  --tag provenance-after \
  --run-id provenance-after
```

Expected:

- A local ignored file appears under `eval/runs/`.
- Rows include `provenance_by_role`, `check_provenance_span_id`, and `final_provenance_span_id`.
- No frozen `test` split rows are used.
- Compare against the Task 0 `provenance-before` run:
  - `metrics.citation_f1`
  - `metrics.task_completion.pass_rate`
  - `metrics.refusal.precision`
  - `metrics.refusal.recall`
- Report whether citation F1 improved and whether task completion or refusal safety regressed.
- Do not commit the generated `eval/runs/` file.

If provider credentials or the local index are unavailable, report that the golden before/after could
not be run and do not claim measured product improvement. Unit tests alone are not enough to call this
product-behavior slice done.

- [ ] **Step 4: Review for guardrails**

Run:

```bash
rg -n "from langgraph|import langgraph|user_query|answer_text|retrieved_span_text|smith\\.langchain\\.com" \
  src/genacademy_coach scripts tests docs/superpowers/plans/2026-06-27-role-keyed-provenance.md
```

Expected:

- No direct `langgraph.*` imports.
- Any `user_query` / `answer_text` hits are existing tests or explicit leak guards, not new committed
  raw content.
- No private LangSmith URLs.

## Success Criteria

- Check generation uses the deterministic preferred span even if the model requests a nonpreferred
  retrieved span.
- `TeachRuntime.provenance` records `teaching`, `check`, and `final` roles with safe metadata only.
- Trace rows include redacted role-keyed provenance.
- Eval rows include new per-role provenance IDs while preserving old fields.
- Existing tests and privacy leak checks pass.
- Local golden before/after is reported, or an explicit provider/index blocker is recorded without
  claiming product improvement.
- No frozen `test` split use.
- No direct `langgraph.*` imports.

## Reviewer Notes

- This plan intentionally does not change citation scoring. It only makes evidence selection explicit
  and auditable.
- Do not delete legacy eval fields in this slice; dashboards and audit tools may still depend on them.
- PR #53 implements `TeachRuntime.provenance` as best-known provenance for the current session/case.
  Trace rows snapshot that current best-known map, so a later turn may carry an earlier turn's
  teaching/check provenance if no new span is selected. This is intentional for the first
  implementation slice because eval row projection reads the runtime's final known role map. If exact
  per-turn provenance becomes important, reset provenance at turn start and keep eval projection
  behavior explicit.
- `final_provenance_span_id` records the first retrieved citation used by the finalized answer. The
  full final citation set remains in `predicted_citation_ids` and `response.citation_ids`.
- If deterministic check-span enforcement causes a task-completion regression, stop and report before
  adding fallback complexity. The intended change is narrow and reversible.
- Task 6 stays in this slice to keep the audit tool provenance-aware, but it must remain a read-only
  projection change. If it starts changing scoring or labels, split it into a follow-up PR.
