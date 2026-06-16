# Two-Day Score-Lift Plan

Status: proposed next build sequence for the final two days before demo. This plan reflects the
second-opinion strategy review after PR #10 and keeps the held-out `test` split untouched.

## Goal

Improve the Week 3 submission score without destabilizing the shipped grounded tutor. The current
merged-main baseline is already demoable:

- Teach-loop MVP is merged, reviewed, and live-verified.
- Final dev eval is `7/10` overall and `7/8` teachable.
- Two non-passing scenarios are safe low-retrieval refusals.
- One teachable scenario has a remaining deterministic `grade_not_correct` diagnostic.

The score-lift strategy is to raise the floor first, then add one visible pull-in.

## Ranking

| Rank | Move | Score lift | Risk | Why |
|---|---|---|---|---|
| 1 | Fix the remaining `grade_not_correct` diagnostic | High | Low | Could move teachable dev evidence from `7/8` to `8/8` without adding scope. |
| 2 | Same-topic lens-switch demo | High | Very low | Makes "adaptive" visible using the existing engine: same concept, different teaching lenses. |
| 3 | Grounded Quiz Mode | High | Low/medium | Adds a real second mode while reusing retrieval, citations, refusal, and deterministic grading. |
| 4 | Mock interview | Highest ceiling | High | Strong agentic story, but open-answer grading and follow-up probing are risky in two days. Stretch only. |

## Reference-Informed Refinements

Two external AI-tutor case studies were reviewed before finalizing the sequence: *How I Built an AI
Teacher with Vector Databases and ChatGPT* (GKCS) and *How to Create an AI Tutor for Your Course*
(M. Rota / Persona AI). The transcripts were reviewed locally and are not committed; they stay under the
gitignored `tmp/` directory. The useful move is to adopt the principles, not copy their product surfaces
or implementation mechanics.

- Frame the teach loop as a low-stakes, within-session mastery loop. The learner can persist through
  grounded re-explanations until the concept clicks. Keep this separate from the eval numbers:
  mastery is the learning surface; the redacted dev eval is the integrity surface. Do not imply
  cross-session mastery or spaced repetition yet.
- Quiz grading should use pre-specified criteria, not freeform AI judgment. For the first quiz slice,
  pin the correct option and criteria at generation from the cited span, then grade deterministically.
  Instructor-authored answer keys are a cohort-rollout surface, not two-day scope.
- The instructor-review surface should be the existing `review_queue.jsonl` plus redacted traces, not
  an admin UI. This reuses the failure path's own artifacts and keeps corpus/eval text private.
- Reproducibility credibility comes from artifacts already in the repo: `eval/split_manifest.json`,
  source checksums, version-pinned dependencies, and idempotent ingest. Do not claim database-level
  branching or provider-specific versioning that the project does not implement.

## Recommended Sequence

### Day 1 Morning: Raise the Floor

1. Diagnose and fix the remaining `grade_not_correct` dev failure.
2. Rerun the redacted dev eval on `--split dev --limit 10`.
3. Keep the two safe low-retrieval refusals framed as the refusal path working, not as product misses.

Acceptance:

- Dev eval remains redacted.
- Held-out `test` split remains untouched.
- If the fix works, teachable evidence should be `8/8`.
- If the fix does not land cleanly, keep the `7/8` teachable baseline and explain the remaining
  diagnostic directly in the demo.

### Day 1 Midday: Polish Adaptivity

1. Add a repeatable same-topic lens-switch demo.
2. Show the same concept through `low_code_no_code` and `code_heavy` teaching lenses.
3. Capture trace metadata that proves the model still uses grounded evidence.

Acceptance:

- The demo uses the existing teach-loop engine.
- No new corpus tagging or track-aware retriever is required.
- The artifact is easy to show in the video.

### Day 1 Afternoon: Pull In Quiz Mode

Build only the smallest grounded quiz slice:

- CLI: `scripts/run_quiz_demo.py`
- Reuse the existing foundation/retrieval/citation types.
- Generate 3 cited multiple-choice questions from retrieved spans.
- Grade deterministically against the correct option/criteria pinned at generation from the cited span;
  no freeform LLM grading. Instructor-authored keys are deferred to cohort rollout.
- Refuse if retrieval is below threshold.
- Write a local quiz trace.
- Add focused tests for question shape, grading, and refusal.
- Update README, roadmap, and demo docs.

Quiz Mode still needs its own approved implementation plan and fresh-context review before code
per AGENTS sections 2 and 8; this sequencing doc is not build approval.

Hard stop:

- If quiz is not green and stable by end of Day 1, cut it from the live demo and keep it as a
  documented stretch.

### Day 2: Package, Then Stretch Only If Clean

1. If Day 1 is clean, consider a tightly timeboxed mock-interview prototype.
2. If mock interview is not green by noon, cut it.
3. Spend the afternoon on the 5-minute video and Google Doc.

## Considered: Grounded Hint Progression

The references show the tutor guiding a wrong answer toward the right one through conversational hints.
That is attractive because it makes personalization visible, but it is easy to implement the wrong way.

- Do not add a Python attempt ladder like "wrong once -> hint, wrong twice -> reveal." That would be a
  scripted workflow around the model, not an agent deciding from the learner's answer.
- If this ever lands, add `hint` as a model-selectable `next_action` grounded in a retrieved span. Python
  should enforce only safety gates such as max-turn refusal/escalation, not the teaching path.
- This is net-new scope: enum, prompt, grading flow, wiring max-turn refusal/escalation to the existing
  `max_teach_turns` setting, tests, and a fresh runtime trace. It competes directly with the grade fix
  and Quiz Mode.

Decision: defer unless the grading fix, lens-switch demo, and quiz slice are already green with time left.

## Considered: Cross-Session Memory

Memory could improve personalization, especially if the tutor remembers a learner's preferred teaching
style, recurring misconceptions, and prior successful explanations. It should not be a new source of
course facts; course claims still come only from retrieved citations.

Options checked on 2026-06-16:

| Option | Fit now | Notes |
|---|---|---|
| Existing within-session profile | Best for demo | Already implemented and guardrail-safe. Use it in the demo narrative before adding state. |
| Tiny first-party persisted profile | Best future first step | A local opt-in JSON/SQLite profile for style and struggle tags would avoid provider lock-in, but still needs a plan, privacy boundary, and tests. |
| LangMem | Promising later | Memory tools persist through LangGraph's `BaseStore`, which would conflict with the MVP's "no explicit LangGraph" rule unless a written delta approves it. LangMem also has storage-agnostic functional primitives, so a future delta could adopt its extractors without taking the store path. |
| Mem0 open source | Possible later | Can run self-hosted/local with extra components such as a vector store and local/provider LLM setup; stronger memory layer, but more infra than the two-day window needs. |
| Zep Cloud | Future/provider option | Strong long-term memory/graph service, but it requires a cloud project/API key and adds privacy/provider review work. Not a free-local demo fit. |

Decision: keep cross-session memory in the roadmap, but do not build it before the grading fix, lens-switch
demo, and Quiz Mode. If memory becomes the next pull-in, start with a first-party persisted profile plan;
compare LangMem/Mem0/Zep during that plan instead of wiring a provider directly.

## Considered: Explicit LangGraph

The project already uses LangChain `create_agent`, which runs on LangGraph's runtime and satisfies the
Week-3 agentic requirement without hand-authoring a graph. Current LangGraph docs make explicit graphs
valuable when the app needs custom state machines, durable checkpointing, interrupts, or deeper memory
stores. Those are real future needs, but they are not required to improve the two-day demo.

Decision: do not add direct `langgraph.*` imports in this window. Add explicit LangGraph only after a
written delta proves `create_agent` is no longer enough. Good future triggers are durable cross-session
memory, human-in-the-loop interrupts, or multiple coordinated modes that become hard to reason about as
one agent loop.

## Avoid In This Window

- Voice: high integration risk and weak proof of the core tutor.
- Cross-session memory: useful for personalization, but too much state and privacy surface to add before
  the core score-lift sequence is green.
- Explicit LangGraph graph/checkpointer/store code: useful later for durable memory and HITL, but
  unnecessary while `create_agent` keeps the two-day demo simpler.
- GraphRAG: conflicts with the current one-retriever discipline and adds infra risk.
- Multimodal: a new modality, not needed for the current score lift.
- Vector DB swap: breaks the one-Chroma, same-embedder reuse contract and forces re-ingest work with weak
  demo lift.
- Admin/gradebook UI: reuse `review_queue.jsonl` and redacted traces instead.
- Equation/image authoring tooling: a new tool surface against MINT restraint.
- Admin upload, caching, cohort rollout, flashcards: useful later, weak demo lift now.

## Review Gate

Every non-trivial implementation PR still needs a different-model or fresh-context review before merge.
Do not use the held-out `test` split for tuning, prompt iteration, demo prep, or pull-in validation.
