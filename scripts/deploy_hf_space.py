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
    "scripts/space_startup_check.py",
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
    "GENACADEMY_COACH_AUTH_ENABLED": "true",
    "GENACADEMY_COACH_DATA_DIR": "/data",
    "GENACADEMY_COACH_TRACE_DIR": "/data/traces",
    "GENACADEMY_COACH_REVIEW_QUEUE_PATH": "/data/review_queue.jsonl",
    "GENACADEMY_DATA_DIR": "/data",
    "GENACADEMY_VECTORSTORE": "pinecone",
    "GENACADEMY_PINECONE_INDEX": "genacademy-coach",
    # Keep these aligned with the Week-2 PineconeStore defaults unless the hosted
    # index is deliberately created in a different serverless region.
    "GENACADEMY_PINECONE_CLOUD": "aws",
    "GENACADEMY_PINECONE_REGION": "us-east-1",
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


def _require_auth_seed_passwords_when_enabled() -> None:
    auth_enabled = _bool_from_env(
        "GENACADEMY_COACH_AUTH_ENABLED",
        default=SPACE_VARIABLES["GENACADEMY_COACH_AUTH_ENABLED"] == "true",
    )
    if not auth_enabled:
        return
    missing = [
        name
        for name in ("GENACADEMY_SEED_ADMIN_PASSWORD", "GENACADEMY_SEED_MEMBER_PASSWORD")
        if not os.environ.get(name)
    ]
    if missing:
        raise SystemExit(
            "auth-enabled deploy requires secret seed passwords: " + ", ".join(missing)
        )


def main() -> None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is required")
    _require_auth_seed_passwords_when_enabled()

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

    secret_statuses = {}
    secret_names = (
        "NEBIUS_API_KEY",
        "PINECONE_API_KEY",
        "GENACADEMY_SEED_ADMIN_PASSWORD",
        "GENACADEMY_SEED_MEMBER_PASSWORD",
        "MEM0_API_KEY",
        "GENACADEMY_COACH_MEMORY_USER_SALT",
    )
    for secret_name in secret_names:
        secret_value = os.environ.get(secret_name)
        if secret_value:
            api.add_space_secret(repo_id, secret_name, secret_value)
            secret_statuses[secret_name] = "set"
        else:
            secret_statuses[secret_name] = "skipped"

    commit = api.upload_folder(
        repo_id=repo_id,
        repo_type="space",
        folder_path=Path.cwd(),
        allow_patterns=ALLOW_PATTERNS,
        ignore_patterns=IGNORE_PATTERNS,
        delete_patterns=["src/**/__pycache__/**", "src/**/*.pyc"],
        commit_message="Deploy GenAcademy Coach Space wrapper",
    )
    # Factory reboot can wipe persistent `/data` storage. Keep it opt-in for the
    # rare case where the operator deliberately wants a clean Space runtime.
    factory_reboot = _bool_from_env("GENACADEMY_HF_FACTORY_REBOOT", default=False)
    api.restart_space(repo_id, factory_reboot=factory_reboot)

    print(f"space={repo_url}")
    print(f"commit={commit.oid}")
    print(f"private={private}")
    print(f"factory_reboot={factory_reboot}")
    for secret_name in secret_names:
        print(f"secret_{secret_name}={secret_statuses[secret_name]}")
    print("uploaded=deployment allow-list only")


if __name__ == "__main__":
    main()
