# Production Roadmap

- Status: planning draft
- Date: 2026-06-21
- Target: turn GenAcademy Coach from a Week-3 demo into a reliable cohort learning product

## Executive Verdict

**GO WITH NITS.** The current direction is correct: reliability before features, eval as the operating
system, a clean web-edge/core boundary, bounded model autonomy, FastAPI + HTMX instead of a React
rewrite, privacy-first memory, and restraint around voice, explicit LangGraph, and multi-agent
orchestration.

The must-fix items before the next implementation phase are:

- define reliability with measurable SLOs and exit criteria;
- decide the FastAPI sync/async boundary;
- expand the agent-failure taxonomy;
- make the `genacademy-rag` dependency reproducible for CI/production.

## Design Principles

Production AI is the deterministic system around an unreliable model:

- The LLM is an upstream service: slow, costly, occasionally wrong, and mostly stateless.
- Code cleans, validates, scopes, routes, retries, checks output, and logs.
- Reliable systems use small steps, clear contracts, schema validation, fallback, confirmation gates,
  and evals.
- Cost is controlled by model choice per step, early scope refusal, rate limits, token budgets, and
  cost caps.
- Latency is controlled through smaller models where possible, crisp output, TTFT budgets, streaming,
  and progress indicators.
- Memory is an application responsibility, not a magic model feature.
- Everything touching the model is attacker input: user messages, retrieved content, tool results, and
  model output.
- The model suggests; code validates; users authorize sensitive actions.
- Provider privacy matters: send the minimum necessary data and mask sensitive data at write time.
- Observe every model call and evaluate continuously.

## Reliable Means

Phase 0 will record current baselines. Phase 1 cannot exit until the following targets pass on the
dev/regression set or are recalibrated with dated evidence.

| Metric | Initial target |
|---|---:|
| Teach-decision accuracy | >= 90% on teachable dev/regression cases |
| Refusal recall on out-of-corpus set | >= 95% |
| Refusal precision | >= 90% |
| Citation-resolution rate | 100% |
| Schema-valid decision rate | >= 99% |
| Invalid-action safe fallback rate | 100% |
| Retrieval golden-set recall@5 | >= 90% |
| p95 teach turn latency | <= 12s |
| TTFT if streaming is enabled | <= 3s |
| Provider timeout/error budget | <= 2% during eval/smoke runs |
| Eval reproducibility | model ID, params, prompt version, corpus version, chunk scheme, git SHA present |

Invalid, malformed, or unparseable agent decisions must become `refuse_escalate` or `stop`. They must
never silently advance the learner. The decision step runs at temperature `0`.

## Target Architecture

```text
Browser
  -> FastAPI + HTMX web edge
  -> Application service layer
  -> GenAcademy Coach core
  -> genacademy-rag adapter/foundation
  -> Chroma locally / Pinecone when hosted retrieval is proven
```

Architecture rules:

- Web frameworks stay at the edge.
- Core/session diagnostics live in the core or service layer, not in Gradio.
- Blocking Coach calls use sync FastAPI route handlers by default; FastAPI runs sync path operations in
  a threadpool. Any `async def` route must wrap blocking work with `run_in_threadpool` or move it to a
  worker.
- Datastores sit behind a seam: SQLite for local/dev/demo, Postgres + Alembic for production/cohort
  scale when needed.
- `genacademy-rag` remains a separate RAG foundation, not code merged into Coach.
- MCP, if added later, is another API client, not a bypass.

## Failure Taxonomy

Every failure class must have detection, diagnostics, fallback behavior, and test/eval coverage. The
table below is the contract: a failure class is not "handled" until all five columns are filled and the
coverage cell points at a real test or eval.

| Failure | Detection signal | Diagnostic fields | Fallback / user state | Coverage |
|---|---|---|---|---|
| Structured-output / schema violation | Pydantic parse/validation error on decision payload | `reason_code=schema_invalid`, raw model output, schema version | `refuse_escalate`; user sees "Coach hit an internal snag, escalating" | fake-agent schema-violation test |
| Malformed or invalid agent action | Action not in allowed enum / missing required args | `reason_code=invalid_action`, attempted action, allowed set | `stop`; user sees invalid-agent-decision state | fake-agent invalid-action test |
| Tool retry failure | Retries exhausted (count == max) | `reason_code=tool_retry_exhausted`, tool name, attempts, last error | `refuse_escalate`; transient-error state | tool-retry test (forced failures) |
| Tool timeout | Tool call exceeds per-tool deadline | `reason_code=tool_timeout`, tool name, elapsed ms, budget | `refuse_escalate`; transient-error state | tool-timeout test |
| Provider timeout / rate-limit / outage | Provider exception or deadline exceeded | `reason_code=provider_unavailable`, provider, http/status, elapsed ms | degraded mode; user sees provider-timeout state | provider-failure injection test |
| Empty retrieval | Retrieval returns zero chunks | `reason_code=retrieval_empty`, query, k, corpus version | refuse to answer; user sees empty-retrieval state | empty-retrieval eval case |
| Low-confidence retrieval | Top score below configured threshold | `reason_code=retrieval_low_conf`, top score, threshold, corpus version | refuse or hedge; user sees low-confidence state | low-confidence eval case + threshold test |
| Citation mismatch | Cited chunk ID not resolvable to a real source | `reason_code=citation_mismatch`, cited IDs, resolvable IDs | `refuse_escalate`; citation not shown | citation-resolution test (100% bar) |
| Faithfulness mismatch | Output claim not entailed by retrieved context | `reason_code=faithfulness_fail`, claim, supporting chunk IDs | refuse to assert; user sees grounding-failure state | faithfulness eval case |
| Deterministic grading edge case | Grader hits ambiguous/uncovered branch | `reason_code=grading_edge`, grader input, branch | `refuse_escalate` to mentor review | deterministic-grading unit test |
| Prompt injection (learner / retrieved / tool / model) | Injection heuristic or scope-gate trip | `reason_code=injection_suspected`, source channel, matched signal | drop instruction, scope-refuse; user sees scope-refusal state | prompt-injection test suite (all 4 channels) |
| Model drift | Eval scores regress vs recorded baseline | `reason_code=drift_detected`, metric, baseline, current, git SHA | alert + hold release; no user-facing change | regression eval vs baseline |
| Non-deterministic decision behavior | Same input yields differing decisions at temp 0 | `reason_code=nondeterministic`, input hash, decisions seen | `stop`; treat as bug, not learner-facing | decision-determinism test (temp 0 invariant) |
| Rate / cost limit reached | Per-user request/token/cost cap exceeded | `reason_code=rate_or_cost_limit`, limit type, usage, cap | refuse new work; user sees rate/cost-limit state | rate/cost-cap test |
| Expired session | Session TTL elapsed on request | `reason_code=session_expired`, session ID, TTL | re-auth/resume prompt; user sees expired-session state | session-TTL test |

User-facing states must distinguish provider timeout, empty retrieval, low confidence, expired session,
invalid agent decision, and rate/cost limit reached.

## Phased Plan

### Phase 0 - Baseline, Reliability Bar, Dependency Reproducibility

- Record current tests, lint, leak checks, and dev eval when provider credentials/corpus are available.
- Classify current failures with the expanded taxonomy.
- Define reliability SLOs and Phase 1 exit criteria.
- Require eval artifacts to include model ID, provider, model params, prompt version, corpus version,
  chunk ID scheme, thresholds, dependency SHA, and git SHA.
- Replace the editable relative `genacademy-rag` dependency with a git SHA pin, or commit the exact PR
  plan that will do it.

### Phase 1 - Agent Reliability Diagnostics And Deterministic Decision Safety

- Extend teach diagnostics with the expanded taxonomy.
- Add fake-agent tests for invalid/missing actions, schema errors, malformed check questions, and
  citation mismatches.
- Assert decision temperature is `0`.
- Assert invalid/unparseable decisions safely refuse/escalate/stop.
- Add prompt-injection and input-validation tests.
- Improve only deterministic bugs that diagnostics expose.

### Phase 2 - Application Service Boundary And Concurrency Model

- Add UI-neutral services and typed DTOs for Teach, Quiz, Skill-Gap, auth/admin, review queue, and
  memory status.
- Make Gradio call those services before FastAPI is introduced.
- Document the sync/threadpool/worker boundary.
- Keep web-framework imports out of the core.

### Phase 3 - FastAPI/HTMX Edge, Validation, Security Gates

- Add FastAPI only under the web edge package.
- Use sync route handlers for blocking Coach calls by default.
- Add input validation and scope gates before expensive calls.
- Treat learner input, retrieved content, tool outputs, and model outputs as untrusted.
- Add route tests for member/admin access and redaction boundaries.

### Phase 4 - UX Latency, Progress, Resume, Accessibility

- Implement either HTMX SSE streaming for teach responses/progress or explicit progress states if SSE
  is deferred.
- Track TTFT if streaming lands.
- Add session resume across reload.
- Add distinct transient-error states.
- Use learner-facing labels such as Start Learning, Why did Coach do this?, and readable citations.
- Run keyboard, contrast, screen-reader label, and mobile checks.

### Phase 5 - Auth, Session, Review Queue Hardening

- Preserve the current cohort-gate framing until production auth is implemented.
- Add session TTL and resume semantics.
- Move review queue behind a repository interface.
- Add mentor/admin review states without exposing raw private learner text by default.

### Phase 6 - Corpus Versioning, Stable Chunk IDs, Retrieval Golden Set

- Add corpus manifest/versioning.
- Add a source map for stable citation references across re-ingest.
- Add re-ingest reference-survival tests.
- Add a retrieval golden set: query -> expected source/citation family.
- Defer reranking until the golden set shows a measured recall gap.

### Phase 7 - Observability, Eval Dashboards, Cost/Latency Tracking

- Add redacted structured logging with request/session IDs.
- Log every model call with model/version, step, latency, TTFT, tokens, estimated cost, retries,
  fallbacks, prompt version, and corpus version.
- Track system health: p95 latency, TTFT, provider errors, retry rate, token spend, and cost per
  conversation.
- Track response quality: eval scores, user flag rate, refusal rate, citation-resolution rate, and
  decision accuracy.

### Phase 8 - Datastore Seam, Provider Resilience, Rate/Cost Controls, Deployment Target

- Add datastore interfaces and an Alembic migration plan.
- Keep SQLite local/demo; add Postgres path for production/cohort scale.
- Add provider timeouts, retries with backoff/jitter, circuit breaker, fallback/degraded mode, and
  user-facing transient states.
- Add per-user request limits, token budgets, and cost caps.
- Treat Hugging Face Spaces as demo-only; use a managed container app plus managed Postgres for the
  production target when cohort persistence is needed.

### Phase 9 - Public Docs, Demo Polish, Optional MCP/API Future

- Keep public docs sanitized.
- Do not publish private corpus/eval/raw trace data.
- Treat future MCP as an API client of the same service boundary.
- Revisit explicit LangGraph only if durable memory, HITL interrupts, or multi-mode coordination
  outgrow `create_agent`.

## QA And Eval Plan

Required suites:

- unit tests for grounding, citations, deterministic grading, privacy, memory, and auth;
- fake-agent tests for decision safety;
- contract tests for the `genacademy-rag` adapter;
- retrieval golden-set eval;
- refusal and out-of-corpus eval;
- prompt-injection/security tests;
- performance/load tests tied to latency budgets;
- reproducible eval artifacts with model/dependency/corpus/prompt metadata.

Run before landing production-hardening PRs:

```bash
uv run pytest -q
uv run ruff check .
uv run python scripts/check_eval_leak.py
uv run python scripts/check_memory_leak.py
```

Provider-backed dev eval can run when credentials and local corpus are available:

```bash
uv run python scripts/eval_teach_loop.py --split dev
```

Do not run or tune against:

```bash
uv run python scripts/eval_teach_loop.py --split test
```

## First Three PRs

1. **Baseline + reliability bar + dependency pin**
   No behavior change. Add SLOs, baseline output, eval artifact requirements, expanded taxonomy, and
   replace or concretely schedule replacement of the editable `genacademy-rag` path.
   Acceptance: baseline eval artifacts carry the full Phase 0 reproducibility set — model ID, provider,
   model params, prompt version, corpus version, chunk ID scheme, thresholds, dependency SHA, and git
   SHA — and the leak checks pass. The `genacademy-rag` dependency is resolved one of two ways, no third
   option: (a) `pyproject.toml` pins an actual git SHA (replacing the editable relative path at
   `pyproject.toml:30`), or (b) a named follow-up PR or issue exists with an owner, a target date, and
   the exact pin target (repo + commit SHA) recorded in it. "Pinned or dated" with no owner/target does
   not pass.

2. **Teach diagnostics + regression harness + deterministic safety**
   Add structured reason codes, fake-agent/schema/invalid-action tests, decision-temperature invariant,
   invalid-output fallback, provider model/params in eval artifacts, and prompt-injection tests.
   Acceptance: fake-agent and invalid-output tests pass; decision temperature is asserted as `0`; every
   invalid decision falls back to `refuse_escalate` or `stop`.

3. **Application service boundary + concurrency decision**
   Add UI-neutral services and typed DTOs; make Gradio call services; document sync/threadpool/worker
   boundary; preserve current user-facing behavior.
   Acceptance: Gradio calls the service layer, typed DTO tests cover the boundary, and the documented
   sync/threadpool/worker rule is enforced in code review.

## Deferred

- React;
- direct `langgraph.*`;
- ElevenLabs voice;
- mock interview;
- multi-agent orchestration;
- hosted Pinecone as production truth before repeatable ingest/eval/smoke;
- reranking before a measured retrieval gap;
- immediate Postgres migration before the datastore seam;
- production LangSmith tracing before a privacy/data-egress decision.
