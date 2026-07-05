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
