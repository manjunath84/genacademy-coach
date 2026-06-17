# Hugging Face Deployment Plan

## Goal

Deploy GenAcademy Coach to Hugging Face Spaces and smoke-test it live without weakening the current
grounding, privacy, or held-out eval boundaries.

Formal implementation plan: `docs/superpowers/plans/2026-06-16-hugging-face-coach-deploy.md`.

## Current Reality

The Week 2 `genacademy-rag` project already has a Hugging Face deployment pattern:

- Docker Space.
- Root `Dockerfile`.
- `scripts/start_hf_space.sh`.
- app runs on `0.0.0.0:${PORT:-7860}`.
- secrets and variables are configured in Hugging Face Space settings.
- private data is not committed.

GenAcademy Coach is different today: it is a pure core plus CLI scripts, not a web app. That is good for
testing and the Week 3 demo, but Hugging Face Spaces needs an interactive surface or server process.

## Current Hugging Face Spaces Facts Checked

Current Hugging Face docs confirm:

- A Gradio Space can run from an `app.py` file at the repository root.
- Python dependencies belong in `requirements.txt`.
- Docker Spaces can expose port `7860`.
- Secrets and variables should be configured in Space settings, not hard-coded.
- For non-static Spaces, secrets and variables are exposed to the app as environment variables.

## Recommended Deployment Path

Use the Week 2 Docker pattern, but add only a thin Coach view:

1. Add a tiny Gradio or FastAPI wrapper outside the core.
2. Keep `src/genacademy_coach/*` free of web-framework imports.
3. Run the same retrieval/teach/quiz core through the wrapper.
4. Store data under a deploy data directory such as `/data`.
5. Configure provider secrets in the Space settings.
6. Smoke-test with a public demo topic only.

The smallest useful first live surface is Gradio:

- Topic text input.
- Teaching style dropdown.
- Track lens dropdown.
- Learner-answer textbox.
- "Run teach session" button.
- Safe output: learner message plus redacted metadata summary.
- Optional "Run quiz" tab after teach works.

Do not expose raw trace JSON in the UI.

## Files The Implementation Slice Should Add

Planned files:

- `app.py` or `src/genacademy_coach/web/gradio_app.py` for the thin Space UI.
- `Dockerfile` if using a Docker Space.
- `.dockerignore`.
- `scripts/start_hf_space.sh`.
- `docs/hugging-face-deployment-plan.md` updates with the actual Space URL and smoke result.
- tests that assert no web-framework imports enter the core.

If using non-Docker Gradio instead, add:

- `app.py`.
- `requirements.txt` generated from the lockfile.
- Hugging Face README metadata for `sdk: gradio`.

## Required Space Settings

Secrets:

- `NEBIUS_API_KEY`
- `HF_TOKEN` only if needed for private model/cache access
- optional `LANGSMITH_API_KEY` only if tracing is enabled

Variables:

- `GENACADEMY_PROVIDER=nebius`
- `NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/`
- `NEBIUS_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507`
- `GENACADEMY_COACH_STOP_THRESHOLD=0.40`
- `GENACADEMY_COACH_CONFIRM_THRESHOLD=0.85`
- `GENACADEMY_COACH_COLLECTION=coach_course`
- `GENACADEMY_COACH_SOURCE_PRIORITY=slide,handout,note,transcript`
- `GENACADEMY_EMBEDDINGS=local`
- `GENACADEMY_EMBED_MODEL=all-MiniLM-L6-v2`
- `GENACADEMY_RERANK_ENABLED=false`

Do not put `.env` in the Space repository.

## Data And Corpus Boundary

Private course material remains local-only unless explicitly approved for the Space. Before deployment,
choose one of these:

1. **Demo-safe public subset**: include only non-private, approved demo snippets.
2. **Private Space**: deploy as a private Space and upload corpus artifacts through a controlled path.
3. **No corpus upload yet**: deploy the UI shell and show refusal behavior until data seeding is
   approved.

For the final public submission, the safest path is a demo-safe public subset or no public Space data.
Do not upload held-out `corpus/eval-questions`.

## Smoke Test Plan

Local container smoke:

1. Build the image.
2. Run it with environment variables.
3. Open `http://127.0.0.1:7860`.
4. Run topic `agent harness`.
5. Confirm the UI returns either a grounded response with citation metadata or a safe refusal.

Live Space smoke:

1. Open `https://huggingface.co/spaces/<user>/<space>`.
2. Use public demo topic `agent harness`.
3. Verify no raw trace/corpus/eval text is exposed.
4. Verify the app does not print secrets in logs.
5. Record the Space URL and result here before merge.

## Acceptance Criteria

- Space boots without requiring local `.env`.
- No direct web-framework imports inside the core modules.
- No private corpus/eval text is committed or displayed.
- Public demo topic works or safely refuses.
- `scripts/check_eval_leak.py` passes after deployment files are added.
- README/roadmap record the Space URL and known limitations.

## Open Decision Before Code

Pick one deployment target:

1. **Gradio Space, non-Docker**: fastest if dependency install works cleanly from `requirements.txt`;
   weaker parity with Week 2.
2. **Docker Space**: closest to Week 2; better control over `uv`, cache dirs, and boot commands; slightly
   more setup.
3. **Private Space first**: safest if using private course corpus; less useful as a public demo link.

Recommendation: Docker Space first, reusing the Week 2 deployment pattern, unless speed matters more
than parity. Use a minimal Gradio UI inside Docker so the Space has something visual to test.
