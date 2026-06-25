# Week-4 Eval Dashboard - Design

> **Status:** design approved in chat on 2026-06-25. This spec covers the dashboard/report artifact for
> the Week-4 evaluation story. It does not change the eval harness, scorer, golden dataset, prompts, model
> provider, or product behavior.

## 1. Goal

Build a visually clear evaluation dashboard that answers:

> Did the Week-4 improvements measurably help the GenAcademy Coach without breaking grounded refusal
> safety?

The dashboard should help three audiences:

- **Evaluator/demo viewer:** understand the before/after result quickly.
- **Project owner/learner:** understand what improved, what still failed, and why.
- **Future AI/build session:** recover the current state without rereading chat history.

## 2. Artifact Split

Use a two-layer design.

### Public-safe committed dashboard

Committed under `docs/`:

- `docs/week4-eval-dashboard.html`
- `docs/week4-eval-dashboard-data.json`

This artifact is safe to keep in public Git history. It may include aggregate metrics, run IDs,
sanitized deltas, high-level failure categories, sanitized case IDs, and guardrail notes. It must not
include raw learner questions, generated tutor prose, retrieved span text, raw traces, secrets, private
screenshots, or private LangSmith URLs.

The dashboard should be useful even after the demo; it should not rely on "remove this later" as a
privacy control.

### Private local appendix

Local-only under ignored `localdocs/`:

- `localdocs/docs/week4-eval-dashboard-private-appendix.md`

This appendix may include private LangSmith project/dataset URLs, ignored eval artifact paths, richer
case watchlists, and local-only notes. It still must not copy raw learner/tutor/retrieved text unless the
owner explicitly requests that local private note.

Update `localdocs/INDEX.md` when adding the appendix.

## 3. Data Sources

The public dashboard uses a committed, redacted snapshot:

- source file: `docs/week4-eval-dashboard-data.json`
- generated/reviewed from ignored local artifacts under `eval/runs/`
- no dependency on ignored files at dashboard-view time

Snapshot contents:

- baseline aggregate metrics from `golden-baseline-20260624.json`
- current-main full LangSmith run aggregates for `r1`, `r2`, and `r3`
- computed current mean and baseline deltas
- class/segment counts
- sanitized remaining failure modes
- guardrail status and caveats
- provenance fields naming the local run IDs and dates, but not raw trace paths or private URLs

Local-only appendix contents:

- ignored eval artifact filenames
- private LangSmith project/dataset URLs
- richer explanation of which local artifacts support each dashboard section

## 4. Dashboard Layout

The default page is a guided analytical report, not a dense BI workbench.

1. **Hero verdict**
   - one-sentence verdict: citation and latency improved; retrieval/refusal recall held; false-refusal
     tradeoff remains
   - four to six KPI cards with baseline/current/delta

2. **Metric delta panel**
   - baseline vs current-main mean
   - show denominator caveat for task completion: baseline excluded two infra errors; current has no infra
     exclusions in the three runs
   - include task completion, teachable completion, citation F1, refusal P/R/F1, tool F1, retrieval
     recall@5, turn p50/p95, case p50/p95, tokens, and cost note

3. **Three-run variance**
   - compact run table for `r1`, `r2`, `r3`
   - small chart for citation F1 and turn p95 movement across runs
   - call out that tiny-N refusal precision is sensitive to one or two cases

4. **Quality and safety guardrails**
   - refusal recall: held at `1.000`
   - retrieval recall@5: held at `1.000`
   - no scorer-hack changes
   - no STOP-threshold lowering
   - no frozen `test` split usage
   - deterministic metrics remain the official scorer; LLM-as-judge is optional/future only

5. **Latency and tool-loop attribution**
   - chart per-tool measured latency share across current runs
   - explain that check generation and retrieval dominate measured tool time
   - show average tool calls per case, retrieval cache hits, max repeated tool count, and agent attempts

6. **Remaining failure modes**
   - stable false refusals for `happy_014` and `known_failure_001`
   - `edge_002` false refusal in two of three runs
   - citation improved but remains imperfect
   - `edge_008` no current infra failure, but remains on watchlist

7. **User and builder perspective**
   - user view: the tutor is faster and cites better, but a few teachable cases still refuse
   - builder view: retrieval is healthy; remaining work is mostly post-retrieval decision behavior and
     false-refusal calibration

8. **Evidence and next steps**
   - list public-safe run IDs
   - point to the committed handoff doc
   - state that private LangSmith links live in the local appendix/submission notes

## 5. Visual Design

Use a restrained analytics-report style:

- calm neutral background, white/very-light panels, 8px card radius
- mixed palette: teal for quality wins, amber for caveats, slate for neutral structure, muted red only for
  regressions or remaining risk
- no decorative orbs, hero gradients, stock imagery, or marketing composition
- charts should be simple and readable: KPI deltas, slope/line charts, horizontal bars, and compact
  tables
- first viewport should answer the main question without scrolling
- dense enough for evaluation work, but with enough spacing that it can be used in a Loom walkthrough

The dashboard is a report artifact, not an app landing page.

## 6. Implementation Shape

Add a small static generator:

- `scripts/build_week4_eval_dashboard.py`

Responsibilities:

- load `docs/week4-eval-dashboard-data.json`
- validate public-safe fields and fail on forbidden keys such as raw prompt/prose/span/trace fields
- compute display-ready deltas when possible
- write `docs/week4-eval-dashboard.html`
- optionally write/update `localdocs/docs/week4-eval-dashboard-private-appendix.md` when local-only
  context is available

The generated HTML should be self-contained:

- no external CDN dependencies
- no framework imports
- vanilla HTML/CSS/JS only
- works by opening the file directly in a browser

## 7. Privacy and Guardrails

Public dashboard guardrails:

- no raw learner text
- no generated tutor prose
- no retrieved span text
- no raw traces
- no secrets or environment values
- no private LangSmith URLs
- no frozen `test` split data
- no RAGAS/LLM-judge claims beyond "optional/future" unless a separate judge-egress decision exists
- no scorer-hack framing or hidden denominator changes

The public data snapshot should include an explicit `privacy_reviewed: true` field and a short
`redaction_policy` string.

## 8. Validation

Before handoff:

- run the generator
- verify the generated HTML opens locally
- inspect the first viewport and mobile/narrow width for text overlap
- verify the key metrics reconcile with `docs/week4-eval-progress-handoff.md`
- scan public dashboard/data files for forbidden private fields and private URL patterns
- run `git diff --check`

No full eval run is required for this dashboard work because it reports already completed eval artifacts.

## 9. Non-goals

- no product or agent behavior changes
- no eval scorer changes
- no new LangSmith upload
- no model/provider bakeoff
- no LLM-as-judge implementation
- no public copy of private LangSmith links or raw trace content
