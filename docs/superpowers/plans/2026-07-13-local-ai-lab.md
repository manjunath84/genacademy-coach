# Local AI Lab — Staged Installation And Interface Plan

> **Status:** Draft for independent AI review. Documentation was requested on 2026-07-13.
> Implementation has not started and is not authorized by this document. After an independent
> review, the owner must resolve the findings and explicitly approve the revised plan before any
> package installation, model download, or application code is written.

**Goal:** Give a beginner a private, understandable local-AI learning environment on an existing
Apple Silicon Mac: first learn how local inference works, then use a small browser interface for
chat, image explanation, transcription, and—only after the base system is measured—private
document search.

**Architecture:** Build an owner-local, standalone `local-ai-lab` application outside this
repository. A localhost-only Gradio interface will call Ollama for chat/vision and an Apple-native
Whisper runtime for transcription. One large model is loaded at a time. The app will not import
GenAcademy Coach code, read its data, or become a Coach product mode.

**Proposed stack:** Python managed by `uv`; Gradio for the thin browser view; Ollama for the first
chat/vision runtime; MLX-compatible Whisper tooling for speech-to-text; pytest and Ruff for checks.
Every package version, model ID, license, download size, command, and API call must be rechecked
against current official documentation immediately before implementation.

## 1. Review Gate And Requested Verdict

This plan exists so a different AI can challenge the model choices, runtime design, scope, privacy
controls, and verification bar before the owner approves implementation. The reviewer should return:

1. **Verdict:** `approve`, `approve with changes`, or `reject`.
2. **Blocking findings:** issues that must be resolved before implementation.
3. **Non-blocking improvements:** useful changes that do not prevent the first stage.
4. **Model/runtime corrections:** any current compatibility, licensing, size, or support errors.
5. **Scope recommendation:** whether document search belongs in v1 or should remain a later stage.

The reviewer should answer these questions explicitly:

- Is Ollama plus Gradio the simplest safe starting point for a first-time local-AI user?
- Are the selected models appropriate for 32 GiB of unified memory on an M1 Max?
- Is Qwen3.6-27B sufficiently valuable to justify a second large download after `gpt-oss:20b`?
- Are localhost binding, disabled sharing, non-persistent chats, and explicit file selection enough
  for the intended privacy posture?
- Does the plan keep this personal learning tool fully separate from GenAcademy Coach?
- Are the performance and acceptance measurements sufficient to make a keep/remove decision?

## 2. Scope Boundary

This is an **owner-local learning tool**, not a GenAcademy Coach feature or roadmap item. This
repository contains only the review plan. If approved, implementation belongs in a separate local
directory or repository such as `~/local-ai-lab`.

Hard boundaries:

- Do not modify `src/genacademy_coach`, its web interface, product specs, roadmap, or architecture.
- Do not automatically read or index the Coach corpus, evaluation questions, traces, learner data,
  environment files, caches, or credentials.
- A future document-search tab may read only files the owner explicitly selects, into a separate
  index owned by the standalone lab.
- Do not commit model weights, generated prompts or responses, uploaded documents, audio, indexes,
  screenshots containing private content, or machine-specific secrets.
- Do not add cloud inference, remote access, tunnels, autonomous shell execution, or public sharing.

## 3. Public-Safe Machine Baseline

Audit date: 2026-07-13. Serial numbers, hardware UUIDs, usernames, volume names, and raw command
output are intentionally omitted.

| Item | Observed baseline | Planning consequence |
|---|---|---|
| Computer | 16-inch 2021 MacBook Pro | Apple-native runtimes are preferred |
| Processor | Apple M1 Max, 10-core CPU | More than sufficient for runtime orchestration |
| GPU | 32-core Metal GPU | Primary local-inference accelerator |
| Memory | 32 GiB unified memory | macOS, model weights, KV cache, and UI share one pool |
| Storage | About 440 GiB available | Enough room for staged downloads, with cleanup controls |
| Architecture | arm64 macOS | Avoid x86-only packages and containers |
| Ollama | 0.31.2 installed; server stopped at audit | Reuse rather than introduce a second chat runtime |
| Existing local model | `gemma4:latest`, about 9.6 GB | Stage 1 can start without a model download |
| Other tooling | `uv`, Python, Hugging Face CLI, and Gradio are available | Revalidate in the standalone environment |

The practical target is 8B–27B models quantized to four or five bits. A 20B–27B four-bit model
should be treated as a measured candidate, not a performance promise. A 70B model is outside the
usable memory envelope once model weights, context cache, macOS, and the interface are counted.

## 4. Candidate Model Set

Sizes below are repository or local-artifact observations, not peak runtime memory. Recheck them
before download because model repositories and quantizations can change.

| Model | Role | Approximate artifact | Why it is in the plan | Decision |
|---|---|---:|---|---|
| [`gemma4:latest`](https://ollama.com/library/gemma4:latest) | Chat and image explanation | 9.6 GB, already present | Zero-download baseline and simplest learning path | Stage 1 default |
| [`gpt-oss:20b`](https://huggingface.co/openai/gpt-oss-20b) | Text reasoning, coding, structured output | About 14 GB in [Ollama](https://ollama.com/library/gpt-oss:20b) | Balanced local reasoning model; mixture-of-experts design reduces active compute | Stage 2 download |
| [`Qwen3.6-27B`](https://huggingface.co/Qwen/Qwen3.6-27B), four-bit | Dense text/coding/vision candidate whose local quality is unproven | About 16.8 GB for one [Ollama-compatible GGUF option](https://huggingface.co/unsloth/Qwen3.6-27B-GGUF); variants differ | Tests whether a larger dense model remains worthwhile under this Mac's context limit | Stage 3, benchmark-gated |
| [`Whisper large-v3-turbo`](https://huggingface.co/openai/whisper-large-v3-turbo) | Multilingual speech-to-text | About [0.46 GB for a four-bit MLX conversion](https://huggingface.co/mlx-community/whisper-large-v3-turbo-q4) | High-value local specialty model with a small storage cost | Stage 2 download |
| [`Qwen3-Embedding-0.6B`](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | Semantic document retrieval | About 1.2 GB | Enables private meaning-based search without using a generative model as the index | Stage 3, owner opt-in |

Deferred alternatives:

- `Qwen3.5-9B` is a compact multimodal alternative if the existing Gemma baseline performs poorly.
- `Qwen3.6-35B-A3B` is a lower-active-parameter mixture-of-experts alternative with a tighter memory
  margin; its actual speed on this M1 Max is unmeasured. Do not download it before the 27B decision.
- FLUX-class local image generation is out of v1 because the full pipeline requires materially more
  memory than the weight file and distracts from learning the core runtime.

Expected new download budget if every proposed stage is approved: approximately 32–34 GB. Stage 1
requires no new model weight. Stage 2 adds roughly 14.5 GB. Stage 3 adds roughly 17–18 GB including
the embedding model. Downloads must remain explicit rather than being triggered automatically by
the interface.

## 5. Beginner Mental Model

The interface is not the model. Hugging Face or an Ollama registry stores model artifacts; a runtime
loads those weights from SSD into unified memory; the Metal GPU performs inference; the browser
shows streamed results.

```text
Browser on this Mac
        ↕ 127.0.0.1 only
Gradio interface
        ↕ local API / local function call
Ollama chat runtime       MLX-compatible Whisper runtime
        ↘                 ↙
        M1 Max Metal GPU + shared unified memory
                         ↕
                  model files on SSD
```

Concepts the UI documentation should teach:

- **Weights:** learned numerical parameters downloaded once and reused.
- **Inference, not training:** chatting runs fixed weights; it does not permanently teach the model.
- **Tokens:** the model repeatedly predicts the next token and streams the result.
- **Quantization:** four-bit weights reduce disk and memory substantially, with some fidelity cost.
- **KV cache/context:** longer prompts and conversations use more memory even when weights are fixed.
- **Dense versus mixture-of-experts:** dense models use most weights for each token; MoE models keep
  all expert weights in memory but activate only a subset for each token.
- **Vision:** image patches become visual tokens consumed by the language model.
- **Whisper:** audio becomes spectral features that are decoded into text.
- **Embeddings:** text becomes vectors for similarity search; embeddings do not write answers.
- **Local is not automatically correct:** models can hallucinate and can be outdated even when no
  data leaves the machine.

Qwen3.6 requires an explicit caveat: its official model card defines a 262,144-token default and
advises at least 128K to preserve thinking capabilities. This 32-GiB Mac is unlikely to run that
context economically with the 27B weights. The Stage-3 experiment therefore asks whether Qwen remains
valuable at the **largest safely measured local context**; it must not be called the quality winner
before that test.

## 6. Runtime And Privacy Decisions

1. **Ollama first.** It is already installed and exposes a local streaming API. Do not introduce
   llama.cpp, LM Studio, Docker, or a second chat server in v1.
2. **Gradio as a thin view.** The interface contains no inference logic. It streams runtime output
   and exposes only settings that a beginner can understand.
3. **Loopback and local-only mode.** Bind Ollama and Gradio to `127.0.0.1`; launch Gradio with
   `share=False`; and use Ollama's documented `OLLAMA_NO_CLOUD=1` setting. Verify Ollama reports
   that cloud features are disabled before sending a test prompt.
4. **No prompt persistence or UI telemetry by default.** Conversation state lives in memory for the
   current browser session. Configure Gradio explicitly with `save_history=False`,
   `analytics_enabled=False`, `flagging_mode="never"`, and private API visibility. Configure
   a dedicated `GRADIO_TEMP_DIR`, restrictive/empty allowed paths, blocked private directories, a
   conservative upload-size cap, scheduled `delete_cache`, and the current supported
   unload/disconnect cleanup callback. Clearing a component is not accepted as proof of file deletion;
   filesystem checks must cover clear, browser disconnect, and app restart. An explicit export feature
   is deferred.
5. **One large model at a time.** Switching models unloads the previous model before loading another.
   Limit Ollama to one loaded model and one parallel request; the unload control uses Ollama's
   documented stop or zero-`keep_alive` behavior.
6. **Conservative context.** Start at 8K even when a model advertises 128K or 262K. Test 16K only
   after measuring memory pressure.
7. **No background downloads.** Every model pull displays its exact ID, source, license, expected
   size, and purpose before the owner runs it.
8. **No cloud fallback.** A local failure remains visible; the app must not silently send the request
   to a hosted provider.
9. **Explicit documents only.** Document search cannot scan home directories or the Coach checkout.
10. **No raw telemetry.** Avoid prompt/response logging; operational logs contain model name,
    duration, token counts when supplied by the runtime, and redacted error type only.
11. **One chat runtime in v1.** Stage-3 Qwen must use an Ollama-compatible GGUF artifact. Adding
    MLX-LM or MLX-VLM as another chat runtime requires a separately reviewed post-v1 delta; MLX in
    this plan is limited to Whisper transcription.

## 7. Planned Interface

### Stage-1 tabs

- **Chat / Reason:** streaming chat, supported-model selector, simple creativity control, context
  preset, clear-session button, unload-model button, and a short model-purpose explanation.
- **See / Explain:** explicit image upload for models whose runtime artifact supports vision; reject
  unsupported model/image combinations before inference.
- **About / Privacy:** machine-safe summary, active model, loaded/unloaded status, local-only
  explanation, current bind address, storage estimate, and limitations.

### Stage-2 tab

- **Transcribe:** explicit audio upload, local Whisper transcription, optional timestamps, language
  choice or auto-detection, and clear/delete controls. Remind the user to obtain consent before
  transcribing other people.

### Stage-3 tab, only if separately approved

- **My Documents:** explicit file picker, separate local index, semantic search results with source
  names and passages, and grounded answer generation using only retrieved passages. Include remove
  document, clear index, and storage-location controls.

The first version will not include accounts, persistent memory, remote access, tool execution,
web search, model fine-tuning, image generation, or simultaneous multi-model conversations.

## 8. Proposed Standalone File Structure

The final structure should remain small and may be simplified further during review:

```text
local-ai-lab/
├── README.md
├── pyproject.toml
├── uv.lock
├── src/local_ai_lab/
│   ├── app.py                 # Gradio composition only
│   ├── model_registry.py      # allow-listed model capabilities and sizes
│   ├── ollama_client.py       # local streaming chat/vision adapter
│   ├── transcription.py       # local Whisper adapter
│   └── document_search.py     # optional Stage 3, explicit files only
└── tests/
    ├── test_model_registry.py
    ├── test_ollama_client.py
    ├── test_transcription.py
    └── test_privacy_defaults.py
```

Do not create `document_search.py` or its dependencies until Stage 3 is approved. If the first two
adapters remain very small, the reviewer may recommend combining them rather than preserving this
suggested split.

## 9. Staged Execution Plan

### Stage 0 — Revalidation And Preflight

- [ ] Record the independent review verdict and every blocking finding in this document or a linked
  review handoff.
- [ ] Owner resolves findings and explicitly approves the revised plan.
- [ ] Re-fetch current Ollama, Gradio, MLX/Whisper, and model documentation.
- [ ] Re-resolve exact model IDs, licenses, artifact sizes, runtime support, and reference commands.
- [ ] Resolve and record immutable artifact digests/configuration for every selected model; do not
  treat the mutable `gemma4:latest` tag alone as reproducible evidence.
- [ ] Confirm at least 60 GB free before optional large-model downloads, preserving rollback space.
- [ ] Confirm Ollama binds to loopback and capture the pre-install listener list.
- [ ] Benchmark no model yet; record idle memory pressure and available unified memory.

**Exit gate:** approved reviewed plan, verified commands, verified loopback configuration, and no
unresolved model-license or runtime-compatibility blocker.

### Stage 1 — Existing Gemma Baseline And Minimal UI

- [ ] Create the separate `local-ai-lab` repository and reproducible `uv` environment.
- [ ] Write failing tests for model allow-listing, unsupported vision inputs, localhost defaults,
  disabled cloud/sharing/analytics/flagging, private API visibility, temporary-file cleanup, and
  non-persistent history.
- [ ] Allocate a lab-owned temporary directory, set restrictive file-serving paths and upload caps,
  and test that uploaded files disappear after clear, disconnect/unload, and restart.
- [ ] Add the smallest Ollama streaming adapter needed for `gemma4:latest`.
- [ ] Build the Chat / Reason, See / Explain, and About / Privacy tabs.
- [ ] Add clear-session and unload-model controls.
- [ ] Run one text prompt and one user-supplied, non-sensitive image through the existing model.
- [ ] Record first-token latency, generation throughput when reported, total duration, memory
  pressure, and whether swap grows materially during an 8K-context test.

**Exit gate:** the existing model streams text and processes one image; the app is reachable only
from loopback; tests and lint pass; no additional model has been downloaded.

### Stage 2 — Balanced Reasoning Model And Speech-To-Text

- [ ] Present the exact `gpt-oss:20b` download command and expected size to the owner.
- [ ] Download only after confirmation and verify the artifact checksum/manifest the runtime exposes.
- [ ] Add it to the allow-listed registry as text-only unless the current artifact explicitly says
  otherwise; keep Ollama as the adapter because it handles the model's required chat format.
- [ ] Run the same benchmark prompts as Gemma plus one coding explanation and one structured-output
  task; record results without declaring a winner from a single prompt.
- [ ] Select and pin the current Apple-native Whisper package after documentation review.
- [ ] Write transcription adapter tests using generated or explicitly public-safe audio.
- [ ] Download the chosen Whisper artifact and add the Transcribe tab.
- [ ] Verify timestamps, clear/delete behavior, and no retained upload after the session ends.

**Exit gate:** `gpt-oss:20b` is usable at 8K context without unacceptable memory pressure; local
transcription succeeds; all data remains local after the downloads complete.

### Stage 3 — Quality Tier And Optional Document Search

- [ ] Review Stage-1/2 evidence before downloading another large model.
- [ ] Confirm whether Qwen3.6-27B adds a needed capability or measurable quality improvement.
- [ ] Select one Ollama-compatible GGUF quantization; MLX chat runtimes remain outside v1.
- [ ] Download Qwen only after the owner confirms the exact artifact, digest, license, and storage cost.
- [ ] Benchmark text, coding, model-load time, unload behavior, and the largest context that fits
  safely. Test vision only if the selected Ollama artifact explicitly supports it.
- [ ] Compare Qwen with `gpt-oss:20b` at feasible contexts and keep it only if its measured benefit
  justifies its speed, memory cost, and known reduced-context thinking tradeoff.
- [ ] If document search is approved, add the embedding model, explicit file ingestion, an isolated
  index, citations, document removal, and clear-index controls.

**Exit gate:** a written keep/remove decision for Qwen and a separate acceptance record for document
search. Failure to meet the bar triggers removal rather than another runtime layer.

### Stage 4 — Independent Review And Handoff

- [ ] Run Ruff, the focused test suite, and a clean-environment install check.
- [ ] Verify listeners show no public bind and Gradio sharing remains disabled.
- [ ] Verify no runtime sends inference requests to external hosts.
- [ ] Run real text, image, and audio smoke tests with non-sensitive inputs.
- [ ] Have a different model or fresh context review code, privacy defaults, tests, and benchmark
  evidence.
- [ ] Resolve blocking review findings and rerun affected checks.
- [ ] Deliver a beginner README covering start, stop, model selection, storage, privacy, limitations,
  and complete uninstall steps.

## 10. Acceptance Criteria And Evidence Table

The builder must fill this table with results from the audited M1 Max; estimates or results from
other Macs do not count.

| Check | Required bar | Evidence to record |
|---|---|---|
| Network exposure | Ollama and UI listen on `127.0.0.1` only; no share URL | Listener command output, redacted of unrelated processes |
| Cloud disablement | Ollama local-only mode is enabled; Gradio analytics are disabled | Ollama startup status and explicit UI configuration |
| Reproducibility | Fresh `uv sync` succeeds from the lockfile | Command and exit code |
| Static checks | Ruff clean | Exact command and summary |
| Tests | All local-lab tests pass | Exact command and test count |
| Gemma text | Streaming response completes | First-token latency, total time, throughput if reported |
| Gemma vision | One non-sensitive image is explained | Duration and any visible failure |
| `gpt-oss:20b` | Text, coding, and structured-output cases complete | Same benchmark fields as Gemma |
| Whisper | One short and one longer audio sample transcribe | Duration, language, obvious error notes |
| Memory | No crash; model unload releases pressure; one large model loaded | Memory-pressure and swap observations |
| Context | 8K succeeds; 16K attempted only if headroom remains | Prompt size, peak pressure, result |
| Privacy | No persisted prompts/uploads by default; no external inference request | Network inspection plus filesystem checks after clear, disconnect, and restart |
| Review | Different model/fresh context reviews implementation | Verdict, blockers, resolutions |

No universal tokens-per-second target is specified before measuring this exact machine. The owner
will judge whether interaction feels acceptable using the recorded results. Published context-window
limits are compatibility ceilings, not acceptance targets.

## 11. Failure Handling And Rollback

- If Ollama is unavailable, show a local setup error with the expected loopback address; do not start
  a cloud fallback.
- If a model does not support images, reject the image locally before sending a request.
- If memory pressure becomes unacceptable, unload the model, reduce context, close unrelated heavy
  applications, and retest once. Do not add swap-tuning or system hacks.
- If Qwen fails the measured value/performance test, remove only its named runtime artifact and keep
  the working Gemma/`gpt-oss` setup.
- If transcription support is unstable, remove the Whisper tab and dependency without changing chat.
- Uninstall must be reversible: stop the app, remove only explicitly named downloaded models, delete
  the standalone environment/index after confirmation, and leave this Coach repository untouched.

## 12. Open Decisions For The Owner After Review

| Decision | Recommended default | Alternatives |
|---|---|---|
| Standalone location | Separate `~/local-ai-lab` repository | Another owner-chosen directory outside Coach |
| First added chat model | `gpt-oss:20b` | Skip it and benchmark Qwen directly |
| Qwen timing | Download only after Stage-2 evidence | Download up front at greater storage/time cost |
| Document search | Stage 3, explicit opt-in | Include in v1 or omit entirely |
| Persistent chat history | Off | Later encrypted/export-only design |
| Image generation | Deferred beyond v1 | Separate future plan with its own memory benchmark |

## 13. Review Record

Fill this section after the independent AI review. A review is evidence, not approval; owner approval
is still required afterward.

- **Reviewer/model:** Pending
- **Review date:** Pending
- **Verdict:** Pending
- **Blocking findings:** Pending
- **Non-blocking findings:** Pending
- **Owner resolutions:** Pending
- **Revised-plan commit:** Pending
- **Owner implementation approval:** Pending

## 14. Source Links To Revalidate

- [Ollama API documentation](https://docs.ollama.com/api/introduction)
- [Ollama local-only, bind, context, and unload settings](https://docs.ollama.com/faq)
- [Gradio `ChatInterface` documentation](https://www.gradio.app/docs/gradio/chatinterface)
- [MLX Whisper reference implementation](https://github.com/ml-explore/mlx-examples/tree/main/whisper)
- [Gemma 4 in Ollama](https://ollama.com/library/gemma4)
- [OpenAI gpt-oss-20b model card](https://huggingface.co/openai/gpt-oss-20b)
- [Qwen3.6-27B model card](https://huggingface.co/Qwen/Qwen3.6-27B)
- [Qwen3.6-27B Ollama-compatible GGUF candidates](https://huggingface.co/unsloth/Qwen3.6-27B-GGUF)
- [Whisper large-v3-turbo model card](https://huggingface.co/openai/whisper-large-v3-turbo)
- [Qwen3 Embedding 0.6B model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
