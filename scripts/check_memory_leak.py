from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from genacademy_coach.corpus import iter_indexable_files, load_corpus_document
from genacademy_coach.eval_io import read_eval_text
from genacademy_coach.eval_split import normalized_words, phrase_hashes
from genacademy_coach.settings import CoachSettings

FORBIDDEN_MEMORY_KEYS = frozenset(
    {
        "topic",
        "raw_topic",
        "learner_input",
        "learner_answer",
        "answer",
        "learner_message",
        "assistant_message",
        "tutor_message",
        "course_corpus_text",
        "retrieved_text",
        "span_text",
        "eval_question",
        "question",
        "prompt",
        "options",
        "rationale",
        "expected_answer",
    }
)


def normalized_text(text: str) -> str:
    return " ".join(normalized_words(text))


def iter_default_memory_artifacts(settings: CoachSettings) -> list[Path]:
    candidates: list[Path] = []
    for pattern_root in (settings.trace_dir, settings.repo_root / "tmp"):
        if pattern_root.exists():
            candidates.extend(sorted(pattern_root.rglob("memory*.jsonl")))
            candidates.extend(sorted(pattern_root.rglob("memory*.json")))
    return [path for path in candidates if path.is_file()]


def iter_json_objects(path: Path) -> Iterable[Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix == ".json":
        try:
            yield json.loads(text)
        except json.JSONDecodeError:
            return
        return
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def forbidden_key_paths(payload: Any, *, prefix: str = "") -> list[str]:
    offenders: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in FORBIDDEN_MEMORY_KEYS:
                offenders.append(path)
            offenders.extend(forbidden_key_paths(value, prefix=path))
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            path = f"{prefix}[{index}]"
            offenders.extend(forbidden_key_paths(item, prefix=path))
    return offenders


def private_phrase_hashes(settings: CoachSettings) -> dict[str, list[dict[str, str]]]:
    sources: list[tuple[str, str]] = []
    for path in iter_indexable_files(settings.corpus_dir):
        sources.append((path.name, load_corpus_document(path).text))
    if settings.eval_manifest_path.exists():
        manifest = json.loads(settings.eval_manifest_path.read_text(encoding="utf-8"))
        for item in manifest.get("items", []):
            eval_path = settings.eval_questions_dir / str(item["source_file"])
            if eval_path.exists():
                sources.append((str(item["source_file"]), read_eval_text(eval_path)))
    return phrase_hashes(sources)


def scan_memory_artifacts(
    paths: Iterable[Path],
    *,
    private_phrases: dict[str, list[dict[str, str]]] | None = None,
) -> list[str]:
    offenders: list[str] = []
    phrase_rows = private_phrases or {}
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for payload in iter_json_objects(path):
            for key_path in forbidden_key_paths(payload):
                offenders.append(f"{path} contains forbidden memory key {key_path}")
        normalized = normalized_text(text)
        for phrase, matches in phrase_rows.items():
            if phrase in normalized:
                phrase_refs = ", ".join(
                    f"{match['source_file']}:{match['phrase_hash']}" for match in matches
                )
                offenders.append(f"{path} matched private phrase {phrase_refs}")
    return sorted(set(offenders))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()

    settings = CoachSettings.from_env()
    paths = [path for path in args.paths if path.exists()]
    if not paths and not args.paths:
        paths = iter_default_memory_artifacts(settings)
    if not paths:
        print("no memory artifacts found; memory leak scan passed")
        return

    offenders = scan_memory_artifacts(
        paths,
        private_phrases=private_phrase_hashes(settings),
    )
    if offenders:
        raise SystemExit("memory leak detected: " + "; ".join(offenders))
    print(f"no raw memory leaks detected ({len(paths)} artifact(s) scanned)")


if __name__ == "__main__":
    main()
