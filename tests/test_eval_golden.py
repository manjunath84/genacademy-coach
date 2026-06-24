import json

import pytest

from genacademy_coach.eval_golden import GoldenCase, load_golden_cases


def _row(**over):
    base = dict(
        case_id="happy_001",
        query_type="happy",
        concept="tokenization",
        expected_citation_span_id="doc::3",
        target_check_id="chk1",
        expected_next_action="advance",
        expected_tools=["retrieve_course_corpus", "generate_check_item", "grade_understanding"],
        refusal_expected=False,
        strategy_changed_on_stumble=True,
        split="seed",
        cloud_safe=True,
        cloud_safe_reason="synthetic, no private text",
        user_query="What is a token?",
        initial_wrong_answer="a whole word",
        expected_answer="a sub-word piece",
        expected_check_keywords=["sub-word"],
    )
    base.update(over)
    return base


def test_cloud_safe_requires_reason():
    with pytest.raises(ValueError):
        GoldenCase(**_row(cloud_safe=True, cloud_safe_reason=""))


def test_test_split_rejected():
    with pytest.raises(ValueError):
        GoldenCase(**_row(split="test"))


def test_non_cloud_safe_forbids_inline_text_and_needs_source_ref():
    with pytest.raises(ValueError):
        GoldenCase(
            **_row(
                cloud_safe=False,
                cloud_safe_reason=None,
                user_query=None,
                initial_wrong_answer=None,
                expected_answer="x",
            )
        )
    ok = GoldenCase(
        **_row(
            cloud_safe=False,
            cloud_safe_reason=None,
            user_query=None,
            initial_wrong_answer=None,
            expected_answer=None,
            source_ref="scenario:3df14f64046e6250:000",
        )
    )
    assert ok.source_ref.startswith("scenario:")


def test_teachable_requires_check_keywords():
    with pytest.raises(ValueError):
        GoldenCase(**_row(refusal_expected=False, expected_check_keywords=[]))
    ok = GoldenCase(
        **_row(
            refusal_expected=True,
            expected_next_action="refuse_escalate",
            expected_check_keywords=[],
        )
    )
    assert ok.refusal_expected is True


def test_loader_reads_jsonl(tmp_path):
    p = tmp_path / "g.jsonl"
    p.write_text(json.dumps(_row()) + "\n" + json.dumps(_row(case_id="happy_002")) + "\n")
    assert [c.case_id for c in load_golden_cases(p)] == ["happy_001", "happy_002"]
