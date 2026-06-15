# Build Learnings — GenAcademy Coach

> A running log of the non-obvious things I learned while building this, **in my own words.**
> Two jobs: (1) my future reference, (2) raw material for build-in-public posts and the
> decision-story in the project write-up.
>
> Format per entry: **what I believed → what I found → the reusable principle.** Newest first.
> These are deliberately written as the messy middle, not a polished after-the-fact summary —
> the point is to show how the decisions actually got made.

---

## 2026-06-15 — A parser that works on five files can silently eat the sixth

**What I believed:** my transcript cleaner ran cleanly on the first five session VTTs, so it was done.

**What I found:** the sixth VTT was a different export — no speaker labels, sentences fragmented across
tiny cues, a 2-hour timestamp offset. My cleaner assumed inline `Name:` speakers; with none present, a
branch **silently discarded the whole file — 1,418 caption cues collapsed to 4 words.** No error, no
crash. The only reason I caught it was sanity-checking the *output* (4 words out of 1,418 cues is
obviously wrong).

**Principle:** never assume one source's format generalizes — real corpora are heterogeneous. Validate a
batch by the *plausibility of its output*, not its exit code: a clean run that produces nonsense is worse
than a crash, because nothing flags it. Assert on the obvious invariant (words-out ≈ words-in) and build
parsers to degrade gracefully on the shape you didn't expect.

## 2026-06-15 — A data/permission blocker is usually a reframing opportunity, not a wall

**What I believed:** more data is better, so I should build on the richest corpus I could get —
even though the cleanest one was someone else's processed dataset (~2,000 segments).

**What I found:** using it cleanly meant a permission conversation I didn't want to have. Instead of
treating that as a blocker, I flipped the corpus to **my own course notes** — the deep-notes I wrote
across the program. Smaller (~300 segments), but 100% mine, zero permission risk, and it produced a
*better* demo line: *"a tutor that teaches from the notes I took during this course."* The constraint
turned into the positioning.

**Principle:** owned-but-smaller can beat borrowed-but-bigger — especially when the *story* is graded as
heavily as the metric. When you hit a data or permission wall, ask what you already own before you ask
permission for what you don't.

## 2026-06-15 — Don't author what you can ingest ("missing" data is often just an un-built derivative)

**What I believed:** I was "missing" a lesson from my corpus because I hadn't written my own notes for
it — only the original course PDF existed.

**What I found:** my retrieval pipeline already ingests PDFs (the handouts are PDFs). The *content* was
never missing — only a nicer-formatted copy was. I'd nearly spent ~3 hours authoring notes for something
the pipeline could already read. A 30-second text-extraction check (20K clean characters out of the PDF)
settled it.

**Principle:** before you spend hours *creating* corpus, check whether your pipeline can already consume
what you have. The reflex to make every source uniform and polished is expensive and often unnecessary.
Verify the cheap path before committing to the expensive one.

## 2026-06-15 — For a teaching corpus, slide speaker-notes are the gold — so keep slides as PPTX, not PDF

**What I believed:** slides are slides; PDF vs. PPTX doesn't matter much for retrieval.

**What I found:** it matters a lot, and the reason is **speaker notes.** A slide *body* is bullet
fragments — *"Attention → weighted sum."* The *speaker notes* are where the real explanation lives —
*"attention is a weighted average over all tokens, where the weights come from query–key similarity."*
A standard slides→PDF export **throws the notes away.** `python-pptx` keeps title + body + notes per
slide, in reading order, with one-slide-per-chunk boundaries for free. PDF stores text by x/y position,
so layout-heavy slides extract *out of order* — the classic thin, choppy-chunks problem.

**Principle:** match the format to what your app actually needs. For a tutor whose entire job is
*explaining*, the speaker notes are the single most valuable text in a deck — so the format that
preserves them (PPTX) beats the one that feels more "final" but discards them (PDF). Counter-case: a
purely visual slide (big diagram, three words) — neither format helps; that needs image captioning.

**Tested it the same day — and the premise didn't hold for my decks.** I chased the `.pptx` originals,
then actually opened the notes: **0 notes on 113 slides** across the three Week 1 decks (one slide had
notes, the rest blank). My instructors don't narrate in the notes pane — they talk to bullet slides and
the explanation lives in the *session recording*. So the abstract principle held ("match the format to
where the content actually is") but the concrete answer flipped: for *my* corpus the gold is the
**transcript**, not the deck notes. PPTX still wins marginally on extraction cleanliness (structured
text vs. PDF's x/y scramble), but it stopped being the headline. **Meta-lesson: verify the premise of
your own recommendation against the real artifact before you build on it — a confident, well-reasoned
call can still rest on an assumption that turns out false for your specific data.**

---

> *Add new learnings at the top as they happen. Each one is a candidate LinkedIn post and a beat in the
> "how I made the calls" section of the write-up.*
