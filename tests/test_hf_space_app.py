from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from genacademy_coach.web import gradio_app
from genacademy_coach.web.gradio_app import (
    DEFAULT_LOCAL_SERVER_NAME,
    DEMO_PRESET_TOPICS,
    EMPTY_CORPUS_STATUS_MESSAGE,
    QUIZ_GROUNDED_PRESET,
    SAFE_QUIZ_TRACE_FIELDS,
    SAFE_SKILLGAP_TRACE_FIELDS,
    SAFE_TEACH_TRACE_FIELDS,
    SKILLGAP_SOURCE_PRESET,
    TEACH_GROUNDED_PRESET,
    TEACH_REFUSAL_PRESET,
    UserInputError,
    _coerce_choice,
    _error_payload,
    _format_trace_summary,
    _parse_answers,
    _parse_source_session_ids,
    _require_topic,
    _server_name,
    _space_status_message,
    fill_quiz_grounded_preset,
    fill_skillgap_preset,
    fill_teach_grounded_preset,
    fill_teach_refusal_preset,
    run_quiz_session,
    run_skillgap_session,
    safe_trace_rows,
)


def load_deploy_script():
    script_path = Path("scripts/deploy_hf_space.py").resolve()
    spec = importlib.util.spec_from_file_location("deploy_hf_space", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_safe_trace_rows_omit_raw_teach_fields(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    private_value = "PRIVATE_TOPIC_AND_GENERATED_TEXT"
    trace_path.write_text(
        json.dumps(
            {
                "turn": 1,
                "learner_input": private_value,
                "learner_message": private_value,
                "next_action": "drill",
                "strategy": "short_drill",
                "evidence_score": 0.71,
                "evidence_band": "confirm",
                "retrieved_citation_ids": ["chunk-1"],
                "tool_calls": ["retrieve_course_corpus"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rows = safe_trace_rows(str(trace_path), SAFE_TEACH_TRACE_FIELDS)

    serialized = json.dumps(rows, sort_keys=True)
    assert rows == [
        {
            "turn": 1,
            "next_action": "drill",
            "strategy": "short_drill",
            "evidence_score": 0.71,
            "evidence_band": "confirm",
            "retrieved_citation_ids": ["chunk-1"],
            "tool_calls": ["retrieve_course_corpus"],
        }
    ]
    assert private_value not in serialized
    assert "learner_input" not in serialized
    assert "learner_message" not in serialized


def test_safe_trace_rows_omit_raw_quiz_fields_and_skip_malformed_rows(tmp_path, caplog):
    trace_path = tmp_path / "quiz.jsonl"
    private_value = "PRIVATE_QUIZ_TEXT"
    trace_path.write_text(
        "\n".join(
            [
                "{bad json",
                json.dumps(
                    {
                        "topic_hash": "abc123",
                        "prompt": private_value,
                        "expected_answer": private_value,
                        "rationale": private_value,
                        "evidence_score": 0.71,
                        "evidence_band": "confirm",
                        "citation_ids": ["chunk-1"],
                        "question_ids": ["q1"],
                        "selected_option_ids": ["A"],
                        "correctness": [True],
                        "actions": ["retrieve_course_corpus"],
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    rows = safe_trace_rows(str(trace_path), SAFE_QUIZ_TRACE_FIELDS)

    serialized = json.dumps(rows, sort_keys=True)
    assert rows == [
        {
            "topic_hash": "abc123",
            "evidence_score": 0.71,
            "evidence_band": "confirm",
            "citation_ids": ["chunk-1"],
            "question_ids": ["q1"],
            "selected_option_ids": ["A"],
            "correctness": [True],
            "actions": ["retrieve_course_corpus"],
        }
    ]
    assert private_value not in serialized
    assert "malformed trace row" in caplog.text


def test_safe_trace_rows_omit_raw_skillgap_fields(tmp_path):
    trace_path = tmp_path / "skillgap.jsonl"
    private_value = "PRIVATE_SKILLGAP_TEXT"
    trace_path.write_text(
        json.dumps(
            {
                "session_id": "skillgap-1",
                "topic_hash": "abc123",
                "gap_id": "note/agent-harness::0",
                "source_session_ids": ["teach-1"],
                "evidence_score": 0.91,
                "evidence_band": "proceed",
                "citation_ids": ["chunk-1"],
                "quiz_correct": 0,
                "quiz_total": 1,
                "struggle_count": 1,
                "refusal_count": 0,
                "next_action": "review_next",
                "escalated": False,
                "reason_code": None,
                "raw_topic": private_value,
                "review_next": private_value,
                "learner_message": private_value,
            }
        ),
        encoding="utf-8",
    )

    rows = safe_trace_rows(str(trace_path), SAFE_SKILLGAP_TRACE_FIELDS)

    serialized = json.dumps(rows, sort_keys=True)
    assert set(rows[0]) == set(SAFE_SKILLGAP_TRACE_FIELDS)
    assert private_value not in serialized
    assert "raw_topic" not in serialized
    assert '"review_next":' not in serialized
    assert "learner_message" not in serialized


def test_trace_summary_uses_only_safe_fields():
    private_value = "PRIVATE_TRACE_TEXT"
    metadata = {
        "status": "ok",
        "trace": [
            {
                "turn": 1,
                "learner_message": private_value,
                "next_action": "drill",
                "strategy": "short_drill",
                "evidence_score": 0.7114,
                "evidence_band": "confirm",
                "faithfulness_ok": True,
                "retrieved_citation_ids": ["chunk-1", "chunk-2"],
                "tool_calls": ["retrieve_course_corpus"],
            }
        ],
    }

    summary = _format_trace_summary(metadata, mode="teach")

    assert "gc-trace-card" in summary
    assert "drill" in summary
    assert "0.711" in summary
    assert "2 cited spans" in summary
    assert "chunk-1" not in summary
    assert "chunk-2" not in summary
    assert "| turn |" not in summary
    assert private_value not in summary
    assert "learner_message" not in summary


def test_skillgap_trace_summary_uses_only_safe_fields():
    private_value = "PRIVATE_TRACE_TEXT"
    metadata = {
        "status": "ok",
        "trace": [
            {
                "gap_id": "note/agent-harness::0",
                "review_next": private_value,
                "next_action": "review_next",
                "evidence_score": 0.911,
                "evidence_band": "proceed",
                "source_session_ids": ["teach-1", "quiz-1"],
                "citation_ids": ["chunk-1", "chunk-2"],
                "quiz_correct": 0,
                "quiz_total": 1,
                "struggle_count": 1,
                "refusal_count": 0,
                "escalated": False,
            }
        ],
    }

    summary = _format_trace_summary(metadata, mode="skillgap")

    assert "gc-trace-card" in summary
    assert "review_next" in summary
    assert "0.911" in summary
    assert "2 cited spans" in summary
    assert "2 sessions" in summary
    assert "chunk-1" not in summary
    assert "chunk-2" not in summary
    assert private_value not in summary


def test_error_payload_logs_trace_and_returns_redacted_error_id(caplog):
    private_value = "PRIVATE_PROVIDER_DETAIL"

    try:
        raise RuntimeError(private_value)
    except RuntimeError as exc:
        message, metadata = _error_payload(exc)

    assert metadata["status"] == "error"
    assert len(metadata["error_id"]) == 8
    assert metadata["error_id"] in message
    assert "failed closed" in message
    assert "hard-refresh" in message
    assert "approved Chroma index" in message
    assert private_value not in message
    assert private_value not in json.dumps(metadata)
    assert private_value in caplog.text


def test_space_status_message_explains_empty_corpus_without_private_data(
    tmp_path,
    monkeypatch,
):
    private_value = "PRIVATE_CORPUS_PATH_OR_TEXT"

    class EmptyStore:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get_all_chunks(self):
            return []

    monkeypatch.setenv("GENACADEMY_COACH_DATA_DIR", str(tmp_path / private_value))
    monkeypatch.setattr(gradio_app, "ChromaStore", EmptyStore)

    message = _space_status_message()

    assert message == EMPTY_CORPUS_STATUS_MESSAGE
    assert private_value not in message


def test_space_status_message_omits_banner_when_corpus_exists(tmp_path, monkeypatch):
    class NonEmptyStore:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get_all_chunks(self):
            return [object()]

    monkeypatch.setenv("GENACADEMY_COACH_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(gradio_app, "ChromaStore", NonEmptyStore)

    assert _space_status_message() is None


def test_input_helpers_return_specific_safe_errors():
    assert _parse_answers("a, B,c ") == ["A", "B", "C"]
    assert _parse_answers(" ") is None

    with pytest.raises(UserInputError, match="topic is required"):
        _require_topic(" ")
    with pytest.raises(UserInputError, match="answers must use option IDs"):
        _parse_answers("A,Z")
    with pytest.raises(UserInputError, match="style must be one of"):
        _coerce_choice("verbose", ["concise"], "style")
    assert _parse_source_session_ids("teach-1, quiz_2\nskillgap:3") == [
        "teach-1",
        "quiz_2",
        "skillgap:3",
    ]
    with pytest.raises(UserInputError, match="at least one source session id"):
        _parse_source_session_ids(" ")
    with pytest.raises(UserInputError, match="session id may only contain"):
        _parse_source_session_ids("../private")


def test_demo_presets_are_fixed_public_safe_values_and_not_eval_manifest_entries():
    assert fill_teach_grounded_preset() == TEACH_GROUNDED_PRESET
    assert fill_teach_refusal_preset() == TEACH_REFUSAL_PRESET
    assert fill_quiz_grounded_preset() == QUIZ_GROUNDED_PRESET
    assert fill_skillgap_preset() == SKILLGAP_SOURCE_PRESET
    assert QUIZ_GROUNDED_PRESET == ("agent harness", 1, "A", False)

    manifest = json.loads(Path("eval/split_manifest.json").read_text(encoding="utf-8"))
    eval_tokens = {
        str(value)
        for item in manifest["items"]
        for value in (item["id"], item["source_file"], item["source_sha256"])
    }
    assert DEMO_PRESET_TOPICS.isdisjoint(eval_tokens)
    assert set(_parse_source_session_ids(SKILLGAP_SOURCE_PRESET)).isdisjoint(eval_tokens)
    assert TEACH_REFUSAL_PRESET[0] == "Gen Academy cafeteria menu"


def test_runtime_reuses_foundation_for_local_demo(monkeypatch):
    settings = object()
    foundation = object()
    build_calls = []

    gradio_app._runtime.cache_clear()
    monkeypatch.setattr(gradio_app.CoachSettings, "from_env", lambda: settings)

    def fake_build(value):
        build_calls.append(value)
        return foundation

    monkeypatch.setattr(gradio_app.Foundation, "build", fake_build)

    try:
        assert gradio_app._runtime() == (settings, foundation)
        assert gradio_app._runtime() == (settings, foundation)
    finally:
        gradio_app._runtime.cache_clear()

    assert build_calls == [settings]


def test_quiz_answer_count_mismatch_returns_specific_input_error(monkeypatch):
    def fail_runtime():
        raise AssertionError("runtime should not be built for invalid input")

    monkeypatch.setattr(gradio_app, "_runtime", fail_runtime)

    message, metadata = run_quiz_session("agent harness", 3, "A,B")

    assert message == "expected 3 answers, received 2"
    assert metadata == {"status": "invalid_input"}


def test_run_quiz_session_hides_generated_quiz_text_by_default(tmp_path, monkeypatch):
    private_value = "PRIVATE_GENERATED_QUIZ_TEXT"
    trace_path = tmp_path / "quiz.jsonl"
    trace_path.write_text(
        json.dumps(
            {
                "topic_hash": "abc123",
                "evidence_score": 0.71,
                "evidence_band": "confirm",
                "citation_ids": ["chunk-1"],
                "question_ids": ["q1"],
                "selected_option_ids": ["A"],
                "correctness": [True],
                "actions": ["retrieve_course_corpus", "generate_quiz_items", "grade_quiz"],
            }
        ),
        encoding="utf-8",
    )

    class FakeQuizSession:
        def __init__(self, **kwargs):
            pass

        def run(self, selected_option_ids=None):
            return SimpleNamespace(
                session_id="s1",
                questions=[
                    SimpleNamespace(
                        question_id="q1",
                        prompt=private_value,
                        options=[SimpleNamespace(option_id="A", text=private_value)],
                    )
                ],
                grades=[
                    SimpleNamespace(
                        question_id="q1",
                        selected_option_id="A",
                        correct_option_id="A",
                        correct=True,
                    )
                ],
                score=1,
                refusal_reason=None,
                trace_path=str(trace_path),
            )

    monkeypatch.setattr(gradio_app, "_runtime", lambda: (object(), object()))
    monkeypatch.setattr(gradio_app, "QuizSession", FakeQuizSession)

    message, metadata = run_quiz_session("agent harness", 1, "A")

    serialized = json.dumps(metadata, sort_keys=True)
    assert "Question text is hidden by default" in message
    assert "**Score:** 1/1" in message
    assert "answer A" not in message
    assert private_value not in message
    assert private_value not in serialized

    visible_message, _ = run_quiz_session("agent harness", 1, "A", show_questions=True)
    assert private_value in visible_message


def test_run_quiz_session_metadata_uses_safe_trace_allow_list(tmp_path, monkeypatch):
    private_value = "PRIVATE_GENERATED_QUIZ_TEXT"
    trace_path = tmp_path / "quiz.jsonl"
    trace_path.write_text(
        json.dumps(
            {
                "topic_hash": "abc123",
                "prompt": private_value,
                "expected_answer": private_value,
                "rationale": private_value,
                "evidence_score": 0.71,
                "evidence_band": "confirm",
                "citation_ids": ["chunk-1"],
                "question_ids": [],
                "selected_option_ids": [],
                "correctness": [],
                "refusal_reason": "no citeable course corpus found for quiz",
                "actions": ["retrieve_course_corpus", "refuse_escalate"],
            }
        ),
        encoding="utf-8",
    )

    class FakeQuizSession:
        def __init__(self, **kwargs):
            pass

        def run(self, selected_option_ids=None):
            return SimpleNamespace(
                session_id="s1",
                questions=[],
                grades=[],
                score=0,
                refusal_reason="no citeable course corpus found for quiz",
                trace_path=str(trace_path),
            )

    monkeypatch.setattr(gradio_app, "_runtime", lambda: (object(), object()))
    monkeypatch.setattr(gradio_app, "QuizSession", FakeQuizSession)

    message, metadata = run_quiz_session("agent harness", 1, "")

    serialized = json.dumps(metadata, sort_keys=True)
    assert message == "I could not generate a grounded quiz for this topic."
    assert metadata["status"] == "ok"
    assert private_value not in serialized
    assert "prompt" not in serialized


def test_run_skillgap_session_returns_redacted_report_and_metadata(tmp_path, monkeypatch):
    private_value = "PRIVATE_SKILLGAP_REVIEW_TARGET"
    trace_path = tmp_path / "skillgap.jsonl"
    trace_path.write_text(
        json.dumps(
            {
                "session_id": "skillgap-1",
                "topic_hash": "abc123",
                "gap_id": "note/agent-harness::0",
                "source_session_ids": ["teach-1", "quiz-1"],
                "evidence_score": 0.91,
                "evidence_band": "proceed",
                "citation_ids": ["chunk-1"],
                "quiz_correct": 0,
                "quiz_total": 1,
                "struggle_count": 1,
                "refusal_count": 0,
                "next_action": "review_next",
                "escalated": False,
                "reason_code": None,
                "review_next": private_value,
                "raw_topic": private_value,
            }
        ),
        encoding="utf-8",
    )

    class FakeSkillGapSession:
        def __init__(self, **kwargs):
            assert kwargs["source_session_ids"] == ["teach-1", "quiz-1"]

        def run(self):
            return SimpleNamespace(
                session_id="skillgap-1",
                source_session_ids=["teach-1", "quiz-1"],
                trace_path=str(trace_path),
                items=[
                    SimpleNamespace(
                        gap_id="note/agent-harness::0",
                        priority_score=6,
                        next_action="review_next",
                        evidence_score=0.91,
                        evidence_band="proceed",
                        citation_ids=["chunk-1"],
                        quiz_correct=0,
                        quiz_total=1,
                        struggle_count=1,
                        refusal_count=0,
                        reason_code=None,
                        review_next=private_value,
                    )
                ],
            )

    monkeypatch.setattr(gradio_app, "_runtime", lambda: (object(), object()))
    monkeypatch.setattr(gradio_app, "SkillGapSession", FakeSkillGapSession)

    message, metadata = run_skillgap_session("teach-1, quiz-1")

    serialized = json.dumps(metadata, sort_keys=True)
    assert "Skill-Gap Diagnosis" in message
    assert "review cited course material" in message
    assert "chunk-1" in message
    assert metadata["status"] == "ok"
    assert private_value not in message
    assert private_value not in serialized
    assert "raw_topic" not in serialized


def test_web_framework_imports_stay_outside_core():
    offenders = []
    for path in Path("src/genacademy_coach").rglob("*.py"):
        if "/web/" in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8")
        if "import gradio" in text or "from gradio" in text:
            offenders.append(str(path))
        if "import fastapi" in text or "from fastapi" in text:
            offenders.append(str(path))
    assert offenders == []


def test_gradio_launch_does_not_enable_public_share():
    app_text = Path("src/genacademy_coach/web/gradio_app.py").read_text(encoding="utf-8")

    assert "share=False" in app_text
    assert "share=True" not in app_text


def test_gradio_launch_binds_locally_by_default_and_all_interfaces_when_configured(
    monkeypatch,
):
    monkeypatch.delenv("GENACADEMY_COACH_SERVER_NAME", raising=False)
    assert _server_name() == DEFAULT_LOCAL_SERVER_NAME

    monkeypatch.setenv("GENACADEMY_COACH_SERVER_NAME", "0.0.0.0")
    assert _server_name() == "0.0.0.0"


def test_gradio_ui_uses_genacademy_console_shell():
    app_text = Path("src/genacademy_coach/web/gradio_app.py").read_text(encoding="utf-8")

    assert "gc-app-header" in app_text
    assert "gc-status-rail" in app_text
    assert "gc-workbench" in app_text
    assert "gc-action-row" in app_text
    assert "min-height: 44px" in app_text
    assert "_Awaiting teach run._" in app_text
    assert "_Awaiting quiz run._" in app_text
    assert "_Awaiting diagnosis run._" in app_text
    assert "Skill-Gap" in app_text
    assert "GENACADEMY_COACH_CSS" in app_text
    assert "css=GENACADEMY_COACH_CSS" in app_text
    assert "Evidence fallback" in app_text


def test_hf_deploy_files_pin_port_data_and_embed_dim():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    start_script = Path("scripts/start_hf_space.sh").read_text(encoding="utf-8")

    assert "EXPOSE 7860" in dockerfile
    assert "GENACADEMY_EMBED_DIM=384" in dockerfile
    assert "GENACADEMY_COACH_DATA_DIR=/data" in dockerfile
    assert "GENACADEMY_DATA_DIR=/data" in dockerfile
    assert "ARG GENACADEMY_RAG_REF=517faffbfdf37f8972f5bf3076e21eb2ab0ba7b4" in dockerfile
    assert "server_port=int(os.environ.get(\"PORT\", \"7860\"))" in Path(
        "src/genacademy_coach/web/gradio_app.py"
    ).read_text(encoding="utf-8")
    assert "GENACADEMY_COACH_SERVER_NAME" in start_script
    assert "0.0.0.0" in start_script
    assert "GENACADEMY_EMBED_DIM" in start_script
    assert "space_startup_check.py || true" in start_script
    assert "logging.basicConfig" in Path("src/genacademy_coach/web/gradio_app.py").read_text(
        encoding="utf-8"
    )


def test_hf_deploy_upload_allow_list_excludes_private_data():
    module = load_deploy_script()
    serialized_allow = " ".join(module.ALLOW_PATTERNS)
    serialized_ignore = " ".join(module.IGNORE_PATTERNS)

    assert ".env" not in serialized_allow
    assert "corpus/" not in serialized_allow
    assert "data/" not in serialized_allow
    assert "traces/" not in serialized_allow
    assert ".env*" in serialized_ignore
    assert "corpus/**" in serialized_ignore
    assert "data/**" in serialized_ignore
    assert "traces/**" in serialized_ignore
    assert "**/__pycache__/**" in serialized_ignore
    assert "**/*.pyc" in serialized_ignore
    assert "eval/**" in serialized_ignore
    assert "scripts/space_startup_check.py" in module.ALLOW_PATTERNS
    assert module.SPACE_VARIABLES["GENACADEMY_EMBED_DIM"] == "384"


def test_hf_deploy_defaults_avoid_factory_reboot(monkeypatch, capsys):
    module = load_deploy_script()

    class FakeApi:
        def __init__(self, token):
            self.token = token
            self.secrets = []
            self.factory_reboot = None

        def create_repo(self, **kwargs):
            return "https://huggingface.co/spaces/Manjunath84/genacademy-coach"

        def add_space_variable(self, *args, **kwargs):
            pass

        def add_space_secret(self, *args, **kwargs):
            self.secrets.append(args)

        def upload_folder(self, **kwargs):
            return SimpleNamespace(oid="abc123")

        def restart_space(self, repo_id, *, factory_reboot):
            self.factory_reboot = factory_reboot

    fake = FakeApi("token")
    monkeypatch.setattr(module, "HfApi", lambda token: fake)
    monkeypatch.setenv("HF_TOKEN", "token")
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("GENACADEMY_HF_FACTORY_REBOOT", raising=False)

    module.main()

    assert fake.factory_reboot is False
    assert fake.secrets == []
    out = capsys.readouterr().out
    assert "factory_reboot=False" in out
    assert "secret_NEBIUS_API_KEY=skipped" in out


def test_hf_deploy_factory_reboot_is_explicit_opt_in(monkeypatch):
    module = load_deploy_script()

    monkeypatch.setenv("GENACADEMY_HF_FACTORY_REBOOT", "true")

    assert module._bool_from_env("GENACADEMY_HF_FACTORY_REBOOT", default=False) is True


def test_hf_deploy_requires_token(monkeypatch):
    module = load_deploy_script()

    monkeypatch.delenv("HF_TOKEN", raising=False)

    with pytest.raises(SystemExit, match="HF_TOKEN is required"):
        module.main()
