from __future__ import annotations

import json
import re
from pathlib import Path

from genacademy_coach.eval_io import read_eval_text
from genacademy_coach.settings import CoachSettings

QUESTION_PREFIX_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s*")


def load_manifest_items(manifest_path: Path, *, split: str) -> list[dict[str, str]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [item for item in manifest["items"] if item["split"] == split]


def extract_questions(text: str) -> list[str]:
    rows = []
    for line in text.splitlines():
        cleaned = QUESTION_PREFIX_RE.sub("", line).strip()
        if "?" in cleaned:
            rows.append(cleaned[:500])
    if rows:
        return rows
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return [cleaned[:500]]
    return []


def question_records_for_item(
    eval_questions_dir: Path,
    item: dict[str, str],
) -> list[dict[str, str]]:
    source_path = eval_questions_dir / item["source_file"]
    questions = extract_questions(read_eval_text(source_path))
    if not questions:
        questions = [source_path.stem.replace("-", " ")]
    return [
        {
            "scenario_id": f"{item['id']}:{idx:03d}",
            "item_id": item["id"],
            "source_file": item["source_file"],
            "split": item["split"],
            "question_text": question,
        }
        for idx, question in enumerate(questions)
    ]


def load_scenarios(settings: CoachSettings, *, split: str, limit: int) -> list[dict[str, str]]:
    scenarios = []
    for item in load_manifest_items(settings.eval_manifest_path, split=split):
        scenarios.extend(question_records_for_item(settings.eval_questions_dir, item))
    return scenarios[:limit]
