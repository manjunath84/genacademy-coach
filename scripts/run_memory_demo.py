from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any

from genacademy_coach.memory_types import EpisodicMemoryRecord, MemoryTraceRow
from genacademy_coach.privacy import topic_hash, user_id_hash
from genacademy_coach.settings import CoachSettings
from genacademy_coach.teach_session import AgentResponseError, CoachSession
from genacademy_coach.teach_types import (
    CheckItem,
    CoachAgentResponse,
    LearnerProfile,
    RetrievedSpan,
)

DEMO_MEMORY_SALT = "demo-local-memory-salt"
DEMO_CITATION_ID = "note/agent-harness::0"
DEMO_SPAN_TEXT = "An agent harness wraps model calls with tool checks and feedback loops."
OFF_CORPUS_TOPIC = "Gen Academy cafeteria menu"


class DemoMemory:
    provider = "demo"

    def __init__(self):
        self._records_by_user: dict[str, list[EpisodicMemoryRecord]] = {}

    def recall(
        self,
        *,
        user_id_hash: str,
        topic_hash: str,
    ) -> list[EpisodicMemoryRecord]:
        return list(self._records_by_user.get(user_id_hash, []))

    def write(
        self,
        *,
        user_id_hash: str,
        record: EpisodicMemoryRecord,
    ) -> None:
        self._records_by_user.setdefault(user_id_hash, []).append(record)


class DemoFoundation:
    provider = object()

    def __init__(self, grounded_topic: str):
        self.grounded_topic = grounded_topic
        self.queries: list[str] = []

    def retrieve(self, query: str) -> list[dict[str, Any]]:
        self.queries.append(query)
        if query != self.grounded_topic:
            return []
        return [
            {
                "chunk_id": DEMO_CITATION_ID,
                "doc_id": "note/agent-harness",
                "text": DEMO_SPAN_TEXT,
                "score": 0.91,
                "title": "Agent Harness Notes",
                "source_type": "note",
                "page_or_section": "demo",
            }
        ]


class DemoAgentPort:
    def __init__(self, runtime=None):
        self.runtime = runtime

    def invoke(self, messages: list[dict[str, str]]) -> CoachAgentResponse:
        if self.runtime is None:
            raise AgentResponseError("demo runtime was not attached")
        self.runtime.record_tool("retrieve_course_corpus")
        rows = self.runtime.foundation.retrieve(self.runtime.topic)
        spans = [
            RetrievedSpan(
                chunk_id=str(row["chunk_id"]),
                doc_id=str(row["doc_id"]),
                text=str(row["text"]),
                score=float(row["score"]),
                title=str(row["title"]),
                source_type=str(row["source_type"]),
                page_or_section=row.get("page_or_section"),
            )
            for row in rows
            if float(row["score"]) >= self.runtime.stop_threshold and str(row["text"]).strip()
        ]
        if not spans:
            raise AgentResponseError("no citeable course corpus found")
        self.runtime.last_spans = spans
        self.runtime.record_tool("generate_check_item")
        self.runtime.current_check = CheckItem(
            question="What does the agent harness wrap?",
            expected_answer="It wraps model calls with tool checks and feedback loops.",
            expected_keywords=["model calls", "tool checks", "feedback loops"],
            citation_id=spans[0].citation_id,
        )
        strategy = "step_by_step" if self.runtime.profile.style == "step_by_step" else "analogy"
        return CoachAgentResponse(
            learner_message=f"{spans[0].text} [{spans[0].citation_id}]",
            observation="demo retrieved a citeable course span",
            next_action="drill",
            strategy=strategy,
            citation_ids=[spans[0].citation_id],
            check_question=self.runtime.current_check.question,
        )


def append_memory_trace(path: Path, row: MemoryTraceRow) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row.model_dump(mode="json"), sort_keys=True) + "\n")


def build_demo_session(
    *,
    session_id: str,
    topic: str,
    settings: CoachSettings,
    foundation: DemoFoundation,
    memory: DemoMemory,
    hashed_user_id: str,
    profile: LearnerProfile,
) -> CoachSession:
    agent = DemoAgentPort()
    session = CoachSession(
        session_id=session_id,
        topic=topic,
        settings=settings,
        foundation=foundation,
        profile=profile,
        agent_port=agent,
        memory=memory,
        user_id_hash=hashed_user_id,
    )
    agent.runtime = session.runtime
    return session


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--topic", required=True)
    args = parser.parse_args()

    settings = CoachSettings.from_env()
    memory = DemoMemory()
    foundation = DemoFoundation(args.topic)
    hashed_user_id = user_id_hash(args.user_id, salt=DEMO_MEMORY_SALT)
    memory_trace_path = settings.trace_dir / f"memory-demo-{uuid.uuid4().hex[:8]}.jsonl"

    session1 = build_demo_session(
        session_id=f"memory-demo-s1-{uuid.uuid4().hex[:6]}",
        topic=args.topic,
        settings=settings,
        foundation=foundation,
        memory=memory,
        hashed_user_id=hashed_user_id,
        profile=LearnerProfile(style="step_by_step", track_lens="bridge"),
    )
    first = session1.start()
    session1.finish()
    append_memory_trace(
        memory_trace_path,
        MemoryTraceRow(
            session_id=session1.session_id,
            user_id_hash=hashed_user_id,
            topic_hash=topic_hash(args.topic),
            event="write",
            provider=memory.provider,
            wrote_count=1,
        ),
    )

    session2 = build_demo_session(
        session_id=f"memory-demo-s2-{uuid.uuid4().hex[:6]}",
        topic=args.topic,
        settings=settings,
        foundation=foundation,
        memory=memory,
        hashed_user_id=hashed_user_id,
        profile=LearnerProfile(style="concise", track_lens="low_code_no_code"),
    )
    second = session2.start()
    recalled_records = memory.recall(
        user_id_hash=hashed_user_id,
        topic_hash=topic_hash(args.topic),
    )
    append_memory_trace(
        memory_trace_path,
        MemoryTraceRow(
            session_id=session2.session_id,
            user_id_hash=hashed_user_id,
            topic_hash=topic_hash(args.topic),
            event="recall",
            provider=memory.provider,
            recalled_count=len(recalled_records),
        ),
    )

    off_corpus = build_demo_session(
        session_id=f"memory-demo-off-{uuid.uuid4().hex[:6]}",
        topic=OFF_CORPUS_TOPIC,
        settings=settings,
        foundation=foundation,
        memory=memory,
        hashed_user_id=hashed_user_id,
        profile=LearnerProfile(),
    )
    refused = off_corpus.start()

    print(f"user_id_hash={hashed_user_id}")
    print(f"session1_written={len(recalled_records) == 1}")
    print(
        "session2_recalled="
        f"{session2.profile.style == 'step_by_step' and session2.profile.track_lens == 'bridge'}"
    )
    print(f"session2_style={session2.profile.style}")
    print(f"session2_track_lens={session2.profile.track_lens}")
    print(f"grounding_citation_ids={','.join(second.response.citation_ids)}")
    print(f"retrieval_queries={','.join(foundation.queries)}")
    print(f"off_corpus_next_action={refused.response.next_action}")
    print(f"trace={first.trace_path}")
    print(f"memory_trace={memory_trace_path}")


if __name__ == "__main__":
    main()
