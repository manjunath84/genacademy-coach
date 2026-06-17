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
TEACH_GROUNDED_PRESET = (
    "agent harness",
    "analogy",
    "code_heavy",
    "It is just one prompt with no tool checks or feedback.",
)
TEACH_REFUSAL_PRESET = (
    "Gen Academy cafeteria menu",
    "concise",
    "low_code_no_code",
    "",
)
QUIZ_GROUNDED_PRESET = ("agent harness", 3, "A,B,C", False)
DEMO_PRESET_TOPICS = frozenset(
    {
        TEACH_GROUNDED_PRESET[0],
        TEACH_REFUSAL_PRESET[0],
        QUIZ_GROUNDED_PRESET[0],
    }
)
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

GENACADEMY_COACH_CSS = """
:root {
  --gc-paper: #f5f6f1;
  --gc-ink: #202629;
  --gc-rule: #dde3d7;
  --gc-muted: #66706b;
  --gc-muted-2: #8b938d;
  --gc-sage-text: #314f37;
  --gc-sage-bg: #eaf1e9;
  --gc-sage-border: #c9d8c7;
  --gc-mineral-text: #25496d;
  --gc-mineral-bg: #e7eef5;
  --gc-mineral-border: #c6d6e2;
  --gc-brass-bg: #f4efde;
  --gc-brass-border: #c8a76a;
  --gc-warn-bg: #fff5f5;
  --gc-warn-border: #ffa8a8;
  --gc-warn-text: #c92a2a;
  --gc-grid: rgba(214, 222, 211, 0.2);
}

body,
.gradio-container {
  background-color: var(--gc-paper) !important;
  background-image:
    linear-gradient(var(--gc-grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--gc-grid) 1px, transparent 1px) !important;
  background-size: 40px 40px !important;
  color: var(--gc-ink) !important;
}

.gradio-container {
  max-width: 1280px !important;
  margin: 0 auto !important;
  padding: 28px 24px 44px !important;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial,
    sans-serif !important;
}

.gc-app-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 20px;
  align-items: end;
  margin-bottom: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--gc-rule);
}

.gc-brand {
  display: flex;
  gap: 13px;
  align-items: center;
  min-width: 0;
}

.gc-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  border-radius: 999px;
  border: 1px solid var(--gc-rule);
  background: #fff;
  color: var(--gc-mineral-text);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-weight: 800;
  font-size: 22px;
  box-shadow: 0 2px 8px rgba(36, 43, 39, 0.05);
}

.gc-title {
  margin: 0;
  color: var(--gc-ink);
  font-family: Georgia, Cambria, "Times New Roman", Times, serif;
  font-size: clamp(28px, 4vw, 44px);
  line-height: 1.02;
  letter-spacing: 0;
}

.gc-kicker,
.gc-eyebrow {
  margin: 0;
  color: var(--gc-muted);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.gc-subtitle {
  margin: 6px 0 0;
  color: var(--gc-muted);
  font-size: 14px;
  line-height: 1.45;
}

.gc-status-rail {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  max-width: 460px;
}

.gc-chip {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 7px 12px;
  border: 1px solid var(--gc-rule);
  border-radius: 999px;
  background: #fff;
  color: var(--gc-ink);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.gc-chip.sage {
  background: var(--gc-sage-bg);
  color: var(--gc-sage-text);
  border-color: var(--gc-sage-border);
}

.gc-chip.mineral {
  background: var(--gc-mineral-bg);
  color: var(--gc-mineral-text);
  border-color: var(--gc-mineral-border);
}

.gc-deploy-note {
  margin-bottom: 16px;
  padding: 13px 15px;
  border: 1px solid var(--gc-warn-border);
  border-radius: 8px;
  background: var(--gc-warn-bg);
  color: var(--gc-warn-text);
  box-shadow: 0 8px 24px rgba(36, 43, 39, 0.04);
}

.gc-fallback {
  margin-bottom: 16px;
  border: 1px solid var(--gc-rule) !important;
  border-radius: 8px !important;
  background: #fff !important;
  box-shadow: 0 8px 24px rgba(36, 43, 39, 0.04);
}

.gc-tabs {
  border: 0 !important;
}

.gc-workbench {
  gap: 16px !important;
  align-items: stretch !important;
}

.gc-panel {
  min-width: 0;
  padding: 16px;
  border: 1px solid var(--gc-rule);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 18px 48px rgba(36, 43, 39, 0.07), 0 2px 8px rgba(36, 43, 39, 0.03);
}

.gc-panel-soft {
  min-width: 0;
  padding: 16px;
  border: 1px solid var(--gc-rule);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 8px 24px rgba(36, 43, 39, 0.04);
}

.gc-panel-title {
  margin: 0 0 4px;
  color: var(--gc-ink);
  font-family: Georgia, Cambria, "Times New Roman", Times, serif;
  font-size: 22px;
  font-weight: 700;
  line-height: 1.15;
}

.gc-panel-copy {
  margin: 0 0 12px;
  color: var(--gc-muted);
  font-size: 12px;
  line-height: 1.45;
}

.gc-mode-card {
  padding: 13px;
  border: 1px solid var(--gc-mineral-border);
  border-radius: 8px;
  background: var(--gc-mineral-bg);
}

.gc-mode-card strong {
  display: block;
  margin-bottom: 3px;
  color: var(--gc-mineral-text);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.gc-mode-card span {
  color: var(--gc-muted);
  font-size: 12px;
}

.gc-preset-row {
  gap: 8px !important;
}

.gc-preset-button button,
.gc-run-button button {
  min-height: 40px !important;
  border-radius: 999px !important;
  font-weight: 750 !important;
  transition:
    transform 0.15s ease,
    border-color 0.15s ease,
    background 0.15s ease !important;
}

.gc-preset-button button {
  border: 1px solid var(--gc-mineral-border) !important;
  background: #fff !important;
  color: var(--gc-mineral-text) !important;
}

.gc-preset-button button:hover,
.gc-run-button button:hover {
  transform: translateY(-1px);
}

.gc-run-button button {
  border: 1px solid var(--gc-ink) !important;
  background: var(--gc-ink) !important;
  color: #fff !important;
  box-shadow: 0 2px 6px rgba(15, 20, 25, 0.08) !important;
}

.gc-input textarea,
.gc-input input,
.gc-input select {
  border-color: #cbd6c8 !important;
  border-radius: 8px !important;
  background: #fff !important;
  color: var(--gc-ink) !important;
}

.gc-output,
.gc-trace,
.gc-json {
  border: 1px solid var(--gc-rule);
  border-radius: 8px;
  background: #fff;
}

.gc-output {
  min-height: 220px;
  padding: 12px;
}

.gc-trace {
  padding: 12px;
  background: var(--gc-brass-bg);
  border-left: 3px solid var(--gc-brass-border);
}

.gc-trace table {
  width: 100%;
  overflow-wrap: anywhere;
  font-size: 12px;
}

.gc-trace th {
  color: var(--gc-muted);
  font-size: 10px;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.gc-trace td,
.gc-trace th {
  padding: 6px 8px;
  border-bottom: 1px solid rgba(200, 167, 106, 0.35);
  text-align: left;
  vertical-align: top;
}

.gc-json {
  background: #fff;
}

.gc-json textarea,
.gc-json pre,
.gc-json code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace !important;
  font-size: 11px !important;
}

.gc-output h3 {
  margin-top: 0;
  font-family: Georgia, Cambria, "Times New Roman", Times, serif;
}

.gc-output p,
.gc-output li {
  font-size: 14px;
  line-height: 1.6;
}

.gc-accordion {
  border: 1px solid var(--gc-rule) !important;
  border-radius: 8px !important;
  background: #fff !important;
}

.gc-checkbox label {
  color: var(--gc-muted) !important;
  font-size: 12px !important;
}

footer {
  display: none !important;
}

@media (max-width: 860px) {
  .gradio-container {
    padding: 18px 12px 32px !important;
  }

  .gc-app-header {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .gc-status-rail {
    justify-content: flex-start;
  }
}
"""

APP_HEADER_HTML = """
<section class="gc-app-header">
  <div class="gc-brand">
    <div class="gc-mark">C</div>
    <div>
      <p class="gc-kicker">Adaptive grounded tutor</p>
      <h1 class="gc-title">GenAcademy Coach</h1>
      <p class="gc-subtitle">
        Teach, check, re-explain, quiz, or refuse from cited course evidence.
      </p>
    </div>
  </div>
  <div class="gc-status-rail" aria-label="Demo status">
    <span class="gc-chip sage">Teach loop</span>
    <span class="gc-chip mineral">Quiz pull-in</span>
    <span class="gc-chip">Redacted traces</span>
  </div>
</section>
"""


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


def fill_teach_grounded_preset() -> tuple[str, str, str, str]:
    return TEACH_GROUNDED_PRESET


def fill_teach_refusal_preset() -> tuple[str, str, str, str]:
    return TEACH_REFUSAL_PRESET


def fill_quiz_grounded_preset() -> tuple[str, int, str, bool]:
    return QUIZ_GROUNDED_PRESET


def _format_score(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{float(value):.3f}"
    return str(value)


def _format_count_or_values(value: Any) -> str:
    if isinstance(value, list):
        if not value:
            return "0"
        return f"{len(value)}: " + ", ".join(str(item) for item in value)
    return str(value)


def _format_trace_summary(
    metadata: dict[str, Any],
    *,
    mode: str,
) -> str:
    status = metadata.get("status")
    if status != "ok":
        return f"**Status:** `{status or 'unknown'}`"

    rows = metadata.get("trace")
    if not isinstance(rows, list) or not rows:
        return "**Trace summary:** no trace rows available."

    if mode == "teach":
        header = [
            "turn",
            "next_action",
            "strategy",
            "evidence_band",
            "evidence_score",
            "faithfulness_ok",
            "retrieved_citation_ids",
            "tool_calls",
        ]
    else:
        header = [
            "evidence_band",
            "evidence_score",
            "question_ids",
            "selected_option_ids",
            "correctness",
            "refusal_reason",
            "actions",
        ]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in rows:
        if not isinstance(row, dict):
            continue
        cells = []
        for field in header:
            value = row.get(field, "")
            if field == "evidence_score":
                cells.append(_format_score(value))
            elif isinstance(value, list):
                cells.append(_format_count_or_values(value))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


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
    show_questions: bool = False,
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
        if show_questions:
            for index, question in enumerate(result.questions, start=1):
                sections.extend([f"### Question {index}", question.prompt])
                sections.extend(
                    f"{option.option_id}. {option.text}" for option in question.options
                )
                sections.append("")
        else:
            sections.append(
                f"Generated {len(result.questions)} grounded quiz question(s). "
                "Question text is hidden by default for recording privacy; enable "
                "local-only question display only when it is safe to show generated quiz text."
            )

        if selected is not None:
            sections.append(f"**Score:** {result.score}/{len(result.questions)}")
            for grade in result.grades:
                status = "correct" if grade.correct else "incorrect"
                if show_questions:
                    sections.append(
                        f"- {grade.question_id}: {status} "
                        f"(selected {grade.selected_option_id}, answer {grade.correct_option_id})"
                    )
                else:
                    sections.append(
                        f"- {grade.question_id}: {status} "
                        f"(selected {grade.selected_option_id})"
                    )
        return "\n".join(sections).strip(), metadata
    except UserInputError as exc:
        return _input_error_payload(str(exc))
    except Exception as exc:
        return _error_payload(exc)


def run_teach_ui(
    topic: str,
    style: str,
    track_lens: str,
    learner_answer: str,
) -> tuple[str, str, dict[str, Any]]:
    output, metadata = run_teach_session(topic, style, track_lens, learner_answer)
    return output, _format_trace_summary(metadata, mode="teach"), metadata


def run_quiz_ui(
    topic: str,
    question_count: int | float,
    answers: str,
    show_questions: bool,
) -> tuple[str, str, dict[str, Any]]:
    output, metadata = run_quiz_session(topic, question_count, answers, show_questions)
    return output, _format_trace_summary(metadata, mode="quiz"), metadata


def build_demo(status_message: str | None = None) -> gr.Blocks:
    with gr.Blocks(
        title="GenAcademy Coach",
        elem_classes=["gc-root"],
    ) as demo:
        gr.HTML(APP_HEADER_HTML)
        if status_message is not None:
            gr.Markdown(status_message, elem_classes=["gc-deploy-note"])
        with gr.Accordion("Evidence fallback", open=False, elem_classes=["gc-fallback"]):
            gr.Markdown(
                "If a live provider call is slow during recording, use the committed redacted "
                "evidence in `docs/teach-loop-status.md` and `docs/demo-and-deliverables.md`. "
                "The raw trace files remain local/gitignored; only safe metadata should be shown."
            )
        with gr.Tabs(elem_classes=["gc-tabs"]):
            with gr.Tab("Teach"):
                with gr.Row(elem_classes=["gc-workbench"]):
                    with gr.Column(scale=5, min_width=320, elem_classes=["gc-panel"]):
                        gr.HTML(
                            """
                            <p class="gc-eyebrow">Teach session</p>
                            <h2 class="gc-panel-title">Coach the learner</h2>
                            <p class="gc-panel-copy">
                              Pick a known demo path, run one turn, then show the runtime decision
                              trace.
                            </p>
                            <div class="gc-mode-card">
                              <strong>Safety posture</strong>
                              <span>Grounded answer or explicit refusal; no public tunnel.</span>
                            </div>
                            """
                        )
                        teach_topic = gr.Textbox(
                            label="Topic",
                            value="agent harness",
                            elem_classes=["gc-input"],
                        )
                        with gr.Row():
                            style = gr.Dropdown(
                                STYLE_CHOICES,
                                value="analogy",
                                label="Style",
                                elem_classes=["gc-input"],
                            )
                            track_lens = gr.Dropdown(
                                TRACK_LENS_CHOICES,
                                value="code_heavy",
                                label="Track lens",
                                elem_classes=["gc-input"],
                            )
                        learner_answer = gr.Textbox(
                            label="Learner answer",
                            lines=4,
                            elem_classes=["gc-input"],
                        )
                        with gr.Row(elem_classes=["gc-preset-row"]):
                            grounded_preset = gr.Button(
                                "Grounded demo preset",
                                elem_classes=["gc-preset-button"],
                            )
                            refusal_preset = gr.Button(
                                "Refusal demo preset",
                                elem_classes=["gc-preset-button"],
                            )
                        teach_button = gr.Button(
                            "Run teach session",
                            elem_classes=["gc-run-button"],
                        )
                    with gr.Column(scale=7, min_width=420, elem_classes=["gc-panel-soft"]):
                        gr.HTML(
                            """
                            <p class="gc-eyebrow">Learner surface</p>
                            <h2 class="gc-panel-title">Response and decision trace</h2>
                            """
                        )
                        teach_output = gr.Markdown(
                            label="Teach output",
                            elem_classes=["gc-output"],
                        )
                        teach_trace_summary = gr.Markdown(
                            label="Trace summary",
                            elem_classes=["gc-trace"],
                        )
                        with gr.Accordion(
                            "Redacted metadata",
                            open=False,
                            elem_classes=["gc-accordion"],
                        ):
                            teach_metadata = gr.JSON(
                                label="Redacted metadata",
                                elem_classes=["gc-json"],
                            )
                grounded_preset.click(
                    fn=fill_teach_grounded_preset,
                    inputs=[],
                    outputs=[teach_topic, style, track_lens, learner_answer],
                )
                refusal_preset.click(
                    fn=fill_teach_refusal_preset,
                    inputs=[],
                    outputs=[teach_topic, style, track_lens, learner_answer],
                )
                teach_button.click(
                    fn=run_teach_ui,
                    inputs=[teach_topic, style, track_lens, learner_answer],
                    outputs=[teach_output, teach_trace_summary, teach_metadata],
                )

            with gr.Tab("Quiz"):
                with gr.Row(elem_classes=["gc-workbench"]):
                    with gr.Column(scale=5, min_width=320, elem_classes=["gc-panel"]):
                        gr.HTML(
                            """
                            <p class="gc-eyebrow">Quiz mode</p>
                            <h2 class="gc-panel-title">Deterministic assessment</h2>
                            <p class="gc-panel-copy">
                              Generate cited MCQs, grade option IDs in Python, and keep question
                              text hidden for recording.
                            </p>
                            <div class="gc-mode-card">
                              <strong>Recording mode</strong>
                              <span>Score and trace first; raw quiz text stays local-only.</span>
                            </div>
                            """
                        )
                        quiz_topic = gr.Textbox(
                            label="Topic",
                            value="agent harness",
                            elem_classes=["gc-input"],
                        )
                        question_count = gr.Slider(
                            minimum=1,
                            maximum=3,
                            step=1,
                            value=3,
                            label="Questions",
                            elem_classes=["gc-input"],
                        )
                        answers = gr.Textbox(
                            label="Answers",
                            placeholder="A,B,C",
                            elem_classes=["gc-input"],
                        )
                        show_questions = gr.Checkbox(
                            label="Show generated quiz questions (local/private only)",
                            value=False,
                            elem_classes=["gc-checkbox"],
                        )
                        quiz_preset = gr.Button(
                            "Grounded quiz preset",
                            elem_classes=["gc-preset-button"],
                        )
                        quiz_button = gr.Button("Run quiz", elem_classes=["gc-run-button"])
                    with gr.Column(scale=7, min_width=420, elem_classes=["gc-panel-soft"]):
                        gr.HTML(
                            """
                            <p class="gc-eyebrow">Assessment surface</p>
                            <h2 class="gc-panel-title">Score and trace</h2>
                            """
                        )
                        quiz_output = gr.Markdown(
                            label="Quiz output",
                            elem_classes=["gc-output"],
                        )
                        quiz_trace_summary = gr.Markdown(
                            label="Trace summary",
                            elem_classes=["gc-trace"],
                        )
                        with gr.Accordion(
                            "Redacted metadata",
                            open=False,
                            elem_classes=["gc-accordion"],
                        ):
                            quiz_metadata = gr.JSON(
                                label="Redacted metadata",
                                elem_classes=["gc-json"],
                            )
                quiz_preset.click(
                    fn=fill_quiz_grounded_preset,
                    inputs=[],
                    outputs=[quiz_topic, question_count, answers, show_questions],
                )
                quiz_button.click(
                    fn=run_quiz_ui,
                    inputs=[quiz_topic, question_count, answers, show_questions],
                    outputs=[quiz_output, quiz_trace_summary, quiz_metadata],
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
        share=False,
        css=GENACADEMY_COACH_CSS,
    )
