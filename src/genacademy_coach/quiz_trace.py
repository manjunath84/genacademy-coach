from __future__ import annotations

import json
from pathlib import Path

from genacademy_coach.quiz_types import QuizTraceRow


class QuizTraceWriter:
    def __init__(self, trace_dir: Path):
        self._trace_dir = trace_dir

    def append(self, row: QuizTraceRow) -> Path:
        self._trace_dir.mkdir(parents=True, exist_ok=True)
        path = self._trace_dir / f"{row.session_id}.jsonl"
        payload = row.model_dump(mode="json")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
        return path
