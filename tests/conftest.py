from types import SimpleNamespace

import pytest

from genacademy_coach.teach_session import CoachSession
from genacademy_coach.teach_types import CoachAgentResponse, LearnerProfile, TokenUsage


class _FakeFoundation:
    provider = object()

    def __init__(self, rows=None):
        self._rows = rows or []

    def retrieve(self, query: str):
        return list(self._rows)


class FakePort:
    def __init__(
        self,
        response: CoachAgentResponse | None = None,
        last_usage: TokenUsage | None = None,
    ):
        self.response = response or CoachAgentResponse(
            learner_message="I can't find this in the course materials.",
            observation="no citeable course corpus found",
            next_action="refuse_escalate",
            strategy="refusal",
            citation_ids=[],
        )
        self.last_usage = last_usage or TokenUsage()

    def invoke(self, messages: list[dict[str, str]]) -> CoachAgentResponse:
        return self.response


@pytest.fixture
def fake_settings(tmp_path):
    return SimpleNamespace(
        trace_dir=tmp_path / "traces",
        review_queue_path=tmp_path / "rq.jsonl",
        stop_threshold=0.40,
        confirm_threshold=0.85,
        max_teach_turns=4,
    )


@pytest.fixture
def fake_foundation():
    return _FakeFoundation(
        rows=[
            {
                "chunk_id": "note::0",
                "doc_id": "note",
                "text": "Attention focuses context.",
                "score": 0.91,
                "title": "a.md",
                "source_type": "note",
                "page_or_section": None,
            }
        ]
    )


@pytest.fixture
def make_session(fake_settings, fake_foundation):
    def _make_session(
        *,
        last_usage: TokenUsage | None = None,
        response: CoachAgentResponse | None = None,
    ):
        session = CoachSession(
            session_id="fake-session",
            topic="attention",
            settings=fake_settings,
            foundation=fake_foundation,
            profile=LearnerProfile(),
            agent_port=FakePort(response=response, last_usage=last_usage),
        )
        return session, fake_settings.trace_dir

    return _make_session
