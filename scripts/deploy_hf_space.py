from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import HfApi

DEFAULT_SPACE_ID = "Manjunath84/genacademy-coach"

ALLOW_PATTERNS = [
    ".dockerignore",
    "Dockerfile",
    "app.py",
    "pyproject.toml",
    "uv.lock",
    "scripts/start_hf_space.sh",
    "src/**",
]
IGNORE_PATTERNS = [
    ".env",
    ".env*",
    ".git/**",
    ".kimchi/**",
    ".pytest_cache/**",
    ".ruff_cache/**",
    ".venv/**",
    "__pycache__/**",
    "**/__pycache__/**",
    "*.pyc",
    "**/*.pyc",
    "corpus/**",
    "data/**",
    "eval/**",
    "review_queue.jsonl",
    "tmp/**",
    "traces/**",
]

SPACE_VARIABLES = {
    "GENACADEMY_PROVIDER": "nebius",
    "NEBIUS_BASE_URL": "https://api.tokenfactory.nebius.com/v1/",
    "NEBIUS_MODEL": "Qwen/Qwen3-30B-A3B-Instruct-2507",
    "GENACADEMY_COACH_STOP_THRESHOLD": "0.40",
    "GENACADEMY_COACH_CONFIRM_THRESHOLD": "0.85",
    "GENACADEMY_COACH_COLLECTION": "coach_course",
    "GENACADEMY_COACH_SOURCE_PRIORITY": "slide,handout,note,transcript",
    "GENACADEMY_COACH_DATA_DIR": "/data",
    "GENACADEMY_COACH_TRACE_DIR": "/data/traces",
    "GENACADEMY_COACH_REVIEW_QUEUE_PATH": "/data/review_queue.jsonl",
    "GENACADEMY_DATA_DIR": "/data",
    "GENACADEMY_EMBEDDINGS": "local",
    "GENACADEMY_EMBED_MODEL": "all-MiniLM-L6-v2",
    "GENACADEMY_EMBED_DIM": "384",
    "GENACADEMY_RERANK_ENABLED": "false",
}


def _bool_from_env(name: str, *, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is required")

    repo_id = os.environ.get("GENACADEMY_HF_SPACE_ID", DEFAULT_SPACE_ID)
    private = _bool_from_env("GENACADEMY_HF_SPACE_PRIVATE", default=True)
    api = HfApi(token=token)
    repo_url = api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        private=private,
        exist_ok=True,
    )

    for key, default in SPACE_VARIABLES.items():
        api.add_space_variable(repo_id, key, os.environ.get(key, default))

    nebius_key = os.environ.get("NEBIUS_API_KEY")
    if nebius_key:
        api.add_space_secret(repo_id, "NEBIUS_API_KEY", nebius_key)

    commit = api.upload_folder(
        repo_id=repo_id,
        repo_type="space",
        folder_path=Path.cwd(),
        allow_patterns=ALLOW_PATTERNS,
        ignore_patterns=IGNORE_PATTERNS,
        delete_patterns=["src/**/__pycache__/**", "src/**/*.pyc"],
        commit_message="Deploy GenAcademy Coach Space wrapper",
    )
    api.restart_space(repo_id, factory_reboot=True)

    print(f"space={repo_url}")
    print(f"commit={commit.oid}")
    print(f"private={private}")
    print("uploaded=deployment allow-list only")


if __name__ == "__main__":
    main()
