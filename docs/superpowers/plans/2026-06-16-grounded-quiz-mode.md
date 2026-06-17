# Grounded Quiz Mode Implementation Plan

> **For agentic workers:** do not implement this plan until it has a fresh-context / different-model
> review and approval. When approved, execute task-by-task and keep the held-out `test` split untouched.

**Goal:** Add the smallest useful Quiz Mode pull-in: generate a cited multiple-choice quiz from retrieved
course spans, grade selections deterministically in Python, refuse/escalate when retrieval is not
citeable, and write a local trace for demo evidence.

**Architecture:** Quiz Mode is a second product mode, not a second agent loop. It reuses the Week-2
foundation through `Foundation`, existing retrieval thresholds, `RetrievedSpan`, evidence bands,
review-queue escalation, and local trace patterns. The provider may generate question text and distractor
options from one cited span, but Python validates the generated item shape and grades only by a pinned
answer key. Course claims in questions, correct answers, and rationales must be tied to the retrieved
span; low retrieval confidence refuses instead of generating a quiz.

**Tech Stack:** Python 3.12, `uv`, pytest, ruff, Pydantic, existing Week-2 `genacademy-rag` provider and
retriever via `Foundation`. No new dependencies, no direct `langgraph.*` imports, no memory provider,
and no web framework.

---

## Scope

In scope:

- CLI-only quiz demo: `scripts/run_quiz_demo.py`.
- Generate up to 3 multiple-choice questions from citeable retrieved spans for one topic.
- Session-2 transcript Q&A may be used when it appears as a retrieved course-corpus span; it is not a
  separate question bank in this slice.
- Each question carries exactly one retrieved `citation_id`. In implementation, `citation_id` comes from
  `RetrievedSpan.citation_id`, which is a property over the retrieved row's `chunk_id`; `Foundation`
  rows do not contain a separate `citation_id` field.
- Correct option and grading criteria are pinned at generation time from the cited span.
- Deterministic grading: selected option ID equals the pinned `correct_option_id`.
- Refusal + review queue when no citeable spans pass `GENACADEMY_COACH_STOP_THRESHOLD`.
- Local quiz trace under a local `traces/` directory; trace files are `*.jsonl`, already gitignored.
- Focused unit tests and one live Nebius demo command.

Out of scope:

- Instructor-authored question bank or admin UI.
- Direct Q&A extraction from transcripts into a separate quiz bank.
- Quiz eval harness over private eval questions.
- Held-out `test` split usage.
- Open-answer grading or LLM-as-judge grading.
- Adaptive hint progression.
- Cross-session memory, explicit LangGraph, voice, web UI, auth, or cohort persistence.

## Guardrail Decisions

- **Grounded-or-refuse:** no quiz question is generated unless at least one retrieved span passes the
  stop threshold and has text plus a citation ID.
- **No self-confidence:** quiz traces use retrieval-derived `evidence_score` and `evidence_band`; no
  model confidence field is accepted.
- **Citations captured at retrieval:** generated quiz items may reference only the citation ID passed
  from `RetrievedSpan.citation_id` after converting retrieved rows. That property derives from
  `chunk_id`; do not look for or accept a separate `citation_id` field from `Foundation.retrieve()` or
  the model. Unknown citation IDs are rejected.
- **Deterministic grading:** the model never grades a learner selection. Python compares normalized
  option IDs to the pinned answer key.
- **No hidden course-fact memory:** Quiz Mode does not read or write cross-session learner memory.
- **No private leakage:** committed docs may mention trace IDs, counts, option IDs, scores, and reason
  codes, but not raw corpus text, raw quiz text from private sources, or eval questions.
- **Transcript Q&A boundary:** live-session transcript Q&A is allowed only through the normal course
  retriever when already ingested as corpus. `corpus/eval-questions/` remains separate held-out eval
  material and must not be used for quiz generation, prompts, demos, or tuning.
- **No direct LangGraph:** this slice does not need a graph, checkpointer, store, interrupt, or
  multi-agent orchestration.

## Session-2 Transcript Q&A Use

Session-2 transcripts can be valuable because they often include real learner questions and instructor
answers from the live cohort. For this two-day quiz slice, use them conservatively:

- Treat transcript Q&A as ordinary course corpus evidence only after `Foundation.retrieve()` returns it
  as a `RetrievedSpan`.
- Keep the existing source-priority behavior; do not add a transcript-specific retriever or parser.
- Generate MCQs from the retrieved span exactly the same way as slides, handouts, or notes.
- Preserve the retrieved transcript citation ID on each generated question.
- Do not build a direct Q&A-to-quiz importer in this slice. That belongs to a later instructor-authored
  or corpus-authored question-bank plan.
- Do not use files under `corpus/eval-questions/` for quiz generation. Those are eval artifacts, not
  quiz seed data.

## File Structure

- Create `src/genacademy_coach/quiz_types.py` - Pydantic types for MCQ options, questions, quiz turns,
  grades, and session results.
- Create `src/genacademy_coach/quiz_items.py` - provider prompt, JSON parsing, item validation, and
  deterministic grading helpers.
- Create `src/genacademy_coach/quiz_session.py` - pure quiz runtime: retrieve, validate, generate,
  refuse, grade, trace.
- Create `src/genacademy_coach/quiz_trace.py` - typed quiz trace allow-list model plus JSONL writer.
  Do not reuse `TraceWriter.append()`, which is hardcoded to the teach-loop `TraceTurn` shape.
- Create `scripts/run_quiz_demo.py` - local CLI for generating and optionally grading a quiz.
- Add tests:
  - `tests/test_quiz_types.py`
  - `tests/test_quiz_items.py`
  - `tests/test_quiz_session.py`
  - `tests/test_quiz_trace.py`
  - `tests/test_quiz_cli.py`
- Update docs after implementation:
  - `README.md`
  - `docs/demo-and-deliverables.md`
  - `docs/teach-loop-status.md`
  - `docs/build-learnings.md` if there is a real implementation learning
  - `specs/roadmap.md`

---

### Task 1: Quiz Types and Deterministic Grading

**Files:**
- Create: `src/genacademy_coach/quiz_types.py`
- Create: `tests/test_quiz_types.py`

- [x] Add `QuizOption` with `option_id` and `text`.
- [x] Add `QuizQuestion` with `question_id`, `prompt`, `options`, `correct_option_id`,
  `expected_answer`, `rationale`, `citation_id`, and `expected_keywords`.
- [x] Set Pydantic models to reject extra fields; a model-supplied `confidence` field is invalid.
- [x] Enforce these invariants in Pydantic validators:
  - option IDs normalize to uppercase short IDs such as `A`, `B`, `C`, `D`;
  - option IDs are unique;
  - option text is non-empty and unique within the question;
  - `correct_option_id` must match one provided option;
  - `expected_keywords` contains at least one non-empty normalized keyword;
  - `citation_id` is non-empty.
- [x] Add `QuizGrade` with `question_id`, `selected_option_id`, `correct_option_id`, `correct`, and
  `citation_id`.
- [x] Add `QuizTraceRow` as a typed allow-list for serialized trace metadata. It may contain session ID,
  topic hash, evidence score/band, citation IDs, question IDs, selected option IDs, correctness booleans,
  refusal reason, and action/tool names. It must not contain raw span text, option text, expected answer,
  rationale, expected keywords, or learner-visible quiz text.
- [x] Add `QuizSessionResult` for generated questions, grades, score, refusal reason, and trace path.
- [x] Add tests proving invalid option IDs, duplicate options, missing correct option, empty keywords,
  and empty citation IDs fail validation.
- [x] Add tests proving duplicate option text and extra `confidence` fields fail validation.
- [x] Add tests proving deterministic grading treats `a` and `A` as the same option and rejects unknown
  selections explicitly.

Acceptance:

- MCQ answer correctness can be decided without an LLM call.
- A quiz question cannot exist without a citation ID and a valid pinned answer key.

### Task 2: Grounded Quiz Item Generation

**Files:**
- Create: `src/genacademy_coach/quiz_items.py`
- Create: `tests/test_quiz_items.py`

- [x] Add a provider prompt that receives exactly one `RetrievedSpan` and requests one JSON MCQ item.
- [x] The prompt may receive spans from notes, slides, handouts, or transcripts, including session-2
  transcript Q&A, but it must not receive held-out eval questions.
- [x] Require provider calls to use `json_mode=True`, `temperature=0.0`, and bounded `max_tokens`.
- [x] Parse only this JSON shape:

```json
{
  "prompt": "Which statement is directly supported by the cited span?",
  "options": [
    {"option_id": "A", "text": "Supported answer"},
    {"option_id": "B", "text": "Distractor"},
    {"option_id": "C", "text": "Distractor"},
    {"option_id": "D", "text": "Distractor"}
  ],
  "correct_option_id": "A",
  "expected_answer": "The supported option restated plainly.",
  "rationale": "Short explanation grounded in the span.",
  "expected_keywords": ["supported term"]
}
```

- [x] Build the final `QuizQuestion` in Python with the caller-provided `citation_id`; do not accept a
  model-supplied citation ID.
- [x] Reuse `keywords_for_expected_answer` from `check_items.py` or the same keyword-presence logic so
  the expected answer, rationale, or correct option text must contain at least one keyword supported by
  the span.
- [x] Reject generated items whose correct option or rationale cannot satisfy the expected keyword
  contract.
- [x] Reject generated items unless they contain exactly 4 options with IDs `A`, `B`, `C`, and `D`.
- [x] Add fake-provider tests for:
  - happy-path item generation;
  - provider called with `json_mode=True`;
  - model-supplied citation ID ignored or absent;
  - unsupported expected keywords fail;
  - duplicate option IDs or duplicate option text fail;
  - missing correct option fails.

Acceptance:

- Generation may be model-assisted, but validation and the answer key are Python-owned.
- Unknown or hallucinated citation IDs cannot enter a quiz item.

### Task 3: Quiz Session Runtime

**Files:**
- Create: `src/genacademy_coach/quiz_session.py`
- Create: `tests/test_quiz_session.py`

- [x] Add a `QuizSession` with constructor fields similar to `CoachSession`: `session_id`, `topic`,
  `settings`, `foundation`, and `question_count`.
- [x] Retrieval:
  - call `foundation.retrieve(topic)`;
  - convert rows to `RetrievedSpan` using a quiz-local converter or future public shared helper; do not
    import the private teach-tool `_span_from_row()`;
  - read citation IDs from `RetrievedSpan.citation_id` after conversion; this value is derived from
    `chunk_id`.
  - filter with `require_citeable_spans(..., stop_threshold=settings.stop_threshold)`;
  - compute `evidence_score` and `evidence_band` using runtime helpers.
- [x] Define shared quiz refusal reason constants, including `NO_CITEABLE_QUIZ_CORPUS =
  "no citeable course corpus found for quiz"`, so escalation reasons remain greppable and do not drift
  across tests, trace rows, and docs.
- [x] If no citeable spans remain, return a refusal result and append one review-queue row with reason
  `NO_CITEABLE_QUIZ_CORPUS`.
- [x] Generate questions from the top citeable spans, capped by `question_count`; if generation for one
  span fails validation, skip that span and continue.
- [x] If all generation attempts fail validation, refuse/escalate with reason
  `could not generate grounded quiz items`.
- [x] Grade selections deterministically with `grade_quiz_selection` / `grade_quiz`.
- [x] Write one local quiz trace JSONL row containing only session metadata, topic hash, evidence
  score/band, citation IDs, question IDs, selected option IDs, correctness booleans, refusal reason, and
  tool/action names.
- [x] Add tests for:
  - retrieval below threshold refuses and writes one review-queue row;
  - citeable retrieval generates questions whose citation IDs are from retrieved spans;
  - transcript-source spans are accepted through the same citation path as other source types;
  - deterministic grading produces score and per-question grades;
  - unknown selections produce explicit incorrect grades or validation errors, not silent defaults;
  - all invalid generated items refuses instead of returning an empty quiz;
  - trace row contains no raw span text, option text, correct answers, or private eval question text.

Acceptance:

- Quiz Mode preserves the same grounded-or-refuse boundary as the teach loop.
- Grading cannot be changed by model output after the item is generated.

### Task 4: CLI Demo Script

**Files:**
- Create: `scripts/run_quiz_demo.py`
- Create: `tests/test_quiz_cli.py`

- [x] Add CLI args:
  - `--topic` required;
  - `--question-count` default `3`;
  - `--answers` optional comma-separated option IDs such as `A,B,C`;
  - `--session-id` optional for repeatable traces.
- [x] Build `CoachSettings`, `Foundation`, and `QuizSession`.
- [x] Print generated question prompts, option IDs, visible citation IDs, and trace path.
- [x] If `--answers` is supplied, grade deterministically and print score plus per-question
  correct/incorrect status.
- [x] Add tests for answer parsing and count mismatch handling. Keep CLI subprocess/live-provider testing
  out of unit tests.

Acceptance:

- A repeatable demo command can generate and grade a three-question quiz without interactive input.
- The script does not import web frameworks or direct `langgraph.*`.

### Task 5: Trace Redaction Contract

**Files:**
- Create: `src/genacademy_coach/quiz_trace.py`
- Create: `tests/test_quiz_trace.py`

- [x] Add a focused test that writes a quiz trace with planted raw span text, option text, correct
  answer, rationale, and expected keyword strings available in memory, then asserts the serialized trace
  omits those values.
- [x] Assert the serialized trace keeps only safe identifiers and metrics: session ID, question IDs,
  citation IDs, evidence score/band, selected option IDs, correctness booleans, refusal reason, and
  action/tool names.
- [x] Assert `quiz_trace.py` does not depend on or serialize the teach-loop `TraceTurn` model.

Acceptance:

- Quiz trace output is an allow-list surface, not a scrubbed copy of rich quiz state.

### Task 6: Docs and Demo Evidence

**Files:**
- Modify: `README.md`
- Modify: `docs/demo-and-deliverables.md`
- Modify: `docs/teach-loop-status.md`
- Modify: `specs/roadmap.md`
- Optional: `docs/build-learnings.md`

- [x] Update README with the Quiz Mode command only after the CLI exists.
- [x] Update demo playbook to show Quiz Mode as a pull-in, behind the teach-loop evidence.
- [x] Update teach-loop status with a redacted quiz trace summary after a live run.
- [x] Update roadmap from "Quiz Mode planning" to "Quiz Mode slice shipped" only after tests and live
  trace exist.
- [x] Keep raw question text, raw corpus spans, and generated trace contents out of committed docs.

Acceptance:

- Docs do not overclaim Quiz Mode as an agentic loop; it is a grounded deterministic assessment mode.
- The held-out `test` split remains untouched.

### Task 7: Verification and Review

- [x] Run focused tests:

```bash
uv run pytest tests/test_quiz_types.py tests/test_quiz_items.py tests/test_quiz_session.py tests/test_quiz_trace.py tests/test_quiz_cli.py -q
```

- [x] Run the existing safety checks:

```bash
uv run pytest -q
uv run ruff check .
uv run python scripts/check_eval_leak.py
git diff --check
```

- [x] Run one live local quiz demo with Nebius on a public demo topic, without using the held-out
  `test` split:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_quiz_demo.py \
    --session-id demo-quiz-agent-harness-reviewfix2-20260616 \
    --topic "agent harness" \
    --question-count 3 \
    --answers A,B,C
```

- [x] Record only redacted metadata in docs: trace ID, evidence band, citation count, question count,
  score, and refusal status.
- [x] Request a fresh-context / different-model review before merge.

Final acceptance:

- Quiz Mode generates cited MCQs, refuses when unsupported, grades deterministically, writes a trace, and
  keeps the `test` split untouched.
- No new dependency, direct LangGraph import, memory provider, or web surface is introduced.

## Explicit Non-Goals For Implementers

- Do not modify `CoachSession`, `teach_agent.py`, or `build_teach_tools()` for Quiz Mode.
- Do not reuse `grade_understanding()` as the MCQ grader; it is an open-answer keyword grader.
- Do not import private helpers from teach modules just because their shape is convenient.
- Do not add a quiz eval runner over the private eval split in this slice.
- Do not weaken thresholds, add model self-confidence, or use provider output to override deterministic
  grading after item generation.
