from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EvidenceBand = Literal["stop", "confirm", "proceed"]
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
    tool_calls: list[str]


class TeachSessionResult(BaseModel):
    session_id: str
    profile: LearnerProfile
    response: CoachAgentResponse
    trace_path: str
