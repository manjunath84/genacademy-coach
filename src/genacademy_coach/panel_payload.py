"""PanelPayload — the Tutor Workspace's read-only provenance projection.

Built from the SAME turn objects the engine produced (response + span pool +
band + provenance). It never issues a query: the panel is a projection of the
turn's citations, so the answer and its evidence can never disagree.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

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
