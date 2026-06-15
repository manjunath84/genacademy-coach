from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

NORMALIZED_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.(docx|pdf|txt|md)$")
WORD_RE = re.compile(r"[a-z0-9]+")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def assert_normalized_eval_filename(path: Path) -> None:
    if NORMALIZED_RE.match(path.name) is None:
        raise ValueError(
            f"{path.name!r} must be lowercase kebab-case before splitting held-out eval files"
        )


def build_file_items(eval_dir: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for path in sorted(eval_dir.iterdir()):
        if not path.is_file() or path.name.startswith(".") or path.name == "README.md":
            continue
        assert_normalized_eval_filename(path)
        digest = sha256_file(path)
        items.append(
            {
                "id": hashlib.sha256(f"{path.name}:{digest}".encode()).hexdigest()[:16],
                "source_file": path.name,
                "source_sha256": digest,
            }
        )
    if len({item["id"] for item in items}) != len(items):
        raise ValueError("duplicate eval item IDs after hashing")
    return items


def split_items(items: list[dict[str, str]], *, seed: str) -> list[dict[str, str]]:
    rows = []
    for item in sorted(items, key=lambda row: row["id"]):
        bucket = int(hashlib.sha256(f"{seed}:{item['id']}".encode()).hexdigest(), 16) % 100
        if bucket < 33:
            split = "test"
        elif bucket < 66:
            split = "dev"
        else:
            split = "seed"
        rows.append({**item, "split": split})
    return rows


def normalized_words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def ngrams(text: str, *, n: int = 8) -> set[str]:
    words = normalized_words(text)
    return {" ".join(words[i : i + n]) for i in range(0, max(0, len(words) - n + 1))}


def phrase_hashes(sources: list[tuple[str, str]], *, n: int = 8) -> dict[str, list[dict[str, str]]]:
    rows: dict[str, list[dict[str, str]]] = {}
    for source_file, text in sources:
        for phrase in ngrams(text, n=n):
            rows.setdefault(phrase, []).append(
                {
                    "source_file": source_file,
                    "phrase_hash": hashlib.sha256(phrase.encode("utf-8")).hexdigest()[:12],
                }
            )
    return rows


def write_manifest(eval_dir: Path, manifest_path: Path, *, seed: str) -> dict[str, object]:
    rows = split_items(build_file_items(eval_dir), seed=seed)
    manifest = {
        "version": 1,
        "seed": seed,
        "items": rows,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(payload, encoding="utf-8")
    return manifest
