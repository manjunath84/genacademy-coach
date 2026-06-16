from __future__ import annotations

import json
from pathlib import Path

from genacademy_coach.teach_types import TraceTurn


class TraceWriter:
    def __init__(self, trace_dir: Path):
        self._trace_dir = trace_dir

    def append(self, turn: TraceTurn) -> Path:
        self._trace_dir.mkdir(parents=True, exist_ok=True)
        path = self._trace_dir / f"{turn.session_id}.jsonl"
        payload = turn.model_dump(mode="json")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
        return path


def load_trace(path: Path) -> list[TraceTurn]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(TraceTurn.model_validate_json(line))
    return rows
