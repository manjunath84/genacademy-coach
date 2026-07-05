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
    known_topics = ["Notes Bbbb 3333 4444".title(), "Talk Cccc 5555 6666".title()]
    known_profile = LearnerProfile(known=known_topics)
    chips = _chips(profile=known_profile)
    not_continue = all(
        chip.kind != "continue" or chip.anchor_id not in {NEAR, NEAR2} for chip in chips
    )
    no_continue = all(chip.kind != "continue" for chip in chips)
    assert not_continue or no_continue


def test_labels_carry_no_filename_artifacts():
    for chip in _chips(profile=LearnerProfile(struggled=["vector stores"])):
        assert "::" not in chip.label_safe
        assert ".pptx" not in chip.label_safe and ".md" not in chip.label_safe
        assert "/" not in chip.label_safe


def test_click_payload_preserves_anchor_and_resolves():
    chips = _chips()
    cont = next(chip for chip in chips if chip.kind == "continue")
    click_fields = {"chip_id", "anchor_type", "anchor_id", "filter_scope", "reason_code"}
    click = ChipClick(**cont.model_dump(include=click_fields))
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
