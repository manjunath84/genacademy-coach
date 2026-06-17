from genacademy_coach.settings import CoachSettings


def test_teach_loop_settings_default_under_repo_root(tmp_path, monkeypatch):
    monkeypatch.setenv("GENACADEMY_COACH_ROOT", str(tmp_path))
    monkeypatch.delenv("GENACADEMY_COACH_TRACE_DIR", raising=False)
    monkeypatch.delenv("GENACADEMY_COACH_REVIEW_QUEUE_PATH", raising=False)
    monkeypatch.delenv("GENACADEMY_COACH_STOP_THRESHOLD", raising=False)
    monkeypatch.delenv("GENACADEMY_COACH_CONFIRM_THRESHOLD", raising=False)
    monkeypatch.delenv("GENACADEMY_COACH_MAX_TURNS", raising=False)

    settings = CoachSettings.from_env()

    assert settings.trace_dir == tmp_path / "traces"
    assert settings.review_queue_path == tmp_path / "review_queue.jsonl"
    assert settings.stop_threshold == 0.40
    assert settings.confirm_threshold == 0.85
    assert settings.max_teach_turns == 4


def test_teach_loop_settings_can_be_overridden(tmp_path, monkeypatch):
    monkeypatch.setenv("GENACADEMY_COACH_ROOT", str(tmp_path))
    monkeypatch.setenv("GENACADEMY_COACH_TRACE_DIR", str(tmp_path / "tmp-traces"))
    monkeypatch.setenv("GENACADEMY_COACH_REVIEW_QUEUE_PATH", str(tmp_path / "tmp-review.jsonl"))
    monkeypatch.setenv("GENACADEMY_COACH_STOP_THRESHOLD", "0.55")
    monkeypatch.setenv("GENACADEMY_COACH_CONFIRM_THRESHOLD", "0.82")
    monkeypatch.setenv("GENACADEMY_COACH_MAX_TURNS", "3")

    settings = CoachSettings.from_env()

    assert settings.trace_dir == tmp_path / "tmp-traces"
    assert settings.review_queue_path == tmp_path / "tmp-review.jsonl"
    assert settings.stop_threshold == 0.55
    assert settings.confirm_threshold == 0.82
    assert settings.max_teach_turns == 3


def test_blank_path_env_values_do_not_override_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("GENACADEMY_COACH_ROOT", str(tmp_path))
    monkeypatch.setenv("GENACADEMY_COACH_DATA_DIR", "")
    monkeypatch.setenv("GENACADEMY_COACH_CORPUS_DIR", "")
    monkeypatch.setenv("GENACADEMY_COACH_EVAL_QUESTIONS_DIR", "")
    monkeypatch.setenv("GENACADEMY_COACH_TRACE_DIR", "")
    monkeypatch.setenv("GENACADEMY_COACH_REVIEW_QUEUE_PATH", "")

    settings = CoachSettings.from_env()

    assert settings.data_dir == tmp_path / "data"
    assert settings.corpus_dir == tmp_path / "corpus"
    assert settings.eval_questions_dir == tmp_path / "corpus" / "eval-questions"
    assert settings.trace_dir == tmp_path / "traces"
    assert settings.review_queue_path == tmp_path / "review_queue.jsonl"
