import importlib.util
from pathlib import Path
from types import SimpleNamespace


def load_script(path: str):
    spec = importlib.util.spec_from_file_location(Path(path).stem, Path(path).resolve())
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_skillgap_demo_prints_ranked_redacted_plan(monkeypatch, capsys):
    module = load_script("scripts/run_skillgap_demo.py")

    class FakeSkillGapSession:
        def __init__(self, **kwargs):
            assert kwargs["session_id"] == "gap-demo"
            assert kwargs["source_session_ids"] == ["teach-1", "quiz-1"]

        def run(self):
            return SimpleNamespace(
                items=[
                    SimpleNamespace(
                        gap_id="note/agent-harness::0",
                        priority_score=6,
                        next_action="review_next",
                        evidence_score=0.91,
                        evidence_band="proceed",
                        citation_ids=["handout/review::0"],
                        review_next="Review Agent Field Guide at handout/review::0.",
                        reason_code=None,
                    )
                ],
                trace_path="/tmp/skillgap.jsonl",
            )

    monkeypatch.setattr(module.CoachSettings, "from_env", lambda: object())
    monkeypatch.setattr(module.Foundation, "build", lambda _settings: object())
    monkeypatch.setattr(module, "SkillGapSession", FakeSkillGapSession)
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_skillgap_demo.py",
            "--session-id",
            "gap-demo",
            "--source-session-id",
            "teach-1",
            "--source-session-id",
            "quiz-1",
        ],
    )

    module.main()

    out = capsys.readouterr().out
    assert "Skill-Gap Diagnosis" in out
    assert "note/agent-harness::0" in out
    assert "Review Agent Field Guide" in out
    assert "trace=/tmp/skillgap.jsonl" in out
