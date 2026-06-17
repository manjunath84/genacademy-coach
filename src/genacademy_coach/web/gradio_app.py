from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr

from genacademy_coach.foundation import Foundation
from genacademy_coach.quiz_session import QuizSession
from genacademy_coach.settings import CoachSettings
from genacademy_coach.teach_session import CoachSession
from genacademy_coach.teach_types import LearnerProfile

STYLE_CHOICES = ["concise", "analogy", "step_by_step"]
TRACK_LENS_CHOICES = ["low_code_no_code", "code_heavy", "bridge"]
VALID_OPTION_IDS = frozenset({"A", "B", "C", "D"})

SAFE_TEACH_TRACE_FIELDS = (
    "turn",
    "observation",
    "next_action",
    "strategy",
    "evidence_score",
    "evidence_band",
    "faithfulness_ok",
    "retrieved_citation_ids",
    "tool_calls",
)
SAFE_QUIZ_TRACE_FIELDS = (
    "topic_hash",
    "evidence_score",
    "evidence_band",
    "citation_ids",
    "question_ids",
    "selected_option_ids",
    "correctness",
    "refusal_reason",
    "actions",
)


def _require_topic(topic: str) -> str:
    value = topic.strip()
    if not value:
        raise ValueError("topic is required")
    return value


def _coerce_choice(value: str, choices: list[str], label: str) -> str:
    if value not in choices:
        raise ValueError(f"{label} must be one of: {', '.join(choices)}")
    return value


def _parse_answers(raw: str) -> list[str] | None:
    if not raw.strip():
        return None
    answers = [item.strip().upper() for item in raw.split(",") if item.strip()]
    invalid = sorted(set(answers) - VALID_OPTION_IDS)
    if invalid:
        raise ValueError("answers must use option IDs A, B, C, or D")
    return answers


def safe_trace_rows(trace_path: str, allowed_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    path = Path(trace_path)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        rows.append({field: payload[field] for field in allowed_fields if field in payload})
    return rows


def _runtime() -> tuple[CoachSettings, Foundation]:
    settings = CoachSettings.from_env()
    return settings, Foundation.build(settings)


def _error_payload(exc: Exception) -> tuple[str, dict[str, Any]]:
    return (
        "I could not run the demo safely. Check the Space settings, provider key, "
        "and corpus setup.",
        {"status": "error", "error_type": type(exc).__name__},
    )


def run_teach_session(
    topic: str,
    style: str,
    track_lens: str,
    learner_answer: str,
) -> tuple[str, dict[str, Any]]:
    try:
        clean_topic = _require_topic(topic)
        clean_style = _coerce_choice(style, STYLE_CHOICES, "style")
        clean_lens = _coerce_choice(track_lens, TRACK_LENS_CHOICES, "track lens")
        settings, foundation = _runtime()
        session = CoachSession(
            session_id=f"hf-teach-{uuid.uuid4().hex[:10]}",
            topic=clean_topic,
            settings=settings,
            foundation=foundation,
            profile=LearnerProfile(style=clean_style, track_lens=clean_lens),
        )
        first = session.start()
        sections = ["### Turn 1", first.response.learner_message]
        if first.response.check_question:
            sections.extend(["", f"**Check:** {first.response.check_question}"])

        answer = learner_answer.strip()
        result = first
        if answer:
            result = session.respond(answer)
            sections.extend(["", "### Turn 2", result.response.learner_message])
            if result.response.check_question:
                sections.extend(["", f"**Check:** {result.response.check_question}"])

        metadata = {
            "status": "ok",
            "session_id": result.session_id,
            "trace_file": Path(result.trace_path).name,
            "profile": {
                "style": result.profile.style,
                "track_lens": result.profile.track_lens,
                "turn_count": result.profile.turn_count,
            },
            "trace": safe_trace_rows(result.trace_path, SAFE_TEACH_TRACE_FIELDS),
        }
        return "\n".join(sections), metadata
    except Exception as exc:
        return _error_payload(exc)


def run_quiz_session(
    topic: str,
    question_count: int | float,
    answers: str,
) -> tuple[str, dict[str, Any]]:
    try:
        clean_topic = _require_topic(topic)
        count = int(question_count)
        selected = _parse_answers(answers)
        settings, foundation = _runtime()
        session = QuizSession(
            session_id=f"hf-quiz-{uuid.uuid4().hex[:10]}",
            topic=clean_topic,
            settings=settings,
            foundation=foundation,
            question_count=count,
        )
        result = session.run(selected)
        metadata = {
            "status": "ok",
            "session_id": result.session_id,
            "trace_file": Path(result.trace_path).name,
            "trace": safe_trace_rows(result.trace_path, SAFE_QUIZ_TRACE_FIELDS),
        }
        if result.refusal_reason is not None:
            metadata["refusal_reason"] = result.refusal_reason
            return "I could not generate a grounded quiz for this topic.", metadata

        sections: list[str] = []
        for index, question in enumerate(result.questions, start=1):
            sections.extend([f"### Question {index}", question.prompt])
            sections.extend(
                f"{option.option_id}. {option.text}" for option in question.options
            )
            sections.append("")

        if selected is not None:
            sections.append(f"**Score:** {result.score}/{len(result.questions)}")
            for grade in result.grades:
                status = "correct" if grade.correct else "incorrect"
                sections.append(
                    f"- {grade.question_id}: {status} "
                    f"(selected {grade.selected_option_id}, answer {grade.correct_option_id})"
                )
        return "\n".join(sections).strip(), metadata
    except Exception as exc:
        return _error_payload(exc)


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="GenAcademy Coach") as demo:
        gr.Markdown("# GenAcademy Coach")
        with gr.Tab("Teach"):
            teach_topic = gr.Textbox(label="Topic", value="agent harness")
            with gr.Row():
                style = gr.Dropdown(STYLE_CHOICES, value="analogy", label="Style")
                track_lens = gr.Dropdown(
                    TRACK_LENS_CHOICES,
                    value="code_heavy",
                    label="Track lens",
                )
            learner_answer = gr.Textbox(label="Learner answer", lines=3)
            teach_button = gr.Button("Run teach session")
            teach_output = gr.Markdown(label="Teach output")
            teach_metadata = gr.JSON(label="Redacted metadata")
            teach_button.click(
                fn=run_teach_session,
                inputs=[teach_topic, style, track_lens, learner_answer],
                outputs=[teach_output, teach_metadata],
            )

        with gr.Tab("Quiz"):
            quiz_topic = gr.Textbox(label="Topic", value="agent harness")
            question_count = gr.Slider(
                minimum=1,
                maximum=3,
                step=1,
                value=3,
                label="Questions",
            )
            answers = gr.Textbox(label="Answers", placeholder="A,B,C")
            quiz_button = gr.Button("Run quiz")
            quiz_output = gr.Markdown(label="Quiz output")
            quiz_metadata = gr.JSON(label="Redacted metadata")
            quiz_button.click(
                fn=run_quiz_session,
                inputs=[quiz_topic, question_count, answers],
                outputs=[quiz_output, quiz_metadata],
            )
    return demo


demo = build_demo()


def launch() -> None:
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "7860")),
        show_error=False,
    )
