# Tutor Workspace Phase-1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the split-pane Tutor Workspace slice — a read-only provenance-projection panel
(evidence/clarify/refusal states, per-lane sections, slide-visual card, deterministic next-step
chips, posture chip + collapsed "Behind this answer" disclosure) wired into the existing local
Gradio app, per `docs/superpowers/specs/2026-06-30-tutor-workspace-and-target-architecture-design.md`
§5 and PRD FR-W1..FR-W11.

**Architecture:** Four new pure-core modules (`source_labels.py`, `panel_payload.py`,
`slide_images.py`, `suggestions.py`) build a `PanelPayload` from the SAME turn objects the engine
already produces (`CoachAgentResponse`, the turn's `RetrievedSpan` pool, `TraceTurn.evidence_band`
+ `provenance`) — never a second retrieval. The Gradio app renders the payload as a third column
in the Teach tab. Slide page images are pre-rendered from the decks into a gitignored store and
looked up at runtime by citation → slide-index resolution (deck text already carries `# Slide N`
markers; the index is untouched).

**Tech Stack:** Python 3.12, pydantic v2 (`BaseModel`, `Literal` — match `teach_types.py` style),
pytest, Gradio (`gr.Blocks`, allow-listed components), LibreOffice `soffice` + `pdftoppm` for the
one-time deck render, `uv` for everything.

## Global Constraints

- **No second retrieval:** `PanelPayload` and chips derive only from the turn's own objects
  (response, span pool, trace turn). No retriever import in the new pure-core modules.
- **Provenance-subset invariant:** no panel item without a `citation_id` already in the turn's
  `response.citation_ids`; chips anchor only to the turn's own pool / store / profile.
- **Bands:** `EvidenceBand = "stop" | "confirm" | "proceed"` (from `teach_types.py`). `stop` (or
  `next_action == "refuse_escalate"`) → `refusal`; `confirm` → `clarify`; `proceed` → `evidence`.
  Clarify is in-corpus only — never a refusal bypass.
- **Privacy:** no raw filename / path / URL / `::` chunk suffix in any learner-facing string; reuse
  `RetrievedSpan.source_label` (already strips extensions + hash suffixes). Tests use synthetic
  spans only — no real corpus text in committed test files.
- **Lane names (FR-W5):** `transcript` → "Instructor explanation", `qa` → "Cohort Q&A"; every lane
  id maps (unknown → "Course material", never raw taxonomy fallthrough).
- **Slide images (FR-W9):** real rendered deck pages only, stored under `data/slide_images/`
  (gitignored, runtime-only); `slide_image_ref` only on slide-lane items whose file exists.
- **Chips (FR-W10):** deterministic, no new model calls; ≤ 4; every chip has a resolvable anchor
  (drop-if-not); click payload `{chip_id, anchor_type, anchor_id, filter_scope, reason_code}`;
  stale anchor drops the chip, never triggers refusal; `filter_scope = "all"` in Phase 1 (current
  index has no learner filters) but the field is carried.
- **FR-W11:** reasoning strip (trace summary + metadata) hidden inside a collapsed "Behind this
  answer" accordion + presenter toggle; the posture chip is always visible.
- **Rendering:** allow-listed Gradio components only (Markdown / Accordion / Image / Button /
  Checkbox / State). No new dynamic `gr.HTML`; no FastAPI/HTMX.
- **Untouchables:** `corpus/`, `eval/`, the golden set, `eval_metrics.py`, the runner. `git status`
  must show nothing changed there.
- **Environment:** `python` is NOT on PATH — always `uv run python` / `uv run pytest` /
  `uv run ruff`. Branch: `feat/tutor-workspace-phase1` off `main`. Codex review on the PR before
  merge (`codex exec` with stdin closed when backgrounded: `</dev/null`).

## File Structure

| File | Responsibility |
|---|---|
| `src/genacademy_coach/source_labels.py` (new) | lane-id → learner lane name; per-lane "why this source" templates; safe label passthrough |
| `src/genacademy_coach/panel_payload.py` (new) | `PanelItem`/`PanelPayload` types + `build_panel_payload(...)` — pure projection |
| `src/genacademy_coach/slide_images.py` (new) | store paths, `resolve_slide_index`, `make_slide_image_resolver` |
| `scripts/render_slide_images.py` (new) | one-time deck → per-slide PNG render into the gitignored store |
| `src/genacademy_coach/suggestions.py` (new) | `SuggestionChip`/`ChipClick` + `build_suggestion_chips(...)` + `resolve_chip_click(...)` |
| `src/genacademy_coach/web/gradio_app.py` (modify) | third Teach-tab column rendering the payload; FR-W11 disclosure; chip buttons |
| `tests/test_source_labels.py`, `tests/test_panel_payload.py`, `tests/test_slide_images.py`, `tests/test_suggestions.py`, `tests/test_workspace_view.py` (new) | per-module tests listed in spec §5.6 |

---

### Task 1: `source_labels.py` — lane names, why-templates, safe labels (FR-W5)

**Files:**
- Create: `src/genacademy_coach/source_labels.py`
- Test: `tests/test_source_labels.py`

**Interfaces:**
- Consumes: `RetrievedSpan` from `genacademy_coach.teach_types` (its `.source_label` property is
  the existing privacy-safe label builder).
- Produces: `lane_name(source_type: str) -> str`, `why_this_source(source_type: str) -> str`,
  `safe_source_label(span: RetrievedSpan) -> str`, `LANE_ORDER: tuple[str, ...]`. Tasks 2 and 5
  import all four.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_source_labels.py
from genacademy_coach.source_labels import (
    LANE_ORDER,
    lane_name,
    safe_source_label,
    why_this_source,
)
from genacademy_coach.teach_types import RetrievedSpan


def _span(**overrides):
    values = dict(
        chunk_id="slide/week1-session1-82cf85861f9f::16",
        doc_id="slide/week1-session1-82cf85861f9f",
        text="# Slide 16\n\nAgent harness basics",
        score=0.91,
        title="week1-session1.pptx",
        source_type="slide",
        page_or_section=None,
    )
    values.update(overrides)
    return RetrievedSpan(**values)


def test_learner_language_lane_names():
    assert lane_name("transcript") == "Instructor explanation"
    assert lane_name("qa") == "Cohort Q&A"
    assert lane_name("slide") == "Course slides"
    assert lane_name("handout") == "Handout"
    assert lane_name("note") == "Course notes"


def test_unknown_lane_never_falls_through_raw():
    assert lane_name("weird_internal_type") == "Course material"


def test_every_ordered_lane_has_name_and_why():
    for lane in LANE_ORDER:
        assert lane_name(lane) != lane  # never the raw taxonomy id
        assert len(why_this_source(lane)) > 10


def test_why_template_is_tutor_voice_not_taxonomy():
    text = why_this_source("transcript")
    assert "transcript" not in text.lower()
    assert "instructor" in text.lower()


def test_safe_label_has_no_filename_artifacts():
    label = safe_source_label(_span())
    assert ".pptx" not in label
    assert "::" not in label
    assert "/" not in label
    assert "82cf85861f9f" not in label
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_source_labels.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'genacademy_coach.source_labels'`

- [ ] **Step 3: Write the implementation**

```python
# src/genacademy_coach/source_labels.py
"""Learner-facing lane language + safe source labels (PRD FR-W5).

Maps the internal corpus taxonomy to words a learner recognizes and owns the
per-lane tutor-voice "why this source" microcopy. Internal lane ids stay
unchanged in contracts and traces; only display strings live here.
"""

from __future__ import annotations

from genacademy_coach.teach_types import RetrievedSpan

LANE_ORDER: tuple[str, ...] = ("slide", "handout", "note", "transcript", "qa")

_FALLBACK_LANE_NAME = "Course material"

_LANE_NAMES: dict[str, str] = {
    "slide": "Course slides",
    "handout": "Handout",
    "note": "Course notes",
    "transcript": "Instructor explanation",
    "qa": "Cohort Q&A",
}

_WHY_TEMPLATES: dict[str, str] = {
    "slide": "This is the slide the answer is built on — the course's canonical wording.",
    "handout": "The handout carries the worked detail behind this answer.",
    "note": "The course notes give the fuller written explanation of this idea.",
    "transcript": "This is how the instructor explained it live in session.",
    "qa": "A cohort question that covered the same ground, answered from the course.",
}

_FALLBACK_WHY = "Cited course material that grounds this answer."


def lane_name(source_type: str) -> str:
    return _LANE_NAMES.get(source_type, _FALLBACK_LANE_NAME)


def why_this_source(source_type: str) -> str:
    return _WHY_TEMPLATES.get(source_type, _FALLBACK_WHY)


def safe_source_label(span: RetrievedSpan) -> str:
    return span.source_label
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_source_labels.py -q`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/source_labels.py tests/test_source_labels.py
git commit -m "feat: learner-language lane names + why-templates (FR-W5)"
```

---

### Task 2: `panel_payload.py` — the provenance projection (FR-W1..W4, FR-W11 posture)

**Files:**
- Create: `src/genacademy_coach/panel_payload.py`
- Test: `tests/test_panel_payload.py`

**Interfaces:**
- Consumes: Task 1's `lane_name`, `why_this_source`, `safe_source_label`, `LANE_ORDER`;
  `CoachAgentResponse`, `RetrievedSpan`, `EvidenceBand`, `ProvenanceRecord` from `teach_types`.
- Produces (Tasks 3–5 rely on these exact names):
  - `PanelItem(BaseModel)` with fields `lane: str`, `lane_label: str`, `source_label_safe: str`,
    `citation_id: str`, `role: str`, `confidence_band: EvidenceBand`, `extract_text: str`,
    `why_text: str`, `slide_image_ref: str | None = None`
  - `PanelPayload(BaseModel)` with fields `state: Literal["evidence","clarify","refusal"]`,
    `posture_text: str`, `items: list[PanelItem]`
  - `build_panel_payload(*, response, spans, evidence_band, provenance=None,
    slide_image_for=None) -> PanelPayload` where `slide_image_for` is
    `Callable[[RetrievedSpan], str | None] | None` (Task 3 supplies the real callable).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_panel_payload.py
import subprocess
import sys

from genacademy_coach.panel_payload import PanelPayload, build_panel_payload
from genacademy_coach.teach_types import CoachAgentResponse, ProvenanceRecord, RetrievedSpan


def _span(cid, stype="slide", score=0.9, text="# Slide 4\n\nAgent harness basics"):
    return RetrievedSpan(
        chunk_id=cid,
        doc_id=cid.split("::", 1)[0],
        text=text,
        score=score,
        title="week1-session1.pptx" if stype == "slide" else "week1-session1.md",
        source_type=stype,
        page_or_section=None,
    )


def _response(citations, next_action="advance"):
    return CoachAgentResponse(
        learner_message="An agent harness wires the model to tools. [slide]",
        observation="learner on track",
        next_action=next_action,
        strategy="step_by_step",
        citation_ids=citations,
    )


SLIDE = "slide/week1-session1-82cf85861f9f::16"
NOTE = "note/agents-note-11aa22bb33cc::3"
STRAY = "transcript/other-deck-99ff88ee77dd::9"


def test_evidence_state_projects_only_cited_spans():
    spans = [_span(SLIDE), _span(NOTE, stype="note"), _span(STRAY, stype="transcript")]
    payload = build_panel_payload(
        response=_response([SLIDE, NOTE]), spans=spans, evidence_band="proceed"
    )
    assert payload.state == "evidence"
    assert {i.citation_id for i in payload.items} == {SLIDE, NOTE}


def test_provenance_subset_invariant_even_with_alien_citation():
    # a citation id not present in the turn's pool must never become a panel item
    payload = build_panel_payload(
        response=_response([SLIDE, "slide/not-in-pool-000000000000::1"]),
        spans=[_span(SLIDE)],
        evidence_band="proceed",
    )
    assert [i.citation_id for i in payload.items] == [SLIDE]


def test_refusal_state_on_stop_band_has_no_evidence_items():
    payload = build_panel_payload(
        response=_response([], next_action="refuse_escalate"),
        spans=[_span(SLIDE, score=0.1)],
        evidence_band="stop",
    )
    assert payload.state == "refusal"
    assert payload.items == []
    assert "mentor" in payload.posture_text.lower()


def test_clarify_state_on_confirm_band_keeps_items_in_corpus_only():
    payload = build_panel_payload(
        response=_response([SLIDE]), spans=[_span(SLIDE)], evidence_band="confirm"
    )
    assert payload.state == "clarify"
    assert [i.citation_id for i in payload.items] == [SLIDE]


def test_teaching_role_span_is_featured_first():
    prov = {
        "teaching": ProvenanceRecord(
            role="teaching",
            span_id=NOTE,
            source_type="note",
            selected_at="2026-07-04T00:00:00Z",
            selection_reason="primary teaching span",
        )
    }
    payload = build_panel_payload(
        response=_response([SLIDE, NOTE]),
        spans=[_span(SLIDE), _span(NOTE, stype="note")],
        evidence_band="proceed",
        provenance=prov,
    )
    assert payload.items[0].citation_id == NOTE
    assert payload.items[0].role == "teaching"


def test_item_carries_learner_language_and_safe_label():
    payload = build_panel_payload(
        response=_response([STRAY]),
        spans=[_span(STRAY, stype="transcript", text="the instructor said…")],
        evidence_band="proceed",
    )
    item = payload.items[0]
    assert item.lane_label == "Instructor explanation"
    assert "::" not in item.source_label_safe and ".md" not in item.source_label_safe
    assert len(item.why_text) > 10


def test_slide_image_for_callable_is_used_when_given():
    payload = build_panel_payload(
        response=_response([SLIDE]),
        spans=[_span(SLIDE)],
        evidence_band="proceed",
        slide_image_for=lambda span: "/tmp/fake/slide-16.png",
    )
    assert payload.items[0].slide_image_ref == "/tmp/fake/slide-16.png"


def test_pure_core_never_imports_gradio():
    code = (
        "import sys; import genacademy_coach.panel_payload; "
        "sys.exit(1 if 'gradio' in sys.modules else 0)"
    )
    proc = subprocess.run([sys.executable, "-c", code], check=False)
    assert proc.returncode == 0


def test_posture_text_present_in_every_state():
    for band, next_action in (("proceed", "advance"), ("confirm", "advance"), ("stop", "refuse_escalate")):
        payload = build_panel_payload(
            response=_response([SLIDE] if band != "stop" else [], next_action=next_action),
            spans=[_span(SLIDE)],
            evidence_band=band,
        )
        assert payload.posture_text.strip(), f"posture missing for band={band}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_panel_payload.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'genacademy_coach.panel_payload'`

- [ ] **Step 3: Write the implementation**

```python
# src/genacademy_coach/panel_payload.py
"""PanelPayload — the Tutor Workspace's read-only provenance projection.

Built from the SAME turn objects the engine produced (response + span pool +
band + provenance). It never issues a query: the panel is a projection of the
turn's citations, so the answer and its evidence can never disagree.
"""

from __future__ import annotations

from typing import Callable, Literal

from pydantic import BaseModel, Field

from genacademy_coach.source_labels import (
    LANE_ORDER,
    lane_name,
    safe_source_label,
    why_this_source,
)
from genacademy_coach.teach_types import (
    CoachAgentResponse,
    EvidenceBand,
    ProvenanceRecord,
    RetrievedSpan,
)

PanelState = Literal["evidence", "clarify", "refusal"]

_POSTURE = {
    "evidence": "Grounded in the course material — every claim below is cited.",
    "clarify": "Grounded, but let's make sure we're on the right part of the course.",
    "refusal": (
        "Not in the course material — refusing rather than guessing. "
        "A mentor has been offered instead."
    ),
}


class PanelItem(BaseModel):
    lane: str
    lane_label: str
    source_label_safe: str
    citation_id: str
    role: str
    confidence_band: EvidenceBand
    extract_text: str
    why_text: str
    slide_image_ref: str | None = None


class PanelPayload(BaseModel):
    state: PanelState
    posture_text: str
    items: list[PanelItem] = Field(default_factory=list)


def build_panel_payload(
    *,
    response: CoachAgentResponse,
    spans: list[RetrievedSpan],
    evidence_band: EvidenceBand,
    provenance: dict[str, ProvenanceRecord] | None = None,
    slide_image_for: Callable[[RetrievedSpan], str | None] | None = None,
) -> PanelPayload:
    if evidence_band == "stop" or response.next_action == "refuse_escalate":
        return PanelPayload(state="refusal", posture_text=_POSTURE["refusal"])

    state: PanelState = "clarify" if evidence_band == "confirm" else "evidence"

    cited_ids = list(dict.fromkeys(response.citation_ids))
    pool = {span.citation_id: span for span in spans}
    role_by_span = {
        record.span_id: record.role for record in (provenance or {}).values()
    }

    items: list[PanelItem] = []
    for citation_id in cited_ids:
        span = pool.get(citation_id)
        if span is None:  # provenance-subset invariant: never invent an item
            continue
        items.append(
            PanelItem(
                lane=span.source_type,
                lane_label=lane_name(span.source_type),
                source_label_safe=safe_source_label(span),
                citation_id=span.citation_id,
                role=role_by_span.get(span.citation_id, "cited"),
                confidence_band=evidence_band,
                extract_text=span.text,
                why_text=why_this_source(span.source_type),
                slide_image_ref=(
                    slide_image_for(span) if slide_image_for is not None else None
                ),
            )
        )

    def _sort_key(item: PanelItem) -> tuple[int, int]:
        featured = 0 if item.role == "teaching" else 1
        lane_rank = (
            LANE_ORDER.index(item.lane) if item.lane in LANE_ORDER else len(LANE_ORDER)
        )
        return (featured, lane_rank)

    items.sort(key=_sort_key)
    return PanelPayload(state=state, posture_text=_POSTURE[state], items=items)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_panel_payload.py -q`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/panel_payload.py tests/test_panel_payload.py
git commit -m "feat: PanelPayload provenance projection (evidence/clarify/refusal)"
```

---

### Task 3: `slide_images.py` + render script (FR-W9)

**Files:**
- Create: `src/genacademy_coach/slide_images.py`
- Create: `scripts/render_slide_images.py`
- Test: `tests/test_slide_images.py`

**Interfaces:**
- Consumes: `RetrievedSpan` (its `text` carries `# Slide N` markers emitted by the pptx loader in
  `corpus.py`; `doc_id` like `slide/week1-session1-<hash>`); `CoachSettings` from `settings.py`
  (`data_dir`); `build_doc_id` + `source_type_for_path` from `corpus.py` (render script only).
- Produces: `resolve_slide_index(span) -> int | None`, `slide_image_path(store, doc_id, index)
  -> Path`, `make_slide_image_resolver(store: Path) -> Callable[[RetrievedSpan], str | None]`,
  `slide_store_dir(settings) -> Path`, `safe_doc_dirname(doc_id) -> str`. Task 5 passes
  `make_slide_image_resolver(...)` as `build_panel_payload(slide_image_for=...)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_slide_images.py
import subprocess

from genacademy_coach.slide_images import (
    make_slide_image_resolver,
    resolve_slide_index,
    safe_doc_dirname,
    slide_image_path,
)
from genacademy_coach.teach_types import RetrievedSpan


def _span(stype="slide", text="# Slide 16\n\nAgent harness basics", loc=None):
    return RetrievedSpan(
        chunk_id="slide/week1-session1-82cf85861f9f::4",
        doc_id="slide/week1-session1-82cf85861f9f",
        text=text,
        score=0.9,
        title="week1-session1.pptx",
        source_type=stype,
        page_or_section=loc,
    )


def test_resolves_index_from_slide_marker_in_text():
    assert resolve_slide_index(_span()) == 16


def test_resolves_index_from_page_or_section_fallback():
    assert resolve_slide_index(_span(text="no markers here", loc="slide 7")) == 7
    assert resolve_slide_index(_span(text="no markers here", loc="12")) == 12


def test_non_slide_lane_never_resolves():
    assert resolve_slide_index(_span(stype="transcript")) is None


def test_unresolvable_slide_returns_none():
    assert resolve_slide_index(_span(text="no markers", loc=None)) is None


def test_safe_doc_dirname_has_no_path_separator():
    assert "/" not in safe_doc_dirname("slide/week1-session1-82cf85861f9f")


def test_resolver_returns_path_only_when_file_exists(tmp_path):
    store = tmp_path / "slide_images"
    target = slide_image_path(store, "slide/deck-abc", 16)
    resolver = make_slide_image_resolver(store)
    assert resolver(_span()) is None  # file absent -> no ref (real-asset-only)
    target.parent.mkdir(parents=True)
    # resolver keys the path on the span's own doc_id
    real = slide_image_path(store, _span().doc_id, 16)
    real.parent.mkdir(parents=True, exist_ok=True)
    real.write_bytes(b"png-bytes")
    assert resolver(_span()) == str(real)


def test_slide_image_store_is_gitignored():
    proc = subprocess.run(
        ["git", "check-ignore", "-q", "data/slide_images/probe/slide-1.png"],
        check=False,
    )
    assert proc.returncode == 0, "data/slide_images/ must be gitignored (public repo)"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_slide_images.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'genacademy_coach.slide_images'`

- [ ] **Step 3: Write the module**

```python
# src/genacademy_coach/slide_images.py
"""Slide-visual card assets (PRD FR-W9).

Decks are rendered to per-slide PNGs at build time (scripts/render_slide_images.py)
into a gitignored store; at runtime a citation resolves deck-side to its slide
index (the pptx loader emits `# Slide N` markers into chunk text), so the
retrieval index is untouched. Real rendered assets only — a missing file means
no slide card, never a generated stand-in.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from genacademy_coach.teach_types import RetrievedSpan

SLIDE_IMAGE_DIRNAME = "slide_images"

_SLIDE_MARKER = re.compile(r"^# Slide (\d+)\b", re.MULTILINE)


def slide_store_dir(settings) -> Path:
    return Path(settings.data_dir) / SLIDE_IMAGE_DIRNAME


def safe_doc_dirname(doc_id: str) -> str:
    return doc_id.replace("/", "__")


def slide_image_path(store: Path, doc_id: str, index: int) -> Path:
    return store / safe_doc_dirname(doc_id) / f"slide-{index}.png"


def resolve_slide_index(span: RetrievedSpan) -> int | None:
    if span.source_type != "slide":
        return None
    match = _SLIDE_MARKER.search(span.text)
    if match:
        return int(match.group(1))
    location = str(span.page_or_section or "").strip().lower()
    if location.startswith("slide "):
        tail = location.removeprefix("slide ").strip()
        if tail.isdigit():
            return int(tail)
    if location.isdigit():
        return int(location)
    return None


def make_slide_image_resolver(store: Path) -> Callable[[RetrievedSpan], str | None]:
    def _resolve(span: RetrievedSpan) -> str | None:
        index = resolve_slide_index(span)
        if index is None:
            return None
        path = slide_image_path(store, span.doc_id, index)
        return str(path) if path.exists() else None

    return _resolve
```

- [ ] **Step 4: Ensure the store is gitignored**

Run: `git check-ignore -q data/slide_images/probe/slide-1.png; echo "rc=$?"`
If `rc=0`: nothing to do (`data/` is already ignored). If `rc=1`: append a line `data/` to
`.gitignore` and re-run until `rc=0`.

- [ ] **Step 5: Write the render script**

```python
# scripts/render_slide_images.py
"""Render every deck in corpus/slides/ to per-slide PNGs (gitignored store).

Usage: uv run python scripts/render_slide_images.py
Requires LibreOffice (`soffice`) and poppler (`pdftoppm`) on PATH.
Re-run whenever the decks change (store is keyed by content-hashed doc_id).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from genacademy_coach.corpus import build_doc_id
from genacademy_coach.settings import CoachSettings
from genacademy_coach.slide_images import safe_doc_dirname, slide_store_dir

_PAGE_SUFFIX = re.compile(r"-0*(\d+)\.png$")


def render_deck(deck: Path, store: Path) -> int:
    raw = deck.read_bytes()
    doc_id = f"slide/{build_doc_id(deck, raw)}"
    out_dir = store / safe_doc_dirname(doc_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", str(deck), "--outdir", tmp],
            check=True,
            capture_output=True,
        )
        pdf = next(Path(tmp).glob("*.pdf"))
        subprocess.run(
            ["pdftoppm", "-png", "-r", "110", str(pdf), str(Path(tmp) / "page")],
            check=True,
            capture_output=True,
        )
        count = 0
        for png in sorted(Path(tmp).glob("page-*.png")):
            match = _PAGE_SUFFIX.search(png.name)
            if not match:
                continue
            shutil.copy2(png, out_dir / f"slide-{int(match.group(1))}.png")
            count += 1
    return count


def main() -> None:
    settings = CoachSettings.load()
    store = slide_store_dir(settings)
    decks = sorted(settings.corpus_dir.glob("slides/*.pptx"))
    if not decks:
        print(f"no decks found under {settings.corpus_dir}/slides")
        return
    for deck in decks:
        count = render_deck(deck, store)
        print(f"{deck.name}: {count} slides -> {store}")


if __name__ == "__main__":
    main()
```

Note: `CoachSettings.load()` — check `settings.py` for the actual constructor name (the class
method that reads env vars; it appears in `CoachSettings`'s definition around line 36–72). If it
is named differently (e.g. `CoachSettings.from_env()`), use that name here and nowhere else.

- [ ] **Step 6: Run tests, then the script once**

Run: `uv run pytest tests/test_slide_images.py -q`
Expected: `7 passed`

Run: `uv run python scripts/render_slide_images.py`
Expected: one line per deck, e.g. `week1-session1.pptx: 24 slides -> …/data/slide_images`
(slide counts vary by deck). Then `git status --short` must show NO new tracked files (store is
ignored).

- [ ] **Step 7: Commit**

```bash
git add src/genacademy_coach/slide_images.py scripts/render_slide_images.py tests/test_slide_images.py .gitignore
git commit -m "feat: slide-image store + deck-side citation resolution (FR-W9)"
```

(Include `.gitignore` only if Step 4 changed it.)

---

### Task 4: `suggestions.py` — deterministic next-step chips (FR-W10)

**Files:**
- Create: `src/genacademy_coach/suggestions.py`
- Test: `tests/test_suggestions.py`

**Interfaces:**
- Consumes: `CoachAgentResponse`, `RetrievedSpan`, `EvidenceBand`, `LearnerProfile` from
  `teach_types`; `safe_source_label` from Task 1.
- Produces (Task 5 relies on these exact names):
  - `SuggestionChip(BaseModel)`: `chip_id: str`, `kind: Literal["continue","comprehension",
    "practice","recovery"]`, `label_safe: str`, `anchor_type: Literal["span","action"]`,
    `anchor_id: str`, `filter_scope: str = "all"`, `reason_code: str`
  - `ChipClick(BaseModel)`: `chip_id`, `anchor_type`, `anchor_id`, `filter_scope`, `reason_code`
    (same types)
  - `build_suggestion_chips(*, response, spans, evidence_band, profile) -> list[SuggestionChip]`
  - `resolve_chip_click(click: ChipClick, *, spans: list[RetrievedSpan]) -> str | None`
    (returns the topic text to submit as a normal turn, or `None` → chip is stale, drop silently)
  - `MAX_CHIPS = 4`

Phase-1 deterministic slot rules (no new model calls, everything from the turn's own objects):
- **Refusal turn** (`evidence_band == "stop"` or `next_action == "refuse_escalate"`): up to 2
  `recovery` chips anchored to the strongest spans in the turn's own pool (the refusal still
  retrieved a pool) — "the door back into the course". No other kinds.
- **Grounded turn:**
  - `continue`: the strongest retrieved-but-uncited span ("near-miss") whose label is not in
    `profile.known` → span anchor, `reason_code="near-miss"`.
  - `comprehension`: the primary cited span → action anchor `recheck::<citation_id>`,
    `reason_code="cited-recheck"`.
  - `practice`: most recent `profile.struggled` topic → action anchor `drill::<topic>`,
    `reason_code="check-failed"`.
- Dedupe against `profile.known` (case-insensitive label match); cap at `MAX_CHIPS`; a chip whose
  anchor cannot be built is simply not emitted (drop-if-not).

**Contract note (record in the PR body):** the spec's §5.3 contract shows `chips` inside
`PanelPayload`; this implementation composes them as a pair `(payload, chips)` built from the same
turn objects in the same call site (`_build_workspace_payload`, Task 5). Semantically identical —
same turn, same emission, no second retrieval — while keeping `panel_payload.py` and
`suggestions.py` import-independent. The single-object form lands in Phase C when an external
consumer needs it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_suggestions.py
from genacademy_coach.suggestions import (
    MAX_CHIPS,
    ChipClick,
    SuggestionChip,
    build_suggestion_chips,
    resolve_chip_click,
)
from genacademy_coach.teach_types import CoachAgentResponse, LearnerProfile, RetrievedSpan


def _span(cid, stype="slide", score=0.9, title="week1-session1.pptx"):
    return RetrievedSpan(
        chunk_id=cid,
        doc_id=cid.split("::", 1)[0],
        text="# Slide 4\n\ncontent",
        score=score,
        title=title,
        source_type=stype,
        page_or_section=None,
    )


def _response(citations, next_action="advance"):
    return CoachAgentResponse(
        learner_message="msg [cite]",
        observation="obs",
        next_action=next_action,
        strategy="step_by_step",
        citation_ids=citations,
    )


CITED = "slide/deck-aaaa11112222::4"
NEAR = "note/notes-bbbb33334444::7"
NEAR2 = "transcript/talk-cccc55556666::2"


def _chips(profile=None, band="proceed", citations=(CITED,), next_action="advance"):
    return build_suggestion_chips(
        response=_response(list(citations), next_action=next_action),
        spans=[_span(CITED), _span(NEAR, stype="note"), _span(NEAR2, stype="transcript")],
        evidence_band=band,
        profile=profile or LearnerProfile(),
    )


def test_grounded_turn_emits_anchored_chips_capped():
    chips = _chips(profile=LearnerProfile(struggled=["agent harness"]))
    assert 1 <= len(chips) <= MAX_CHIPS
    assert all(chip.anchor_id for chip in chips)
    kinds = {chip.kind for chip in chips}
    assert "recovery" not in kinds


def test_continue_chip_anchors_to_near_miss_span_not_cited_one():
    chips = _chips()
    cont = next(chip for chip in chips if chip.kind == "continue")
    assert cont.anchor_type == "span"
    assert cont.anchor_id in {NEAR, NEAR2}
    assert cont.reason_code == "near-miss"


def test_refusal_turn_emits_recovery_set_only():
    chips = _chips(band="stop", citations=(), next_action="refuse_escalate")
    assert chips, "refusal must offer a door back into the course"
    assert {chip.kind for chip in chips} == {"recovery"}
    assert all(chip.anchor_type == "span" for chip in chips)


def test_known_topic_dedupe_drops_continue_candidate():
    # the near-miss labels resolve from titles; mark them known
    known_profile = LearnerProfile(known=["Notes Bbbb 3333 4444".title(), "Talk Cccc 5555 6666".title()])
    chips = _chips(profile=known_profile)
    assert all(chip.kind != "continue" or chip.anchor_id not in {NEAR, NEAR2} for chip in chips) or all(
        chip.kind != "continue" for chip in chips
    )


def test_labels_carry_no_filename_artifacts():
    for chip in _chips(profile=LearnerProfile(struggled=["vector stores"])):
        assert "::" not in chip.label_safe
        assert ".pptx" not in chip.label_safe and ".md" not in chip.label_safe
        assert "/" not in chip.label_safe


def test_click_payload_preserves_anchor_and_resolves():
    chips = _chips()
    cont = next(chip for chip in chips if chip.kind == "continue")
    click = ChipClick(**cont.model_dump(include={"chip_id", "anchor_type", "anchor_id", "filter_scope", "reason_code"}))
    topic = resolve_chip_click(click, spans=[_span(NEAR, stype="note"), _span(CITED)])
    assert isinstance(topic, str) and len(topic) > 0


def test_stale_anchor_drops_not_refuses():
    click = ChipClick(
        chip_id="continue::gone",
        anchor_type="span",
        anchor_id="note/vanished-000000000000::1",
        filter_scope="all",
        reason_code="near-miss",
    )
    assert resolve_chip_click(click, spans=[_span(CITED)]) is None


def test_action_anchor_resolves_to_drill_topic():
    click = ChipClick(
        chip_id="practice::x",
        anchor_type="action",
        anchor_id="drill::vector stores",
        filter_scope="all",
        reason_code="check-failed",
    )
    assert resolve_chip_click(click, spans=[]) == "vector stores"


def test_chip_model_carries_filter_scope_field():
    chip = SuggestionChip(
        chip_id="c",
        kind="continue",
        label_safe="Next: Something",
        anchor_type="span",
        anchor_id=NEAR,
        reason_code="near-miss",
    )
    assert chip.filter_scope == "all"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_suggestions.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'genacademy_coach.suggestions'`

- [ ] **Step 3: Write the implementation**

```python
# src/genacademy_coach/suggestions.py
"""Deterministic next-step suggestion chips (PRD FR-W10).

One hard rule: never suggest what you can't ground. Every chip carries an
anchor built from the turn's own objects (span pool, profile) — no new model
calls, no second retrieval. Clicking a chip submits a normal turn through the
full pipeline; a stale anchor drops the chip, it never bypasses refusal.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from genacademy_coach.source_labels import safe_source_label
from genacademy_coach.teach_types import (
    CoachAgentResponse,
    EvidenceBand,
    LearnerProfile,
    RetrievedSpan,
)

MAX_CHIPS = 4
_RECOVERY_COUNT = 2

ChipKind = Literal["continue", "comprehension", "practice", "recovery"]
AnchorType = Literal["span", "action"]


class SuggestionChip(BaseModel):
    chip_id: str
    kind: ChipKind
    label_safe: str
    anchor_type: AnchorType
    anchor_id: str
    filter_scope: str = "all"
    reason_code: str


class ChipClick(BaseModel):
    chip_id: str
    anchor_type: AnchorType
    anchor_id: str
    filter_scope: str = "all"
    reason_code: str


def build_suggestion_chips(
    *,
    response: CoachAgentResponse,
    spans: list[RetrievedSpan],
    evidence_band: EvidenceBand,
    profile: LearnerProfile,
) -> list[SuggestionChip]:
    cited = set(response.citation_ids)
    pool = [span for span in spans if span.citation_id not in cited]
    known = {topic.strip().lower() for topic in profile.known}

    if evidence_band == "stop" or response.next_action == "refuse_escalate":
        recovery: list[SuggestionChip] = []
        for span in sorted(spans, key=lambda s: -s.score):
            label = safe_source_label(span)
            if label.lower() in known:
                continue
            recovery.append(
                SuggestionChip(
                    chip_id=f"recovery::{span.citation_id}",
                    kind="recovery",
                    label_safe=f"Back to the course: {label}",
                    anchor_type="span",
                    anchor_id=span.citation_id,
                    reason_code="refusal-recovery",
                )
            )
            if len(recovery) == _RECOVERY_COUNT:
                break
        return recovery

    chips: list[SuggestionChip] = []

    for span in sorted(pool, key=lambda s: -s.score):
        label = safe_source_label(span)
        if label.lower() in known:
            continue
        chips.append(
            SuggestionChip(
                chip_id=f"continue::{span.citation_id}",
                kind="continue",
                label_safe=f"Next: {label}",
                anchor_type="span",
                anchor_id=span.citation_id,
                reason_code="near-miss",
            )
        )
        break

    primary_cited = next((s for s in spans if s.citation_id in cited), None)
    if primary_cited is not None:
        chips.append(
            SuggestionChip(
                chip_id=f"comprehension::{primary_cited.citation_id}",
                kind="comprehension",
                label_safe="Check my understanding of this",
                anchor_type="action",
                anchor_id=f"recheck::{primary_cited.citation_id}",
                reason_code="cited-recheck",
            )
        )

    if profile.struggled:
        topic = profile.struggled[-1].strip()
        if topic and topic.lower() not in known:
            chips.append(
                SuggestionChip(
                    chip_id=f"practice::{topic.lower()}",
                    kind="practice",
                    label_safe=f"Practice: {topic}",
                    anchor_type="action",
                    anchor_id=f"drill::{topic}",
                    reason_code="check-failed",
                )
            )

    return chips[:MAX_CHIPS]


def resolve_chip_click(
    click: ChipClick, *, spans: list[RetrievedSpan]
) -> str | None:
    """Resolve a clicked chip back to a topic to submit as a normal turn.

    Returns None when the anchor no longer resolves (stale) — the caller
    drops the chip silently; a stale chip must never trigger a refusal.
    """
    if click.anchor_type == "span":
        span = next((s for s in spans if s.citation_id == click.anchor_id), None)
        return safe_source_label(span) if span is not None else None
    if click.anchor_id.startswith("drill::"):
        topic = click.anchor_id.removeprefix("drill::").strip()
        return topic or None
    if click.anchor_id.startswith("recheck::"):
        citation_id = click.anchor_id.removeprefix("recheck::")
        span = next((s for s in spans if s.citation_id == citation_id), None)
        return safe_source_label(span) if span is not None else None
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_suggestions.py -q`
Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add src/genacademy_coach/suggestions.py tests/test_suggestions.py
git commit -m "feat: deterministic anchor-validated next-step chips (FR-W10)"
```

---

### Task 5: Workspace wiring in the Gradio app (FR-W1..W11 in the UI)

**Files:**
- Modify: `src/genacademy_coach/web/gradio_app.py` (Teach tab layout `~lines 2248–2380`; the two
  handlers `start_teach_check_ui` and `submit_teach_answer_ui`)
- Test: `tests/test_workspace_view.py`

**Interfaces:**
- Consumes: everything produced by Tasks 1–4, plus existing app internals: `teach_state`
  (`gr.State` holding the session wrapper), `_current_spans(session) -> list[RetrievedSpan]`
  (already in `gradio_app.py`), `load_trace` from `genacademy_coach.trace`,
  `TeachSessionResult.trace_path`.
- Produces: `render_panel_markdown(payload: PanelPayload) -> str` and
  `panel_view_updates(session, result) -> tuple` (the 18-tuple documented in its docstring) —
  helpers in `gradio_app.py`, the first unit-testable without launching the app.

**What the turn objects give the view:** after a teach run, the UI state holds the
`TeachSessionResult`; the last `TraceTurn` (via `load_trace(Path(result.trace_path))[-1]`)
carries `evidence_band` and `provenance`; `_current_spans(session)` is the turn's retrieval pool.
That triple + `result.response` is exactly `build_panel_payload`'s input — no new query anywhere.

- [ ] **Step 1: Write the failing view-helper tests**

```python
# tests/test_workspace_view.py
from genacademy_coach.panel_payload import PanelItem, PanelPayload
from genacademy_coach.web.gradio_app import render_panel_markdown


def _item(**overrides):
    values = dict(
        lane="transcript",
        lane_label="Instructor explanation",
        source_label_safe="Week 1 Session 1 (chunk 9)",
        citation_id="transcript/x-000000000000::9",
        role="cited",
        confidence_band="proceed",
        extract_text="the instructor explained the harness",
        why_text="This is how the instructor explained it live in session.",
        slide_image_ref=None,
    )
    values.update(overrides)
    return PanelItem(**values)


def test_evidence_render_groups_by_learner_lane_and_hides_ids():
    payload = PanelPayload(
        state="evidence",
        posture_text="Grounded in the course material — every claim below is cited.",
        items=[_item()],
    )
    md = render_panel_markdown(payload)
    assert "Instructor explanation" in md
    assert "the instructor explained the harness" in md
    assert "::9" not in md  # raw chunk ids never render
    assert "transcript/" not in md


def test_refusal_render_offers_mentor_not_evidence():
    payload = PanelPayload(
        state="refusal",
        posture_text="Not in the course material — refusing rather than guessing. A mentor has been offered instead.",
        items=[],
    )
    md = render_panel_markdown(payload)
    assert "mentor" in md.lower()
    assert "Instructor explanation" not in md


def test_why_text_renders_with_each_section():
    md = render_panel_markdown(
        PanelPayload(state="evidence", posture_text="p", items=[_item()])
    )
    assert "instructor explained it live" in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_workspace_view.py -q`
Expected: FAIL — `ImportError: cannot import name 'render_panel_markdown'`

- [ ] **Step 3: Add the view helpers to `gradio_app.py`**

Add near the other `_format_*` helpers (module scope, before `build_demo`):

```python
from genacademy_coach.panel_payload import PanelPayload, build_panel_payload
from genacademy_coach.settings import CoachSettings
from genacademy_coach.slide_images import make_slide_image_resolver, slide_store_dir
from genacademy_coach.suggestions import (
    ChipClick,
    build_suggestion_chips,
    resolve_chip_click,
)
from genacademy_coach.trace import load_trace


def render_panel_markdown(payload: PanelPayload) -> str:
    if payload.state == "refusal":
        return (
            "### Not in the course material\n\n"
            f"{payload.posture_text}\n\n"
            "_The suggestions below route back into the course._"
        )
    lines: list[str] = []
    seen_lanes: list[str] = []
    for item in payload.items:
        if item.lane_label not in seen_lanes:
            seen_lanes.append(item.lane_label)
            lines.append(f"#### {item.lane_label}")
        lines.append(f"**{item.source_label_safe}**")
        lines.append(f"> {item.extract_text}")
        lines.append(f"_{item.why_text}_")
        lines.append("")
    return "\n".join(lines) if lines else "_No cited evidence to project._"


def _build_workspace_payload(session, result) -> tuple[PanelPayload, list]:
    """PanelPayload + chips from the turn's own objects. Never a new query."""
    spans = _current_spans(session)
    last_turn = load_trace(Path(result.trace_path))[-1]
    resolver = make_slide_image_resolver(slide_store_dir(CoachSettings.load()))
    payload = build_panel_payload(
        response=result.response,
        spans=spans,
        evidence_band=last_turn.evidence_band,
        provenance={k: v for k, v in last_turn.provenance.items()},
        slide_image_for=resolver,
    )
    chips = build_suggestion_chips(
        response=result.response,
        spans=spans,
        evidence_band=last_turn.evidence_band,
        profile=result.profile,
    )
    return payload, chips
```

(`Path` is already imported in the file; `CoachSettings.load()` — use the same constructor name
Task 3's script settled on.)

Then add `panel_view_updates`, which turns `(payload, chips)` into the component updates:

```python
_EMPTY_PANEL = "_Run a teach turn to see the evidence panel._"


def _lane_body_markdown(items) -> str:
    return "\n".join(
        f"**{item.source_label_safe}**\n\n> {item.extract_text}\n\n_{item.why_text}_\n"
        for item in items
    )


def panel_view_updates(session, result):
    """Returns an 18-tuple, in this exact order:
    (posture_md, status_md, slide_image_update,
     lane_accordion_updates x5, lane_markdown_updates x5,
     chip_updates x4, chips_state)."""
    import gradio as gr

    from genacademy_coach.source_labels import LANE_ORDER

    hidden_lanes = [gr.update(visible=False)] * len(LANE_ORDER)
    empty_lane_md = [gr.update(value="")] * len(LANE_ORDER)
    chip_hidden = [gr.update(visible=False, value="")] * 4
    if session is None or result is None:
        return (
            "",
            _EMPTY_PANEL,
            gr.update(visible=False),
            *hidden_lanes,
            *empty_lane_md,
            *chip_hidden,
            [],
        )

    payload, chips = _build_workspace_payload(session, result)
    posture = f"**{payload.posture_text}**"
    if payload.state == "refusal":
        status_md = render_panel_markdown(payload)
    elif payload.state == "clarify":
        status_md = (
            "_Grounded with caveats — the sections below are the parts of the "
            "course this answer stands on._"
        )
    else:
        status_md = "_Every section below is a source this answer actually cited._"

    lane_accordion_updates = []
    lane_markdown_updates = []
    for lane in LANE_ORDER:
        lane_items = [item for item in payload.items if item.lane == lane]
        if lane_items:
            lane_accordion_updates.append(gr.update(visible=True))
            lane_markdown_updates.append(gr.update(value=_lane_body_markdown(lane_items)))
        else:
            lane_accordion_updates.append(gr.update(visible=False))
            lane_markdown_updates.append(gr.update(value=""))

    slide_ref = next(
        (item.slide_image_ref for item in payload.items if item.slide_image_ref), None
    )
    image_update = (
        gr.update(value=slide_ref, visible=True)
        if slide_ref
        else gr.update(visible=False)
    )

    chip_updates = []
    for slot in range(4):
        if slot < len(chips):
            chip_updates.append(gr.update(visible=True, value=chips[slot].label_safe))
        else:
            chip_updates.append(gr.update(visible=False, value=""))
    chips_state = [chip.model_dump() for chip in chips]
    return (
        posture,
        status_md,
        image_update,
        *lane_accordion_updates,
        *lane_markdown_updates,
        *chip_updates,
        chips_state,
    )
```

- [ ] **Step 4: Run the view tests**

Run: `uv run pytest tests/test_workspace_view.py -q`
Expected: `3 passed`

- [ ] **Step 5: Add the panel column + FR-W11 disclosure to the Teach tab layout**

In `build_demo()`, inside `with gr.Tab("Teach"):` — the Row currently has two Columns (controls
at scale 5, learner surface at scale 7, lines ~2249–2331). Make three changes:

**(a)** Add a third column after the learner-surface column (i.e., after the
`teach_metadata` accordion block, still inside the `gr.Row`):

```python
                    with gr.Column(scale=5, min_width=360, elem_classes=["gc-panel-soft"]):
                        gr.HTML(
                            """
                            <p class="gc-eyebrow">Evidence panel</p>
                            <h2 class="gc-panel-title">Where this answer comes from</h2>
                            """
                        )
                        teach_posture = gr.Markdown(value="", elem_classes=["gc-trace"])
                        teach_panel_status = gr.Markdown(
                            value="_Run a teach turn to see the evidence panel._",
                            elem_classes=["gc-output"],
                        )
                        teach_slide_image = gr.Image(
                            label="Cited slide",
                            visible=False,
                            interactive=False,
                            type="filepath",
                        )
                        # A2: per-lane collapsible sections — one static accordion
                        # per lane, shown only when the turn cited that lane.
                        lane_accordions = []
                        lane_markdowns = []
                        for _lane in LANE_ORDER:
                            with gr.Accordion(
                                lane_name(_lane),
                                open=True,
                                visible=False,
                                elem_classes=["gc-accordion"],
                            ) as _lane_acc:
                                _lane_md = gr.Markdown("")
                            lane_accordions.append(_lane_acc)
                            lane_markdowns.append(_lane_md)
                        chips_state = gr.State([])
                        with gr.Row():
                            chip_0 = gr.Button("", visible=False, elem_classes=["gc-preset-button"])
                            chip_1 = gr.Button("", visible=False, elem_classes=["gc-preset-button"])
                        with gr.Row():
                            chip_2 = gr.Button("", visible=False, elem_classes=["gc-preset-button"])
                            chip_3 = gr.Button("", visible=False, elem_classes=["gc-preset-button"])
```

(`LANE_ORDER` and `lane_name` come from `genacademy_coach.source_labels` — add them to the
module's imports.)

**(b)** FR-W11 — wrap the existing `teach_trace_summary` + `teach_metadata` (currently a bare
Markdown + an accordion in the learner-surface column) inside one collapsed disclosure, and add
the presenter toggle. Replace the current block

```python
                        teach_trace_summary = gr.Markdown(...)
                        with gr.Accordion("Redacted metadata", open=False, ...):
                            teach_metadata = gr.JSON(...)
```

with:

```python
                        presenter_mode = gr.Checkbox(
                            label="Presenter mode (show reasoning)", value=False
                        )
                        with gr.Accordion(
                            "Behind this answer",
                            open=False,
                            elem_classes=["gc-accordion"],
                        ) as behind_accordion:
                            teach_trace_summary = gr.Markdown(
                                label="Trace summary",
                                value="_Trace summary appears after a run._",
                                elem_classes=["gc-trace"],
                            )
                            teach_metadata = gr.JSON(
                                label="Redacted metadata",
                                elem_classes=["gc-json"],
                            )
                        presenter_mode.change(
                            fn=lambda on: gr.update(open=bool(on)),
                            inputs=[presenter_mode],
                            outputs=[behind_accordion],
                        )
```

**(c)** Extend the two teach handlers' wiring. Both `start_teach_button.click(...)` and
`submit_teach_button.click(...)` gain the panel outputs appended to their existing `outputs`
lists (order matters — append exactly):

```python
                        # appended to BOTH click outputs lists, after submit_teach_button:
                        teach_posture,
                        teach_panel_status,
                        teach_slide_image,
                        *lane_accordions,
                        *lane_markdowns,
                        chip_0,
                        chip_1,
                        chip_2,
                        chip_3,
                        chips_state,
```

Inside `start_teach_check_ui` and `submit_teach_answer_ui`: every `return` site currently returns
a 6-tuple. Append `*panel_view_updates(session, result)` on success paths (where the fresh
session/result are in scope) and `*panel_view_updates(None, None)` on error/early-return paths,
e.g.:

```python
    return (
        output_md,
        trace_md,
        metadata,
        new_state,
        answer_value,
        submit_button_update,
        *panel_view_updates(session, result),
    )
```

**(d)** Chip clicks submit a normal turn through the existing pipeline. After the handler
wiring, add:

```python
                def _chip_click(slot: int):
                    def _handler(chips, topic, style_v, lens_v, state):
                        if not chips or slot >= len(chips):
                            return start_teach_check_ui(topic, style_v, lens_v, state)
                        click = ChipClick(**{
                            k: chips[slot][k]
                            for k in ("chip_id", "anchor_type", "anchor_id", "filter_scope", "reason_code")
                        })
                        session = state.get("session") if isinstance(state, dict) else None
                        spans = _current_spans(session) if session is not None else []
                        resolved = resolve_chip_click(click, spans=spans)
                        next_topic = resolved if resolved else topic  # stale -> drop, keep current topic
                        return start_teach_check_ui(next_topic, style_v, lens_v, state)

                    return _handler

                for slot, chip_button in enumerate([chip_0, chip_1, chip_2, chip_3]):
                    chip_button.click(
                        fn=_chip_click(slot),
                        inputs=[chips_state, teach_topic, style, track_lens, teach_state],
                        outputs=[
                            teach_output,
                            teach_trace_summary,
                            teach_metadata,
                            teach_state,
                            learner_answer,
                            submit_teach_button,
                            teach_posture,
                            teach_panel_status,
                            teach_slide_image,
                            *lane_accordions,
                            *lane_markdowns,
                            chip_0,
                            chip_1,
                            chip_2,
                            chip_3,
                            chips_state,
                        ],
                    )
```

Note: inspect how `teach_state` actually stores the session (read `start_teach_check_ui`'s body
before writing `_chip_click`) — if the state object is not a dict, fetch the session the same way
that function does. The invariant that matters: **a chip click calls the existing
`start_teach_check_ui` — the full pipeline runs; chips are navigation, never evidence.**

- [ ] **Step 6: Full suite + lint**

Run: `uv run pytest -q`
Expected: all green (existing suite + the 4 new test files).
Run: `uv run ruff check .`
Expected: clean.

- [ ] **Step 7: Manual smoke (evidence for the done-bar)**

```bash
uv run python -m genacademy_coach.web.gradio_app  # or the repo's documented launch entry point
```
In the browser: **(1)** Grounded preset → Start check → right panel shows posture chip +
"Where this answer comes from" with cited lanes, the slide image if the store is rendered, and
2–3 chips; "Behind this answer" starts collapsed; presenter toggle opens it. **(2)** Refusal
preset → panel flips to the refusal card + recovery chips. **(3)** Click a chip → a normal turn
runs. Capture both states as screenshots (local only — not committed).

- [ ] **Step 8: Commit**

```bash
git add src/genacademy_coach/web/gradio_app.py tests/test_workspace_view.py
git commit -m "feat: split-pane Tutor Workspace panel + chips + behind-this-answer disclosure"
```

---

### Task 6: Evidence, PR, Codex gate, merge

**Files:**
- Create: `tmp/codex-review-workspace-prompt.md` (gitignored, operational)

- [ ] **Step 1: The done-bar checks (spec §5.8)**

```bash
uv run pytest -q                     # all green
uv run ruff check .                  # clean
git status --short -- corpus/ eval/  # EMPTY — untouchables untouched
git log --oneline main..HEAD         # one commit per task
```

Cross-check the spec-§5.6 test list against the four new test files — every bullet
(provenance-subset, no-second-retrieval [pure-core import test + no retriever import],
refusal-renders-escalation, privacy labels, lane-name coverage, slide-image conditions,
reasoning-strip default-hidden, chip anchor/click/stale/dedupe/cap rules) must map to a named
test. Also re-read `docs/coach-product-requirements.md` acceptance criteria (AC-1..AC-7) and note
in the PR body which AC each test file covers.

- [ ] **Step 2: Push + PR**

```bash
git push -u origin feat/tutor-workspace-phase1
gh pr create --title "feat: Tutor Workspace Phase 1 — provenance panel, slide card, chips (FR-W1..W11)" --body "Implements the Phase-A slice of docs/superpowers/specs/2026-06-30-tutor-workspace-and-target-architecture-design.md: PanelPayload projection (no second retrieval), learner-language lanes (FR-W5), slide-visual card with gitignored store (FR-W9), deterministic anchor-validated chips (FR-W10), behind-this-answer disclosure + posture chip (FR-W11), Gradio wiring. Tests per spec 5.6; done-bar per 5.8. Codex review to follow."
```

- [ ] **Step 3: Codex review (builder ≠ reviewer), fix, merge**

Write `tmp/codex-review-workspace-prompt.md` asking Codex to verify against spec §5.3–§5.6:
(1) provenance-subset + no-second-retrieval invariants hold in `panel_payload.py` /
`suggestions.py` (no retriever import, payload derives from turn objects); (2) refusal path never
renders evidence and clarify is in-corpus only; (3) privacy: no raw ids/filenames reach any
learner-facing string, slide store gitignored, no corpus text in tests; (4) FR-W11 default-hidden
disclosure; (5) chip click contract (anchor preserved, stale-drop, full-pipeline submission);
(6) test coverage vs the §5.6 list. Then:

```bash
codex exec -s read-only -C "$PWD" "$(cat tmp/codex-review-workspace-prompt.md)" </dev/null > tmp/codex-review-workspace-out.md 2> tmp/codex-review-workspace-err.log
sed 's#/Users/[^ )]*/genacademy-coach/##g' tmp/codex-review-workspace-out.md > tmp/codex-review-workspace-posted.md
gh pr comment <PR#> --body-file tmp/codex-review-workspace-posted.md
```

Fix blocking findings (re-run the covering tests, push, post a resolution comment), then:

```bash
gh pr merge <PR#> --merge --delete-branch
```
(If "Base branch was modified": `sleep 3`, retry once.)

- [ ] **Step 4: Report evidence**

Report: test counts per file, ruff result, untouchables check output, the two smoke screenshots'
existence (local), Codex verdict + resolution, merge SHA.
