# GenAcademy Coach Submission Draft

> Draft for the external Google Doc. Keep this document free of private corpus excerpts, held-out eval
> questions, generated quiz text, API keys, and raw trace payloads. Use only the redacted evidence
> surfaces already committed in the repo.

## Project Overview

GenAcademy Coach is an adaptive, grounded AI tutor for Gen Academy cohort members. It builds on my Week
2 RAG project (`genacademy-rag`) and adds the Week 3 agentic layer: the tutor teaches a concept, checks
understanding, reacts to the learner's answer, re-explains a different way when the learner stumbles,
tracks within-session learning state, and refuses when it cannot cite course evidence.

The hook:

> It explained attention three different ways until it clicked, and refused to answer what it could not
> cite.

The important design choice was not to make a generic chatbot. The tutor is allowed to teach only from
retrieved course spans. Python enforces the grounding and refusal gates; the model decides the teaching
move at runtime within that safe boundary.

## What I Built

- A text-first **Teach Mode**: retrieve course evidence, explain, ask a grounded check, grade the
  learner's answer, then let the agent choose `advance`, `drill`, `re_explain_differently`,
  `refuse_escalate`, or `stop`.
- A **within-session learner profile**: track the teaching lens, last strategy, generated check item,
  grade, and struggle state during one session. Cross-session memory is deliberately deferred.
- A grounded **refusal and escalation path**: low retrieval confidence or missing citeable evidence
  writes a local mentor-review queue row instead of bluffing.
- A redacted **runtime trace**: each turn records safe metadata such as evidence score, evidence band,
  next action, strategy, citation IDs, and faithfulness result.
- A polished local **recording UI**: preset-driven Teach and Quiz paths, local-only launch, collapsed
  metadata by default, camera-safe decision-trace cards, and hidden generated quiz text unless explicitly
  enabled for local/private inspection.
- A redacted **dev eval harness**: multi-turn scenarios report pass/fail diagnostics without exposing
  private question text.
- A first pull-in, **Grounded Quiz Mode**: generate up to 3 cited MCQs from retrieved spans, pin the
  answer key, grade selected option IDs deterministically in Python, and write a typed redacted quiz
  trace.

## Dataset And Privacy

The corpus is local Gen Academy course material: notes, slides, handouts, and transcripts. The project
uses the Week 2 retrieval foundation: the same embedder, Chroma schema, chunking path, provider
boundary, citation metadata, and eval discipline. The held-out test split comes from real student chat
questions and is corpus-independent.

Privacy rules:

- Private corpus files are gitignored.
- Generated eval artifacts are gitignored.
- The held-out `test` split is frozen and not used for prompt tuning, demo prep, retrieval triage, or
  pull-in validation.
- Public docs and traces use redacted metadata only.
- Quiz traces store `topic_hash`, citation IDs, question IDs, evidence scores/bands, selected option
  IDs, booleans, and actions. They do not store raw topic text, span text, option text, expected
  answers, rationales, or keywords.

The leak guard is `scripts/check_eval_leak.py`. The latest run passed with no eval test IDs/checksums in
code/docs and no eval n-grams where private eval sources were available. The PDF extraction warnings are
known parser warnings and are not treated as a demo blocker.

## Architecture

The project keeps a pure core and thin interface:

- `src/genacademy_coach/foundation.py` adapts the Week 2 RAG foundation.
- `src/genacademy_coach/teach_session.py` runs the teach loop.
- `src/genacademy_coach/teach_tools.py` exposes retrieval, check generation, grading, and profile
  update tools to the agent.
- `src/genacademy_coach/grounding.py` owns evidence scores, evidence bands, citation validation, and
  deterministic grading helpers.
- `src/genacademy_coach/quiz_session.py` and `src/genacademy_coach/quiz_items.py` implement the first
  pull-in without turning Quiz Mode into a second agent loop.
- `scripts/run_teach_demo.py`, `scripts/eval_teach_loop.py`, and `scripts/run_quiz_demo.py` are CLI
  surfaces over the core.

LangChain `create_agent` provides the agent loop on LangGraph's runtime. I intentionally did not import
`langgraph.*` directly this week. Direct graph/checkpointer/store code is reserved for a future delta
when durable cross-session memory, HITL interrupts, or multi-mode orchestration outgrow the current
loop.

## Evidence From The Current Build

Final merged-main evidence was captured without using the held-out `test` split.

Raw trace files are gitignored per privacy rules. The table below names local evidence artifacts and
reproduces only the redacted metadata that is safe to commit or show in the external submission.

| Moment | Redacted evidence | What it proves |
|---|---|---|
| Grounded teach loop | `traces/demo-grounded-main-final-20260616.jsonl` | The tutor retrieved citeable evidence, taught, asked a check, and re-explained after the learner stumbled. |
| Refusal path | `traces/demo-refusal-main-final-20260616.jsonl` and `review_queue.jsonl` | Out-of-corpus topics refuse and escalate instead of answering from priors. |
| Dev eval | `eval/runs/teach-loop-dev-main-final-20260616.json` | Latest dev evidence: `7/10` overall and `7/8` teachable, with two safe low-retrieval refusals. |
| Grade-boundary follow-up | `eval/runs/teach-loop-dev-grade-boundary.json` | The original same-turn grade overwrite bug is fixed. |
| Same-topic lens switch | `traces/demo-lens-low-code-20260616.jsonl` and `traces/demo-lens-code-heavy-20260616.jsonl` | The same public topic and learner answer can be taught through different lenses while the grounding floor stays stable. |
| Grounded quiz | Local UI hidden-question run + `traces/demo-quiz-agent-harness-reviewfix2-20260616.jsonl` fallback | The UI demo keeps generated quiz text hidden, grades answer IDs deterministically, and shows only safe trace metadata. The fallback trace demonstrates the three-question path. |

The honest eval story matters. I did not hide the failures: two dev failures are safe low-retrieval
refusals, and the remaining teachable variance is a conservative escalation case. The held-out test
split remains unused.

## Prompts And Vibe-Coding Workflow

The full prompt appendix is in `docs/vibe-coding-prompt-appendix.md`. The pattern was:

1. Start with a written constitution in `AGENTS.md`.
2. Plan every non-trivial slice before implementation.
3. Ask a different model or fresh context to review the plan or PR.
4. Paste the review findings back into the build loop.
5. Fix agreed findings, rerun tests/lint/leak checks, and only then merge.

Representative prompt categories:

- Plan review prompts for the teach loop, eval diagnostics, retrieval triage, Quiz Mode, and submission
  packaging.
- PR review prompts asking Claude, Gemini/Kimchi, Antigravity, or a fresh Codex context to act as Staff
  AI engineer, privacy reviewer, hackathon judge, and code reviewer.
- Implementation prompts such as "fix the issues if you agree and proceed," "triage why 9/10 dev
  scenarios had zero retrieval coverage," and "merge the PR and suggest next step."

No prompt appendix entry includes private corpus text, held-out eval questions, API keys, or raw
generated quiz content.

## Iterations Tried

The project improved through several loops:

- I first treated the Week 2 RAG system as a loose dependency. Reviews pushed me to write a foundation
  reuse contract so I would not rebuild the embedder, chunker, vector schema, provider wrapper, or eval
  harness.
- I originally planned an eval split that became unsafe after the corpus pivot. The fix was to use real
  student chat questions as the corpus-independent held-out test source and enforce a leak guard.
- Early dev eval showed safe refusals but poor coverage. A retrieval diagnostic proved the issue was not
  missing ingestion; it was an overly strict initial STOP threshold.
- Eval diagnostics first duplicated evidence-band logic. Review caught that drift risk, so diagnostics
  now reuse runtime grounding helpers.
- The teach loop initially allowed a same-turn tool grade to overwrite the canonical boundary grade. The
  fix preserved the grade tied to the learner input that began the turn.
- Same-topic lens switching became the safer personalization demo than rushing memory.
- Quiz Mode shipped only after the teach-loop floor was stable, and it keeps model generation separate
  from deterministic grading.
- A strict UI review found that the first demo polish pass still felt too much like a raw Gradio app:
  the run buttons could fall below the fold, empty states looked unfinished, touch targets were small,
  and raw trace tables were hard to read on camera. The fix moved the main actions higher, added
  recording-safe empty states, improved mobile touch targets, and replaced the trace table with
  decision-trace cards.
- Manual scenario testing found that the three-question quiz path was valid but too brittle as the
  default live recording path. The fix made the UI preset prove the same safety contract with one hidden
  question by default, while leaving the three-question CLI artifact as optional deeper evidence.
- Manual retries also exposed an operational lesson: stale local Gradio processes and browser cache can
  make a fixed branch look broken. The final script now includes a hard-refresh/restart check and visible
  fixed-UI cues before recording.

## Learnings

The deeper learning was scope discipline plus demo honesty. The tempting route was to add memory,
explicit LangGraph, a gradebook UI, or voice. The better route was to make the grounded tutor harder to
break, then make the proof easy to understand on camera: one reliable teach path, one refusal path, one
hidden quiz path, and trace cards that show the safety decisions without exposing raw private text.

Reusable principles:

- A held-out set is not held out if its answers live in the index.
- Redaction is stronger as an allow-list than a cleanup pass.
- Diagnostics should call the same source of truth as the runtime.
- When Python owns a correctness signal, the model's later tool calls should not overwrite it.
- Personalization can be demonstrated with controlled contrast before adding durable memory.
- A second mode is safer when the model creates content but Python owns correctness.
- Demo defaults are product decisions. The first click should prove the promise with the fewest live
  failure points.
- A trace needs both safety and legibility. Citation counts and decision cards are better for video than
  long internal IDs in a raw table.
- A local demo needs an operational checklist: kill stale servers, hard-refresh, confirm fixed UI
  defaults, and keep generated quiz text hidden unless it is explicitly public-safe.

Full learning notes are in `docs/build-learnings.md`.

## What I Cut And Why

I deliberately deferred:

- Cross-session memory: useful, but it adds persistence, privacy, deletion, and "memory as uncited fact"
  risk.
- Explicit LangGraph graphs/checkpointers/stores: useful later, but unnecessary while `create_agent`
  keeps the loop understandable.
- Mock interview: promising, but it would need open-answer grading and a fresh grounding plan.
- Admin UI and gradebook: the existing `review_queue.jsonl` plus traces already give an instructor
  review surface for the demo.
- Voice and multimodal: good polish, but not the core Week 3 proof.

## Next Steps

1. Record the <=5-minute video using `docs/video-demo-script.md` and the local Gradio presets.
2. Create the external Google Doc from this draft.
3. Keep the held-out `test` split unused until final reporting.
4. If there is time after the recording, decide whether to explain or harden the remaining confirm-band
   conservative escalation case.
5. Treat memory as the next personalization plan after submission: first-party persisted profile first,
   then compare LangMem, Mem0 open source, and Zep Cloud under a privacy/deletion review.
