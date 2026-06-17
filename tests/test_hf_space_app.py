from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from genacademy_coach.web.gradio_app import SAFE_TEACH_TRACE_FIELDS, safe_trace_rows


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


def test_hf_deploy_files_pin_port_data_and_embed_dim():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    start_script = Path("scripts/start_hf_space.sh").read_text(encoding="utf-8")

    assert "EXPOSE 7860" in dockerfile
    assert "GENACADEMY_EMBED_DIM=384" in dockerfile
    assert "GENACADEMY_COACH_DATA_DIR=/data" in dockerfile
    assert "GENACADEMY_DATA_DIR=/data" in dockerfile
    assert "PORT" in Path("src/genacademy_coach/web/gradio_app.py").read_text(encoding="utf-8")
    assert "GENACADEMY_EMBED_DIM" in start_script


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
    assert module.SPACE_VARIABLES["GENACADEMY_EMBED_DIM"] == "384"
