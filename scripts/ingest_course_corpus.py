import json

from genacademy_coach.corpus import (
    extraction_summary,
    iter_indexable_files,
    load_corpus_document_with_stats,
)
from genacademy_coach.foundation import Foundation
from genacademy_coach.settings import CoachSettings


def refuse_empty_extractions(report: list[dict[str, object]]) -> None:
    empty = [row for row in report if row["empty"]]
    if empty:
        titles = ", ".join(str(row["title"]) for row in empty)
        raise SystemExit(f"refusing to ingest empty extracted documents: {titles}")


def main() -> None:
    settings = CoachSettings.from_env()
    files = iter_indexable_files(settings.corpus_dir)
    loaded = [load_corpus_document_with_stats(path) for path in files]
    docs = [item.document for item in loaded]
    report = [
        extraction_summary(item.document, slide_shape_count=item.slide_shape_count)
        for item in loaded
    ]
    settings.eval_dir.mkdir(parents=True, exist_ok=True)
    extraction_path = settings.eval_dir / "extraction_report.json"
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    extraction_path.write_text(payload, encoding="utf-8")
    refuse_empty_extractions(report)
    foundation = Foundation.build(settings)
    n_chunks = foundation.ingest(docs)
    print(
        f"ingested {len(docs)} docs -> {n_chunks} chunks into "
        f"collection={settings.course_collection}; "
        f"extraction report={extraction_path}"
    )


if __name__ == "__main__":
    main()
