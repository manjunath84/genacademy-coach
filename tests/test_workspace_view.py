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
        posture_text=(
            "Not in the course material — refusing rather than guessing."
            " A mentor has been offered instead."
        ),
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
