# Eval Evidence First — design + build plan

Date: 2026-07-25
Branch: main
Status: DRAFT (awaiting independent second-model review per `AGENTS.md` gate #2)
Source: `/office-hours` session, 2026-07-25
Scope: one bounded slice. No change to the grounded core, the refusal path, the eval protocol, or the
frozen `test` split.

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
| Deployment shell | `Dockerfile`, HF Space | Unchanged; corpus is the only variable |

## 4. Approach

Four parts. None of them touch agent logic, grading, or refusal behaviour.

### 4.1 A 30-second eval entry point

A new top-level screen that answers four questions before any scrolling:

1. **What was measured.** 40 cases across 4 classes (16 happy, 9 edge, 5 known-failure, 10 adversarial),
   3 runs, 120 case-runs.
2. **What moved.** Citation F1 `0.444 → 0.594`. Turn p95 `11,328 ms → 8,275 ms`.
3. **What got worse.** Refusal precision `0.833 → 0.791`. Stated plainly, not buried.
4. **What it cost.** 1.3M evaluation tokens, `$0.00`, on `Qwen/Qwen3-30B-A3B-Instruct-2507`
   (open-weight, not a frontier API).

Held constant and worth stating: refusal recall `1.000` and retrieval recall@5 `1.000` across baseline
and current.

The existing 29 sections stay exactly as they are, one click below. They are correct for the reader who
continues; the problem is only that nothing earns that click.

**Decision:** build this as a separate page rather than a new hero inside the existing file, so the
submission artifact stays byte-stable and the two audiences do not fight over one document.

### 4.2 Public demo corpus (openly licensed only)

The course corpus stays local and unpublishable. The public instance indexes third-party material that
is explicitly licensed for reuse.

- **Primary: permissively licensed documentation.** LangChain (MIT), Hugging Face (Apache 2.0), public
  vendor documentation. Unambiguously redistributable, licence stated in the repository, and available
  by `git clone` rather than scraping.
- **Secondary: arXiv, checked per paper.** Verified 2026-07-25 against three of the intended canon:

  | Paper | ID | Licence |
  |---|---|---|
  | Attention Is All You Need | 1706.03762 | arXiv perpetual **non-exclusive** |
  | RAG (Lewis et al.) | 2005.11401 | arXiv perpetual **non-exclusive** |
  | Chain-of-Thought | 2201.11903 | **CC BY 4.0** |

  The arXiv non-exclusive licence leaves copyright with the author and grants *arXiv* distribution
  rights only. It grants the indexer nothing, so full text of those papers must not be hosted. CC-BY
  papers may be hosted. **Check the licence on each abs page; do not assume by venue or year**, though
  CC adoption does skew later. Non-CC papers are still usable as snippet-plus-link (below).
- **Display rule, applied regardless of license:** snippet + citation + link back to the canonical
  source. Never reconstitute a full document from retrieved spans. This matches the existing
  citation-at-retrieval contract in `AGENTS.md` §3.
- **Disable the slide-image card (FR-W9)** on the public instance. No image assets are published.

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
no API key, no rate limit, no cost, and no terms-of-service question. A metered scraping API also
conflicts with the `$0.00` cost claim that is part of the evidence story. Reserve HTML-to-markdown
crawling for sources with no repository behind them.

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

### 4.4 Repository hygiene

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
| Citations captured at retrieval | Unchanged, and reinforced by the snippet-plus-link display rule. |
| One retriever, source-prioritized | Unchanged. New corpus enters an existing indexable directory. |
| Agenticity shown in a trace | Unchanged. |
| No raw traces / corpus committed | Upheld. Public corpus is openly licensed; no learner text, no generated prose, no retrieved spans committed. |
| MINT restraint, `create_agent` boundary | Upheld. No new dependency, no `langgraph.*` import. |
| Pure core / thin view | Upheld. No web imports enter the core. |
| Reuse the Week-2 foundation | Upheld. No new chunker, embedder, schema, or eval harness. |
| Frozen `test` split | Untouched. |

**Same-embedder rule applies.** The index is `all-MiniLM-L6-v2` / 384-d. The public corpus is a *separate
collection*, ingested separately. It does not mix with the course collection.

## 6. Measurement integrity (important)

The Week-4 numbers describe a run against the **course corpus**, on dataset version `2026-06-24-plan1`,
generator SHA `31fa64b`, snapshot 2026-06-25. They are not claims about the public demo corpus.

Two rules:

1. **Label every number with the corpus and dataset version it came from.** The 30-second screen must
   not imply the metrics describe the public demo.
2. **Do not reuse the calibrated thresholds without checking them.** STOP 0.40 / CONFIRM 0.85 were
   calibrated against the course index. A different corpus with different embedding density may sit
   differently against those bands. If the public instance behaves differently, that is a recalibration
   task, and it is reported as a separate result rather than retrofitted onto the submitted baseline
   (`specs/roadmap.md`, Risk Caps, "Grader evolution").

## 7. Out of scope

Course-provider approval. Cohort auth hardening. Index seeding for cohort members. A new private
repository. Any change to grading, recovery, or the CONFIRM-band refusal work already queued in
`specs/roadmap.md`. This slice is presentation and reach only.

Also out of scope, and deliberately so, because the four-format adapter boundary in §4.2 means each can
be added later with no redesign: **HTML crawling** (Firecrawl or equivalent), **audio/video ingestion**
via `SSM-Transcriber`, **multimodal retrieval** over frames or images, and **generalising the app to an
arbitrary-corpus chatbot**. The last one is already latent, since corpus is a directory of files; it
needs no project and no rename. The differentiator worth generalising later is the evaluation layer, not
the chat layer.

## 8. Open questions for the reviewer

1. ~~Do enough of the intended arXiv canon carry CC-BY to form a usable corpus?~~ **Resolved 2026-07-25:
   no.** Two of three sampled flagship papers are arXiv non-exclusive. The corpus is now
   documentation-primary (MIT / Apache 2.0), with arXiv split into hostable CC-BY papers and
   snippet-plus-link for the rest. Remaining reviewer question: is snippet-plus-link display of a
   non-redistributable paper acceptable for a public demo, given the snippet comes from a locally built
   index rather than a licensed copy? Position taken: yes, it matches standard search and citation
   practice and the architecture already attaches a source reference to every span. Worth a second
   opinion.
2. Should the public Space keep the auth gate at all, given an openly licensed corpus? Keeping the code
   and defaulting it off for the public instance seems right, but it is a behaviour change worth review.
3. Is publishing the refusal-precision regression (`0.833 → 0.791`) the right call, or should the queued
   CONFIRM-band work land first? Current position: publish the honest number now.
4. Does the separate-page decision in §4.1 risk the two artifacts drifting out of sync, and if so should
   both render from `week4-eval-dashboard-data.json` through the same generator?

## 9. Done bar

- [ ] 30-second screen renders from `week4-eval-dashboard-data.json`; no hand-typed metrics.
- [ ] Every metric on it is labelled with corpus + dataset version.
- [ ] Public instance answers a grounded question with a citation and a working source link.
- [ ] Public instance refuses an out-of-corpus question and escalates, demonstrably.
- [ ] No image asset and no full-document reproduction served by the public instance.
- [ ] `ruff` clean, `pytest` green, `scripts/check_eval_leak.py` passing — output shown, not claimed.
- [ ] Reviewed by a different model or fresh context (`AGENTS.md` gate #2).
- [ ] `docs/INDEX.md` updated.
