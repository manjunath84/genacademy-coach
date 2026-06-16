from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def append_review_queue(
    path: Path,
    *,
    session_id: str,
    topic: str,
    reason: str,
    score: float | None,
    citation_ids: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "session_id": session_id,
        "topic": topic,
        "reason": reason,
        "score": score,
        "citation_ids": citation_ids,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")
