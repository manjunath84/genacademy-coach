from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ALLOWED_SOURCE_TYPES = frozenset({"slide", "handout", "note", "transcript"})
DEFAULT_SOURCE_PRIORITY = ("slide", "handout", "note", "transcript")
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]


def _source_priority_from_env() -> tuple[str, ...]:
    raw = os.environ.get("GENACADEMY_COACH_SOURCE_PRIORITY")
    if raw is None:
        return DEFAULT_SOURCE_PRIORITY
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    unknown = sorted(set(values) - ALLOWED_SOURCE_TYPES)
    if unknown:
        message = "unknown source_type values in GENACADEMY_COACH_SOURCE_PRIORITY: "
        raise ValueError(message + ", ".join(unknown))
    duplicates = sorted({item for item in values if values.count(item) > 1})
    if duplicates:
        message = "duplicate source_type values in GENACADEMY_COACH_SOURCE_PRIORITY: "
        raise ValueError(message + ", ".join(duplicates))
    return values or DEFAULT_SOURCE_PRIORITY


@dataclass(frozen=True)
class CoachSettings:
    repo_root: Path
    data_dir: Path
    chroma_dir: Path
    sqlite_path: Path
    corpus_dir: Path
    eval_questions_dir: Path
    eval_dir: Path
    eval_manifest_path: Path
    review_queue_path: Path
    course_collection: str = "coach_course"
    retrieval_top_k: int = 5
    retrieval_candidate_k: int = 20
    source_priority: tuple[str, ...] = DEFAULT_SOURCE_PRIORITY

    @classmethod
    def from_env(cls) -> CoachSettings:
        repo_root = Path(os.environ.get("GENACADEMY_COACH_ROOT", DEFAULT_REPO_ROOT)).resolve()
        eval_dir = repo_root / "eval"
        data_dir = Path(os.environ.get("GENACADEMY_COACH_DATA_DIR", repo_root / "data")).resolve()
        sqlite_filename = os.environ.get(
            "GENACADEMY_COACH_SQLITE_FILENAME",
            "genacademy-coach.sqlite",
        )
        return cls(
            repo_root=repo_root,
            data_dir=data_dir,
            chroma_dir=(data_dir / "chroma").resolve(),
            sqlite_path=(data_dir / sqlite_filename).resolve(),
            corpus_dir=Path(
                os.environ.get("GENACADEMY_COACH_CORPUS_DIR", repo_root / "corpus")
            ).resolve(),
            eval_questions_dir=Path(
                os.environ.get(
                    "GENACADEMY_COACH_EVAL_QUESTIONS_DIR",
                    repo_root / "corpus" / "eval-questions",
                )
            ).resolve(),
            eval_dir=eval_dir,
            eval_manifest_path=eval_dir / "split_manifest.json",
            review_queue_path=repo_root / "review_queue.jsonl",
            course_collection=os.environ.get("GENACADEMY_COACH_COLLECTION", "coach_course"),
            retrieval_top_k=int(os.environ.get("GENACADEMY_COACH_TOP_K", "5")),
            retrieval_candidate_k=int(os.environ.get("GENACADEMY_COACH_CANDIDATE_K", "20")),
            source_priority=_source_priority_from_env(),
        )
