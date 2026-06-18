from __future__ import annotations

import json
from typing import Any

from genacademy_coach.memory_types import (
    EpisodicMemoryRecord,
    LearnerMemorySeed,
)

SAFE_MEMORY_PREFIX = "GenAcademy safe learner-state JSON:"
MEMORY_RECALL_QUERY = "GenAcademy safe learner state style track lens topic hashes"


class NullEpisodicMemory:
    provider = "null"

    def recall(
        self,
        *,
        user_id_hash: str,
        topic_hash: str,
    ) -> list[EpisodicMemoryRecord]:
        return []

    def write(
        self,
        *,
        user_id_hash: str,
        record: EpisodicMemoryRecord,
    ) -> None:
        return None


class Mem0EpisodicMemory:
    provider = "mem0"

    def __init__(self, *, api_key: str, client: Any | None = None):
        if client is None:
            try:
                from mem0 import MemoryClient
            except ImportError as exc:  # pragma: no cover - depends on optional package.
                raise RuntimeError(
                    "Mem0 memory is configured, but the mem0 Python SDK is not installed. "
                    "Install the package that exposes `from mem0 import MemoryClient`."
                ) from exc
            client = MemoryClient(api_key=api_key)
        self._client = client

    def recall(
        self,
        *,
        user_id_hash: str,
        topic_hash: str,
    ) -> list[EpisodicMemoryRecord]:
        query = f"{MEMORY_RECALL_QUERY} topic_hash {topic_hash}"
        try:
            raw_results = self._client.search(
                query=query,
                filters={"user_id": user_id_hash},
            )
        except TypeError:
            raw_results = self._client.search(query, user_id=user_id_hash)
        records: list[EpisodicMemoryRecord] = []
        for item in _iter_mem0_results(raw_results):
            text = str(item.get("memory") or item.get("content") or "")
            record = _record_from_memory_text(text)
            if record is not None:
                records.append(record)
        return records

    def write(
        self,
        *,
        user_id_hash: str,
        record: EpisodicMemoryRecord,
    ) -> None:
        payload = record.model_dump(mode="json")
        self._client.add(
            messages=[
                {
                    "role": "user",
                    "content": f"{SAFE_MEMORY_PREFIX} {json.dumps(payload, sort_keys=True)}",
                }
            ],
            user_id=user_id_hash,
        )


def build_episodic_memory(settings: Any):
    api_key = str(getattr(settings, "mem0_api_key", "") or "").strip()
    user_salt = str(getattr(settings, "memory_user_salt", "") or "").strip()
    if not api_key or not user_salt:
        return NullEpisodicMemory()
    return Mem0EpisodicMemory(api_key=api_key)


def seed_from_records(records: list[EpisodicMemoryRecord]) -> LearnerMemorySeed:
    seed = LearnerMemorySeed()
    known: set[str] = set()
    struggled: set[str] = set()
    for record in records:
        if record.style is not None:
            seed.style = record.style
        if record.track_lens is not None:
            seed.track_lens = record.track_lens
        known.update(record.known_topic_hashes)
        struggled.update(record.struggled_topic_hashes)
        seed.session_count += record.session_count
        seed.turn_count += record.turn_count
    seed.known_topic_hashes = sorted(known)
    seed.struggled_topic_hashes = sorted(struggled)
    return seed


def _iter_mem0_results(raw_results: Any) -> list[dict[str, Any]]:
    if isinstance(raw_results, dict):
        results = raw_results.get("results", [])
    else:
        results = raw_results
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, dict)]


def _record_from_memory_text(text: str) -> EpisodicMemoryRecord | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    try:
        return EpisodicMemoryRecord.model_validate(payload)
    except ValueError:
        return None
