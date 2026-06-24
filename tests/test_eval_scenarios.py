from genacademy_coach.eval_scenarios import extract_questions, question_records_for_item


def test_extract_questions_numbered():
    assert extract_questions("1. What is attention?\n2. Why cite?") == [
        "What is attention?",
        "Why cite?",
    ]


def test_question_records_reads_runtime_source(tmp_path):
    d = tmp_path / "eq"
    d.mkdir()
    (d / "q.md").write_text("1. What is attention?\n")
    rows = question_records_for_item(d, {"id": "i", "split": "dev", "source_file": "q.md"})
    assert rows[0]["scenario_id"] == "i:000" and rows[0]["question_text"] == "What is attention?"
