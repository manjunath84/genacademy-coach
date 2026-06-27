# Docs Index

This file is the navigation map for new AI sessions and human reviewers. It is not a second
constitution. If anything here conflicts with `AGENTS.md`, `specs/`, or `docs/decisions.md`, those
source-of-truth files win.

## Start Here

Read these before planning or building:

1. `AGENTS.md` - project working agreement, guardrails, review gates, privacy rules.
2. `docs/INDEX.md` - this routing map.
3. `specs/mission.md` - product purpose, audience, in/out of scope.
4. `specs/tech-stack.md` - stack choices, binding implementation guardrails, eval protocol.
5. `specs/roadmap.md` - current priority order and what is deferred.
6. `docs/decisions.md` - settled architecture decisions and rejected alternatives.
7. `docs/build-learnings.md` - non-obvious lessons and the messy reasoning behind changes.

If `localdocs/INDEX.md` exists, read it only for local/private context relevant to the task. Never
commit or quote `localdocs/` content unless the owner explicitly asks.

## Current Priority

For post-Week-4 work, start with:

- `docs/agentic-orchestration-improvement-review.md` - measured diagnosis and orchestration options.
- `docs/superpowers/plans/2026-06-26-citation-provenance-audit.md` - next approved slice: audit
  citation misses before product behavior changes.
- `docs/superpowers/plans/2026-06-27-role-keyed-provenance.md` - proposed next product-behavior slice:
  role-keyed provenance plus deterministic check-span selection.
- `docs/citation-provenance-audit-current-main-r3-20260624.json` - public-safe audit output with
  review buckets, source-family signals, and heuristic citation-F1 ceilings.
- `docs/week4-eval-progress-handoff.md` - detailed eval history, remaining failures, and warnings.
- `docs/week4-eval-dashboard-data.json` - redacted dashboard metrics used for trend evidence.

The current architectural stance is conservative: fix citation provenance, check-span selection, and
false-refusal precision before adding broader multi-agent orchestration or explicit LangGraph graphs.

## Task Routing

Use this table to avoid opening the whole docs folder blindly.

| Task | Read |
|---|---|
| New feature or architecture change | `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `docs/decisions.md` |
| Teach-loop behavior | `docs/teach-loop-status.md`, `docs/teach-loop-threshold-calibration.md`, `docs/week4-eval-progress-handoff.md` |
| Citation, provenance, or eval failures | `docs/week4-eval-plan.md`, `docs/week4-eval-progress-handoff.md`, `docs/agentic-orchestration-improvement-review.md`, `docs/superpowers/plans/2026-06-26-citation-provenance-audit.md`, `docs/superpowers/plans/2026-06-27-role-keyed-provenance.md`, `docs/citation-provenance-audit-current-main-r3-20260624.json` |
| Retrieval/index changes | `docs/genacademy-rag-foundation.md`, `docs/foundation-adapter-spec.md`, `docs/teach-loop-retrieval-triage.md`, `specs/tech-stack.md` |
| UI/demo changes | `docs/architecture-diagrams.md`, `docs/teach-loop-status.md`, relevant UI/demo plans in `docs/superpowers/plans/` |
| Deployment | `docs/hugging-face-deployment-plan.md`, `docs/production-roadmap.md` |
| Learning/write-up material | `docs/build-learnings.md`, `docs/agent-concepts-from-genacademy-coach.md`, `docs/agentic-orchestration-improvement-review.md` |

## Source-Of-Truth Hierarchy

Use this order when files disagree:

1. `AGENTS.md` for guardrails and workflow gates.
2. `specs/` for product scope, tech constraints, roadmap, and eval protocol.
3. `docs/decisions.md` for settled architecture decisions.
4. Current approved plan in `docs/superpowers/plans/` for the active implementation slice.
5. Handoffs, status notes, and learnings for context and history.

Historical files are useful evidence, but they do not override the active roadmap or guardrails.

## Key Reference Docs

### Architecture And Decisions

- `docs/decisions.md` - architecture decision records AD-1 through AD-12.
- `docs/architecture.md` - trust boundary and adapter overview.
- `docs/architecture-diagrams.md` - Mermaid diagrams for product surface, runtime, state, failure paths,
  eval boundaries, and roadmap.
- `docs/agentic-orchestration-improvement-review.md` - post-feedback orchestration analysis, options,
  and final priority order.
- `docs/production-roadmap.md` - longer-term production hardening roadmap.

### Foundation And Retrieval

- `docs/genacademy-rag-foundation.md` - binding reuse contract for the Week-2 RAG foundation.
- `docs/foundation-adapter-spec.md` - adapter surface between Coach and the Week-2 package.
- `docs/teach-loop-retrieval-triage.md` - retrieval diagnosis and likely causes.
- `docs/teach-loop-threshold-calibration.md` - confidence-band evidence and calibration notes.

### Eval And Week-4 Evidence

- `docs/week4-eval-plan.md` - eval design and metric map.
- `docs/week4-eval-progress-handoff.md` - main Week-4 execution handoff.
- `docs/week4-eval-dashboard-data.json` - redacted dashboard data.
- `docs/week4-eval-dashboard.html` - local dashboard artifact.
- `docs/week4-latency-and-failure-fix-plan.md` - latency and failure remediation plan.
- `docs/citation-provenance-audit-current-main-r3-20260624.json` - public-safe citation audit output
  generated from a local current-main golden run.

### Build History And Learning

- `docs/build-learnings.md` - reusable build lessons, newest first.
- `docs/teach-loop-status.md` - detailed teach-loop verification history.
- `docs/open-decisions-handoff.md` - resolved early handoff, historical.
- `docs/agent-concepts-from-genacademy-coach.md` - learning notes that explain agent concepts through
  this project.

### Superpowers Plans And Specs

- `docs/superpowers/specs/2026-06-15-genacademy-coach-mvp-design.md` - original MVP design anchor.
- `docs/superpowers/specs/2026-06-23-week4-eval-execution-design.md` - Week-4 eval design.
- `docs/superpowers/specs/2026-06-25-week4-eval-dashboard-design.md` - dashboard design.
- `docs/superpowers/plans/` - implementation plans and review handoffs by date.

## Privacy Notes

Committed docs may contain redacted IDs, aggregate counts, public-safe architecture notes, and safe
trace summaries. They must not contain raw course corpus, raw learner questions, generated tutor prose,
retrieved span text, secrets, private URLs, or frozen `test` split content.

When creating a new doc, prefer:

- public-safe summaries in `docs/`
- active implementation plans in `docs/superpowers/plans/`
- private/local context in ignored `localdocs/`, with `localdocs/INDEX.md` updated
