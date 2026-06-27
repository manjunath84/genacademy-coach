import json
from collections.abc import Iterator
from pathlib import Path

from genacademy_coach.corpus import iter_indexable_files, load_corpus_document
from genacademy_coach.eval_io import read_eval_text
from genacademy_coach.eval_split import normalized_words, phrase_hashes
from genacademy_coach.settings import CoachSettings

SCAN_GLOBS = [
    "AGENTS.md",
    "README.md",
    "docs/**/*.md",
    "docs/**/*.json",
    "specs/**/*.md",
    "src/**/*.py",
    "scripts/**/*.py",
]

GOLDEN_INLINE_FIELDS = ("user_query", "initial_wrong_answer", "expected_answer", "answer_text")


def normalized_text(text: str) -> str:
    return " ".join(normalized_words(text))


def scan_golden_cases(
    path: Path,
    *,
    test_needles: set[str],
    test_phrases: dict[str, list[dict[str, str]]],
) -> list[str]:
    if not path.exists():
        return []

    offenders: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        case_id = str(row.get("case_id") or f"line {line_number}")
        prefix = f"{path}:{line_number} {case_id}"

        if row.get("split") == "test":
            offenders.append(f"{prefix} uses forbidden test split")

        cloud_safe = bool(row.get("cloud_safe"))
        inline_values = [
            str(row.get(field) or "")
            for field in GOLDEN_INLINE_FIELDS
            if row.get(field)
        ]
        inline_text = "\n".join(inline_values)

        if cloud_safe and not str(row.get("cloud_safe_reason") or "").strip():
            offenders.append(f"{prefix} cloud_safe=true requires cloud_safe_reason")
        if not cloud_safe and inline_text:
            offenders.append(f"{prefix} cloud_safe=false carries inline text")

        for needle in test_needles:
            if needle and needle in inline_text:
                offenders.append(f"{prefix} inline text contains test needle {needle}")

        normalized = normalized_text(inline_text)
        for phrase, matches in test_phrases.items():
            if phrase and phrase in normalized:
                phrase_refs = ", ".join(
                    f"{match['source_file']}:{match['phrase_hash']}" for match in matches
                )
                offenders.append(f"{prefix} matched eval phrase {phrase_refs}")

    return offenders


def iter_committed_scan_texts(settings: CoachSettings) -> Iterator[tuple[Path, str]]:
    for pattern in SCAN_GLOBS:
        for path in settings.repo_root.glob(pattern):
            if path.is_file():
                yield path, path.read_text(encoding="utf-8", errors="ignore")


def iter_local_corpus_scan_texts(settings: CoachSettings) -> Iterator[tuple[Path, str]]:
    for path in iter_indexable_files(settings.corpus_dir):
        yield path, load_corpus_document(path).text


def collect_eval_phrase_sources(
    eval_questions_dir: Path,
    test_items: list[dict[str, object]],
) -> tuple[list[tuple[str, str]], list[str]]:
    phrase_sources: list[tuple[str, str]] = []
    unscanned_sources: list[str] = []
    for item in test_items:
        source_file = str(item["source_file"])
        eval_path = eval_questions_dir / source_file
        if not eval_path.exists():
            unscanned_sources.append(source_file)
            continue
        text = read_eval_text(eval_path)
        if not text.strip():
            unscanned_sources.append(f"{source_file} (no extractable text)")
            continue
        phrase_sources.append((source_file, text))
    return phrase_sources, unscanned_sources


def main() -> None:
    settings = CoachSettings.from_env()
    if not settings.eval_manifest_path.exists():
        raise SystemExit(f"missing eval manifest: {settings.eval_manifest_path}")
    manifest = json.loads(settings.eval_manifest_path.read_text(encoding="utf-8"))
    test_items = [item for item in manifest["items"] if item["split"] == "test"]
    needles = {item["id"] for item in test_items} | {item["source_sha256"] for item in test_items}
    offenders: list[str] = []
    eval_phrase_sources, unscanned_eval_sources = collect_eval_phrase_sources(
        settings.eval_questions_dir,
        test_items,
    )
    test_phrase_hashes = phrase_hashes(eval_phrase_sources)
    scan_texts = list(iter_committed_scan_texts(settings))
    offenders.extend(
        scan_golden_cases(
            settings.eval_dir / "golden" / "golden_cases.jsonl",
            test_needles=needles,
            test_phrases=test_phrase_hashes,
        )
    )

    # This direct scan is deliberately simple and adequate for current corpus size. If the corpus
    # grows to thousands of files, replace it with trie/Aho-Corasick matching before making
    # it CI-hard.
    if test_phrase_hashes:
        scan_texts.extend(iter_local_corpus_scan_texts(settings))
    for path, text in scan_texts:
        if any(needle in text for needle in needles):
            offenders.append(str(path))
        normalized = normalized_text(text)
        for phrase, matches in test_phrase_hashes.items():
            if phrase in normalized:
                phrase_refs = ", ".join(
                    f"{match['source_file']}:{match['phrase_hash']}" for match in matches
                )
                offenders.append(f"{path} matched eval phrase {phrase_refs}")
    if offenders:
        raise SystemExit("eval test leak detected in: " + ", ".join(sorted(set(offenders))))
    if unscanned_eval_sources:
        print(
            "private eval sources unavailable; skipped local n-gram leak scan for: "
            + ", ".join(sorted(unscanned_eval_sources))
        )
    print(
        "no eval test IDs/checksums found in code/docs; no eval n-grams found where "
        "private eval sources were available "
        f"({len(test_items)} test items)"
    )


if __name__ == "__main__":
    main()
