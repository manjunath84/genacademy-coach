"""Render every deck in corpus/slides/ to per-slide PNGs (gitignored store).

Usage: uv run python scripts/render_slide_images.py
Requires LibreOffice (`soffice`) and poppler (`pdftoppm`) on PATH.
Re-run whenever the decks change (store is keyed by content-hashed doc_id).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from genacademy_coach.corpus import build_doc_id
from genacademy_coach.settings import CoachSettings
from genacademy_coach.slide_images import safe_doc_dirname, slide_store_dir

_PAGE_SUFFIX = re.compile(r"-0*(\d+)\.png$")


def render_deck(deck: Path, store: Path) -> int:
    raw = deck.read_bytes()
    doc_id = f"slide/{build_doc_id(deck, raw)}"
    out_dir = store / safe_doc_dirname(doc_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", str(deck), "--outdir", tmp],
            check=True,
            capture_output=True,
        )
        pdf = next(Path(tmp).glob("*.pdf"))
        subprocess.run(
            ["pdftoppm", "-png", "-r", "110", str(pdf), str(Path(tmp) / "page")],
            check=True,
            capture_output=True,
        )
        count = 0
        for png in sorted(Path(tmp).glob("page-*.png")):
            match = _PAGE_SUFFIX.search(png.name)
            if not match:
                continue
            shutil.copy2(png, out_dir / f"slide-{int(match.group(1))}.png")
            count += 1
    return count


def main() -> None:
    settings = CoachSettings.from_env()
    store = slide_store_dir(settings)
    decks = sorted(settings.corpus_dir.glob("slides/*.pptx"))
    if not decks:
        print(f"no decks found under {settings.corpus_dir}/slides")
        return
    for deck in decks:
        count = render_deck(deck, store)
        print(f"{deck.name}: {count} slides -> {store}")


if __name__ == "__main__":
    main()
