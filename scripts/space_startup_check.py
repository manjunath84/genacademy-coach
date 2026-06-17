from __future__ import annotations

import logging
import os

from genacademy_rag.core.vectorstore import ChromaStore

from genacademy_coach.settings import CoachSettings

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("genacademy_coach.space_startup")


def main() -> None:
    settings = CoachSettings.from_env()
    store = ChromaStore(persist_dir=settings.chroma_dir, collection=settings.course_collection)
    chunks = store.get_all_chunks()
    logger.info(
        "startup corpus check: collection=%s chroma_dir=%s chunks=%d",
        settings.course_collection,
        settings.chroma_dir,
        len(chunks),
    )
    if not chunks:
        logger.warning(
            "startup corpus check: no chunks found; the Space will safely refuse corpus-backed "
            "requests until an approved index is available under /data"
        )
    if os.environ.get("NEBIUS_API_KEY"):
        logger.info("startup provider check: NEBIUS_API_KEY is configured")
    else:
        logger.warning("startup provider check: NEBIUS_API_KEY is not configured")


if __name__ == "__main__":
    main()
