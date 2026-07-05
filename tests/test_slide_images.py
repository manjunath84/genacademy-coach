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
