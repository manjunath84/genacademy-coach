# Hugging Face Coach Deploy Implementation Plan

> Status: implementation in progress. PR #19 adds the thin Gradio/Docker wrapper, local Docker smoke,
> and private Hugging Face Space HTTP smoke. Provider/corpus-backed Space click smoke remains pending
> because no private corpus/index is uploaded.

## Goal

Deploy GenAcademy Coach to Hugging Face Spaces with a minimal interactive UI and verify it with a live
smoke test, while preserving the current privacy, grounding, and pure-core boundaries.

## Source Checks

- Current Hugging Face docs: Gradio Spaces run from a root `app.py`; dependencies are declared in
  `requirements.txt`; secrets and variables are configured in Space settings and exposed as environment
  variables.
- Week 2 reference: `genacademy-rag` deployed through a Docker Space with `Dockerfile`,
  `scripts/start_hf_space.sh`, `/data`, and port `7860`.
- Same-embedder rule: the deployed variables must match the uploaded Chroma collection:
  `GENACADEMY_EMBED_MODEL=all-MiniLM-L6-v2` and `GENACADEMY_EMBED_DIM=384`.
- Local Docker verification found that Linux `torch` must be routed to the PyTorch CPU index; otherwise
  the build pulls CUDA/NVIDIA wheels and becomes too large for practical CPU Space iteration.

## Key Decision

Use a Docker Space with a minimal Gradio UI unless review recommends otherwise.

Why:

- It reuses the known Week 2 deployment model.
- It keeps dependency and cache behavior under `uv` control.
- It avoids committing `.env`.
- Gradio gives enough UI to "see how it works" without introducing a full web app.

## Scope

In scope:

- Thin Gradio UI outside the core.
- Docker Space packaging.
- Space secrets/variables documentation.
- Local smoke check.
- Live Space HTTP smoke check.
- Provider/corpus-backed Space click smoke after a public-safe corpus/index decision.
- README/roadmap update with URL and limitations after smoke.

Out of scope:

- Cross-session memory.
- Admin auth/upload.
- Public upload of private corpus.
- Direct `langgraph.*` imports.
- Rebuilding Week 2 retrieval/storage.

## Guardrails

- No web-framework or Gradio imports inside `src/genacademy_coach` core modules unless isolated under a
  dedicated view/web boundary.
- No private corpus or held-out eval files committed to the Space repo.
- No `.env` committed.
- UI outputs only learner-facing text plus redacted metadata summaries.
- Trace files remain local/gitignored; do not display raw trace JSON.
- If no citeable corpus is available in the Space, the app must refuse rather than answer from priors.

## Planned Files

- `app.py` or `src/genacademy_coach/web/gradio_app.py` — thin UI wrapper.
- `Dockerfile`.
- `.dockerignore`.
- `scripts/start_hf_space.sh`.
- `docs/hugging-face-deployment-plan.md` — update with actual URL and smoke result.
- Tests:
  - deploy file presence/metadata
  - no web imports in core
  - UI wrapper returns redacted metadata only for a fake session

## Implementation Tasks

### Task 1 — Pick Deploy Shape

- Confirm Docker Space vs non-Docker Gradio.
- If Docker: mirror Week 2's `uv` base image and `PORT:-7860`.
- If non-Docker: generate pinned `requirements.txt` and keep app startup simple.

### Task 2 — Thin UI Wrapper

- Add one screen for Teach Mode:
  - topic
  - style
  - track lens
  - optional learner answer
  - safe response panel
  - redacted metadata panel
- Add Quiz Mode only if Teach Mode smoke is already green.

### Task 3 — Deployment Packaging

- Add Docker/Space files.
- Configure `GENACADEMY_COACH_DATA_DIR=/data` for Coach-owned files and `GENACADEMY_DATA_DIR=/data`
  for the reused Week 2 RAG layer when it needs a deploy data root.
- Configure `GENACADEMY_COACH_TRACE_DIR=/data/traces` and
  `GENACADEMY_COACH_REVIEW_QUEUE_PATH=/data/review_queue.jsonl` so runtime writes do not depend on
  the repository checkout being writable.
- Document required secrets and variables.
- Do not include private corpus.

### Task 4 — Local Smoke

- Build/run locally.
- Use public topic `agent harness`.
- Verify grounded response or safe refusal.
- Verify no secrets/raw traces in output.

### Task 5 — Live Space Smoke

- Push to Hugging Face Space.
- Configure secrets/variables.
- Open the URL.
- Run public topic `agent harness`.
- Record URL, result, and limitations in README/roadmap/deploy doc.

## Acceptance Criteria

- Space boots.
- Runtime write paths for data, traces, and review queue stay under `/data`.
- Embed model and dimension match the uploaded collection (`all-MiniLM-L6-v2` / `384`).
- Docker build uses CPU-only `torch` on Linux; no CUDA/NVIDIA packages appear in `uv.lock`.
- The private Space URL returns HTTP 200.
- The UI can run a public demo topic or safely refuse after a public-safe corpus/index decision.
- No private corpus/eval text is committed or displayed.
- No held-out `test` split use.
- `uv run pytest -q`, `uv run ruff check .`, `git diff --check`, and
  `uv run python scripts/check_eval_leak.py` pass.
- A different model/fresh context reviews the deploy PR before merge.

## Open Questions For Review

1. Should the first Space be private until corpus handling is decided?
2. Should the first deploy intentionally show safe refusal only, or include a small approved public demo
   corpus subset?
3. Should Quiz Mode be exposed in the first Space, or held until Teach Mode is live-smoked?
