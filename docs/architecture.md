# Design Decisions & Trust Boundary

GenAcademy Coach is a thin agentic layer on top of the Week-2 `genacademy-rag` foundation. The core
claim is not "the model knows the course"; it is "the app teaches only from retrieved course evidence,
or refuses and escalates."

## Trust Boundary

The `create_agent` teach loop is trusted for pedagogy, not facts or safety. It chooses the learner-facing
teaching move at runtime: `next_action` (`advance`, `drill`, `re_explain_differently`,
`refuse_escalate`, or `stop`) and the `strategy` used to explain or drill.

Python owns the deterministic gates:

- retrieval confidence bands and citation-presence checks
- refusal and mentor review-queue writes
- check-item and quiz grading
- stop/progress protection
- trace redaction and export allow-lists

The local/private demo UI is allowed to render a human-readable projection of the trace: `Decision
basis`, labeled `action ...` and `band ...` status chips, score, strategy, citation summaries, and tool
summaries. Those cards are a view over safe in-memory metadata, not permission to commit raw trace JSON,
raw learner inputs, generated tutor prose, retrieved span text, or secrets.

Course facts come only from retrieved citations. Memory can seed safe learner state, such as style,
track lens, topic hashes, and counts, but memory is never a citation source and never changes retrieval,
grading, refusal, or faithfulness decisions.

## Adapter Seams

- **Provider seam:** model calls route through the reused `genacademy-rag` provider boundary, so the
  Coach does not hard-code a new LLM client in its core workflows.
- **Vectorstore seam:** `build_course_vectorstore` keeps local Chroma as the tested path and allows the
  Week-2 Pinecone adapter for hosted serving once an approved corpus/index is seeded.
- **Memory seam:** `build_episodic_memory` selects `NullEpisodicMemory` by default. Mem0 is enabled only
  when both `MEM0_API_KEY` and `GENACADEMY_COACH_MEMORY_USER_SALT` are configured.
- **Auth seam:** the Gradio app has a bounded cohort login gate using the reused Week-2 user store,
  bcrypt password hashes, deploy seed-secret accounts, and server-side admin checks for account
  creation. It is not presented as production-grade or enterprise auth.
- **View seam:** Gradio and CLI are thin shells. Core modules under `src/genacademy_coach/*` keep agent,
  retrieval, grading, diagnosis, memory, and trace logic free of web-framework imports.

## Design Choices

The Week-3 agenticity proof is the teach loop, because it observes a learner answer and chooses a new
pedagogical action from that observation. Quiz and Skill-Gap are intentionally deterministic pull-ins:
they reuse retrieval, citations, grading, traces, and refusal rather than introducing new agent loops.
The UI reflects that distinction: Teach trace cards expose the runtime decision basis for the demo;
Quiz and Skill-Gap show deterministic scores, counts, actions, and safe metadata.

The deployment story is privacy-first. The private Hugging Face Space proves the app shell can run, but
private course corpus and generated indexes are not committed or uploaded. The hosted Pinecone adapter
is implemented; Chroma remains the tested path for the graded local walkthrough.

## Safety Evidence

The submission points graders to repeatable checks instead of raw artifacts:

- `uv run python scripts/check_eval_leak.py`
- `uv run python scripts/check_memory_leak.py`
- `uv run ruff check .`
- `uv run pytest -q`
- conservative dev evidence in `docs/teach-loop-status.md`
- live auth smoke: configured admin/member seed secrets accepted, default admin/member credentials
  rejected

Held-out eval questions, private corpus files, raw traces, review queues, generated local screenshots,
generated demo packets, generated quiz text, and secrets stay out of the committed repo unless a
separate review explicitly approves a public-safe artifact.
