#!/usr/bin/env bash
set -euo pipefail

export GENACADEMY_COACH_DATA_DIR="${GENACADEMY_COACH_DATA_DIR:-/data}"
export GENACADEMY_DATA_DIR="${GENACADEMY_DATA_DIR:-/data}"
export GENACADEMY_COACH_TRACE_DIR="${GENACADEMY_COACH_TRACE_DIR:-/data/traces}"
export GENACADEMY_COACH_REVIEW_QUEUE_PATH="${GENACADEMY_COACH_REVIEW_QUEUE_PATH:-/data/review_queue.jsonl}"
export GENACADEMY_EMBED_DIM="${GENACADEMY_EMBED_DIM:-384}"

mkdir -p "${GENACADEMY_COACH_DATA_DIR}" "${GENACADEMY_DATA_DIR}" "${GENACADEMY_COACH_TRACE_DIR}"
uv run --no-sync python scripts/space_startup_check.py
exec uv run --no-sync python app.py
