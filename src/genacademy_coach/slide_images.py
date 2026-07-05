"""Slide-visual card assets (PRD FR-W9).

Decks are rendered to per-slide PNGs at build time (scripts/render_slide_images.py)
into a gitignored store; at runtime a citation resolves deck-side to its slide
index (the pptx loader emits `# Slide N` markers into chunk text), so the
retrieval index is untouched. Real rendered assets only — a missing file means
no slide card, never a generated stand-in.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

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
