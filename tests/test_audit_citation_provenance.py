import importlib.util
import json
from pathlib import Path


def load_audit_module():
    script_path = Path("scripts/audit_citation_provenance.py").resolve()
    spec = importlib.util.spec_from_file_location("audit_citation_provenance", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(**overrides):
    base = {
        "case_id": "happy_001",
        "query_type": "happy",
        "split": "seed",
        "cloud_safe": False,
        "refusal_expected": False,
        "expected_citation_span_id": "slide/week2-session1::3",
        "predicted_citation_ids": ["slide/week2-session1::4"],
        "retrieved_citation_ids": ["slide/week2-session1::3", "slide/week2-session1::4"],
        "answered_check_id": "slide/week2-session1::4",
        "post_final_check_id": "slide/week2-session1::4",
        "boundary_grade_citation_id": "slide/week2-session1::4",
        "anchor_present_in_final_retrieved": True,
        "citation_precision": 0.0,
        "citation_recall": 0.0,
        "citation_f1": 0.0,
        "retrieval_recall_at_5": True,
        "evidence_band": "confirm",
        "evidence_score": 0.55,
        "faithfulness_ok": True,
        "actual_next_action": "advance",
        "decision_source": "python safety gate",
        "refusal_reason_code": None,
    }
    return {**base, **overrides}


def test_buckets_same_family_and_extra_citations():
    module = load_audit_module()
    payload = {
        "tag": "current-main",
        "run_id": "r1",
        "golden_manifest_version": "v1",
        "golden_cases_sha256": "abc",
        "rows": [
            row(),
            row(
                case_id="edge_001",
                predicted_citation_ids=[
                    "slide/week2-session1::3",
                    "handout/agent-memory::1",
                ],
                citation_precision=0.5,
                citation_recall=1.0,
                citation_f1=0.6666666667,
            ),
        ],
    }

    audit = module.build_audit(payload, source_path=Path("run.json"))

    assert audit["citation_miss_rows"] == 2
    assert audit["review_bucket_counts"] == {
        "expected_exact_plus_extra_citations": 1,
        "expected_retrieved_predicted_same_source_family": 1,
    }
    assert audit["rows"][0]["citation_miss_category"] is None
    assert audit["rows"][0]["predicted_same_source_family"] is True
    assert audit["heuristic_same_source_family_ceiling_f1"] == 1.0


def test_audit_output_omits_private_text_fields():
    module = load_audit_module()
    payload = {
        "rows": [
            row(
                user_query="private learner wording",
                answer_text="private tutor prose",
            )
        ]
    }

    audit = module.build_audit(payload, source_path=Path("run.json"))
    rendered = json.dumps(audit)

    assert "private learner wording" not in rendered
    assert "private tutor prose" not in rendered
    assert "user_query" not in rendered
    assert "answer_text" not in rendered


def test_public_safe_backstop_rejects_forbidden_keys_and_private_urls():
    module = load_audit_module()

    for value in (
        {"trace_id": "abc123"},
        {"nested": [{"u": "https://smith.langchain.com/o/project/r/run"}]},
    ):
        try:
            module._assert_public_safe(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected audit backstop to reject {value!r}")


def test_refuses_frozen_test_rows():
    module = load_audit_module()
    payload = {"rows": [row(case_id="test_case", split="test")]}

    try:
        module.build_audit(payload, source_path=Path("run.json"))
    except ValueError as exc:
        assert "frozen test rows" in str(exc)
    else:
        raise AssertionError("audit must reject frozen test rows")


def test_refused_no_final_citation_bucket():
    module = load_audit_module()
    payload = {
        "rows": [
            row(
                predicted_citation_ids=[],
                retrieved_citation_ids=["slide/week2-session1::3"],
                actual_next_action="refuse_escalate",
                refusal_reason_code="agent_refusal",
            )
        ]
    }

    audit = module.build_audit(payload, source_path=Path("run.json"))

    assert audit["review_bucket_counts"] == {"refused_no_final_citation": 1}


def test_remaining_review_buckets():
    module = load_audit_module()
    payload = {
        "rows": [
            row(
                case_id="other-source",
                predicted_citation_ids=["handout/week2::1"],
                retrieved_citation_ids=["slide/week2-session1::3", "handout/week2::1"],
            ),
            row(
                case_id="ranked-only",
                predicted_citation_ids=["transcript/week2::1"],
                retrieved_citation_ids=["transcript/week2::1"],
                retrieval_recall_at_5=True,
            ),
            row(
                case_id="not-retrieved",
                predicted_citation_ids=["transcript/week2::1"],
                retrieved_citation_ids=["transcript/week2::1"],
                retrieval_recall_at_5=False,
            ),
            row(
                case_id="other",
                expected_citation_span_id=None,
                predicted_citation_ids=["transcript/week2::1"],
                retrieved_citation_ids=["transcript/week2::1"],
            ),
        ],
    }

    audit = module.build_audit(payload, source_path=Path("run.json"))

    assert audit["review_bucket_counts"] == {
        "expected_missing_from_final_trace_but_seen_in_ranked_retrieval": 1,
        "expected_not_in_final_retrieved": 1,
        "expected_retrieved_predicted_other_source": 1,
        "other_citation_mismatch": 1,
    }
