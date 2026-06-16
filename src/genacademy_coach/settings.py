from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ALLOWED_SOURCE_TYPES = frozenset({"slide", "handout", "note", "transcript"})
DEFAULT_SOURCE_PRIORITY = ("slide", "handout", "note", "transcript")
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STOP_THRESHOLD = 0.40
DEFAULT_CONFIRM_THRESHOLD = 0.85


def _env_value(name: str, default: str | Path) -> str | Path:
    raw = os.environ.get(name)
    return default if raw is None or not raw.strip() else raw


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
    trace_dir: Path
    course_collection: str = "coach_course"
    retrieval_top_k: int = 5
    retrieval_candidate_k: int = 20
    source_priority: tuple[str, ...] = DEFAULT_SOURCE_PRIORITY
    stop_threshold: float = DEFAULT_STOP_THRESHOLD
    confirm_threshold: float = DEFAULT_CONFIRM_THRESHOLD
    max_teach_turns: int = 4

    @classmethod
    def from_env(cls) -> CoachSettings:
        repo_root = Path(_env_value("GENACADEMY_COACH_ROOT", DEFAULT_REPO_ROOT)).resolve()
        eval_dir = repo_root / "eval"
        data_dir = Path(_env_value("GENACADEMY_COACH_DATA_DIR", repo_root / "data")).resolve()
        sqlite_filename = _env_value(
            "GENACADEMY_COACH_SQLITE_FILENAME",
            "genacademy-coach.sqlite",
        )
        return cls(
            repo_root=repo_root,
            data_dir=data_dir,
            chroma_dir=(data_dir / "chroma").resolve(),
            sqlite_path=(data_dir / sqlite_filename).resolve(),
            corpus_dir=Path(
                _env_value("GENACADEMY_COACH_CORPUS_DIR", repo_root / "corpus")
            ).resolve(),
            eval_questions_dir=Path(
                _env_value(
                    "GENACADEMY_COACH_EVAL_QUESTIONS_DIR",
                    repo_root / "corpus" / "eval-questions",
                )
            ).resolve(),
            eval_dir=eval_dir,
            eval_manifest_path=eval_dir / "split_manifest.json",
            review_queue_path=repo_root / "review_queue.jsonl",
            trace_dir=Path(
                _env_value("GENACADEMY_COACH_TRACE_DIR", repo_root / "traces")
            ).resolve(),
            course_collection=os.environ.get("GENACADEMY_COACH_COLLECTION", "coach_course"),
            retrieval_top_k=int(os.environ.get("GENACADEMY_COACH_TOP_K", "5")),
            retrieval_candidate_k=int(os.environ.get("GENACADEMY_COACH_CANDIDATE_K", "20")),
            source_priority=_source_priority_from_env(),
            stop_threshold=float(
                os.environ.get(
                    "GENACADEMY_COACH_STOP_THRESHOLD",
                    str(DEFAULT_STOP_THRESHOLD),
                )
            ),
            confirm_threshold=float(
                os.environ.get(
                    "GENACADEMY_COACH_CONFIRM_THRESHOLD",
                    str(DEFAULT_CONFIRM_THRESHOLD),
                )
            ),
            max_teach_turns=int(os.environ.get("GENACADEMY_COACH_MAX_TURNS", "4")),
        )
