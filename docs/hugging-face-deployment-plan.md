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

GenAcademy Coach started as a pure core plus CLI scripts. PR #19 adds a thin Gradio surface and Docker
packaging outside the core so Hugging Face Spaces has an interactive server process without changing the
teach/quiz engine.

Implementation status:

- Gradio wrapper added at `src/genacademy_coach/web/gradio_app.py` with root `app.py`.
- Docker Space packaging added with CPU-only PyTorch resolution to avoid CUDA-sized images.
- Docker build pins the Week 2 `genacademy-rag` dependency to commit
  `517faffbfdf37f8972f5bf3076e21eb2ab0ba7b4` instead of a moving branch.
- Startup logs the active vectorstore chunk count and warns when no indexed corpus is available.
- The Gradio page shows a deployment-shell banner when no approved corpus/index is loaded, so a cold
  visitor does not mistake safe refusals for a broken app.
- Local app launch smoke passed.
- Local Docker image build passed.
- Local Docker container smoke passed: `HTTP/1.1 200 OK` from `http://127.0.0.1:7863`.
- Live private Hugging Face Space push/smoke passed:
  `https://huggingface.co/spaces/Manjunath84/genacademy-coach`
  (`aefac2cf3d4c3f02eaac82c843071354777e7adc`, `HTTP/2 200` from the Gradio app).
- Post Skill-Gap UI redeploy passed on 2026-06-17:
  `dcdf92a3c7ceb46a22f691a0d0cd35666220b19c`, `factory_reboot=False`,
  `secret_NEBIUS_API_KEY=set`, allow-list upload only, authenticated root smoke `HTTP/2 200`.
- Hosted retrieval has an implemented Pinecone adapter through the reused Week-2 vectorstore factory:
  `GENACADEMY_VECTORSTORE=pinecone`, `GENACADEMY_PINECONE_INDEX=genacademy-coach`, and
  `GENACADEMY_COACH_COLLECTION=coach_course` as the namespace.
- Chroma remains the tested path for this submission until an approved hosted corpus/index is seeded
  and smoked end to end.
- Provider/corpus-backed click smoke is still pending because no approved corpus/index has been seeded
  for the Space.

## Shipped Hugging Face Space Shape

The shipped path is a private Docker Space with a root `app.py`, a thin Gradio wrapper outside the core,
and a Dockerfile-managed `uv` environment. Secrets and variables are configured in Hugging Face Space
settings, never hard-coded or committed.

## Deployment Path

The implementation uses the Week 2 Docker pattern, with only a thin Coach view:

1. Add a tiny Gradio wrapper outside the core.
2. Keep `src/genacademy_coach/*` free of web-framework imports.
3. Run the same retrieval/teach/quiz core through the wrapper.
4. Store data under `/data` by setting `GENACADEMY_COACH_DATA_DIR=/data` for Coach-owned files and
   `GENACADEMY_DATA_DIR=/data` for the reused Week 2 RAG layer when it needs a deploy data root.
   Trace and review-queue writes should also stay under `/data`.
5. Configure provider secrets in the Space settings.
6. Smoke-test with a public-safe sample topic only after an approved corpus/index decision.

The live surface is Gradio:

- Topic text input.
- Teaching style dropdown.
- Track lens dropdown.
- Learner-answer textbox.
- "Run teach session" button.
- Safe output: learner message plus redacted metadata summary.
- "Run quiz" tab for the grounded deterministic assessment pull-in.
- Deployment-shell banner when the active vectorstore has no approved index.

Do not expose raw trace JSON in the UI.

## Implemented Deployment Slice

Implemented files:

- `app.py` plus `src/genacademy_coach/web/gradio_app.py` for the thin Space UI.
- `Dockerfile` for a Docker Space.
- `.dockerignore`.
- `scripts/start_hf_space.sh`.
- tests that assert no web-framework imports enter the core and trace metadata stays redacted.
- tests that assert deploy restarts avoid factory reboot, error paths are redacted in the UI and logged
  server-side, malformed trace rows are skipped, and empty-corpus UX is explicit.

Completed deployment setup:

- private Hugging Face Space repo created/updated.
- deployment variables configured by `scripts/deploy_hf_space.py`.
- `NEBIUS_API_KEY` configured as a Space secret.
- `PINECONE_API_KEY` supported as a Space secret for the hosted vectorstore.
- local app, local Docker, and live private Space HTTP smokes passed.

Still pending before claiming provider/corpus-backed live behavior:

- approved decision on whether to seed the Coach-specific Pinecone index/namespace with approved corpus
  chunks.
- click smoke that exercises retrieval/provider calls against that approved hosted index.

## Required Space Settings

Secrets:

- `NEBIUS_API_KEY`
- `PINECONE_API_KEY` when `GENACADEMY_VECTORSTORE=pinecone`
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
- `GENACADEMY_COACH_DATA_DIR=/data`
- `GENACADEMY_COACH_TRACE_DIR=/data/traces`
- `GENACADEMY_COACH_REVIEW_QUEUE_PATH=/data/review_queue.jsonl`
- `GENACADEMY_DATA_DIR=/data`
- `GENACADEMY_VECTORSTORE=pinecone`
- `GENACADEMY_PINECONE_INDEX=genacademy-coach`
- `GENACADEMY_PINECONE_CLOUD=aws`
- `GENACADEMY_PINECONE_REGION=us-east-1`
- `GENACADEMY_EMBEDDINGS=local`
- `GENACADEMY_EMBED_MODEL=all-MiniLM-L6-v2`
- `GENACADEMY_EMBED_DIM=384`
- `GENACADEMY_RERANK_ENABLED=false`

Do not put `.env` in the Space repository.

Latency tuning note: keep Nebius as the default hosted provider for the Week-3 rubric path. For local
or private latency experiments, the inherited Week-2 provider surface also supports
`GENACADEMY_PROVIDER=openrouter` with `OPENROUTER_MODEL=openai/gpt-4.1-nano`, which OpenRouter lists as
a low-latency GPT-4.1 variant with JSON/structured-output parameters. Benchmark with the same quiz and
teach prompts before changing the hosted default.

Deploy-specific dependency note: `pyproject.toml` explicitly routes Linux `torch` installs to the
PyTorch CPU wheel index. Without that, the Docker build pulls CUDA/NVIDIA transitive wheels and becomes
too large/slow for a practical CPU Space iteration loop.

Deploy-script persistence note: `scripts/deploy_hf_space.py` restarts the Space without
`factory_reboot` by default so future `/data` corpus/index artifacts are not wiped. Set
`GENACADEMY_HF_FACTORY_REBOOT=true` only when deliberately resetting the Space runtime. The script also
prints whether `NEBIUS_API_KEY` and `PINECONE_API_KEY` were set or skipped without printing secret
values.

## Data And Corpus Boundary

Private course material remains local-only unless explicitly approved for the Space. Before deployment,
choose one of these:

1. **Public-safe sample subset**: include only non-private, approved snippets.
2. **Private Space + hosted vectorstore**: deploy as a private Space and seed a Coach-specific
   Pinecone index/namespace through a controlled path.
3. **No corpus upload yet**: deploy the UI shell and show refusal behavior until data seeding is
   approved.

For a public portfolio release, the safest path is a public-safe subset or no public Space data.
Do not upload held-out `corpus/eval-questions`.

## Smoke Test Plan

Local container smoke:

1. Build the image: `docker build --progress=plain -t genacademy-coach-hf .`.
2. Run it with environment variables:
   `docker run --rm -p 7863:7860 -e GENACADEMY_PROVIDER=nebius genacademy-coach-hf`.
3. Open `http://127.0.0.1:7863`.
4. Confirm the UI boots.
5. If provider secrets and an approved corpus/index are available, run topic `agent harness`.
6. Confirm the UI returns either a grounded response with citation metadata or a safe refusal.

Observed local result on 2026-06-17: CPU-only Docker build passed, container booted, and localhost
returned `HTTP/1.1 200 OK`. Provider-backed click smoke was not run inside the container because the
live Space secrets/corpus decision is still pending.

Live Space smoke:

1. Open `https://huggingface.co/spaces/Manjunath84/genacademy-coach`.
2. Verify the private Space boots and serves the Gradio app.
3. Use a public-safe sample topic only after a public-safe corpus/index decision is made.
4. Verify no raw trace/corpus/eval text is exposed.
5. Verify the app does not print secrets in logs.

Observed live result on 2026-06-17: private Space is `RUNNING`; runtime logs show Gradio serving on
`0.0.0.0:7860`; authenticated live URL smoke returned `HTTP/2 200`. No provider-backed click smoke was
run because the Space intentionally does not contain private course corpus/index artifacts. The
post-PR-28 redeploy also returned authenticated `HTTP/2 200`; deeper body/config checks from this local
environment hit intermittent DNS resolution errors, not an app-level status code.

## Acceptance Criteria

- Space boots without requiring local `.env`.
- Runtime write paths for data, traces, and review queue stay under `/data`.
- Embed model and dimension match the active vector index:
  `all-MiniLM-L6-v2` / `384`.
- Hosted Space vectorstore points at a Coach-specific Pinecone index/namespace, not the Week-2 demo
  collection.
- Week 2 dependency is pinned by commit SHA in the Docker build.
- Deploy restarts do not factory-reboot by default.
- Startup logs chunk count and warns clearly when no corpus/index is present.
- No direct web-framework imports inside the core modules.
- No private corpus/eval text is committed or displayed.
- Live private Space URL returns HTTP 200.
- Public-safe sample topic works or safely refuses after a public-safe corpus/index decision is made.
- Empty-corpus Space state is visible in the UI as a deployment-shell status, not only in server logs.
- `scripts/check_eval_leak.py` passes after deployment files are added.
- README/roadmap record the Space URL and known limitations.
