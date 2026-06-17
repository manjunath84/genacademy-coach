# Build Learnings — GenAcademy Coach

> A running log of the non-obvious things I learned while building this, **in my own words.**
> Two jobs: (1) my future reference, (2) raw material for build-in-public posts and the
> decision-story in the project write-up.
>
> Format per entry: **what I believed → what I found → the reusable principle.** Newest first.
> These are deliberately written as the messy middle, not a polished after-the-fact summary —
> the point is to show how the decisions actually got made.

---

## 2026-06-16 — A second mode is safer when the model creates content but Python owns correctness

**What I believed:** adding Quiz Mode might require another agent loop or an LLM judge to decide whether
the learner picked the right answer.

**What I found:** the safer first slice was simpler: let the model generate MCQ text from a retrieved
span, then pin the answer key and grade only option IDs in Python. The privacy-sensitive part was not the
grade; it was the trace. A typed allow-list trace kept IDs, scores, actions, and booleans while excluding
span text, option text, rationales, expected answers, and keywords.

**Principle:** for a demo pull-in, separate creative generation from correctness. The model can draft a
grounded artifact, but the system should own the answer key, grading, refusal boundary, and public
evidence surface.

---

## 2026-06-16 — A demo can prove adaptivity without adding a new feature

**What I believed:** making personalization visible might require cross-session memory, a new hint action,
or another mode.

**What I found:** the existing track-lens field was already enough to show the same learner asking for
the same concept through different teaching lenses. The safer demo move was to capture two grounded
traces with the same topic and answer, then show that only the lens changed while retrieval, citations,
grading, and re-explanation still worked.

**Principle:** before adding state or new control flow, look for a traceable behavior the system already
has. In a short demo window, the strongest personalization proof is often controlled contrast: keep the
inputs constant, change one learner preference, and show the runtime evidence.

---

## 2026-06-16 — The boundary grade and the tool grade are not always the same thing

**What I believed:** once the stale grade lock was fixed, the session's `last_grade` would reliably
represent the learner's answer to the current check.

**What I found:** in one turn, the session can grade the learner's answer to check A, then the agent can
generate check B and call the grading tool again before the response is finalized. The tool-grade for B
is a real tool result, but it must not replace the canonical boundary grade for the learner's answer to A.

**Principle:** when a value drives workflow safety, preserve the value at the boundary where it was
created. Tool calls inside the turn can generate useful observations, but they should not rewrite the
decision signal for the user input that started the turn.

## 2026-06-16 — Personalization does not require rushing a memory stack

**What I believed:** adding cross-session memory or explicit LangGraph orchestration might be the best
way to make the tutor feel more personalized in the final demo.

**What I found:** the current within-session learner profile already proves personalization without new
persistence risk. LangMem, Mem0, and Zep are credible future options, but each adds a privacy/provider or
state-management surface. Explicit LangGraph is also real architecture, especially for durable memory and
human-in-the-loop interrupts, but this project already gets the LangGraph runtime through LangChain
`create_agent`.

**Principle:** in a two-day demo window, show the personalization you already have and document the next
architecture trigger. Add memory only when there is a written privacy/deletion story and a reason
`create_agent` can no longer keep the loop understandable.

## 2026-06-16 — Use examples to sharpen scope, not to borrow surfaces

**What I believed:** the quickest score lift after reviewing public AI-tutor examples might be a flashy
feature like hint progression or a gradebook UI.

**What I found:** the strongest low-risk ideas were reframes and reuse: low-stakes mastery framing,
deterministic criteria for quizzes, the existing review queue as the instructor-review surface, and
reproducibility through split manifests and source checksums. The risky part was following another
product's surface mechanics too literally: a hardcoded "wrong once -> hint, wrong twice -> reveal" ladder
would violate the agenticity guardrail because Python would be choosing the teaching path.

**Principle:** use external examples as a pressure test for your own priorities, not as a template. In a
time-boxed demo, raise the floor with honest framing and existing artifacts before adding scope; when
adding teaching behavior, keep the choice model-decided and let Python enforce only safety gates.

## 2026-06-16 — A lock without an identity is just stale state waiting to happen

**What I believed:** once Python computed the canonical answer grade, a simple `grade_locked` flag was
enough to stop later tool calls from overwriting it.

**What I found:** the lock protected the old grade too broadly. In one agent turn, the runtime could
grade check A, generate a new check B, then call the grading tool again. A bare boolean lock would return
check A's grade while the active check was B.

**Principle:** when you lock a correctness-critical signal, lock it to the object it belongs to. A guard
should carry or verify identity, not just say "some value is locked." Clear the lock on ownership changes,
and only reuse the locked value when its identifier still matches the active state.

## 2026-06-16 — If Python computes the canonical grade, tool calls cannot be allowed to overwrite it

**What I believed:** moving answer grading to the session boundary meant the eval's final grade was
protected from model behavior.

**What I found:** the agent still had access to the `grade_understanding` tool during the same turn. It
could call that tool after Python had already graded the learner's answer, overwriting the canonical
session-boundary grade and making a self-consistent expected answer appear incorrect in eval.

**Principle:** when a safety-critical signal moves from model discretion into deterministic Python, lock
that signal for the rest of the turn. Tools may report the canonical value, but they should not be able
to replace it after the boundary has made the decision.

## 2026-06-16 — Safe refusal is not always the best repair when evidence exists

**What I believed:** the demo trace step would just record the already-hardened teach loop: retrieve,
teach, stumble, re-explain, and refuse on out-of-corpus topics.

**What I found:** the public demo topic had citeable evidence and a generated check item, but the model's
first explanation failed the faithfulness check. The runtime did the safe thing and escalated, but that
made the happy-path demo fail despite having enough course evidence to teach from. The right repair was
not to loosen grounding; it was to reuse the retrieved span directly for a grounded first-turn fallback,
the same way the later correct/wrong-answer fallbacks already do.

**Principle:** when the model wording fails but retrieved evidence is valid, repair by narrowing to the
evidence, not by relaxing the guardrail. Refusal is the right answer when evidence is missing; exact-span
fallback is better when evidence is present and the model's phrasing is the weak link.

## 2026-06-16 — A failed follow-up retrieval should not erase the evidence you already earned

**What I believed:** the remaining citation failures were just final-response formatting: the model ended
with `refuse_escalate` and no citation IDs even though retrieval had found spans.

**What I found:** there was a deeper state issue. In a multi-turn teach session, a later retrieval call can
use a worse query than the initial topic query. The tool was replacing `last_spans` every time, so one bad
follow-up retrieval could erase the citeable evidence the session had already earned. Python then had
nothing stable to use for the grounded fallback.

**Principle:** in an agent loop, distinguish "current tool call found nothing" from "the session has no
evidence." Retrieval misses should be visible to the model, but they should not automatically wipe prior
valid evidence for the same teaching session.

## 2026-06-16 — If the eval answers with your "expected answer" and still fails, your rubric is broken

**What I believed:** the remaining teach-loop grading failures were likely model behavior: the tutor was
not choosing the right action, or the learner-answer grader was too strict.

**What I found:** after moving grading into the session boundary, the eval still failed some "correct"
turns. The answer being graded was the generated `expected_answer` itself, but some generated check items
had `expected_keywords` that were not present in that expected answer. The model had produced an invalid
rubric, and the deterministic grader correctly rejected it.

**Principle:** when an eval uses generated rubrics, validate the rubric against itself before blaming the
agent loop. A deterministic grader is only as good as the check item it receives; make the generator prove
that its expected answer can satisfy its own keyword contract.

## 2026-06-16 — Diagnostics should reuse the runtime's truth, not re-copy it

**What I believed:** an eval diagnostic can compute its own score bands because the logic is tiny:
`stop`, `confirm`, `proceed` from the same two thresholds.

**What I found:** tiny duplicate logic is still duplicate logic on an honesty-critical surface. The teach
runtime already had canonical `evidence_score` and `evidence_band` helpers. Re-implementing the same
threshold checks in the eval script was correct today, but it created a future drift path: if the runtime
threshold convention changed, the diagnostics could silently report a different band than the learner
actually experienced.

**Principle:** when a diagnostic explains what the product did, it should call the same code path the
product uses. Diagnostics are not a second implementation; they are an instrument panel. Reuse the
runtime's source of truth, then test the boundary values that make drift expensive.

## 2026-06-16 — Redaction is stronger as an allow-list than a cleanup pass

**What I believed:** avoiding raw eval text in outputs was mostly a matter of remembering not to print
`question_text`.

**What I found:** the safer design was to build diagnostics from an explicit allow-list projection:
scenario IDs, source filenames, counts, retrieval scores, source types, actions, and reason codes. The
tests then asserted that planted private-text keys do not cross the output boundary. That is much easier
to reason about than trying to scrub a rich row after the fact.

**Principle:** for private eval data, do not redact by subtraction. Emit by construction. Build the
public artifact from only the fields that are safe to expose, and make the redaction boundary a testable
contract.

## 2026-06-16 — A working refusal path can hide a retrieval problem unless you count it

**What I believed:** the teach loop was behaving safely because low-confidence items refused and
escalated instead of bluffing.

**What I found:** safe behavior and useful behavior are different bars. The live dev run showed the
agent mostly did the right safety move, but the new diagnostics made the real next problem obvious:
most scenarios had zero retrieval coverage, while the one teachable scenario failed on teaching-loop
behavior. Without counts and reason codes, those would all collapse into "failed eval" and point in the
wrong direction.

**Principle:** refusal is not failure, but repeated refusal is a product signal. Separate "safe refusal",
"retrieval coverage gap", and "teachable behavior failure" in the eval output so the next fix targets
the right layer.

## 2026-06-15 — A pivot can silently break the safeguard your old design depended on

**What I believed:** switching my corpus to my own course notes was a clean win — owned beats borrowed,
done. I'd already "fixed" eval contamination with a hard seed/dev/test split and felt good about it.

**What I found:** the pivot quietly hollowed out that exact fix. The split was only contamination-safe
because the *questions* (student Q&A) and the *corpus* (lectures) were separate artifacts. Once the corpus
became my own notes and the natural eval questions lived in the "Quiz Yourself" sets *inside* those same
notes, the answer span was in the index by construction — a "held-out" test set whose answers I retrieve
from is not held out. Three earlier review passes never caught it because they all predated the pivot, and
the file the whole protocol named — `student_questions.jsonl`, 973 rows — didn't even exist on disk. The
real fix was already sitting there: ~100+ **real student chat-questions** people asked live in session are
corpus-*independent*, so they're the leak-safe held-out set.

**Principle:** when you change your data source, re-run the threat model your old design depended on. A
safeguard that was sound under the old assumptions can be silently invalidated by the new ones — and a
prior "looks fine" review expires the moment its premise moves. A held-out test set isn't held out if its
answers live in the index you retrieve from.

## 2026-06-15 — If a project builds on your prior work, make it a written contract, not a footnote

**What I believed:** this was a fresh build that happened to reuse "the index format" from my Week-2 RAG
app. That's literally how my own README put it: "reused the index format (no re-ingest)."

**What I found:** the Week-2 repo wasn't a footnote — it was the whole foundation. It already shipped the
embedder (`all-MiniLM-L6-v2`, 384-d), the Chroma schema, an A/B-tested chunker, the refusal/citation
pipeline, the Nebius call, *and* a working eval harness (12-question gold set, recall/precision/MRR,
refusal-correctness, an LLM-judge) plus the real student questions. "Reuse the index format" buried in one
prose line is an instruction a reviewer — or me in three weeks — will cheerfully ignore and rebuild from
scratch. I'd even written "no re-ingest" while planning to add 176k words of new transcripts that were
never in that index.

**Principle:** when you build on your own prior project, promote the dependency to a first-class written
contract — a named foundation doc plus a "reuse, don't reinvent: no new chunker/embedder/eval-harness
without a written delta" rule. And pin the inherited interfaces (audit them into an adapter spec) before
you assume their signatures; "reuse X" is worthless if nobody knows X's actual API.

## 2026-06-15 — A scattered corpus hides duplicates a filename check won't catch

**What I believed:** my course corpus was basically "collected," and the copies floating around different
folders were the same files.

**What I found:** it was spread across four places (the project folder, my Week-2 `data/` dir, a
`CuratedRAGMaterials/` folder, and seven lesson-note folders). When I pulled it into one gitignored
`corpus/`, two chat-question files with the **same name** turned out to differ by content hash — one was
the more complete version. A filename-based dedupe would have silently dropped the better copy. While
consolidating I also gave the held-out eval questions their own `eval-questions/` zone that the ingestion
step structurally skips, so "never index the test set" is the folder layout now, not something I remember.

**Principle:** before you trust a corpus, pull it into one place and dedupe by **content hash, not
filename** — same name doesn't mean same bytes. And when a boundary is correctness-critical (keeping the
held-out test set out of the index), encode it in the directory structure so the pipeline can't cross it by
accident.

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
