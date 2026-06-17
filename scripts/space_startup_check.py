from __future__ import annotations

import logging
import os

from genacademy_coach.foundation import build_course_vectorstore, rag_settings_for_coach
from genacademy_coach.settings import CoachSettings

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("genacademy_coach.space_startup")


def main() -> None:
    settings = CoachSettings.from_env()
    rag_settings = rag_settings_for_coach(settings)
    store = build_course_vectorstore(settings, rag_settings)
    chunks = store.get_all_chunks()
    logger.info(
        "startup corpus check: vectorstore=%s collection=%s chroma_dir=%s chunks=%d",
        rag_settings.vectorstore,
        settings.course_collection,
        settings.chroma_dir,
        len(chunks),
    )
    if not chunks:
        logger.warning(
            "startup corpus check: no chunks found; the Space will safely refuse corpus-backed "
            "requests until an approved index is available in the active vectorstore"
        )
    if os.environ.get("NEBIUS_API_KEY"):
        logger.info("startup provider check: NEBIUS_API_KEY is configured")
    else:
        logger.warning("startup provider check: NEBIUS_API_KEY is not configured")


if __name__ == "__main__":
    main()
