from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from genacademy_rag.core.vectorstore import ChromaStore

from genacademy_coach.foundation import Foundation
from genacademy_coach.quiz_session import QuizSession
from genacademy_coach.settings import CoachSettings
from genacademy_coach.teach_session import CoachSession
from genacademy_coach.teach_types import LearnerProfile

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr

logger = logging.getLogger(__name__)

STYLE_CHOICES = ["concise", "analogy", "step_by_step"]
TRACK_LENS_CHOICES = ["low_code_no_code", "code_heavy", "bridge"]
VALID_OPTION_IDS = frozenset({"A", "B", "C", "D"})
EMPTY_CORPUS_STATUS_MESSAGE = (
    "**Deployment shell:** no approved corpus/index is loaded in this Space. "
    "Teach and quiz requests will safely refuse until an approved Chroma index "
    "is available under `/data/chroma`; see the recorded demo for grounded behavior."
)
CORPUS_STATUS_UNAVAILABLE_MESSAGE = (
    "**Deployment status:** corpus status could not be checked. The app fails closed "
    "when course evidence is unavailable; check the private Space logs for the error ID."
)

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


class UserInputError(ValueError):
    """Raised for UI input errors safe to display to the learner."""


def _require_topic(topic: str) -> str:
    value = topic.strip()
    if not value:
        raise UserInputError("topic is required")
    return value


def _coerce_choice(value: str, choices: list[str], label: str) -> str:
    if value not in choices:
        raise UserInputError(f"{label} must be one of: {', '.join(choices)}")
    return value


def _coerce_question_count(value: int | float) -> int:
    count = int(value)
    if count < 1 or count > 3:
        raise UserInputError("question count must be between 1 and 3")
    return count


def _parse_answers(raw: str) -> list[str] | None:
    if not raw.strip():
        return None
    answers = [item.strip().upper() for item in raw.split(",") if item.strip()]
    invalid = sorted(set(answers) - VALID_OPTION_IDS)
    if invalid:
        raise UserInputError("answers must use option IDs A, B, C, or D")
    return answers


def _validate_answer_count(selected: list[str] | None, count: int) -> None:
    if selected is not None and len(selected) != count:
        raise UserInputError(f"expected {count} answers, received {len(selected)}")


def safe_trace_rows(trace_path: str, allowed_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    path = Path(trace_path)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            logger.warning(
                "skipping malformed trace row path=%s line=%d",
                path.name,
                line_number,
            )
            continue
        if not isinstance(payload, dict):
            logger.warning(
                "skipping non-object trace row path=%s line=%d",
                path.name,
                line_number,
            )
            continue
        rows.append({field: payload[field] for field in allowed_fields if field in payload})
    return rows


def _runtime() -> tuple[CoachSettings, Foundation]:
    settings = CoachSettings.from_env()
    return settings, Foundation.build(settings)


def _corpus_chunk_count(settings: CoachSettings) -> int:
    store = ChromaStore(persist_dir=settings.chroma_dir, collection=settings.course_collection)
    return len(store.get_all_chunks())


def _space_status_message() -> str | None:
    try:
        settings = CoachSettings.from_env()
        chunk_count = _corpus_chunk_count(settings)
    except Exception:
        error_id = uuid.uuid4().hex[:8]
        logger.exception("space corpus status check failed error_id=%s", error_id)
        return f"{CORPUS_STATUS_UNAVAILABLE_MESSAGE} `{error_id}`."
    if chunk_count == 0:
        return EMPTY_CORPUS_STATUS_MESSAGE
    return None


def _input_error_payload(message: str) -> tuple[str, dict[str, Any]]:
    return message, {"status": "invalid_input"}


def _error_payload(exc: Exception) -> tuple[str, dict[str, Any]]:
    error_id = uuid.uuid4().hex[:8]
    logger.exception("space handler failed error_id=%s", error_id)
    return (
        "I could not run the demo safely. Check the Space settings, provider key, "
        f"and corpus setup. Error ID: {error_id}.",
        {"status": "error", "error_id": error_id},
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
    except UserInputError as exc:
        return _input_error_payload(str(exc))
    except Exception as exc:
        return _error_payload(exc)


def run_quiz_session(
    topic: str,
    question_count: int | float,
    answers: str,
) -> tuple[str, dict[str, Any]]:
    try:
        clean_topic = _require_topic(topic)
        count = _coerce_question_count(question_count)
        selected = _parse_answers(answers)
        _validate_answer_count(selected, count)
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
    except UserInputError as exc:
        return _input_error_payload(str(exc))
    except Exception as exc:
        return _error_payload(exc)


def build_demo(status_message: str | None = None) -> gr.Blocks:
    with gr.Blocks(title="GenAcademy Coach") as demo:
        gr.Markdown("# GenAcademy Coach")
        if status_message is not None:
            gr.Markdown(status_message)
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


demo = build_demo(_space_status_message())


def launch() -> None:
    logging.basicConfig(
        level=os.environ.get("GENACADEMY_LOG_LEVEL", "INFO"),
        format="%(levelname)s:%(name)s:%(message)s",
    )
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "7860")),
        show_error=False,
    )
