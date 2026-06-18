from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from genacademy_coach.memory import Mem0EpisodicMemory, NullEpisodicMemory, build_episodic_memory
from genacademy_coach.memory_types import EpisodicMemoryRecord, MemoryTraceRow
from genacademy_coach.privacy import topic_hash
from genacademy_coach.teach_session import CoachSession, StaticAgentPort
from genacademy_coach.teach_types import CoachAgentResponse, LearnerProfile, RetrievedSpan


class FakeSettings:
    stop_threshold = 0.40
    confirm_threshold = 0.85
    mem0_api_key = None
    memory_user_salt = None

    def __init__(self, root: Path, max_teach_turns: int = 4):
        self.trace_dir = root / "traces"
        self.review_queue_path = root / "review_queue.jsonl"
        self.max_teach_turns = max_teach_turns


class FakeFoundation:
    provider = object()

    def retrieve(self, query: str):
        return []


class FakeMemory:
    provider = "fake"

    def __init__(self, records_by_user: dict[str, list[EpisodicMemoryRecord]] | None = None):
        self.records_by_user = records_by_user or {}
        self.recalls: list[tuple[str, str]] = []
        self.writes: list[tuple[str, EpisodicMemoryRecord]] = []

    def recall(
        self,
        *,
        user_id_hash: str,
        topic_hash: str,
    ) -> list[EpisodicMemoryRecord]:
        self.recalls.append((user_id_hash, topic_hash))
        return list(self.records_by_user.get(user_id_hash, []))

    def write(
        self,
        *,
        user_id_hash: str,
        record: EpisodicMemoryRecord,
    ) -> None:
        self.writes.append((user_id_hash, record))
        self.records_by_user.setdefault(user_id_hash, []).append(record)


def span(score: float = 0.91) -> RetrievedSpan:
    return RetrievedSpan(
        chunk_id="note/attention::0",
        doc_id="note/attention",
        text="Attention highlights relevant context.",
        score=score,
        title="attention.md",
        source_type="note",
    )


def grounded_response(citation_id: str = "note/attention::0") -> CoachAgentResponse:
    return CoachAgentResponse(
        learner_message=f"Attention highlights relevant context. [{citation_id}]",
        observation="retrieved a citeable span",
        next_action="drill",
        strategy="analogy",
        citation_ids=[citation_id],
    )


def test_null_memory_is_default_noop():
    memory = build_episodic_memory(
        SimpleNamespace(mem0_api_key=None, memory_user_salt=None)
    )

    assert isinstance(memory, NullEpisodicMemory)
    assert memory.recall(user_id_hash="u1", topic_hash="t1") == []
    memory.write(
        user_id_hash="u1",
        record=EpisodicMemoryRecord(
            topic_hash="t1",
            source_session_id="s1",
        ),
    )


def test_session_without_user_hash_keeps_memory_null_even_when_configured(tmp_path):
    settings = FakeSettings(tmp_path)
    settings.mem0_api_key = "mem0-key"
    settings.memory_user_salt = "salt"

    session = CoachSession(
        session_id="anonymous",
        topic="attention",
        settings=settings,
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=StaticAgentPort(grounded_response()),
    )

    assert isinstance(session.memory, NullEpisodicMemory)


def test_fake_memory_isolates_users():
    record = EpisodicMemoryRecord(
        topic_hash=topic_hash("attention"),
        source_session_id="s1",
        style="step_by_step",
    )
    memory = FakeMemory(records_by_user={"user-a": [record]})

    assert memory.recall(user_id_hash="user-a", topic_hash=record.topic_hash) == [record]
    assert memory.recall(user_id_hash="user-b", topic_hash=record.topic_hash) == []


def test_recall_seeds_profile_without_changing_grounding(tmp_path):
    memory = FakeMemory(
        records_by_user={
            "user-a": [
                EpisodicMemoryRecord(
                    topic_hash=topic_hash("attention"),
                    source_session_id="s1",
                    style="step_by_step",
                    track_lens="bridge",
                    known_topic_hashes=["abc123def456"],
                )
            ]
        }
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(style="concise", track_lens="low_code_no_code"),
        agent_port=StaticAgentPort(grounded_response()),
        memory=memory,
        user_id_hash="user-a",
    )
    session.runtime.last_spans = [span()]

    result = session.start()

    assert result.profile.style == "step_by_step"
    assert result.profile.track_lens == "bridge"
    assert result.profile.known == ["abc123def456"]
    assert result.response.citation_ids == ["note/attention::0"]
    assert memory.recalls == [("user-a", topic_hash("attention"))]


def test_grounded_turn_writes_only_safe_memory_payload(tmp_path):
    memory = FakeMemory()
    session = CoachSession(
        session_id="abc",
        topic="PRIVATE RAW TOPIC",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(style="analogy", track_lens="code_heavy"),
        agent_port=StaticAgentPort(grounded_response()),
        memory=memory,
        user_id_hash="user-a",
    )
    session.runtime.last_spans = [span()]

    session.start()
    session.finish()

    assert len(memory.writes) == 1
    _, record = memory.writes[0]
    serialized = record.model_dump_json()
    assert "PRIVATE RAW TOPIC" not in serialized
    assert record.topic_hash == topic_hash("PRIVATE RAW TOPIC")
    assert record.struggled_topic_hashes == [topic_hash("PRIVATE RAW TOPIC")]


def test_refusal_and_stop_band_turns_do_not_write_memory(tmp_path):
    refusal_memory = FakeMemory()
    refusal_session = CoachSession(
        session_id="refusal",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=StaticAgentPort(
            CoachAgentResponse(
                learner_message="I cannot verify this.",
                observation="no citation",
                next_action="advance",
                strategy="summary",
                citation_ids=[],
            )
        ),
        memory=refusal_memory,
        user_id_hash="user-a",
    )

    refusal_session.start()
    refusal_session.finish()

    stop_memory = FakeMemory()
    stop_session = CoachSession(
        session_id="stop-band",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=StaticAgentPort(grounded_response()),
        memory=stop_memory,
        user_id_hash="user-a",
    )
    stop_session.runtime.last_spans = [span(score=0.2)]

    stop_session.start()
    stop_session.finish()

    assert refusal_memory.writes == []
    assert stop_memory.writes == []


def test_memory_raw_fields_are_rejected():
    with pytest.raises(ValidationError):
        EpisodicMemoryRecord(
            topic_hash="abc123def456",
            source_session_id="s1",
            raw_topic="PRIVATE TOPIC",
        )
    with pytest.raises(ValidationError):
        MemoryTraceRow(
            session_id="s1",
            user_id_hash="user-a",
            topic_hash="abc123def456",
            event="write",
            provider="fake",
            learner_answer="PRIVATE ANSWER",
        )


def test_memory_is_never_accepted_as_citation_source(tmp_path):
    memory = FakeMemory(
        records_by_user={
            "user-a": [
                EpisodicMemoryRecord(
                    topic_hash=topic_hash("attention"),
                    source_session_id="s1",
                    known_topic_hashes=[topic_hash("memory-only citation")],
                )
            ]
        }
    )
    session = CoachSession(
        session_id="abc",
        topic="attention",
        settings=FakeSettings(tmp_path),
        foundation=FakeFoundation(),
        profile=LearnerProfile(),
        agent_port=StaticAgentPort(grounded_response("memory/only::0")),
        memory=memory,
        user_id_hash="user-a",
    )
    session.runtime.last_spans = [span()]

    result = session.start()

    assert result.response.next_action == "refuse_escalate"
    assert result.response.citation_ids == []


def test_mem0_adapter_uses_current_client_add_and_search_shapes():
    record = EpisodicMemoryRecord(
        topic_hash=topic_hash("attention"),
        source_session_id="s1",
        style="analogy",
    )

    class FakeMem0Client:
        def __init__(self):
            self.add_kwargs = None
            self.search_kwargs = None

        def add(self, **kwargs):
            self.add_kwargs = kwargs

        def search(self, **kwargs):
            self.search_kwargs = kwargs
            return {"results": [{"memory": kwargs["query"] + " " + record.model_dump_json()}]}

    client = FakeMem0Client()
    memory = Mem0EpisodicMemory(api_key="unused", client=client)

    memory.write(user_id_hash="user-a", record=record)
    recalled = memory.recall(user_id_hash="user-a", topic_hash=record.topic_hash)

    assert client.add_kwargs["user_id"] == "user-a"
    assert client.add_kwargs["messages"][0]["role"] == "user"
    assert client.search_kwargs["filters"] == {"user_id": "user-a"}
    assert recalled == [record]
