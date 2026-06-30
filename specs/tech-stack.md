# Tech Stack

The framework is the handout's **Track 2**: LangChain + LangGraph, implemented with LangChain
`create_agent` on its LangGraph-backed runtime. The discipline is **MINT**: earn each layer, default to
the lightest tool that can pass the demo honestly, and keep the long-term cohort product extensible
through clean metadata and adapter seams.

## The Stack (Week-3 MVP)

| Layer | Choice | Why |
|---|---|---|
| Agent | **LangChain `create_agent`** | Official LangChain docs describe `create_agent` as a configurable agent harness composed from a model, tools, prompt, and middleware; LangChain agents are built on LangGraph. This satisfies the handout's LangChain + LangGraph track without hand-authoring a graph before the MVP earns it. |
| Generative call | **Nebius Token Factory via Week-2 provider surface** | The handout requires at least one Nebius model call. The richest MVP use is `generate_check_item`, grounded in a retrieved span. |
| Retrieval | **One source-prioritized course-corpus retriever** | One retriever over the extended Week-2 collection is more reliable than sparse source-specific tools. Every chunk carries `source_type`; slides and handouts are preferred, notes fill gaps, transcripts support/fallback. |
| Corpus | **Local owned corpus in `corpus/`** | `notes/`, `slides/`, `handouts/`, and `transcripts/` are the indexable sources; `eval-questions/` is never indexed. Content stays local/gitignored. |
| Auth | **Gradio `launch(auth=...)` + Week-2 SQLite user store** | Cohort member/admin login is enforced at the web boundary. Admin account creation reuses the Week-2 bcrypt/password table; core tutor logic stays framework-free. |
| State | **Within-session profile + optional episodic memory** | `style`, `track_lens`, optional `bridge_from`, `known[]`, `struggled[]`, coverage, and turn budget stay in session. Mem0-backed cross-session memory is off by default and stores only safe learner-state hashes/counts. |
| Grading | **Narrowest reliable scorer; deterministic MVP gate** | The current pass/fail decision uses normalized answer matching, semantic aliases, and citation-resolves checks. Open-ended model-assisted grading is deferred behind AD-13's evidence-bound ladder: labeled insufficiency evidence, egress approval, scorer versioning, and re-evaluation. |
| Trace | **Local JSON trace + CLI pretty print + allow-listed UI cards; private LangSmith eval traces by owner approval** | The local artifact remains the reproducible agenticity proof. The Gradio demo renders safe decision-basis/status cards from allow-listed metadata. LangSmith is adopted for Week-4 evaluation in a private project; seed/dev golden eval runs may be uploaded with raw inputs/outputs only when explicitly owner-approved and documented. The frozen `test` split, secrets, public screenshots, and committed raw traces remain forbidden (see `docs/decisions.md` AD-12 and `docs/week4-eval-plan.md`). Custom HTML is deferred. |
| Eval | **Hard-split real chat questions** | Held-out test comes from live student chat questions in `corpus/eval-questions/`. Optional NotebookLM or "Quiz Yourself" material may become dev/seed only. |
| Build tooling | **Codex / Claude Code with gates** | Builder and reviewer are different models or contexts; no code until the implementation plan is approved. |

## Frontend Boundary

The near-term learner and admin surfaces remain **Gradio-native**. Gradio is the shipped thin view for
Teach, Quiz, Skill-Gap, auth/admin, trace cards, and the first Coach v2 evidence-card/context-pane proof.
Use Gradio to validate retrieval behavior and user workflow before changing the web edge.

**FastAPI + HTMX is the production target, not an immediate rewrite.** Introduce it only after a
UI-neutral application service layer exists and the current Gradio app calls that layer through typed
DTOs. The migration trigger is product need: route-level security tests, better session/resume behavior,
admin workflows, progress/SSE streaming, production accessibility control, or deployment constraints
that Gradio cannot satisfy cleanly.

Review blockers:

- no FastAPI, HTMX, template, or route imports inside the core;
- no custom HTML or frontend migration inside Slice 0;
- no FastAPI/HTMX edge before the service boundary has tests;
- no duplicate UI logic: Gradio and any future FastAPI/HTMX surface call the same services.

## Handout Alignment

- **Agentic system, not one-shot RAG:** the model observes retrieval, grading, learner response, and
  profile state before choosing `next_action` and `strategy`.
- **State:** the within-session learner profile drives subsequent explanations and the session report.
  Track is a switchable teaching lens (`low_code_no_code`, `code_heavy`, or bridge), not a permanent
  persona.
- **Tool calls:** retrieval, check-item generation, grading, profile/session updates, and mentor
  escalation. Trace writing is a Python side-effect at the session boundary, not a model tool.
- **Human-in-the-loop:** out-of-corpus or low-confidence questions produce a learner-visible refusal and a
  review-queue entry.
- **Failure handling:** retry/tool validation, confidence thresholds, fallback source policy,
  human escalation, and stop/progress guards.
- **Nebius:** at least one provider call is routed through the inherited Week-2 provider path.
- **LangChain + LangGraph:** `create_agent` gives the LangChain agent surface and LangGraph-backed
  runtime; explicit `StateGraph` authoring is deferred until cross-session memory, pause/resume HITL, or
  auditable state transitions become core.

## Binding Guardrails (Review-Blockers)

- **Grounded-or-refuse.** The tutor only teaches/asks/grades what it can cite from retrieved spans.
- **Evidence-bound answerability.** Refuse/STOP is driven by retrieval score plus citation-present
  checks, never an LLM self-rating. Below STOP or with no citeable span, refusal is deterministic.
  CONFIRM-band model verification is deferred and may only become an advisory, cited-span-only input
  inside the AD-13 conjunction after deterministic false-refusal work is measured insufficient.
- **Narrowest reliable grader.** Closed-form and short conceptual checks use deterministic scoring
  first. Evidence-bound model grading for open-ended answers is a future AD-13 rung, not the active MVP
  gate.
- **Citations captured at retrieval.** Never reconstruct a citation after generation.
- **Agenticity = runtime decisioning shown in a trace.** Python enforces safety; the model chooses
  `advance`, `re_explain_differently`, `drill`, `refuse_escalate`, or `stop` plus a strategy.
- **Trace UI labels status, not controls.** In the Gradio demo, runtime decisions render as labeled
  status chips such as `action advance` and `band confirm`, plus `Decision basis`; they are evidence
  of the agent loop, not clickable workflow controls.
- **Pure core / thin view.** Agent, retrieval, grading, and learner-profile logic have no web-framework
  imports.
- **Reuse Week-2.** Do not rebuild the embedder, chunker, vector schema, refusal logic, provider wrapper,
  or eval harness without a written delta versus `genacademy-rag`.

## Eval & Data-Split Protocol

The held-out test set is only credible if leakage is mechanically prevented:

- **Source.** Test candidates come from real student chat-question files under `corpus/eval-questions/`.
  These questions are corpus-independent and are never indexed.
- **Dev/seed.** Optional NotebookLM exports or deep-note "Quiz Yourself" sets are corpus-derived and may
  be used only for seed/dev scenarios. They must stay outside `corpus/eval-questions/`. NotebookLM is not
  an MVP dependency.
- **Deterministic split, fixed seed.** A single script derives seed/dev/test with stable IDs and
  week/session stratification where the data supports it.
- **Commit the manifest, not private content.** Commit split IDs and checksums, never private answer text.
- **No-test-access rule.** Test content loads only inside eval; it never enters prompts, few-shots, the
  retriever index, or the demo script.
- **Leak check.** Fail the build if test IDs/checksums appear in index artifacts, prompts, examples, or
  demo scripts. Also check semantic/verbatim overlap against transcripts before freezing test items.
- **Frozen test.** Admin-authored, mentor-flagged, or learner-flagged items can grow dev/regression sets;
  changing test requires a new manifest and a note in `docs/decisions.md`.

## Success-Metric Protocol

The dev eval result needs a reproducible scenario file:

```json
{"concept":"...","initial_wrong_answer":"...","expected_citation_span_id":"...","target_check_id":"..."}
```

Pass criteria:

- The agent reaches a correct check-answer within the turn/time budget.
- The deterministic grounded grader marks the final answer correct.
- Every learner-visible citation resolves to a retrieved span.
- The trace shows a model-chosen `next_action` and `strategy`, not a scripted branch.

Current result: **7/10 overall, 7/8 teachable** on the dev split (2026-06-16). The original planning
target was 8/10. The 2 non-passing scenarios are safe low-retrieval refusals of out-of-corpus topics;
the 1 remaining teachable failure was a model-behavior diagnostic (cautious refusal in a confirm-band
retrieval case). The held-out `test` split remains unused.

## Confidence Bands

STOP < 0.40, CONFIRM 0.40-0.85, and PROCEED > 0.85 are the current calibrated MVP bands. The initial
`0.60` STOP seed threshold was too strict for the expanded Coach corpus; see
`docs/teach-loop-threshold-calibration.md`. Before changing these values again, run known-good and
known-bad queries against the actual extended index, record scores by `source_type`, and set MVP bands
from those distributions. The calibration is per-source analysis; shared numeric bands are acceptable
only if the measured slide/handout/note/transcript distributions justify them. Source priority is
ranking policy, not blind trust:

1. Prefer slides and handouts for teach explanations.
2. Use notes when slides/handouts are thin.
3. Use transcripts as support/fallback, especially for details not captured elsewhere.
4. Refuse/escalate when no source provides a citeable span.

## Runtime-Decision Trace

Primary artifact: `traces/<session_id>.json` plus a CLI pretty printer/screenshot.

Per turn:

```json
{
  "session_id": "abc123",
  "turn": 3,
  "topic_hash": "8f2e1d4c9a70",
  "learner_input_hash": "ad1c9e8042bb",
  "next_action": "re_explain_differently",
  "strategy": "contrastive_example",
  "evidence_score": 0.84,
  "evidence_band": "confirm",
  "faithfulness_ok": true,
  "tool_calls": ["retrieve_course_corpus"],
  "retrieved_citation_ids": ["week3-session1:chunk-42"]
}
```

LangSmith is adopted for Week 4 evaluation when `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, and
`LANGSMITH_PROJECT` are configured. Per AD-12, the project owner may approve seed/dev golden eval uploads
to a private LangSmith project, including raw learner questions, generated tutor prose, retrieved
citations, tool calls, scores, latency, and token counts. The frozen `test` split, secrets, public
screenshots, and committed raw traces remain forbidden. Fields not needed for submission or evaluators
should be masked by default, and eval traces should be deleted/retired after the submission window unless
the owner records a retention reason. Local JSON artifacts remain the reproducible source of truth;
LangSmith is the review/observability surface. See `docs/decisions.md` AD-12 and
`docs/week4-eval-plan.md`.

The local Gradio view may show an allow-listed trace-card projection for demos: rendered decision basis,
labeled action/band/score chips, strategy, faithfulness, citation summaries, and tool-call summaries.
Raw learner inputs, generated tutor prose, retrieved spans, raw quiz content, raw JSON trace rows, and
secrets stay ignored and must not be committed as screenshots or docs. Owner-approved LangSmith eval
uploads are the bounded exception for private seed/dev traces.

## Allowed vs. Forbidden Imports

- **Allowed:** LangChain `create_agent`, tool definitions, message types, callbacks/streaming needed to
  capture trace events, and plain-Python state passed through tool functions.
- **Forbidden this week:** direct imports from `langgraph.*`, including `langgraph.graph.*`,
  `langgraph.prebuilt.*`, `langgraph.checkpoint.*`, `from langgraph.types import Command, interrupt`,
  and `langgraph.func.*`. Current LangGraph docs show those as direct graph, prebuilt, checkpoint,
  interrupt, or functional APIs; they are earned only when explicit graph control becomes necessary. The
  MVP uses LangGraph transitively through LangChain `create_agent`.

## Minimal Refusal UX

On out-of-corpus or below-threshold retrieval, the agent returns a learner-visible message and appends a
line to `review_queue.jsonl`:

```json
{"topic_hash":"8f2e1d4c9a70","score":0.41,"reason":"no supporting span","timestamp":"..."}
```

No webhook or mentor-notification system is required for the MVP.

## Pull-Ins and Triggers

| Pull-in / Deferred Layer | Earned when |
|---|---|
| **Quiz mode** | The teach loop, refusal path, eval split/leak check, and trace are demoable end-to-end. |
| **Mock interview mode** | The shared engine is stable; open-answer grading has enough grounded scenarios. It asks open-ended questions, grades against cited expected points, follows up on gaps, and reports strengths/weak concepts. |
| **Admin upload** | Low-priority pull-in after the MVP works; reuse Week-2 auth/upload machinery and keep `source_origin` metadata. |
| **ElevenLabs voice** | Pull-in over the same text engine after text UX is reliable; text transcript remains source of truth. |
| **Explicit LangGraph graph** | Cross-session memory, pause/resume HITL, or auditable state transitions become core. |
| **MCP / A2A** | More than one system boundary or a genuine multi-agent split across systems appears. |
| **Memory hardening** | Cohort rollout needs retention/deletion/admin visibility beyond the off-by-default Mem0 adapter. |
| **Caching + model tiering** | Multi-user cost/latency matters. |
| **Layout-aware ingestion** | Raw diagram-heavy PDFs become central and Week-2 loaders are insufficient. |

## Repo Conventions

- `AGENTS.md` is the tool-neutral source of truth; `CLAUDE.md` is a thin mirror.
- The first implementation task is a read-only audit of `genacademy-rag` interfaces into a tiny adapter
  spec.
- Reference calls and current API facts are copied from official sources before use, not reconstructed
  from memory.
