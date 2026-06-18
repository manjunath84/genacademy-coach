from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

LearnerStyle = Literal["concise", "analogy", "step_by_step"]
TrackLens = Literal["low_code_no_code", "code_heavy", "bridge"]
MemoryEvent = Literal["recall", "write", "skip"]


class LearnerMemorySeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style: LearnerStyle | None = None
    track_lens: TrackLens | None = None
    known_topic_hashes: list[str] = Field(default_factory=list)
    struggled_topic_hashes: list[str] = Field(default_factory=list)
    session_count: int = 0
    turn_count: int = 0


class EpisodicMemoryRecord(LearnerMemorySeed):
    topic_hash: str
    source_session_id: str


class MemoryTraceRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    user_id_hash: str
    topic_hash: str
    event: MemoryEvent
    provider: str
    recalled_count: int = 0
    wrote_count: int = 0
    skipped_reason: str | None = None


class EpisodicMemory(Protocol):
    provider: str

    def recall(
        self,
        *,
        user_id_hash: str,
        topic_hash: str,
    ) -> list[EpisodicMemoryRecord]: ...

    def write(
        self,
        *,
        user_id_hash: str,
        record: EpisodicMemoryRecord,
    ) -> None: ...
