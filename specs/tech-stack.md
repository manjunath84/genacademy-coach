# Tech Stack

The framework is the handout's **Track 2** (code-heavy). The discipline is **MINT** — earn each layer;
default to the lightest tool and justify every step up.

## The stack (Week-3 MVP)

| Layer | Choice | Why |
|---|---|---|
| Agent | **LangChain `create_agent`** | Standard agent entry point; a model-chooses-tools loop. Built on LangGraph, so middleware, a typed state schema, checkpointers, and HITL-interrupt middleware are available later **without a rewrite**. Matches the cohort `agentic_rag` reference; fastest to ship. |
| Generative call | **Nebius Token Factory** | Routes the `generate_check_item` call (rubric requires ≥1 Nebius call; the richest call to showcase). |
| Retrieval | **2–3 retriever tools** over the corpus | Multi-tool router/decomposition: the model picks *which* corpus (lectures / assignments / student-qa) at runtime. Tool docstrings are the routing logic; a decomposition nudge in the system prompt buys planning with no planner node. |
| Corpus | **CohortBrain processed data** + curated handouts | Pre-segmented Week 1–2 lectures/assignments with metadata + timestamps for citations. Attribution/permission to confirm before use; nothing committed to this repo. |
| State | **Within-session learner profile** (in-memory) | `style · known[] · struggled[] · coverage · transcript`. Durable cross-session state = deferred. |
| Grading | **Deterministic** where possible | MCQ grading is index-match (no model). Open-answer grading (interview pull-in) is grounded against the retrieved span. |
| Eval | **Item-quality on a hard-split, held-out test set** | answerability · unique-correct · distractor validity · citation support · no span-leakage. Deterministic grading alone masks bad items. |
| Build tooling | **Codex / Claude Code** | Vibe-coding; builder and reviewer are **different** models (AGENTS §2). |

## Binding guardrails (full text in `AGENTS.md` §3 — repeated here as stack constraints)

- **Grounded-or-refuse**; confidence from **real signals** (retrieval similarity + citation-present),
  never an LLM self-rating. Bands: STOP < 0.60 · CONFIRM 0.60–0.85 · PROCEED > 0.85.
- **Citations captured at retrieval, never reconstructed.**
- **Agenticity = runtime decisioning shown in a trace**, not a scripted loop.
- **Pure core / thin view**: agent + retrieval + grading logic is testable with no web-framework imports.

## Eval & data-split protocol (enforceable — `AGENTS.md` §2 gate 4)

The held-out test set is only credible if leakage is *mechanically* prevented, not just promised:

- **Deterministic split, fixed seed.** A single `split_eval.py` derives seed/dev/test from
  `student_questions.jsonl` with a hard-coded seed and week-stratification; re-running reproduces the
  exact split.
- **Commit the manifest, not the content.** Commit `eval/split_manifest.json` = per-split question
  **IDs + a sha256 content checksum**, never answer text. The **test** content stays out of the indexed
  corpus and is git-ignored.
- **No-test-access rule.** The retriever index and every prompt / example / few-shot are built from
  **seed/dev only**. Test items load **only** inside the eval runner — never the agent, a prompt, or the
  demo.
- **Leak check (CI / pre-commit).** `check_eval_leak.py` fails the build if any test ID or checksum
  appears in the index, a prompt template, a few-shot example, or the demo script. Green is shown, not
  asserted.
- **Frozen test.** The regression/dev set may grow from learner-flagged items; the **test** split is
  frozen — changing it requires a new manifest + a note in `docs/decisions.md`.
- **Pre-build data audit (gate).** Before writing any prompt: `wc -l` each split, check **per-week**
  counts, and confirm ≥ 10 eval scenarios can be drawn from `test` without replacement. If a week is too
  thin, broaden stratification or lower N — never claim a number the data can't support.

## Success-metric protocol — the eval scenario (lock before code)

The "8/10" claim is only real with a concrete scenario format. Starting definition (finalize in the plan):

- **Scenario file** (`eval/scenarios.jsonl`), one per line:
  `{"concept": "...", "initial_wrong_answer": "...", "expected_citation_span_id": "...", "target_check_id": "..."}`.
- **Sim loop.** A scripted learner-sim replays `initial_wrong_answer`; the agent must re-explain; the sim
  then answers correctly. **Pass = the agent reaches a correct check-answer within ≤ 3 re-explain turns
  AND every citation shown resolves to a retrieved span.**
- **Grader.** The "deterministic grounded grader" = exact/normalized match against the scenario's
  `target_check_id` answer key + a citation-resolves check. No LLM-judge in the MVP.
- **Target: ≥ 8/10 scenarios pass** on held-out `test` concepts (mirrors `specs/mission.md`).

## Confidence bands — calibrated, not magic (gate)

STOP < 0.60 / CONFIRM 0.60–0.85 / PROCEED > 0.85 are **starting points, not a settled signal.** Before
relying on them: run retrieval on **5 known-good and 5 known-bad** queries against the *actual* index,
record the scores, and set the bands from that distribution. Document the metric (cosine vs. dot-product,
raw vs. normalized). An uncalibrated band makes "won't bluff" vibes-based.

## Runtime-decision trace — the agenticity artifact (spec)

The trace IS the agenticity proof, so it must be a real artifact, not a log dump:

- **Format** (`traces/<session_id>.json`): per turn =
  `{turn, observation, reasoning, action, tool_calls[], confidence}`, where
  `action ∈ {explain, re_explain_differently, advance, refuse_escalate, stop}`.
- **Render.** A small CLI/HTML panel pretty-prints the reasoning chain side-by-side with the chat —
  **not** raw JSON on screen. This is the demo centerpiece (~2-hour build; schedule it, don't let it slip).
- **Real, not decorated.** `action`/`reasoning` are captured from the model's actual tool-call/output via
  a callback — never hand-written after the fact.

## Allowed vs. forbidden imports (the `create_agent` boundary — review-blocker)

To keep "no explicit LangGraph this week" honest and prevent accidental drift:

- **Allowed:** `langchain`'s `create_agent`, tool definitions, message types; plain-Python state passed
  through tool functions.
- **Forbidden this week:** importing `langgraph.graph.StateGraph`, `langgraph.checkpoint.*`, or
  `langgraph.interrupt` directly — that's hand-authoring a graph (the deferred layer). A direct import of
  any of these in a PR is a reject.

## Minimal refusal UX (won't-bluff, made demoable)

On out-of-corpus / below-threshold the agent returns a learner-visible message —
*"I can't find this in the course materials (retrieval score: 0.41). I've flagged it for a mentor."* —
**and** appends a line to `review_queue.jsonl` (`{topic, score, timestamp}`). That's the whole refusal
path: a real message + a real queue file, both demoable. No webhook / mentor-notification needed for the MVP.

## Deliberately deferred — and the trigger that earns each

| Deferred | Earned when |
|---|---|
| **LangGraph** (explicit graph) | Cross-session memory or a real pause/resume HITL **interrupt** becomes demo-core, or state transitions must be auditable. `create_agent` covers the MVP. |
| **MCP / A2A** | More tools/pipelines than one corpus + a few read tools (MCP); a genuine multi-agent split **across systems** (A2A). Neither applies now. |
| **Mem0 cross-session memory** | The rollout — "remembers you across days" (semantic + episodic). |
| **Caching (L1/L4/L5) + model tiering** | Cost/scale matters (multi-user). Trivial for one user now. |
| **Layout-aware re-ingestion** (LlamaParse / LiteParse) | Raw PDFs with diagrams enter the corpus. CohortBrain data arrives pre-segmented, so not yet. |
| **Voice (ElevenLabs) / multimodal** | After the text engine ships and demos end-to-end. |

## Repo conventions (mirrors `genacademy-rag`)

- `AGENTS.md` is the tool-neutral source of truth; `CLAUDE.md` is a thin mirror.
- Pluggability via interface + config, not branching (`if provider == ...` scattered through logic is a
  reject).
- Reference API calls (LangChain / Nebius signatures, model IDs, embedding dimensions) are pasted
  verbatim into the relevant spec, never reconstructed from memory.
