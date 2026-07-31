# Eval Evidence First — design + build plan

Date: 2026-07-25 · revised 2026-07-31 after independent review
Branch: main
Status: **PROPOSED**, not active. `specs/roadmap.md` names the Tutor Workspace Phase-1 slice as the
active build item (that slice shipped in PR #71, so the roadmap is stale rather than contradicted).
This document does not become the active slice until an owner-approved reprioritization is recorded in
`specs/roadmap.md`.
Review: Codex independent pass 2026-07-31 returned 8 × P1 / 3 × P2 (see §8). All P1s addressed; the
revision itself is unreviewed and needs a second pass.
Source: `/office-hours` session, 2026-07-25
Scope: one bounded slice. No change to the grounded core, the refusal path, the eval protocol, or the
frozen `test` split. **Two code changes are in scope** and were missed in the first draft: provenance
fields on `RetrievedSpan` (§4.2.1) and the public-instance abuse boundary (§4.4).

---

## 1. Problem

The Coach's strongest engineering evidence is invisible to an external technical reader.

- The deployed Space serves an empty corpus, so the product cannot be tried.
- `docs/week4-eval-dashboard.html` carries 29 sections and opens with "Tutor Safety Contract" and
  "Evaluation Setup & Scope" before the first number. That ordering is correct for an evaluator obliged
  to read it and wrong for a reader who arrives cold and leaves in 30 seconds.
- `SSM-Transcriber` (ingest), `knowledge-base` (notes with retrieval metadata), and this repo (grounded
  teaching + measurement) form a working pipeline, and nothing published says they connect.

The gap is presentation and reach, not capability. Nothing in this plan changes what the system does.

## 2. Audience

**External technical reader**, arriving cold with no context, evaluating engineering capability in
30 to 90 seconds. Not a cohort learner. Cohort access, course-provider approval, and cohort auth
hardening are explicitly out of scope for this slice and remain parked.

## 3. What already exists (reused, not rebuilt)

| Asset | Path | Role in this slice |
|---|---|---|
| Eval dashboard | `docs/week4-eval-dashboard.html` | Kept intact as the deep artifact |
| Dashboard data | `docs/week4-eval-dashboard-data.json` | Source of every number shown |
| Dashboard generator | `scripts/build_week4_eval_dashboard.py` | Extended, not replaced |
| Gradio app | `src/genacademy_coach/web/gradio_app.py` | Public instance, corpus swapped |
| Ingestion | `src/genacademy_coach/corpus.py` (`INDEXABLE_DIRS`) | New corpus lands in `corpus/notes` |
| Retrieval foundation | `genacademy-rag` adapter | Unchanged |
| Deployment shell | `Dockerfile`, HF Space | Unchanged; corpus plus the §4.2.1 provenance fields and the §4.4 abuse boundary |

## 4. Approach

Four parts. None of them touch agent logic, grading, or refusal behaviour.

### 4.1 A 30-second eval entry point

A new top-level screen that answers four questions before any scrolling:

1. **What was measured.** 40 cases across 4 classes (16 happy, 9 edge, 5 known-failure, 10 adversarial),
   3 runs, 120 case-runs.
2. **What moved.** Citation F1 `0.444 → 0.594`. Turn p95 `11,328 ms → 8,275 ms`.
3. **What got worse.** Refusal precision `0.833 → 0.791`. Stated plainly, not buried.
4. **What it cost.** 3,902,709 tokens across the three current runs (r1 1,310,309 / r2 1,380,538 /
   r3 1,211,862) on `Qwen/Qwen3-30B-A3B-Instruct-2507`, an open-weight model rather than a frontier
   API. **Cost is not reliably recorded:** r1 logged `$0.00` because pricing configuration was
   missing, r2 logged `$0.147` and r3 `$0.130`, and `current_mean.cost_usd` is `null`. State
   "pricing not recorded for all runs" and show the two runs that have a figure. Do **not** present
   `$0.00` as the cost of the evaluation.

Held constant and worth stating: refusal recall `1.000` and retrieval recall@5 `1.000` across baseline
and current.

**Comparison caveat that must appear wherever these numbers do.** The baseline is a **single run**;
"current" figures are the **mean of three repeated runs over the same 40 cases**. That is 120
case-runs, not 120 independent cases, and a single run compared against a mean of three is not a
like-for-like comparison. Show the run-to-run range alongside every current mean, give refusal
metrics as counts rather than three-decimal rates given the small denominators, and do not let
three-decimal precision imply more certainty than 40 cases support.

The existing 29 sections stay exactly as they are, one click below. They are correct for the reader who
continues; the problem is only that nothing earns that click.

**Decision:** build this as a separate page rather than a new hero inside the existing file, so the
submission artifact stays byte-stable and the two audiences do not fight over one document.

### 4.2 Public demo corpus (openly licensed only)

The course corpus stays local and unpublishable. The public instance indexes third-party material that
is explicitly licensed for reuse.

**Containment rule (governs everything below).** The hosted index is a **copy**. The retrieval
foundation persists full chunk text and returns it at query time, so uploading an index to the Space is
copying and hosting that text regardless of what the UI displays. Therefore: **only material that is
redistributable may enter the public index at all.** "Built locally" does not cure a missing licence,
and a short snippet in the UI does not cure a full copy on the server. Display rules are a second line
of defence, never the first.

- **Primary: explicitly licensed documentation.** LangChain and Hugging Face documentation, obtained by
  `git clone` rather than scraping.

  **"Public vendor documentation" is not a licensing category and must not appear in the manifest.**
  Record per source: exact repository, subpath, pinned revision or commit, the licence that actually
  covers *that subpath*, any exceptions, required attribution text, and Apache-2.0 `NOTICE`
  obligations where they apply. A repository's software licence does not automatically cover every
  documentation asset inside it, and `git clone` does not settle a site's terms of service. Any source
  whose licence cannot be stated in those terms is excluded.

- **Secondary: arXiv, CC-licensed papers only.** Verified 2026-07-25 against three of the intended
  canon:

  | Paper | ID | Licence | Public index |
  |---|---|---|---|
  | Attention Is All You Need | 1706.03762 | arXiv perpetual **non-exclusive** | **Excluded** |
  | RAG (Lewis et al.) | 2005.11401 | arXiv perpetual **non-exclusive** | **Excluded** |
  | Chain-of-Thought | 2201.11903 | **CC BY 4.0** | Included, with attribution |

  The arXiv non-exclusive licence leaves copyright with the author and grants *arXiv* limited
  distribution rights and the indexer nothing; arXiv's own reuse guidance says further reuse may
  require the copyright holder's permission.

  **Revised position (was open question 1; the earlier snippet-plus-link argument is withdrawn).**
  Non-CC papers are excluded from the public index entirely, not merely from display. The
  search-engine analogy does not hold: a search engine helps a user *locate* a work, while this system
  *teaches from* its content, which is a different use. Fair use is jurisdiction- and fact-specific
  with no safe snippet length, and that is not a foundation for a public artifact whose whole purpose
  is to demonstrate rigour. Non-CC papers remain usable in the **local** instance, where reading
  papers you may lawfully read is a different act from publishing an index of them.

  **Check the licence on each abs page; do not assume by venue or year**, though CC adoption skews
  later. If the CC-licensed subset is too thin, the corpus is documentation-only. That is an
  acceptable outcome.

- **Display rule (second line of defence, not the licence argument):** snippet + citation + link back
  to the canonical source, and never reconstitute a full document from retrieved spans. This matches
  the citation-at-retrieval contract in `AGENTS.md` §3.
- **Disable the slide-image card (FR-W9)** on the public instance. No image assets are published.

#### 4.2.1 Provenance metadata is a code change, not a corpus swap

The done bar promises a working source link. The current types cannot deliver one:

- `RetrievedSpan` (`src/genacademy_coach/teach_types.py:45`) carries `chunk_id, doc_id, text, score,
  title, source_type, page_or_section`. There is **no URL, licence, or canonical-reference field**.
- `source_label()` composes a display **label**, not a link.
- `corpus.py:48` sets `title=path.name`, so a citation would render as `1706.03762.pdf` rather than
  the paper's title, and `stored_path` is a local filesystem path.

Required, and in scope for this slice:

1. A **source manifest** keyed by `doc_id`, carrying canonical URL, human title, licence identifier,
   attribution string, pinned revision, and any `NOTICE` text.
2. **Retrieval-time propagation** of those fields onto `RetrievedSpan`, so provenance travels with the
   evidence rather than being reconstructed at render time. Reconstructed citations are a correctness
   bug under `AGENTS.md` §3.
3. **UI rendering** of citations as links plus the attribution the licence requires.

This corrects §3's "corpus is the only variable" and the claim in §4.3 that nothing but the corpus
changes. It is a small, additive metadata change, but it is a change, and the done bar depends on it.

#### Ingestion is an adapter boundary, not a component

`src/genacademy_coach/corpus.py:13` defines `INDEXABLE_SUFFIXES = {".md", ".pdf", ".pptx", ".docx"}`
over `INDEXABLE_DIRS = ("notes", "transcripts", "slides", "handouts")`.

Every ingestion tool is therefore a **pre-processor whose only contract is to emit one of those four
formats into one of those four directories.** No ingestion tool is part of the Coach, appears in its
dependency graph, or requires a design change to add. This keeps the `AGENTS.md` §3 "pure core" boundary
intact and means new sources are additive by construction.

| Source type | Adapter | Emits | Needed for this slice |
|---|---|---|---|
| PDF papers (arXiv) | `SSM-PDFTool` | `.pdf` / `.md` | **Yes** |
| Markdown docs in public repos | `git clone` + copy | `.md` | **Yes** |
| Websites with no repo behind them | Firecrawl or equivalent HTML-to-markdown | `.md` | No, later |
| Audio / video | `SSM-Transcriber` | `.md` transcript, cite to timestamp | No, later |

**Printing Press** (`printingpress.dev`) is not an adapter and does not belong in the table above. It is
an adapter *generator*: given an API spec, a website, or a project, it emits a Go CLI, a Claude Code
skill, an OpenClaw skill, and an MCP server. It would be the tool used to *build* a repeatable
ingestion CLI for a source hit often enough to justify one. Not needed for this slice, where the
primary corpus arrives by `git clone`, and it adds Go 1.26.3+ and Node to the toolchain.

**For this slice, prefer `git clone` over scraping.** LangChain (MIT) and Hugging Face (Apache 2.0)
documentation is markdown in public repositories. Cloning gets the same content with a stated license,
no API key, no rate limit, and a pinnable revision. Reserve HTML-to-markdown crawling for sources with
no repository behind them, and note that cloning still does not settle a site's terms of service or
prove a subpath's licence (see §4.2).

**Video is transcript-first, not multimodal.** Transcribe, index the text, cite back to the timestamp.
Multimodal retrieval is explicitly deferred in `specs/roadmap.md` (future pull-in #11, and it sits late
in the cut order), it would require a second collection because the index is `all-MiniLM-L6-v2` / 384-d
and vision embeddings occupy a different space, and it degrades the citation contract: a transcript span
cites a clickable timestamp, a retrieved frame cites nothing a learner can verify. It is earned only by
a measured retrieval gap that text cannot close.

**Rejected corpus options and why:**

- *Author's own study notes.* Almost certainly the author's own expression, but they make the demo about
  a specific course rather than about material the reader can independently judge, and pre-written notes
  exercise no part of the ingestion pipeline.
- *Third-party video transcripts and newsletter posts.* Publicly viewable is not the same as licensed for
  reuse. Platform terms restrict downloading, and the content remains copyrighted.

### 4.3 Pipeline landing page

One page declaring the three repos as one system, structured as a case study: the problem, the
architecture, what broke, and what was measured after fixing it. Linked from each repo's README.

### 4.4 Public-instance abuse boundary (required before any public launch)

A public instance is a **generative endpoint pointed at a paid provider account**. Removing the auth
gate without a spend boundary exposes the owner's provider balance to anyone who finds the URL. The
roadmap defers per-user cost caps (`specs/roadmap.md`, future pull-in #5), so this slice must not
quietly consume that deferral.

Therefore, for the public instance:

1. **Keep the auth gate on.** It already exists, it is already tested, and it is the cheapest bound.
   A hiring manager receiving a demo credential is not meaningful friction.
2. **Global spend cap plus kill switch**, independent of auth. A hard ceiling that stops serving
   rather than degrading, checked before the provider call, not after.
3. **Rate limiting and bounded concurrency** per session and in total.

None of these are optional-if-auth-is-on. Auth bounds *who*, not *how much*: a single credential
handed to five readers can still run the bill up. If any of the three is absent, the public instance
does not launch.

### 4.5 Repository hygiene

Enable the pre-push credential guard before further public pushes:

```
gstack-config set redact_prepush_hook true
```

Roughly 970 MB of unpublishable material sits in the working tree, correctly untracked (0 files under
`corpus/`, `data/`, `traces/` are in git) but protected only by `.gitignore` and operator discipline.

## 5. Guardrail compliance

| Guardrail (`AGENTS.md` §3) | Effect of this slice |
|---|---|
| Grounded or it refuses | Unchanged. No prompt, threshold, or refusal-gate edits. |
| Answerability evidence-bound | Unchanged. STOP 0.40 / CONFIRM 0.85 logic untouched. |
| Citations captured at retrieval | **Extended, not unchanged.** §4.2.1 adds canonical URL, licence, and attribution to `RetrievedSpan` at retrieval time. Reconstructing them at render time would violate this guardrail. |
| One retriever, source-prioritized | Unchanged. New corpus enters an existing indexable directory. |
| Agenticity shown in a trace | Unchanged. |
| No raw traces / corpus committed | Upheld, and extended: the §4.2 containment rule bars non-redistributable text from the hosted index, not just from the repo. No learner text, generated prose, or retrieved spans committed. |
| MINT restraint, `create_agent` boundary | Upheld. No new dependency, no `langgraph.*` import. |
| Pure core / thin view | Upheld. No web imports enter the core. |
| Reuse the Week-2 foundation | Upheld. No new chunker, embedder, schema, or eval harness. |
| Frozen `test` split | Untouched. |

**Same-embedder rule applies.** The index is `all-MiniLM-L6-v2` / 384-d. The public corpus is a *separate
collection*, ingested separately. It does not mix with the course collection.

## 6. Measurement integrity (important)

The Week-4 numbers describe a run against the **course corpus**, on dataset version `2026-06-24-plan1`,
generator SHA `31fa64b`, snapshot 2026-06-25. They are not claims about the public demo corpus.

Three rules:

1. **Label every number with the corpus and dataset version it came from.** The 30-second screen must
   not imply the metrics describe the public demo.
2. **Labels alone do not prevent overclaiming.** Also state, wherever the numbers appear, that the
   baseline is a single run while current values are the mean of three repeated runs over the same 40
   cases; show run-to-run ranges; give refusal metrics as counts alongside rates, because the
   denominators are small; and do not report cost as `$0.00` (see §4.1).
3. **Threshold validation is a launch gate, not a follow-up.** STOP 0.40 / CONFIRM 0.85 were
   calibrated against the course index. A different corpus with different embedding density may sit
   differently against those bands. "If the public instance behaves differently" is post hoc and
   therefore not a control. **Before launch**, measure score distributions on the public index for
   known-good and known-bad queries, broken out by `source_type`, and either confirm the existing
   bands or set and record new ones. Failing that measurement blocks launch. Any recalibration is
   reported as a separate versioned result, never retrofitted onto the submitted baseline
   (`specs/roadmap.md`, Risk Caps, "Grader evolution").

## 7. Out of scope

Course-provider approval. Cohort auth hardening. Index seeding for cohort members. A new private
repository. Any change to grading, recovery, or the CONFIRM-band refusal work already queued in
`specs/roadmap.md`. This slice is presentation and reach only.

Also out of scope, and deliberately so, because the four-format adapter boundary in §4.2 means each can
be added later with no redesign: **HTML crawling** (Firecrawl or equivalent), **audio/video ingestion**
via `SSM-Transcriber`, and **multimodal retrieval** over frames or images.

**Generalising the app to an arbitrary-corpus chatbot** is also out of scope, and the earlier claim
that it "needs no project and no rename" was wrong. Pointing the *index* at another corpus is cheap,
but the surrounding product is domain-specific: `source_type` prioritisation assumes
slides/handouts/notes/transcripts, mentor escalation assumes a cohort, and the learner-facing copy
assumes a course. Generalising is cheaper than a rewrite, not free. The differentiator worth
generalising later is the evaluation layer, not the chat layer.

## 8. Review history and resolved questions

Independent second-model review (Codex, `codex-cli` 0.145.0, `model_reasoning_effort=high`) ran
2026-07-31 against this document plus `AGENTS.md`, `specs/roadmap.md`, and `src/genacademy_coach/`.
Verdict: **changes required before merge**, 8 × P1 and 3 × P2. All P1s are addressed above. The
findings that changed the design:

| # | Finding | Resolution |
|---|---|---|
| 1 | Snippet-plus-link is not permission for non-CC papers | Position **withdrawn**. Non-CC arXiv excluded from the public index entirely (§4.2). |
| 2 | Index construction is exposure separate from display | Containment rule added; the hosted index may hold only redistributable text (§4.2). |
| 3 | Cost headline false: 1.3M is a per-run mean, `$0.00` is missing pricing config | Corrected to 3,902,709 tokens across three runs, cost reported as not reliably recorded (§4.1). |
| 4 | `RetrievedSpan` has no URL or licence field, so "working source link" is unbuildable | Provenance metadata scoped as an in-slice code change (§4.2.1). |
| 5 | "Public vendor documentation" is not a licensing category | Per-source manifest with repo, subpath, revision, licence, attribution, `NOTICE` (§4.2). |
| 6 | Threshold validation was prose, not a gate | Promoted to a pre-launch blocking measurement (§6.3, done bar). |
| 7 | Priority conflicts with `specs/roadmap.md` | Status changed to PROPOSED pending an owner-approved roadmap entry (header). |
| 8 | Auth-off with no abuse boundary exposes the provider balance | Auth stays on; spend cap, kill switch, and rate limiting required (§4.4). |

Two P1 narrowings applied rather than accepted wholesale, recorded for the next reviewer:

- Finding 1 governs the **public** index only. Indexing a lawfully readable paper on the local
  instance is a different act from publishing an index of it, and this document already separates the
  two instances.
- Finding 7 is roadmap **staleness**, not contradiction: the Tutor Workspace Phase-1 slice named as
  active in `specs/roadmap.md` shipped in PR #71. The fix is the same either way.

### Still open

1. Does the separate-page decision in §4.1 risk the two artifacts drifting out of sync, and should both
   render from `week4-eval-dashboard-data.json` through the same generator? (P2, unresolved.)
2. Is publishing the refusal-precision regression (`0.833 → 0.791`) the right call? Position: yes,
   publish now with counts and run-to-run range. Codex concurred. Recorded as settled unless
   challenged.
3. Which documentation subpaths survive the §4.2 manifest requirement? Not yet enumerated, and it
   determines corpus size. Blocks `/spec-team`.

## 9. Done bar

Licensing and safety gates, all blocking:

- [ ] Source manifest exists: every public-corpus item lists repo, subpath, pinned revision, licence,
      attribution, and `NOTICE` text where applicable.
- [ ] No non-redistributable text present **in the hosted index**, verified against the manifest, not
      just absent from the UI.
- [ ] Global spend cap, kill switch, and rate limiting live on the public instance; auth gate on.
- [ ] Pre-launch threshold validation run on the public index: score distributions for known-good and
      known-bad queries by `source_type`, with bands either confirmed or reset and recorded.

Product:

- [ ] 30-second screen renders from `week4-eval-dashboard-data.json`; no hand-typed metrics.
- [ ] Every metric labelled with corpus + dataset version, and carrying the single-run-vs-mean-of-three
      caveat, run-to-run ranges, and refusal counts.
- [ ] No `$0.00` cost claim anywhere in the artifact.
- [ ] `RetrievedSpan` carries canonical URL, licence, and attribution from retrieval, not render.
- [ ] Public instance answers a grounded question with a citation rendering as a **working link** and
      the attribution its licence requires.
- [ ] Public instance refuses an out-of-corpus question and escalates, demonstrably.
- [ ] No image asset and no full-document reproduction served by the public instance.

Process:

- [ ] `ruff` clean, `pytest` green, `scripts/check_eval_leak.py` passing — output shown, not claimed.
- [x] Reviewed by a different model or fresh context (`AGENTS.md` gate #2) — Codex, 2026-07-31.
- [ ] Re-review after this revision, since the P1 fixes are substantial and unreviewed.
- [ ] `specs/roadmap.md` carries an owner-approved entry for this slice, or the status stays PROPOSED.
- [x] `docs/INDEX.md` updated.
