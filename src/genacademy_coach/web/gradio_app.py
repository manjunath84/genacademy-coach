from __future__ import annotations

import json
import logging
import os
import re
import uuid
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any

from genacademy_coach.foundation import Foundation, build_course_vectorstore
from genacademy_coach.privacy import user_id_hash
from genacademy_coach.quiz_session import QuizSession
from genacademy_coach.quiz_types import QuizQuestion, QuizSessionResult, grade_quiz
from genacademy_coach.settings import CoachSettings
from genacademy_coach.skillgap_session import SkillGapSession, validate_skillgap_session_id
from genacademy_coach.teach_session import CoachSession
from genacademy_coach.teach_types import LearnerProfile, RetrievedSpan
from genacademy_coach.web.auth import (
    DEFAULT_AUTH_MESSAGE,
    CoachAuth,
    auth_enabled_from_env,
)

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr

logger = logging.getLogger(__name__)

STYLE_CHOICES = ["concise", "analogy", "step_by_step"]
TRACK_LENS_CHOICES = ["low_code_no_code", "code_heavy", "bridge"]
VALID_OPTION_IDS = frozenset({"A", "B", "C", "D"})
MARKDOWN_LITERAL_PATTERN = re.compile(r"([\\`*_{}\[\]()#+\-!|>])")
DECISION_OBSERVATION_LIMIT = 240
PYTHON_GATE_OBSERVATION_PREFIXES = (
    "grounded fallback",
    "turn budget reached",
    "no citeable course corpus found",
    "agent failed",
    "agent chose",
    "agent displayed",
    "grounded check",
    "agent response was not faithful",
    "agent response had no retrieved citation_ids",
)
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
QUIZ_GROUNDED_PRESET = ("agent harness", 1, "A", True)
SKILLGAP_SOURCE_PRESET = "\n".join(
    (
        "demo-grounded-main-final-20260616",
        "demo-quiz-agent-harness-reviewfix2-20260616",
    )
)
DEMO_PRESET_TOPICS = frozenset(
    {
        TEACH_GROUNDED_PRESET[0],
        TEACH_REFUSAL_PRESET[0],
        QUIZ_GROUNDED_PRESET[0],
    }
)
EMPTY_CORPUS_STATUS_MESSAGE = (
    "**Deployment shell:** no approved corpus/index is loaded in this Space. "
    "Teach and quiz requests will safely refuse until an approved vector index "
    "is available for the active backend; see the recorded demo for grounded behavior."
)
CORPUS_STATUS_UNAVAILABLE_MESSAGE = (
    "**Deployment status:** corpus status could not be checked. The app fails closed "
    "when course evidence is unavailable; check the private Space logs for the error ID."
)
DEFAULT_LOCAL_SERVER_NAME = "127.0.0.1"

SAFE_TEACH_TRACE_FIELDS = (
    "session_id",
    "turn",
    "topic_hash",
    "learner_input_hash",
    "next_action",
    "strategy",
    "evidence_score",
    "evidence_band",
    "faithfulness_ok",
    "retrieved_citation_ids",
    "retrieved_citation_labels",
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
SAFE_SKILLGAP_TRACE_FIELDS = (
    "session_id",
    "topic_hash",
    "gap_id",
    "source_session_ids",
    "evidence_score",
    "evidence_band",
    "citation_ids",
    "quiz_correct",
    "quiz_total",
    "struggle_count",
    "refusal_count",
    "next_action",
    "escalated",
    "reason_code",
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

body {
  margin: 0 !important;
}

.gradio-container {
  width: 100% !important;
  max-width: none !important;
  min-height: 100vh !important;
  margin: 0 !important;
  padding: 24px clamp(10px, 1.1vw, 18px) 40px !important;
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
  cursor: default;
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
  overflow: hidden !important;
  box-shadow: 0 8px 24px rgba(36, 43, 39, 0.04);
}

.gc-tabs {
  border: 0 !important;
}

.gc-tabs button[role="tab"],
.gc-tabs .tab-nav button,
.gc-tabs [role="tab"] {
  min-height: 44px !important;
  border-color: transparent !important;
  color: var(--gc-muted) !important;
  font-weight: 750 !important;
}

.gc-tabs button[role="tab"][aria-selected="true"],
.gc-tabs .selected,
.gc-tabs [aria-selected="true"] {
  border-color: var(--gc-mineral-border) !important;
  background: var(--gc-mineral-bg) !important;
  color: var(--gc-mineral-text) !important;
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

.gc-action-row {
  gap: 8px !important;
  align-items: stretch !important;
}

.gc-action-row > * {
  min-width: 0 !important;
}

.gc-auth-row {
  gap: 16px !important;
  align-items: flex-start !important;
  margin-bottom: 16px;
}

.gc-auth-status {
  min-width: 0 !important;
}

.gc-auth-status p {
  margin: 0 0 8px;
  line-height: 1.45;
}

.gc-signout-button {
  max-width: 240px;
  margin-left: auto;
}

button.gc-preset-button,
.gc-preset-button button,
button.gc-run-button,
.gc-run-button button,
button.gc-score-button,
.gc-score-button button {
  min-height: 44px !important;
  border-radius: 8px !important;
  font-weight: 750 !important;
  transition:
    transform 0.15s ease,
    border-color 0.15s ease,
    background 0.15s ease !important;
}

button.gc-preset-button,
.gc-preset-button button {
  border: 1px solid var(--gc-mineral-border) !important;
  background: #fff !important;
  color: var(--gc-mineral-text) !important;
}

button.gc-preset-button:hover,
.gc-preset-button button:hover,
button.gc-run-button:hover,
.gc-run-button button:hover,
button.gc-score-button:hover,
.gc-score-button button:hover {
  transform: translateY(-1px);
}

button.gc-run-button,
.gc-run-button button {
  border: 1px solid var(--gc-ink) !important;
  background: var(--gc-ink) !important;
  color: #fff !important;
  box-shadow: 0 2px 6px rgba(15, 20, 25, 0.08) !important;
}

button.gc-score-button,
.gc-score-button button {
  border-color: var(--gc-sage-border) !important;
  background: var(--gc-sage-bg) !important;
  color: var(--gc-sage-text) !important;
}

button.gc-score-button:not([disabled]),
.gc-score-button button:not([disabled]) {
  border-color: #31533d !important;
  background: #31533d !important;
  color: #fff !important;
  box-shadow: 0 2px 6px rgba(49, 83, 61, 0.14) !important;
}

button.gc-score-button[disabled],
.gc-score-button button[disabled] {
  box-shadow: none !important;
  opacity: 0.66 !important;
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

.gc-output em,
.gc-trace em {
  color: var(--gc-muted);
}

.gc-trace {
  overflow-x: auto;
  padding: 12px;
  background: var(--gc-brass-bg);
  border-left: 3px solid var(--gc-brass-border);
}

.gc-trace-stack {
  display: grid;
  gap: 10px;
}

.gc-trace-card {
  padding: 12px;
  border: 1px solid rgba(200, 167, 106, 0.35);
  border-radius: 8px;
  background: rgba(255, 252, 241, 0.82);
}

.gc-trace-head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.gc-trace-title {
  color: var(--gc-ink);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.gc-trace-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.gc-trace-pill {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 4px 8px;
  border: 1px solid var(--gc-rule);
  border-radius: 999px;
  background: #fff;
  color: var(--gc-ink);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
}

.gc-trace-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.gc-trace-field {
  min-width: 0;
}

.gc-trace-field-wide {
  grid-column: 1 / -1;
}

.gc-trace-label {
  display: block;
  margin-bottom: 3px;
  color: var(--gc-muted);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.gc-trace-value {
  color: var(--gc-ink);
  font-size: 12px;
  line-height: 1.35;
}

.gc-trace-value code {
  white-space: normal;
  overflow-wrap: anywhere;
}

@media (max-width: 680px) {
  .gc-trace-grid {
    grid-template-columns: 1fr;
  }
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

.gc-output h1,
.gc-output h2,
.gc-output h3,
.gc-output h4 {
  margin: 0 0 8px;
  font-family: Georgia, Cambria, "Times New Roman", Times, serif;
  line-height: 1.25;
}

.gc-output h1 {
  font-size: 20px;
}

.gc-output h2 {
  font-size: 18px;
}

.gc-output h3,
.gc-output h4 {
  font-size: 16px;
}

.gc-output p,
.gc-output li {
  font-size: 14px;
  line-height: 1.6;
}

.gc-output ul {
  margin-top: 8px;
  padding-left: 20px;
}

.gc-accordion {
  border: 1px solid var(--gc-rule) !important;
  border-radius: 8px !important;
  background: #fff !important;
  overflow: hidden !important;
}

.gc-accordion button,
.gc-fallback button {
  min-height: 44px !important;
}

.gc-answer-choice {
  border: 1px solid var(--gc-rule) !important;
  border-radius: 8px !important;
  background: #fff !important;
  padding: 8px 10px !important;
}

.gc-answer-choice label {
  color: var(--gc-muted) !important;
  font-size: 12px !important;
  font-weight: 600 !important;
}

.gc-answer-choice .wrap {
  display: grid !important;
  grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  gap: 8px !important;
}

.gc-answer-choice .wrap label {
  justify-content: center !important;
  min-width: 0 !important;
  min-height: 36px !important;
}

.gc-checkbox {
  min-height: 44px;
}

.gc-checkbox label {
  display: flex !important;
  align-items: center !important;
  min-height: 44px !important;
  color: var(--gc-muted) !important;
  font-size: 12px !important;
}

.gc-checkbox input {
  min-width: 20px !important;
  min-height: 20px !important;
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

  .gc-auth-row {
    display: grid !important;
    grid-template-columns: 1fr;
  }

  .gc-signout-button {
    width: 100%;
    max-width: none;
    margin-left: 0;
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
    <span class="gc-chip">Skill-Gap</span>
    <span class="gc-chip">Demo traces</span>
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


def _parse_source_session_ids(raw: str) -> list[str]:
    tokens = [
        item.strip()
        for line in raw.splitlines()
        for item in line.split(",")
        if item.strip()
    ]
    if not tokens:
        raise UserInputError("at least one source session id is required")
    try:
        return [validate_skillgap_session_id(token) for token in tokens]
    except ValueError as exc:
        raise UserInputError(str(exc)) from exc


def _validate_answer_count(selected: list[str] | None, count: int) -> None:
    if selected is not None and len(selected) != count:
        raise UserInputError(f"expected {count} answers, received {len(selected)}")


def fill_teach_grounded_preset() -> tuple[str, str, str, str]:
    return TEACH_GROUNDED_PRESET


def fill_teach_refusal_preset() -> tuple[str, str, str, str]:
    return TEACH_REFUSAL_PRESET


def fill_quiz_grounded_preset() -> tuple[str, int, str, bool]:
    return QUIZ_GROUNDED_PRESET


def fill_skillgap_preset() -> str:
    return SKILLGAP_SOURCE_PRESET


def _format_score(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{float(value):.3f}"
    return str(value)


def _short_value(value: Any, *, limit: int = 34) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}..."


def _friendly_review_target(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "the cited course material"
    if text.lower().startswith("review "):
        text = text[7:].strip()
    if text.endswith("."):
        text = text[:-1]
    if " at " in text:
        title_part, citation_id = text.rsplit(" at ", 1)
    else:
        title_part, citation_id = text, ""

    title = title_part.strip()
    metadata: list[str] = []
    if title.endswith(")") and " (" in title:
        title, metadata_text = title.rsplit(" (", 1)
        metadata = [item.strip() for item in metadata_text[:-1].split(",") if item.strip()]

    source_type = ""
    source_name = citation_id
    location = ""
    if metadata:
        source_type = metadata[0]
        location = " · ".join(metadata[1:])
    if citation_id:
        base = citation_id.split("::", 1)[0]
        parts = base.split("/", 1)
        if len(parts) == 2:
            source_type = source_type or parts[0]
            source_name = parts[1]
        else:
            source_name = base
        lowered = source_name.lower()
        for token in ("slide", "slides", "page", "section"):
            marker = f"{token}-"
            if not location and marker in lowered:
                location = source_name[lowered.rfind(marker) :].replace("-", " ")
                source_name = source_name[: lowered.rfind(marker)].rstrip("-_ ")
                break

    if not source_name and title:
        source_name = title
    readable_name = source_name.replace("-", " ").replace("_", " ").strip()
    readable_type = (source_type or "course material").replace("_", " ").strip()
    if readable_type == "slide":
        readable_type = "slides"
    elif readable_type == "handout":
        readable_type = "handout"
    elif readable_type == "note":
        readable_type = "notes"
    elif readable_type == "transcript":
        readable_type = "transcript"

    label = f"the cited {readable_type}"
    if title:
        chunks = [f"{label}: {title.strip()}"]
    else:
        chunks = [label]
    if not title and readable_name:
        chunks.append(f"from {readable_name}")
    if location:
        chunks.append(f"({location})")
    return " ".join(chunks)


def _format_chip(value: Any) -> str:
    return f'<span class="gc-trace-pill">{escape(str(value))}</span>'


def _format_list_summary(
    values: Any,
    *,
    unit: str,
    sample_limit: int = 2,
    show_samples: bool = True,
) -> str:
    if not isinstance(values, list):
        return escape(str(values))
    if not values:
        return f"0 {unit}"

    count = len(values)
    plural = unit if count == 1 else f"{unit}s"
    if not show_samples:
        return f"{count} {plural}"

    samples = ", ".join(escape(_short_value(item)) for item in values[:sample_limit])
    more = count - sample_limit
    suffix = f" + {more} more" if more > 0 else ""
    return f"{count} {plural}<br><code>{samples}{escape(suffix)}</code>"


def _format_learner_message_citations(message: str, spans: list[RetrievedSpan]) -> str:
    rendered = message
    for span in spans:
        rendered = rendered.replace(f"[{span.citation_id}]", f"[{span.source_label}]")
        rendered = rendered.replace(span.citation_id, span.source_label)
    return _markdown_literal(rendered)


def _markdown_literal(value: str) -> str:
    html_safe = escape(value, quote=False)
    return MARKDOWN_LITERAL_PATTERN.sub(r"\\\1", html_safe)


def _safe_decision_observation(value: Any) -> str:
    text = " ".join(str(value or "not captured").split())
    return _short_value(text, limit=DECISION_OBSERVATION_LIMIT)


def _decision_source_from_observation(value: Any) -> str:
    text = str(value or "").strip().lower()
    if any(text.startswith(prefix) for prefix in PYTHON_GATE_OBSERVATION_PREFIXES):
        return "python safety gate"
    return "agent"


def _current_spans(session: Any) -> list[RetrievedSpan]:
    runtime = getattr(session, "runtime", None)
    spans = getattr(runtime, "last_spans", None)
    return spans if isinstance(spans, list) else []


def _format_bool(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return escape(str(value))


def _trace_field(label: str, value: str) -> str:
    extra_class = " gc-trace-field-wide" if label == "Decision basis" else ""
    return (
        f'<div class="gc-trace-field{extra_class}">'
        f'<span class="gc-trace-label">{escape(label)}</span>'
        f'<div class="gc-trace-value">{value}</div>'
        "</div>"
    )


def _trace_card(title: str, pills: list[str], fields: list[tuple[str, str]]) -> str:
    field_markup = "".join(_trace_field(label, value) for label, value in fields)
    return (
        '<section class="gc-trace-card">'
        '<div class="gc-trace-head">'
        f'<span class="gc-trace-title">{escape(title)}</span>'
        f'<div class="gc-trace-pills">{"".join(pills)}</div>'
        "</div>"
        f'<div class="gc-trace-grid">{field_markup}</div>'
        "</section>"
    )


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

    cards: list[str] = []
    memory = metadata.get("memory")
    if mode == "teach" and isinstance(memory, dict):
        cards.append(
            _trace_card(
                "Memory",
                [
                    _format_chip(str(memory.get("provider", "unknown"))),
                    _format_chip("enabled" if memory.get("enabled") else "off"),
                ],
                [
                    ("User scoped", _format_bool(memory.get("user_scoped", False))),
                    ("Safe state written", _format_bool(memory.get("safe_state_written", False))),
                ],
            )
        )
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        if mode == "teach":
            decision_observation = _safe_decision_observation(
                row.get("decision_observation", "not captured")
            )
            decision_source = row.get("decision_source") or _decision_source_from_observation(
                decision_observation
            )
            title = f"Turn {row.get('turn', '?')}"
            pills = [
                _format_chip(f"action {row.get('next_action', 'unknown')}"),
                _format_chip(f"band {row.get('evidence_band', 'unknown')}"),
                _format_chip(f"score {_format_score(row.get('evidence_score', '?'))}"),
                _format_chip(f"source {decision_source}"),
            ]
            fields = [
                (
                    "Decision basis",
                    _markdown_literal(decision_observation),
                ),
                ("Topic", f"<code>{escape(str(row.get('topic_hash', 'unknown')))}</code>"),
                (
                    "Input",
                    f"<code>{escape(str(row.get('learner_input_hash', 'unknown')))}</code>",
                ),
                ("Strategy", f"<code>{escape(str(row.get('strategy', 'unknown')))}</code>"),
                ("Faithful", _format_bool(row.get("faithfulness_ok", "unknown"))),
                (
                    "Citations",
                    _format_list_summary(
                        row.get("retrieved_citation_labels")
                        or row.get("retrieved_citation_ids", []),
                        unit="cited span",
                        show_samples=bool(row.get("retrieved_citation_labels")),
                    ),
                ),
                ("Tools", _format_list_summary(row.get("tool_calls", []), unit="tool call")),
            ]
        elif mode == "quiz":
            title = "Quiz run"
            pills = [
                _format_chip(f"band {row.get('evidence_band', 'unknown')}"),
                _format_chip(f"score {_format_score(row.get('evidence_score', '?'))}"),
            ]
            fields = [
                ("Questions", _format_list_summary(row.get("question_ids", []), unit="question")),
                (
                    "Answers",
                    _format_list_summary(row.get("selected_option_ids", []), unit="answer"),
                ),
                ("Correctness", _format_list_summary(row.get("correctness", []), unit="grade")),
                ("Actions", _format_list_summary(row.get("actions", []), unit="action")),
            ]
            refusal_reason = row.get("refusal_reason")
            if refusal_reason:
                fields.append(("Refusal", f"<code>{escape(str(refusal_reason))}</code>"))
        else:
            title = f"Gap {index}"
            pills = [
                _format_chip(f"action {row.get('next_action', 'unknown')}"),
                _format_chip(f"band {row.get('evidence_band', 'unknown')}"),
                _format_chip(f"score {_format_score(row.get('evidence_score', '?'))}"),
            ]
            fields = [
                (
                    "Source sessions",
                    _format_list_summary(
                        row.get("source_session_ids", []),
                        unit="session",
                        show_samples=False,
                    ),
                ),
                (
                    "Citations",
                    _format_list_summary(
                        row.get("citation_ids", []),
                        unit="cited span",
                        show_samples=False,
                    ),
                ),
                (
                    "Quiz",
                    f"{escape(str(row.get('quiz_correct', 0)))}/"
                    f"{escape(str(row.get('quiz_total', 0)))}",
                ),
                ("Struggles", escape(str(row.get("struggle_count", 0)))),
                ("Refusals", escape(str(row.get("refusal_count", 0)))),
                ("Escalated", _format_bool(row.get("escalated", False))),
            ]
            reason_code = row.get("reason_code")
            if reason_code:
                fields.append(("Reason", f"<code>{escape(str(reason_code))}</code>"))
        cards.append(_trace_card(title, pills, fields))
    if not cards:
        return "**Trace summary:** no displayable trace rows available."
    return '<div class="gc-trace-stack">' + "".join(cards) + "</div>"


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


@lru_cache(maxsize=1)
def _runtime() -> tuple[CoachSettings, Foundation]:
    settings = CoachSettings.from_env()
    return settings, Foundation.build(settings)


@lru_cache(maxsize=1)
def _auth_backend() -> CoachAuth:
    return CoachAuth(CoachSettings.from_env())


def _auth_enabled() -> bool:
    return auth_enabled_from_env(os.environ.get("GENACADEMY_COACH_AUTH_ENABLED"))


def _launch_auth() -> Any | None:
    return _auth_backend().authenticate if _auth_enabled() else None


def _request_username(request: gr.Request | None) -> str | None:
    username = getattr(request, "username", None) if request is not None else None
    return str(username) if username else None


def _memory_user_hash(settings: CoachSettings, user_email: str | None) -> str | None:
    if user_email is None or settings.memory_user_salt is None:
        return None
    return user_id_hash(user_email, salt=settings.memory_user_salt)


def _memory_status_message(
    settings: CoachSettings,
    user_email: str | None,
    *,
    auth_enabled: bool,
) -> str:
    if not settings.mem0_api_key or not settings.memory_user_salt:
        return "**Memory:** off by default."
    if user_email is None:
        if not auth_enabled:
            return "**Memory:** Mem0 configured; auth is disabled for local development."
        return "**Memory:** Mem0 configured; sign in to scope memory to a salted learner ID."
    return "**Memory:** Mem0 enabled for salted learner-state only."


def auth_status_ui(request: gr.Request | None = None) -> str:
    settings = CoachSettings.from_env()
    username = _request_username(request)
    auth_enabled = _auth_enabled()
    memory_status = _memory_status_message(settings, username, auth_enabled=auth_enabled)
    if not auth_enabled:
        return "**Access:** auth disabled for local development.\n\n" + memory_status
    user = _auth_backend().get_user(username)
    if user is None:
        return "**Access:** signed in cohort account.\n\n" + memory_status
    return f"**Access:** `{user.role}` cohort account.\n\n{memory_status}"


def admin_tab_visibility_ui(request: gr.Request | None = None) -> dict[str, Any]:
    return gr.update(visible=_auth_backend().is_admin(_request_username(request)))


def _format_admin_users(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "No users are visible for this account."
    lines = ["| Email | Role | Created |", "|---|---|---|"]
    for row in rows:
        lines.append(
            f"| `{escape(row['email'])}` | `{escape(row['role'])}` | "
            f"{escape(row['created_at'])} |"
        )
    return "\n".join(lines)


def list_admin_users_ui(request: gr.Request | None = None) -> str:
    rows = _auth_backend().list_users(actor_email=_request_username(request))
    if not rows:
        return "Admin access required."
    return _format_admin_users(rows)


def create_auth_user_ui(
    email: str,
    role: str,
    password: str,
    request: gr.Request | None = None,
) -> tuple[str, str]:
    ok, message = _auth_backend().create_user(
        actor_email=_request_username(request),
        email=email,
        role=role,
        password=password,
    )
    rows = _auth_backend().list_users(actor_email=_request_username(request)) if ok else []
    return message, _format_admin_users(rows) if rows else "Admin access required."


def _corpus_chunk_count(settings: CoachSettings) -> int:
    store = build_course_vectorstore(settings)
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


def _server_name() -> str:
    return os.environ.get("GENACADEMY_COACH_SERVER_NAME", DEFAULT_LOCAL_SERVER_NAME)


def _input_error_payload(message: str) -> tuple[str, dict[str, Any]]:
    return message, {"status": "invalid_input"}


def _error_payload(exc: Exception) -> tuple[str, dict[str, Any]]:
    error_id = uuid.uuid4().hex[:8]
    logger.exception("space handler failed error_id=%s", error_id)
    return (
        "This run failed closed before showing generated or corpus-derived text. "
        "For a local recording, restart the app, hard-refresh the browser, and confirm "
        f"the provider key plus approved vector index are loaded. Error ID: {error_id}.",
        {"status": "error", "error_id": error_id},
    )


def run_teach_session(
    topic: str,
    style: str,
    track_lens: str,
    learner_answer: str,
    user_email: str | None = None,
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
            user_id_hash=_memory_user_hash(settings, user_email),
        )
        first = session.start()
        sections = [
            "### Turn 1",
            _format_learner_message_citations(
                first.response.learner_message,
                _current_spans(session),
            ),
        ]
        if first.response.check_question:
            sections.extend(["", f"**Check:** {_markdown_literal(first.response.check_question)}"])

        answer = learner_answer.strip()
        result = first
        if answer:
            result = session.respond(answer)
            sections.extend(
                [
                    "",
                    "### Turn 2",
                    _format_learner_message_citations(
                        result.response.learner_message,
                        _current_spans(session),
                    ),
                ]
            )
            if result.response.check_question:
                sections.extend(
                    ["", f"**Check:** {_markdown_literal(result.response.check_question)}"]
                )
        session.finish()
        trace_rows = safe_trace_rows(result.trace_path, SAFE_TEACH_TRACE_FIELDS)
        decision_observations = {1: getattr(first.response, "observation", None)}
        if answer:
            decision_observations[2] = getattr(result.response, "observation", None)
        for row in trace_rows:
            if not isinstance(row, dict):
                continue
            observation = decision_observations.get(row.get("turn"))
            if observation:
                # Intentionally demo-only and outside the persisted trace schema: this lets
                # the UI explain the live decision without writing raw observations to disk.
                row["decision_observation"] = _safe_decision_observation(observation)
                row["decision_source"] = _decision_source_from_observation(observation)

        metadata = {
            "status": "ok",
            "session_id": result.session_id,
            "trace_file": Path(result.trace_path).name,
            "memory": {
                "provider": getattr(session.memory, "provider", "unknown"),
                "enabled": getattr(session.memory, "provider", "unknown") != "null",
                "user_scoped": session.user_id_hash is not None,
                "safe_state_written": session._memory_written,
            },
            "profile": {
                "style": result.profile.style,
                "track_lens": result.profile.track_lens,
                "turn_count": result.profile.turn_count,
            },
            "trace": trace_rows,
        }
        return "\n".join(sections), metadata
    except UserInputError as exc:
        return _input_error_payload(str(exc))
    except Exception as exc:
        return _error_payload(exc)


def _run_quiz_result(
    topic: str,
    question_count: int | float,
    answers: str,
) -> tuple[str, int, list[str] | None, QuizSessionResult, dict[str, Any]]:
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
    return clean_topic, count, selected, result, metadata


def _format_quiz_result(result: QuizSessionResult, *, show_questions: bool) -> str:
    if result.refusal_reason is not None:
        return "I could not generate a grounded quiz for this topic."

    question_sections: list[str] = []
    if show_questions:
        for index, question in enumerate(result.questions, start=1):
            question_sections.extend(
                [f"### Question {index}", "", _markdown_literal(question.prompt), ""]
            )
            question_sections.extend(
                f"- **{option.option_id}.** {_markdown_literal(option.text)}"
                for option in question.options
            )
            question_sections.append("")
    else:
        question_sections.append(
            f"Generated {len(result.questions)} grounded quiz question(s). "
            "Question text is hidden by default for recording privacy; enable "
            "local-only question display only when it is safe to show generated quiz text."
        )

    sections = [*question_sections]
    if result.grades:
        sections.extend(
            ["", "### Score", "", f"**{result.score}/{len(result.questions)} correct**"]
        )
        for grade in result.grades:
            status = "correct" if grade.correct else "incorrect"
            if show_questions:
                sections.append(
                    f"- {grade.question_id}: {status} "
                    f"(selected {grade.selected_option_id}, answer {grade.correct_option_id})"
                )
            else:
                sections.append(
                    f"- {grade.question_id}: {status} (selected {grade.selected_option_id})"
                )
    return "\n".join(sections).strip()


def run_quiz_session(
    topic: str,
    question_count: int | float,
    answers: str,
    show_questions: bool = False,
) -> tuple[str, dict[str, Any]]:
    try:
        *_, result, metadata = _run_quiz_result(topic, question_count, answers)
        return _format_quiz_result(result, show_questions=show_questions), metadata
    except UserInputError as exc:
        return _input_error_payload(str(exc))
    except Exception as exc:
        return _error_payload(exc)


def _quiz_state_from_result(
    *,
    topic: str,
    question_count: int,
    result: QuizSessionResult,
    metadata: dict[str, Any],
) -> dict[str, Any] | None:
    if result.refusal_reason is not None or len(result.questions) != question_count:
        return None
    return {
        "topic": topic,
        "question_count": question_count,
        "session_id": result.session_id,
        "trace_file": Path(result.trace_path).name,
        "trace": metadata.get("trace", []),
        "questions": [question.model_dump(mode="json") for question in result.questions],
    }


def _quiz_questions_from_state(state: Any) -> list[QuizQuestion]:
    if not isinstance(state, dict):
        raise UserInputError("generate questions before scoring")
    raw_questions = state.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        raise UserInputError("generate questions before scoring")
    return [QuizQuestion.model_validate(question) for question in raw_questions]


def _quiz_answer_updates(question_count: int, *, interactive: bool) -> tuple[Any, Any, Any]:
    return tuple(
        gr.update(
            visible=interactive and index <= question_count,
            value=None,
            interactive=interactive,
            label=f"Answer for Question {index}",
        )
        for index in range(1, 4)
    )


def _quiz_score_button_update(*, interactive: bool) -> Any:
    return gr.update(interactive=interactive)


def _selected_quiz_answers(
    question_count: int,
    answer_1: str | None,
    answer_2: str | None,
    answer_3: str | None,
) -> list[str]:
    answers = [answer_1, answer_2, answer_3][:question_count]
    missing = [str(index) for index, value in enumerate(answers, start=1) if not value]
    if missing:
        raise UserInputError("select an answer for question " + ", ".join(missing))
    selected = [str(answer).strip().upper() for answer in answers if answer]
    invalid = sorted(set(selected) - VALID_OPTION_IDS)
    if invalid:
        raise UserInputError("answers must use option IDs A, B, C, or D")
    return selected


def _metadata_for_scored_quiz(
    *,
    state: dict[str, Any],
    result: QuizSessionResult,
) -> dict[str, Any]:
    trace_rows = state.get("trace") if isinstance(state.get("trace"), list) else []
    row = dict(trace_rows[-1]) if trace_rows and isinstance(trace_rows[-1], dict) else {}
    actions = [str(action) for action in row.get("actions", [])]
    if "grade_quiz" not in actions:
        actions.append("grade_quiz")
    row.update(
        {
            "question_ids": [question.question_id for question in result.questions],
            "selected_option_ids": [grade.selected_option_id for grade in result.grades],
            "correctness": [grade.correct for grade in result.grades],
            "actions": actions,
        }
    )
    return {
        "status": "ok",
        "session_id": state.get("session_id", "unknown"),
        "trace_file": state.get("trace_file", "generated-quiz-state"),
        "trace": [row],
    }


def _format_skillgap_report(result: Any) -> str:
    if not result.items:
        return "No trace-backed gaps found for the supplied sessions."

    sections = ["### Skill-Gap Diagnosis", ""]
    for index, item in enumerate(result.items, start=1):
        sections.append(f"#### {index}. Gap from teach + quiz signals")
        sections.append(
            f"Priority `{item.priority_score}` · evidence `{item.evidence_band}` "
            f"({_format_score(item.evidence_score)}) · action `{item.next_action}`"
        )
        sections.append(
            f"- Signals: quiz `{item.quiz_correct}/{item.quiz_total}`, "
            f"struggles `{item.struggle_count}`, refusals `{item.refusal_count}`"
        )
        if item.citation_ids:
            target = _friendly_review_target(getattr(item, "review_next", None))
            sections.append(f"- Next step: review {target}.")
        if item.reason_code:
            sections.append(f"- Refused/escalated: `{item.reason_code}`")
        sections.append("")
    return "\n".join(sections)


def run_skillgap_session(source_session_ids: str) -> tuple[str, dict[str, Any]]:
    try:
        clean_source_ids = _parse_source_session_ids(source_session_ids)
        settings, foundation = _runtime()
        session = SkillGapSession(
            session_id=f"hf-skillgap-{uuid.uuid4().hex[:10]}",
            source_session_ids=clean_source_ids,
            settings=settings,
            foundation=foundation,
        )
        result = session.run()
        metadata = {
            "status": "ok",
            "session_id": result.session_id,
            "source_session_ids": result.source_session_ids,
            "trace_file": Path(result.trace_path).name,
            "trace": safe_trace_rows(result.trace_path, SAFE_SKILLGAP_TRACE_FIELDS),
        }
        return _format_skillgap_report(result), metadata
    except UserInputError as exc:
        return _input_error_payload(str(exc))
    except Exception as exc:
        return _error_payload(exc)


def run_teach_ui(
    topic: str,
    style: str,
    track_lens: str,
    learner_answer: str,
    request: gr.Request | None = None,
) -> tuple[str, str, dict[str, Any]]:
    output, metadata = run_teach_session(
        topic,
        style,
        track_lens,
        learner_answer,
        user_email=_request_username(request),
    )
    return output, _format_trace_summary(metadata, mode="teach"), metadata


def run_quiz_ui(
    topic: str,
    question_count: int | float,
    answers: str,
    show_questions: bool,
) -> tuple[str, str, dict[str, Any]]:
    output, metadata = run_quiz_session(topic, question_count, answers, show_questions)
    return output, _format_trace_summary(metadata, mode="quiz"), metadata


def generate_quiz_questions_ui(
    topic: str,
    question_count: int | float,
    show_questions: bool,
) -> tuple[str, str, dict[str, Any]]:
    # Legacy callable for programmatic preview. The visible app uses
    # generate_quiz_questions_state_ui so scoring grades the stored questions.
    output, metadata = run_quiz_session(topic, question_count, "", show_questions)
    return output, _format_trace_summary(metadata, mode="quiz"), metadata


def reset_generated_quiz_state_ui() -> tuple[str, str, None, None, Any, Any, Any, Any]:
    return (
        "_Generate questions to review the local quiz text._",
        "_Trace summary appears after a run._",
        None,
        None,
        *_quiz_answer_updates(0, interactive=False),
        _quiz_score_button_update(interactive=False),
    )


def fill_quiz_grounded_preset_state_ui() -> tuple[str, int, bool, None, Any, Any, Any, Any]:
    topic, question_count, _, show_questions = fill_quiz_grounded_preset()
    return (
        topic,
        question_count,
        show_questions,
        None,
        *_quiz_answer_updates(0, interactive=False),
        _quiz_score_button_update(interactive=False),
    )


def generate_quiz_questions_state_ui(
    topic: str,
    question_count: int | float,
    show_questions: bool,
) -> tuple[str, str, dict[str, Any], dict[str, Any] | None, Any, Any, Any, Any]:
    try:
        clean_topic, count, _, result, metadata = _run_quiz_result(topic, question_count, "")
        output = _format_quiz_result(result, show_questions=show_questions)
        state = _quiz_state_from_result(
            topic=clean_topic,
            question_count=count,
            result=result,
            metadata=metadata,
        )
        if result.refusal_reason is None and len(result.questions) != count:
            output = "\n\n".join(
                [
                    output,
                    (
                        f"**Regenerate needed:** the model returned {len(result.questions)} "
                        f"of {count} requested question(s). Click **Generate questions** again "
                        "before scoring."
                    ),
                ]
            )
        answer_updates = _quiz_answer_updates(count, interactive=state is not None)
        return (
            output,
            _format_trace_summary(metadata, mode="quiz"),
            metadata,
            state,
            *answer_updates,
            _quiz_score_button_update(interactive=state is not None),
        )
    except UserInputError as exc:
        output, metadata = _input_error_payload(str(exc))
    except Exception as exc:
        output, metadata = _error_payload(exc)
    return (
        output,
        _format_trace_summary(metadata, mode="quiz"),
        metadata,
        None,
        *_quiz_answer_updates(0, interactive=False),
        _quiz_score_button_update(interactive=False),
    )


def score_generated_quiz_ui(
    topic: str,
    question_count: int | float,
    answer_1: str | None,
    answer_2: str | None,
    answer_3: str | None,
    show_questions: bool,
    quiz_state: dict[str, Any] | None,
) -> tuple[str, str, dict[str, Any]]:
    try:
        clean_topic = _require_topic(topic)
        count = _coerce_question_count(question_count)
        if not isinstance(quiz_state, dict):
            raise UserInputError("generate questions before scoring")
        if quiz_state.get("topic") != clean_topic or quiz_state.get("question_count") != count:
            raise UserInputError("generate questions again after changing topic or question count")

        questions = _quiz_questions_from_state(quiz_state)
        if len(questions) != count:
            raise UserInputError("generate questions again after changing topic or question count")
        selected = _selected_quiz_answers(count, answer_1, answer_2, answer_3)
        grades = grade_quiz(questions, selected)
        result = QuizSessionResult(
            session_id=str(quiz_state.get("session_id", "unknown")),
            questions=questions,
            grades=grades,
            score=sum(1 for grade in grades if grade.correct),
            trace_path=str(quiz_state.get("trace_file", "generated-quiz-state")),
        )
        metadata = _metadata_for_scored_quiz(state=quiz_state, result=result)
        return (
            _format_quiz_result(result, show_questions=show_questions),
            _format_trace_summary(metadata, mode="quiz"),
            metadata,
        )
    except UserInputError as exc:
        output, metadata = _input_error_payload(str(exc))
    except Exception as exc:
        output, metadata = _error_payload(exc)
    return output, _format_trace_summary(metadata, mode="quiz"), metadata


def run_skillgap_ui(source_session_ids: str) -> tuple[str, str, dict[str, Any]]:
    output, metadata = run_skillgap_session(source_session_ids)
    return output, _format_trace_summary(metadata, mode="skillgap"), metadata


def build_demo(status_message: str | None = None) -> gr.Blocks:
    with gr.Blocks(
        title="GenAcademy Coach",
        elem_classes=["gc-root"],
    ) as demo:
        gr.HTML(APP_HEADER_HTML)
        with gr.Row(elem_classes=["gc-auth-row"]):
            auth_status = gr.Markdown(
                "**Access:** checking account.",
                elem_classes=["gc-auth-status"],
            )
            if _auth_enabled():
                gr.Button(
                    "Sign out",
                    link="/logout",
                    elem_classes=["gc-preset-button", "gc-signout-button"],
                )
        if status_message is not None:
            gr.Markdown(status_message, elem_classes=["gc-deploy-note"])
        with gr.Accordion("Evidence fallback", open=False, elem_classes=["gc-fallback"]):
            gr.Markdown(
                "If a live provider call is slow during recording, use the committed redacted "
                "evidence in `docs/teach-loop-status.md` and `docs/demo-and-deliverables.md`. "
                "The raw trace files remain local/gitignored; demo trace cards show the rendered "
                "decision basis for walkthroughs."
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
                              Pick a known demo path, run the teach loop, then inspect the runtime
                              decision trace.
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
                        with gr.Row(elem_classes=["gc-action-row"]):
                            grounded_preset = gr.Button(
                                "Grounded preset",
                                elem_classes=["gc-preset-button"],
                            )
                            refusal_preset = gr.Button(
                                "Refusal preset",
                                elem_classes=["gc-preset-button"],
                            )
                            teach_button = gr.Button(
                                "Run teach",
                                elem_classes=["gc-run-button"],
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
                            lines=3,
                            elem_classes=["gc-input"],
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
                            value="_Awaiting teach run._",
                            elem_classes=["gc-output"],
                        )
                        teach_trace_summary = gr.Markdown(
                            label="Trace summary",
                            value="_Trace summary appears after a run._",
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
                quiz_state = gr.State(value=None)
                with gr.Row(elem_classes=["gc-workbench"]):
                    with gr.Column(scale=5, min_width=320, elem_classes=["gc-panel"]):
                        gr.HTML(
                            """
                            <p class="gc-eyebrow">Quiz mode</p>
                            <h2 class="gc-panel-title">Deterministic assessment</h2>
                            <p class="gc-panel-copy">
                              Generate cited MCQs, review them locally, then choose answers
                              and grade in Python.
                            </p>
                            <div class="gc-mode-card">
                              <strong>Demo visibility</strong>
                              <span>Questions can show in the app; traces stay redacted.</span>
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
                            value=1,
                            label="Questions",
                            elem_classes=["gc-input"],
                        )
                        show_questions = gr.Checkbox(
                            label="Show generated quiz questions (local/private demo only)",
                            value=True,
                            elem_classes=["gc-checkbox"],
                        )
                        with gr.Row(elem_classes=["gc-action-row"]):
                            quiz_preset = gr.Button(
                                "Grounded quiz preset",
                                elem_classes=["gc-preset-button"],
                            )
                            quiz_generate_button = gr.Button(
                                "Generate questions",
                                elem_classes=["gc-run-button"],
                            )
                    with gr.Column(scale=7, min_width=420, elem_classes=["gc-panel-soft"]):
                        gr.HTML(
                            """
                            <p class="gc-eyebrow">Assessment surface</p>
                            <h2 class="gc-panel-title">Questions, score, and trace</h2>
                            """
                        )
                        quiz_output = gr.Markdown(
                            label="Quiz questions and score",
                            value="_Generate questions to review the local quiz text._",
                            elem_classes=["gc-output"],
                        )
                        answer_1 = gr.Radio(
                            choices=sorted(VALID_OPTION_IDS),
                            label="Answer for Question 1",
                            value=None,
                            visible=False,
                            elem_classes=["gc-answer-choice"],
                        )
                        answer_2 = gr.Radio(
                            choices=sorted(VALID_OPTION_IDS),
                            label="Answer for Question 2",
                            value=None,
                            visible=False,
                            elem_classes=["gc-answer-choice"],
                        )
                        answer_3 = gr.Radio(
                            choices=sorted(VALID_OPTION_IDS),
                            label="Answer for Question 3",
                            value=None,
                            visible=False,
                            elem_classes=["gc-answer-choice"],
                        )
                        quiz_button = gr.Button(
                            "Score selected answers",
                            elem_classes=["gc-score-button"],
                            interactive=False,
                        )
                        quiz_trace_summary = gr.Markdown(
                            label="Trace summary",
                            value="_Trace summary appears after a run._",
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
                    fn=fill_quiz_grounded_preset_state_ui,
                    inputs=[],
                    outputs=[
                        quiz_topic,
                        question_count,
                        show_questions,
                        quiz_state,
                        answer_1,
                        answer_2,
                        answer_3,
                        quiz_button,
                    ],
                )
                quiz_topic.change(
                    fn=reset_generated_quiz_state_ui,
                    inputs=[],
                    outputs=[
                        quiz_output,
                        quiz_trace_summary,
                        quiz_metadata,
                        quiz_state,
                        answer_1,
                        answer_2,
                        answer_3,
                        quiz_button,
                    ],
                )
                question_count.change(
                    fn=reset_generated_quiz_state_ui,
                    inputs=[],
                    outputs=[
                        quiz_output,
                        quiz_trace_summary,
                        quiz_metadata,
                        quiz_state,
                        answer_1,
                        answer_2,
                        answer_3,
                        quiz_button,
                    ],
                )
                quiz_generate_button.click(
                    fn=generate_quiz_questions_state_ui,
                    inputs=[quiz_topic, question_count, show_questions],
                    outputs=[
                        quiz_output,
                        quiz_trace_summary,
                        quiz_metadata,
                        quiz_state,
                        answer_1,
                        answer_2,
                        answer_3,
                        quiz_button,
                    ],
                )
                quiz_button.click(
                    fn=score_generated_quiz_ui,
                    inputs=[
                        quiz_topic,
                        question_count,
                        answer_1,
                        answer_2,
                        answer_3,
                        show_questions,
                        quiz_state,
                    ],
                    outputs=[quiz_output, quiz_trace_summary, quiz_metadata],
                )

            with gr.Tab("Skill-Gap"):
                with gr.Row(elem_classes=["gc-workbench"]):
                    with gr.Column(scale=5, min_width=320, elem_classes=["gc-panel"]):
                        gr.HTML(
                            """
                            <p class="gc-eyebrow">Skill-Gap diagnosis</p>
                            <h2 class="gc-panel-title">Cited next-step plan</h2>
                            <p class="gc-panel-copy">
                              Diagnose existing teach and quiz sessions without adding memory,
                              a second agent loop, or LLM mastery grading.
                            </p>
                            <div class="gc-mode-card">
                              <strong>Trace-first workflow</strong>
                              <span>Input local session IDs; output only safe gap metadata.</span>
                            </div>
                            """
                        )
                        source_session_ids = gr.Textbox(
                            label="Source session IDs",
                            value=SKILLGAP_SOURCE_PRESET,
                            lines=3,
                            placeholder="demo-grounded-main-final-20260616",
                            elem_classes=["gc-input"],
                        )
                        with gr.Row(elem_classes=["gc-action-row"]):
                            skillgap_preset = gr.Button(
                                "Skill-Gap preset",
                                elem_classes=["gc-preset-button"],
                            )
                            skillgap_button = gr.Button(
                                "Run diagnosis",
                                elem_classes=["gc-run-button"],
                            )
                    with gr.Column(scale=7, min_width=420, elem_classes=["gc-panel-soft"]):
                        gr.HTML(
                            """
                            <p class="gc-eyebrow">Gap report</p>
                            <h2 class="gc-panel-title">Ranked gaps and redacted trace</h2>
                            """
                        )
                        skillgap_output = gr.Markdown(
                            label="Skill-Gap output",
                            value="_Awaiting diagnosis run._",
                            elem_classes=["gc-output"],
                        )
                        skillgap_trace_summary = gr.Markdown(
                            label="Trace summary",
                            value="_Trace summary appears after a run._",
                            elem_classes=["gc-trace"],
                        )
                        with gr.Accordion(
                            "Redacted metadata",
                            open=False,
                            elem_classes=["gc-accordion"],
                        ):
                            skillgap_metadata = gr.JSON(
                                label="Redacted metadata",
                                elem_classes=["gc-json"],
                            )
                skillgap_preset.click(
                    fn=fill_skillgap_preset,
                    inputs=[],
                    outputs=[source_session_ids],
                )
                skillgap_button.click(
                    fn=run_skillgap_ui,
                    inputs=[source_session_ids],
                    outputs=[skillgap_output, skillgap_trace_summary, skillgap_metadata],
                )
            with gr.Tab("Admin", visible=False) as admin_tab:
                with gr.Row(elem_classes=["gc-workbench"]):
                    with gr.Column(scale=5, min_width=320, elem_classes=["gc-panel"]):
                        gr.HTML(
                            """
                            <p class="gc-eyebrow">Cohort administration</p>
                            <h2 class="gc-panel-title">Create login accounts</h2>
                            <p class="gc-panel-copy">
                              Admin-only account management backed by the Week-2 user store.
                            </p>
                            <div class="gc-mode-card">
                              <strong>Access boundary</strong>
                              <span>Members can use Coach; only admins can create accounts.</span>
                            </div>
                            """
                        )
                        admin_email = gr.Textbox(
                            label="Email",
                            placeholder="learner@example.com",
                            elem_classes=["gc-input"],
                        )
                        with gr.Row():
                            admin_role = gr.Dropdown(
                                ["member", "admin"],
                                value="member",
                                label="Role",
                                elem_classes=["gc-input"],
                            )
                            admin_password = gr.Textbox(
                                label="Temporary password",
                                type="password",
                                elem_classes=["gc-input"],
                            )
                        create_user_button = gr.Button(
                            "Create account",
                            elem_classes=["gc-run-button"],
                        )
                    with gr.Column(scale=7, min_width=420, elem_classes=["gc-panel-soft"]):
                        gr.HTML(
                            """
                            <p class="gc-eyebrow">Admin state</p>
                            <h2 class="gc-panel-title">Users</h2>
                            """
                        )
                        admin_message = gr.Markdown(
                            value="_Awaiting admin action._",
                            elem_classes=["gc-output"],
                        )
                        admin_users = gr.Markdown(
                            value="_User list appears for admins._",
                            elem_classes=["gc-trace"],
                        )
                create_user_button.click(
                    fn=create_auth_user_ui,
                    inputs=[admin_email, admin_role, admin_password],
                    outputs=[admin_message, admin_users],
                )
        demo.load(auth_status_ui, inputs=[], outputs=[auth_status])
        demo.load(admin_tab_visibility_ui, inputs=[], outputs=[admin_tab])
        demo.load(list_admin_users_ui, inputs=[], outputs=[admin_users])
    return demo


demo = build_demo(_space_status_message())


def launch() -> None:
    logging.basicConfig(
        level=os.environ.get("GENACADEMY_LOG_LEVEL", "INFO"),
        format="%(levelname)s:%(name)s:%(message)s",
    )
    demo.launch(
        server_name=_server_name(),
        server_port=int(os.environ.get("PORT", "7860")),
        show_error=False,
        share=False,
        css=GENACADEMY_COACH_CSS,
        auth=_launch_auth(),
        auth_message=DEFAULT_AUTH_MESSAGE if _auth_enabled() else None,
    )
