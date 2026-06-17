from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")


def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_path, override=False)


_load_local_env()

from genacademy_coach.web.gradio_app import launch  # noqa: E402

if __name__ == "__main__":
    launch()
