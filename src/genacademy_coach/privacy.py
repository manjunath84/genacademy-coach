from __future__ import annotations

import hashlib
import re

DEFAULT_HASH_LENGTH = 12
TOPIC_HASH_PATTERN = re.compile(r"^[0-9a-f]{12}$")


def _normalized(value: str) -> str:
    return " ".join(value.strip().split())


def _digest(kind: str, value: str, *, salt: str = "", length: int = DEFAULT_HASH_LENGTH) -> str:
    normalized = _normalized(value)
    material = f"{kind}\0{salt}\0{normalized}".encode()
    return hashlib.sha256(material).hexdigest()[:length]


def topic_hash(topic: str) -> str:
    return _digest("topic", topic)


def topic_hash_or_existing(value: str) -> str:
    normalized = _normalized(value)
    return normalized if TOPIC_HASH_PATTERN.fullmatch(normalized) else topic_hash(value)


def learner_input_hash(learner_input: str) -> str:
    return _digest("learner_input", learner_input)


def user_id_hash(user_id: str, *, salt: str) -> str:
    if not salt.strip():
        raise ValueError("GENACADEMY_COACH_MEMORY_USER_SALT is required for user_id_hash")
    return _digest("user_id", user_id, salt=salt, length=16)
