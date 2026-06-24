from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from genacademy_coach.teach_types import NextAction

QueryType = Literal["happy", "edge", "known_failure", "adversarial"]
GoldenSplit = Literal["seed", "dev", "synthetic", "negative_control"]  # never "test"


class GoldenCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    query_type: QueryType
    concept: str
    expected_citation_span_id: str | None = None
    target_check_id: str | None = None
    expected_next_action: NextAction
    expected_tools: list[str]
    refusal_expected: bool = False
    strategy_changed_on_stumble: bool = False
    split: GoldenSplit
    cloud_safe: bool
    cloud_safe_reason: str | None = None
    user_query: str | None = None
    initial_wrong_answer: str | None = None
    expected_answer: str | None = None  # inline (cloud-safe only); drives the "correct" turn
    expected_check_keywords: list[str] = []  # short golden labels
    source_ref: str | None = None  # "scenario:<scenario_id>" for cloud_safe=false rows

    @model_validator(mode="after")
    def _check_cloud_safe(self) -> GoldenCase:
        if self.cloud_safe:
            if not (self.cloud_safe_reason and self.cloud_safe_reason.strip()):
                raise ValueError(f"{self.case_id}: cloud_safe=true requires cloud_safe_reason")
            if not self.user_query and not self.source_ref:
                raise ValueError(
                    f"{self.case_id}: cloud_safe=true requires user_query or source_ref"
                )
        else:
            if any([self.user_query, self.initial_wrong_answer, self.expected_answer]):
                raise ValueError(f"{self.case_id}: cloud_safe=false must not carry inline text")
            if not self.source_ref:
                raise ValueError(f"{self.case_id}: cloud_safe=false requires source_ref")
        if not self.refusal_expected and not self.expected_check_keywords:
            raise ValueError(f"{self.case_id}: teachable case requires expected_check_keywords")
        return self


def load_golden_cases(path: Path) -> list[GoldenCase]:
    rows: list[GoldenCase] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(GoldenCase.model_validate_json(line))
    return rows
