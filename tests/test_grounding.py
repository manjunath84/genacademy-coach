from genacademy_coach.grounding import (
    answer_grounded_in_spans,
    evidence_band,
    evidence_score,
    grade_understanding,
    require_citeable_spans,
)
from genacademy_coach.teach_types import CheckItem, RetrievedSpan


def span(score: float = 0.9, text: str = "Attention focuses relevant context.") -> RetrievedSpan:
    return RetrievedSpan(
        chunk_id="note/attention::0",
        doc_id="note/attention",
        text=text,
        score=score,
        title="attention.md",
        source_type="note",
    )


def test_evidence_band_uses_configured_thresholds():
    assert evidence_band(0.50, stop_threshold=0.60, confirm_threshold=0.85) == "stop"
    assert evidence_band(0.70, stop_threshold=0.60, confirm_threshold=0.85) == "confirm"
    assert evidence_band(0.91, stop_threshold=0.60, confirm_threshold=0.85) == "proceed"


def test_evidence_score_uses_top_retrieval_score():
    assert evidence_score([span(0.50), span(0.91)]) == 0.91
    assert evidence_score([]) == 0.0


def test_require_citeable_spans_needs_score_and_text():
    assert require_citeable_spans([span(0.91)], stop_threshold=0.60) == [span(0.91)]
    assert require_citeable_spans([span(0.50)], stop_threshold=0.60) == []
    assert require_citeable_spans([span(0.95, text="  ")], stop_threshold=0.60) == []


def test_grade_understanding_is_keyword_based_and_citation_bound():
    item = CheckItem(
        question="What does attention do?",
        expected_answer="It focuses relevant context.",
        expected_keywords=["focuses", "context"],
        citation_id="note/attention::0",
    )

    grade = grade_understanding("It focuses context for the model.", item)

    assert grade.correct is True
    assert grade.matched_keywords == ["focuses", "context"]
    assert grade.missing_keywords == []
    assert grade.citation_id == "note/attention::0"


def test_grade_understanding_reports_scorer_version_and_match_modes():
    item = CheckItem(
        question="What does attention do?",
        expected_answer="It focuses relevant context.",
        expected_keywords=["focus", "context"],
        citation_id="note/attention::0",
    )

    grade = grade_understanding("It can focus on context.", item)

    assert grade.scorer_version == "concept-v1"
    assert grade.matched_keyword_modes == {
        "focus": "literal",
        "context": "literal",
    }
    assert grade.missing_keyword_count == 0


def test_grade_understanding_matches_multi_word_keywords():
    item = CheckItem(
        question="What does attention do?",
        expected_answer="It focuses relevant context.",
        expected_keywords=["relevant context"],
        citation_id="note/attention::0",
    )

    grade = grade_understanding("It helps focus on relevant context.", item)

    assert grade.correct is True
    assert grade.matched_keywords == ["relevant context"]


def test_grade_understanding_reports_missing_keywords():
    item = CheckItem(
        question="What does attention do?",
        expected_answer="It focuses relevant context.",
        expected_keywords=["focuses", "context"],
        citation_id="note/attention::0",
    )

    grade = grade_understanding("It helps the model.", item)

    assert grade.correct is False
    assert grade.missing_keywords == ["focuses", "context"]


def test_grade_understanding_accepts_curated_semantic_aliases():
    item = CheckItem(
        question="What does attention help the model do?",
        expected_answer="It helps focus on relevant context.",
        expected_keywords=["focus", "relevant context"],
        citation_id="note/attention::0",
    )

    grade = grade_understanding(
        "It helps the model pay attention to the important context.",
        item,
    )

    assert grade.correct is True
    assert grade.matched_keywords == ["focus", "relevant context"]
    assert grade.missing_keywords == []
    assert grade.matched_keyword_modes == {
        "focus": "semantic_alias",
        "relevant context": "semantic_alias",
    }


def test_grade_understanding_keeps_partial_semantic_answers_incorrect():
    item = CheckItem(
        question="What does attention help the model do?",
        expected_answer="It helps focus on relevant context.",
        expected_keywords=["focus", "relevant context"],
        citation_id="note/attention::0",
    )

    grade = grade_understanding("It stores context in memory.", item)

    assert grade.correct is False
    assert grade.matched_keywords == []
    assert grade.missing_keywords == ["focus", "relevant context"]
    assert grade.matched_keyword_modes == {}


def test_grade_understanding_rejects_alias_without_all_expected_concepts():
    item = CheckItem(
        question="What does attention help the model do?",
        expected_answer="It helps focus on relevant context.",
        expected_keywords=["focus", "relevant context"],
        citation_id="note/attention::0",
    )

    grade = grade_understanding("It pays attention to random details.", item)

    assert grade.correct is False
    assert grade.matched_keywords == ["focus"]
    assert grade.missing_keywords == ["relevant context"]
    assert grade.matched_keyword_modes == {"focus": "semantic_alias"}


def test_grade_understanding_allows_literal_and_semantic_mix():
    item = CheckItem(
        question="What does an agent harness control?",
        expected_answer="It controls tools and guardrails around the model.",
        expected_keywords=["tools", "guardrails"],
        citation_id="slide/harness::37",
    )

    grade = grade_understanding(
        "It controls external tools and safety boundaries.",
        item,
    )

    assert grade.correct is True
    assert grade.matched_keyword_modes == {
        "tools": "literal",
        "guardrails": "semantic_alias",
    }


def test_answer_grounded_in_spans_reuses_week2_faithfulness_fallback():
    assert answer_grounded_in_spans("Attention focuses relevant context.", [span()])
    assert not answer_grounded_in_spans("Attention stores long term customer profiles.", [span()])
