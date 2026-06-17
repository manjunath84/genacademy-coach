from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from genacademy_coach.teach_types import EvidenceBand

SkillGapAction = Literal["review_next", "refuse_escalate"]


class SkillGapItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gap_id: str
    topic_hash: str
    source_session_ids: list[str] = Field(default_factory=list)
    priority_score: int
    evidence_score: float
    evidence_band: EvidenceBand
    citation_ids: list[str] = Field(default_factory=list)
    quiz_correct: int = 0
    quiz_total: int = 0
    struggle_count: int = 0
    refusal_count: int = 0
    next_action: SkillGapAction
    escalated: bool = False
    reason_code: str | None = None
    review_next: str | None = None


class SkillGapTraceRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    topic_hash: str
    gap_id: str
    source_session_ids: list[str] = Field(default_factory=list)
    evidence_score: float
    evidence_band: EvidenceBand
    citation_ids: list[str] = Field(default_factory=list)
    quiz_correct: int = 0
    quiz_total: int = 0
    struggle_count: int = 0
    refusal_count: int = 0
    next_action: SkillGapAction
    escalated: bool = False
    reason_code: str | None = None


class SkillGapReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    source_session_ids: list[str]
    items: list[SkillGapItem] = Field(default_factory=list)
    trace_path: str
