from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator

EvidenceBand = Literal["stop", "confirm", "proceed"]
DecisionSource = Literal["agent", "python safety gate"]
NextAction = Literal[
    "advance",
    "re_explain_differently",
    "drill",
    "refuse_escalate",
    "stop",
]
Strategy = Literal[
    "analogy",
    "step_by_step",
    "contrastive_example",
    "code_walkthrough",
    "workflow_map",
    "short_drill",
    "refusal",
    "summary",
]


class RetrievedSpan(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    score: float
    title: str
    source_type: str
    page_or_section: str | None = None

    @property
    def citation_id(self) -> str:
        return self.chunk_id

    @property
    def source_label(self) -> str:
        return source_label(
            title=self.title,
            source_type=self.source_type,
            page_or_section=self.page_or_section,
            citation_id=self.citation_id,
        )


class CheckItem(BaseModel):
    question: str
    expected_answer: str
    expected_keywords: list[str] = Field(min_length=1)
    citation_id: str

    @field_validator("expected_keywords")
    @classmethod
    def normalize_keywords(cls, value: list[str]) -> list[str]:
        normalized = [item.strip().lower() for item in value if item.strip()]
        if not normalized:
            raise ValueError("expected_keywords must contain at least one non-empty value")
        return normalized


class UnderstandingGrade(BaseModel):
    correct: bool
    matched_keywords: list[str]
    missing_keywords: list[str]
    citation_id: str


class LearnerProfile(BaseModel):
    style: Literal["concise", "analogy", "step_by_step"] = "analogy"
    track_lens: Literal["low_code_no_code", "code_heavy", "bridge"] = "code_heavy"
    bridge_from: str | None = None
    known: list[str] = Field(default_factory=list)
    struggled: list[str] = Field(default_factory=list)
    previous_strategies: list[Strategy] = Field(default_factory=list)
    last_grade_correct: bool | None = None
    turn_count: int = 0


class CoachAgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    _decision_source: DecisionSource = PrivateAttr(default="agent")

    learner_message: str
    observation: str
    next_action: NextAction
    strategy: Strategy
    citation_ids: list[str] = Field(default_factory=list)
    check_question: str | None = None


class TraceTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    turn: int
    topic_hash: str
    learner_input_hash: str
    next_action: NextAction
    strategy: Strategy
    evidence_score: float
    evidence_band: EvidenceBand
    faithfulness_ok: bool | None = None
    retrieved_citation_ids: list[str]
    retrieved_citation_labels: list[str] = Field(default_factory=list)
    tool_calls: list[str]


class TeachSessionResult(BaseModel):
    session_id: str
    profile: LearnerProfile
    response: CoachAgentResponse
    trace_path: str


def source_label(
    *,
    title: str,
    source_type: str,
    page_or_section: str | None,
    citation_id: str,
) -> str:
    readable_title = _readable_title(title, citation_id)
    location = _readable_location(page_or_section, source_type, citation_id)
    if location:
        return f"{readable_title} ({location})"
    return readable_title


def _readable_title(title: str, citation_id: str) -> str:
    candidate = title.strip()
    if not candidate:
        candidate = citation_id.split("::", 1)[0].split("/", 1)[-1]
    candidate = re.sub(r"\.[A-Za-z0-9]+$", "", candidate)
    candidate = re.sub(r"-[0-9a-f]{8,}$", "", candidate, flags=re.IGNORECASE)
    candidate = candidate.replace("_", " ").replace("-", " ")
    candidate = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", candidate)
    candidate = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip()
    return candidate.title() if candidate else "Course Material"


def _readable_location(
    page_or_section: str | None,
    source_type: str,
    citation_id: str,
) -> str:
    raw_location = str(page_or_section or "").strip()
    if raw_location:
        lowered = raw_location.lower()
        if lowered.startswith(("slide", "page", "section", "chunk")):
            return raw_location
        if raw_location.isdigit():
            if source_type == "slide":
                return f"slide {raw_location}"
            if source_type in {"handout", "transcript"}:
                return f"page {raw_location}"
            return f"section {raw_location}"
        return raw_location

    suffix = citation_id.split("::", 1)[1] if "::" in citation_id else ""
    if suffix.isdigit():
        return f"chunk {suffix}"
    return ""
