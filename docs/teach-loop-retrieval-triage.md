# Teach Loop Retrieval Triage

Date: 2026-06-16

## Question

Why did the dev teach-loop eval report 9/10 scenarios with zero retrieval coverage?

## Short Answer

The index is not empty, and the Week 1 Session 2 corpus is present. The zero-coverage rows were a
post-filter symptom: the retriever returned candidates for every dev scenario, but 9/10 scenarios had
top cosine similarity below the current `0.60` STOP threshold, so `require_citeable_spans` filtered all
spans before the agent could teach from them.

## Evidence

Command:

```bash
set -a; source .env; set +a
uv run python scripts/diagnose_teach_retrieval.py \
  --split dev \
  --limit 10 \
  --json-out eval/runs/teach-retrieval-dev-diagnostics.json
```

Observed, redacted:

- Collection: `coach_course`
- Local index: `1540` chunks from `33` ingested docs
- Week 1 Session 2 transcript is indexed: `155` chunks
- Dev split: `10` scenarios from `week1-session2-chat-questions.docx`
- Raw retrieval returned `20` candidates for every scenario
- Raw top-score summary:
  - min: `0.3452`
  - p50 nearest-rank: `0.4174`
  - max: `0.6109`
  - `>= 0.40`: `9/10`
  - `>= 0.50`: `3/10`
  - `>= 0.55`: `3/10`
  - `>= 0.60`: `1/10`
- Raw source-type hits across the 10 scenarios:
  - transcript: `136`
  - slide: `28`
  - handout: `26`
  - note: `10`
- Selected top scores matched raw top scores because the adapter deliberately reserves one slot for the
  globally top-scored candidate.
- Natural source-priority ordering would have demoted the top-scored candidate in `8/10` dev
  scenarios. That does not explain the zero-coverage symptom, because the reserved top-score slot still
  preserves the top candidate before STOP filtering, but it is a separate retrieval-quality signal to
  revisit after threshold calibration.

Seed comparison, redacted:

- Command:

  ```bash
  set -a; source .env; set +a
  uv run python scripts/diagnose_teach_retrieval.py \
    --split seed \
    --limit 20 \
    --json-out eval/runs/teach-retrieval-seed-diagnostics.json
  ```

- Raw retrieval returned `20` candidates for every seed scenario.
- Raw top-score summary:
  - min: `0.2093`
  - p50 nearest-rank: `0.4704`
  - max: `0.7416`
  - `>= 0.40`: `15/20`
  - `>= 0.50`: `9/20`
  - `>= 0.55`: `6/20`
  - `>= 0.60`: `4/20`
- Natural source-priority ordering would have demoted the top-scored candidate in `14/20` seed
  scenarios.

No raw eval question text or corpus snippets were printed or written.

## What This Rules Out

- **Not missing ingestion:** local Chroma/SQLite exist, the corpus has `1540` chunks, and the relevant
  transcript has indexed chunks.
- **Not total retrieval failure:** every scenario returned raw candidates.
- **Not source-priority causing zero coverage:** the adapter reserves one selected slot for the globally
  top-scored candidate, so the selected top score still equals the raw top score before STOP filtering.
  Natural source-priority ordering does often demote the top hit, so source-priority composition remains
  worth evaluating separately.
- **Not just an unauthenticated HF issue:** after adding `HF_TOKEN` to `.env`, the diagnostic loaded
  embeddings without the prior unauthenticated Hugging Face warning.

## Likely Cause

The initial `0.60` STOP threshold is too strict for this expanded, transcript-heavy Coach corpus and the
current `all-MiniLM-L6-v2` cosine score distribution. The Week-2 foundation explicitly warned that
Week-2 metrics and thresholds do not automatically transfer to the Coach corpus; they need
recalibration after ingestion.

This does not mean lowering the threshold blindly is safe. Negative controls still need to remain below
STOP. Initial redacted controls showed unrelated course-policy queries in the `0.22-0.38` range, while
many plausible course queries landed in the `0.40-0.60` range.

## Follow-Up

Calibration completed in `docs/teach-loop-threshold-calibration.md`; the default Coach STOP threshold is
now `0.40`.

Original calibration steps:

1. Run `scripts/diagnose_teach_retrieval.py` on `seed` and `dev`.
2. Add a small, non-private negative-control set for clearly out-of-corpus topics.
3. Pick a threshold that separates negative controls from plausible course questions.
4. Rerun the teach-loop eval.
5. Separately evaluate whether source-priority ordering is over-favoring slides/handouts after
   calibration, because natural priority order often demotes the top-scored hit.
6. If many plausible course questions still cluster below the chosen threshold, improve query rewriting
   or retrieval before lowering the threshold further.

The held-out `test` split was not used for tuning.
