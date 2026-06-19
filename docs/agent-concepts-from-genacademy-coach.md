# Agent Concepts Through GenAcademy Coach

This note maps the agent concepts from the course slides to the project we built. The useful mental
model is:

**Teach is the agentic proof. Quiz and Skill-Gap are deterministic workflows. Gradio is the view.
Python owns the safety boundary.**

That distinction is what keeps the project honest. The app does not call everything an agent just
because an LLM is involved.

## Project Compass

| Surface | What it is | Why it is designed that way |
|---|---|---|
| Teach | Supervised single-agent loop | LangChain `create_agent` chooses `next_action` and `strategy` at runtime from learner observations. |
| Quiz | Deterministic grounded assessment | The provider drafts cited MCQs, but Python validates and grades selected option IDs. |
| Skill-Gap | Deterministic diagnosis workflow | It composes teach traces, quiz traces, review-queue events, and retrieval into a cited next-step report. |
| Gradio app | Thin view | UI renders controls and safe trace cards; core behavior stays in testable Python modules. |
| Memory | Optional safe learner-state recall | Memory can personalize style/lens hints, but it never supplies facts, citations, grades, or refusal decisions. |

Check yourself: if the model is choosing the next step from an observation, it is agentic. If Python is
following a fixed path, it is a workflow.

## Agent, Chatbot, Workflow

| Concept | In the slides | In this project |
|---|---|---|
| Chatbot | One user message in, one answer out | Not the main product shape. A plain "answer my question" interface would not prove the adaptive tutor. |
| Workflow | Developer fixes the path ahead of time | Quiz and Skill-Gap. They retrieve, validate, grade, summarize, and stop through known code paths. |
| Agent | Goal plus tools; model chooses next step in a loop | Teach. The model chooses `advance`, `drill`, `re_explain_differently`, `refuse_escalate`, or `stop` from runtime evidence. |

Anchors: `src/genacademy_coach/teach_agent.py`, `src/genacademy_coach/teach_session.py`,
`src/genacademy_coach/quiz_session.py`, `src/genacademy_coach/skillgap_session.py`.

The course phrase "if the path is fixed, it is a workflow" is the cleanest way to explain the product:
GenAcademy Coach uses both, deliberately.

## The Teach Agent Loop

The Teach loop is the project version of reason -> act -> observe -> adapt.

| Loop part | Project component |
|---|---|
| Goal | Teach the requested course topic in the selected style and track lens. |
| State | `LearnerProfile`, current turn, active check item, topic hash, style, lens, recent observations. |
| Tools | Retrieve course corpus, generate check item, grade understanding, update profile, write trace, escalate to mentor. |
| Observation | Retrieved spans, evidence band, citation presence, learner answer grade, tool results, refusal state. |
| Runtime decision | `CoachAgentResponse.next_action` and `strategy`. |
| Stop condition | Turn limits, low grounding, explicit stop, progress guard, or mentor escalation. |

The model is allowed to teach and choose the next pedagogy move. It is not allowed to decide whether
course evidence exists, whether an answer is grounded, or whether a grade is correct.

Check yourself: when the learner gives a partial answer, the interesting product moment is not the
explanation text. It is whether the next action changes because of the observation.

## Autonomy And Control

GenAcademy Coach is not fully autonomous. It sits closer to a supervised or semi-autonomous system:

| Autonomy question | Project answer |
|---|---|
| Who chooses the next teaching move? | The Teach agent chooses at runtime. |
| Who decides whether evidence is good enough? | Python grounding gates. |
| Who decides whether to refuse? | Python thresholds and citation checks force refusal or escalation. |
| Who can see the steps? | The local/private demo UI shows allow-listed trace cards. |
| Who approves risky outcomes? | Mentor review queue handles unsupported or low-confidence cases. |

This is the right level for a tutor over private course material. Full autonomy would be the wrong
product shape because the cost of bluffing is high: it teaches the learner the wrong thing.

## Tools And MINT

The project follows the MINT principle: Minimal Intelligence, Necessary Tools.

| Slide idea | Project decision |
|---|---|
| More tools is not automatically better | We use one source-prioritized course retriever instead of separate slide, handout, notes, and transcript tools. |
| Read tools are safer than write tools | Most tools are read or metadata-write. Mentor escalation writes a bounded review queue row. |
| Tool schema matters | Tool calls use typed structures and tested core paths. |
| Agents pick wrong tools when the toolset is too broad | Explicit MCP, A2A, and multi-agent tool networks are deferred until an eval shows the need. |

Anchors: `src/genacademy_coach/teach_tools.py`, `src/genacademy_coach/foundation.py`,
`specs/tech-stack.md`, `docs/decisions.md`.

The senior-builder move here was boring on purpose: do not add tool breadth until the narrow toolset
fails in a measurable way.

## Memory

The project separates memory from evidence.

| Memory type | Course meaning | Project mapping |
|---|---|---|
| Working memory | Current prompt, recent tool results, current task state | Current Teach turn, retrieved spans, active check item, grade, trace metadata. |
| Session memory | Conversation/session history | `LearnerProfile` and recent turns inside the running session. |
| Long-term memory | Durable facts/preferences across sessions | Optional Mem0 safe state: style, lens, topic hashes, counts. Off by default. |
| Semantic memory | Stable facts/preferences | Safe learner preferences only, not course facts. |
| Episodic memory | Prior events/actions | Safe event summaries and hashes, not raw learner text or generated tutor prose. |

Memory can make the tutor feel continuous, but it must not become a hidden evidence source. Course facts
still come only from retrieval with citations.

Anchors: `src/genacademy_coach/memory.py`, `scripts/check_memory_leak.py`,
`docs/architecture.md`.

## Planning, Feedback, And Progress

The Teach agent does not write a long plan up front. It plans one teaching move at a time:

1. Retrieve citeable context.
2. Teach the concept.
3. Ask a check question.
4. Observe the learner answer.
5. Choose the next move.

That is closer to "plan one step at a time" than "planner-executor." It is slower than a single answer,
but it is the point of the product: the learner response changes the route.

The project guards against bad agent loops with:

| Failure mode | Guard |
|---|---|
| Repeating the same action forever | Turn limits and stop/progress protection. |
| Continuing from weak retrieval | Evidence bands and citation-present checks. |
| Ignoring the learner answer | Boundary grade locks and active check state. |
| Treating tool output as truth without validation | Python grading, citation checks, and faithfulness fallback. |

Anchors: `src/genacademy_coach/teach_session.py`, `src/genacademy_coach/grounding.py`,
`src/genacademy_coach/teach_types.py`.

## Confidence, Review Queues, And Human Checkpoints

The slides use STOP, CONFIRM, and PROCEED as a useful mental model. The project uses calibrated
retrieval bands instead of an LLM self-rating:

| Band | Current project threshold | Behavior |
|---|---:|---|
| STOP | below `0.40` | Refuse and/or escalate because evidence is too weak. |
| CONFIRM | `0.40` to `0.85` | Continue carefully with trace evidence and citation checks. |
| PROCEED | above `0.85` | Strong retrieval evidence, still citation-gated. |

The exact numbers are project-calibrated, not universal. If you quote them publicly, say they are the
current GenAcademy Coach thresholds, not general agent thresholds.

Human checkpoints appear where the project needs control:

- unsupported topic -> refusal and mentor review queue
- low grounding -> stop/refuse instead of guessing
- public/demo trace -> allow-listed evidence only
- deployment -> private corpus and generated indexes stay out of the hosted shell

Anchors: `src/genacademy_coach/escalation.py`, `docs/teach-loop-threshold-calibration.md`,
`README.md`.

## Observability

An agent without observability is hard to debug and hard to trust. GenAcademy Coach makes the loop
inspectable through safe traces:

| Observable signal | Project example |
|---|---|
| Trace | Decision basis, action, band, score, strategy, citation count, tool-call summary. |
| Tool history | Retrieval, check generation, grading, profile update, mentor escalation. |
| State | Topic hash, input hash, active check ownership, learner profile counts. |
| Metrics | Dev eval pass counts, refusal reasons, leak checks, lint/tests. |
| Error categories | Low retrieval, faithfulness fallback, grading mismatch, UI state confusion. |

The UI lesson we learned the hard way: a trace value must look like status, not like a broken button.
That is why status chips now read `action advance` and `band confirm`.

Anchors: `src/genacademy_coach/trace.py`, `src/genacademy_coach/web/gradio_app.py`,
`docs/build-learnings.md`.

## Cost And Latency

Loops multiply cost and latency. The project keeps that visible in the architecture:

| Cost/latency pressure | Project response |
|---|---|
| Every extra LLM turn adds time | Quiz and Skill-Gap are workflows, not extra agents. |
| Every tool call can fail | Toolset is small and read-mostly. |
| Every retry can waste tokens | Teach has run limits and fallback paths. |
| Model choice can drift | Provider/model IDs, pricing, and latency should be re-checked before public claims. |

If you write a public post about latency rankings or model providers, re-check the source on the day of
posting. Model speed, price, and IDs change.

Anchors: `src/genacademy_coach/teach_agent.py`, `docs/build-learnings.md`, `specs/tech-stack.md`.

## Risks We Actually Faced

| Slide risk | Project version | Guard |
|---|---|---|
| Agents get stuck in loops | Teach controls could appear to rerun the same state if the UI did not label the active check clearly. | Start/Submit split, active check state, Playwright regression. |
| Hallucinated tool calls | Model should not invent course facts or unsupported actions. | Small tool registry, schema validation, Python gates. |
| Wasted tokens | Repeated generation is slow and brittle for demos. | Cached foundation, simple demo defaults, deterministic pull-ins. |
| Bad decisions | Agent might advance after a weak learner answer. | Deterministic grading and boundary grade lock. |
| Wrong tools | Too many retrievers would invite routing mistakes. | One source-prioritized retriever. |
| Weak evals | Safe refusal can hide retrieval gaps. | Dev split diagnostics, reason counts, leak checks. |

This is the "failure path is the demo" lesson: the interesting parts of the project are the places where
it refuses, stops, or asks for review.

## Multi-Agent Patterns

The runtime app is intentionally not a multi-agent system yet.

| Pattern | Project status |
|---|---|
| Single agent | Teach uses one `create_agent` loop with a bounded toolset. |
| Router | Not needed yet. The three modes are selected by UI/CLI, not an LLM router. |
| Supervisor | Not in runtime. Builder/reviewer separation exists in the development process. |
| Subagents | Used by development tools to research docs/plans faster, not part of the product architecture. |
| Handoffs | Mentor escalation is a review-queue handoff to a human, not an agent-to-agent handoff. |
| Explicit LangGraph graph | Deferred until durable HITL pause/resume, cross-session coordination, or complex state earns it. |

This is a good public lesson: not building multi-agent architecture can be the correct senior decision.

## Development Lifecycle

The project followed the Agent Development Lifecycle in miniature:

| ADLC phase | What happened here |
|---|---|
| Scope | Adaptive grounded tutor, not a general course chatbot. |
| Prototype | Teach loop first, with retrieval, check, grade, and trace. |
| Build | Add Quiz, Skill-Gap, UI, auth, safe memory as bounded pull-ins. |
| Evaluate | Dev evals, regression tests, lint, leak checks, manual UI QA. |
| Deploy | Private Hugging Face Space shell, no private corpus uploaded. |
| Monitor/improve | Build learnings, PR review, trace-card UX fixes, threshold calibration. |

## Public-Safe Storytelling Rules

Use the concepts publicly, but keep the project boundary intact:

- Do not post private corpus excerpts, raw traces, generated tutor prose, held-out eval text, secrets, or
  local demo artifacts.
- Prefer original diagrams, redacted screenshots, or screenshots that show UI structure without private
  course text.
- If using course slide screenshots directly, confirm attribution and permission first.
- For model speed/pricing claims, re-check current sources before posting.
- Good public phrasing: "In this project, Teach is agentic; Quiz and Skill-Gap are workflows by design."

The strongest learning is not "agents are powerful." It is "agents are powerful only when the boundary
around them is explicit."
