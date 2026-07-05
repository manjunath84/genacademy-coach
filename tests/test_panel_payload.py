import subprocess
import sys

from genacademy_coach.panel_payload import build_panel_payload
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
    test_cases = (
        ("proceed", "advance"),
        ("confirm", "advance"),
        ("stop", "refuse_escalate"),
    )
    for band, next_action in test_cases:
        payload = build_panel_payload(
            response=_response([SLIDE] if band != "stop" else [], next_action=next_action),
            spans=[_span(SLIDE)],
            evidence_band=band,
        )
        assert payload.posture_text.strip(), f"posture missing for band={band}"
