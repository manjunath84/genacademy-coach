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

    def is_known_text(text: str) -> bool:
        """Check if text matches any known topic."""
        text_lower = text.lower()
        # Check for exact match or substring match against known topics
        return text_lower in known or any(known_topic in text_lower for known_topic in known)

    def is_known_span(span: RetrievedSpan) -> bool:
        """Check if a span's topic is known using label and doc_id matching."""
        label = safe_source_label(span)
        if is_known_text(label):
            return True
        # Also check doc_id: if any word from a known topic appears in the doc_id, it's known
        doc_id_part = span.doc_id.split("/")[-1].lower() if span.doc_id else ""
        for known_topic in known:
            for word in known_topic.split():
                if word and word in doc_id_part:
                    return True
        return False

    if evidence_band == "stop" or response.next_action == "refuse_escalate":
        recovery: list[SuggestionChip] = []
        for span in sorted(spans, key=lambda s: -s.score):
            if is_known_span(span):
                continue
            label = safe_source_label(span)
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
        if is_known_span(span):
            continue
        label = safe_source_label(span)
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
        if topic and not is_known_text(topic):
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
