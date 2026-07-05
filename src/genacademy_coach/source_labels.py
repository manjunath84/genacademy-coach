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
