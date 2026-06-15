# Corpus (local staging — content is **never** committed)

This folder is where the tutor's retrieval corpus is staged before ingestion. **Only this layout +
README + the `.gitkeep` placeholders are version-controlled** — every actual source file (`.md`, `.pptx`,
`.pdf`, `.docx`, transcripts, indexes) stays out of git via `.gitignore`. The content is the builder's
own course material, used locally; we don't republish it.

Corpus = **the builder's own content** (own deep-notes + own transcripts + course slides/handouts the
builder received as a student). No external dataset, no permission dependency. See
[`../docs/build-learnings.md`](../docs/build-learnings.md) for why.

## Drop-zones, by retrieval priority

Ranked by the MVP teaching policy: use slides and handouts as the primary course artifacts, then use
notes to fill gaps and transcripts as support/fallback. The earlier extraction learning still matters:
deck speaker-notes were empty, so slide text may need support from handouts, notes, or transcripts.

| Folder | What goes here | Tier | Why |
|---|---|---|---|
| `slides/` | Lecture decks — **`.pptx` preferred**, `.pdf` fallback | **1 — primary** | The official lesson spine and first source to cite when enough text is available. |
| `handouts/` | Reference PDFs/docs (Caching, LlamaIndex, Field Guide = L6, token-usage, guidebook) | **1 — primary** | Deeper official/reference explanations; best source for topic depth. |
| `notes/` | The builder's own deep-notes `.md` (Lessons 1–5, 7, 8) | 2 — gap fill | Plain-English explanations used when slides/handouts are thin. |
| `transcripts/` | Session-recording transcripts (`.md`) | 3 — support/fallback | Spoken narration and examples; useful but noisy, so trim/tag filler at ingest. |

## Naming & chunk convention

Keep source filenames or normalize to `week<N>-<session|lesson>-<slug>.<ext>`. The chunker emits a
header of **`week · title · section/slide`** per chunk, so each retrieved span is citable back to its
origin.

## Collection checklist (update as you gather)

**Tier 2 — gap fill / Tier 3 — support:**
- [x] `notes/` — own deep-notes for L1–5, 7, 8
- [ ] `notes/` — Lesson 6 enters as the Field Guide **PDF** in `handouts/` (author a `.md` only if retrieval is weak)
- [x] `transcripts/` — Week 1 · Session 1 (staged, cleaned from VTT)
- [x] `transcripts/` — Week 1 · Session 2 (staged)
- [x] `transcripts/` — Week 2 · Session 1 (staged)
- [x] `transcripts/` — Week 2 · Session 2 (staged — ⚠️ **partial**: source starts at `02:00:43`, ~12.5k words, no speaker labels; likely the Q&A/demo tail only)
- [x] `transcripts/` — Week 3 · Session 1 (staged)
- [x] `transcripts/` — Week 3 · Session 2 (staged)

> Transcripts are staged as cleaned markdown: VTT scaffolding (header, cue IDs, per-line timestamps)
> stripped, same-speaker cues merged into readable turns, a start-timestamp kept per turn for citation.
> ~171k words across 6 sessions. **Known item for build-time:** the first minutes of each session are
> orientation/logistics (not teaching) — handle via section-tagging or trimming at chunking/eval, not now.

**Tier 1 — primary official/reference material:**
- [x] `slides/` — Week 1 Decks 1–3 (`.pptx`), Week 2 Sessions 1–2 (`.pdf`), Week 3 Session 1 (`.pdf`)
- [x] `handouts/` — Caching, LlamaIndex, Field Guide (L6), Getting-Started Guidebook, token-usage best-practices

> **Rule:** never `git add` anything under here except this README and `.gitkeep` files. If `git status`
> ever shows a `.pptx`/`.pdf`/transcript as staged, stop — the ignore rule has been bypassed.
