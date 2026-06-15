# Corpus (local staging — content is **never** committed)

This folder is where the tutor's retrieval corpus is staged before ingestion. **Only this layout +
README + the `.gitkeep` placeholders are version-controlled** — every actual source file (`.md`, `.pptx`,
`.pdf`, `.docx`, transcripts, indexes) stays out of git via `.gitignore`. The content is the builder's
own course material, used locally; we don't republish it.

Corpus = **the builder's own content** (own deep-notes + own transcripts + course slides/handouts the
builder received as a student). No external dataset, no permission dependency. See
[`../docs/build-learnings.md`](../docs/build-learnings.md) for why.

## Drop-zones, by teaching value

Ranked by *where the actual explanation lives* — which, after we found the deck speaker-notes were empty
(0 of 113 Week-1 slides), is **not** the slides.

| Folder | What goes here | Tier | Why |
|---|---|---|---|
| `notes/` | The builder's own deep-notes `.md` (Lessons 1–5, 7, 8) | **1 — explanation** | Plain-English explanations the builder wrote — highest-quality teaching text. |
| `transcripts/` | Session-recording transcripts (`.md`) | **1 — explanation** | The spoken narration the slides only gesture at. **The gold**, since deck notes are blank. |
| `slides/` | Lecture decks — **`.pptx` preferred**, `.pdf` fallback | 2 — reference | Concept coverage + visuals; skeletal on explanation. Keep `.pptx` (cleaner extraction). |
| `handouts/` | Reference PDFs/docs (Caching, LlamaIndex, Field Guide = L6, token-usage, guidebook) | 2 — reference | Topic depth on specific themes; the "agentic ops" cluster. |

## Naming & chunk convention

Keep source filenames or normalize to `week<N>-<session|lesson>-<slug>.<ext>`. The chunker emits a
header of **`week · title · section/slide`** per chunk, so each retrieved span is citable back to its
origin.

## Collection checklist (update as you gather)

**Tier 1 — explanation (priority):**
- [x] `notes/` — own deep-notes for L1–5, 7, 8
- [ ] `notes/` — Lesson 6 enters as the Field Guide **PDF** in `handouts/` (author a `.md` only if retrieval is weak)
- [x] `transcripts/` — Week 2 · Session 1
- [ ] `transcripts/` — Week 1 · Session 1
- [ ] `transcripts/` — Week 1 · Session 2
- [ ] `transcripts/` — Week 2 · Session 2
- [ ] `transcripts/` — Week 3 · Session 1 (+ any Session 2)

**Tier 2 — reference (have):**
- [x] `slides/` — Week 1 Decks 1–3 (`.pptx`), Week 2 Sessions 1–2 (`.pdf`), Week 3 Session 1 (`.pdf`)
- [x] `handouts/` — Caching, LlamaIndex, Field Guide (L6), Getting-Started Guidebook, token-usage best-practices

> **Rule:** never `git add` anything under here except this README and `.gitkeep` files. If `git status`
> ever shows a `.pptx`/`.pdf`/transcript as staged, stop — the ignore rule has been bypassed.
