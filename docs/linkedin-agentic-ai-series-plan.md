# Build-In-Public Series Plan: Agent Concepts Through GenAcademy Coach

Goal: turn the agent concepts from the course into a public learning series grounded in the GenAcademy
Coach build, without publishing private corpus, raw traces, secrets, generated quiz text, or held-out
eval content.

Recommended series title:

**Building an Agent That Refuses to Bluff: Notes from GenAcademy Coach**

## Recommendation

Publish this as a series, not one large post. The project contains too many useful concepts for one
LinkedIn post, and the best audience experience is one idea per post:

1. short hook
2. concrete project moment
3. concept name
4. what changed in the implementation
5. reusable lesson

The through-line should be:

**I did not build a smarter chatbot. I built a bounded tutor where the agent teaches, Python verifies,
and unsupported topics escalate instead of becoming confident nonsense.**

## Public Guardrails

- Use redacted UI screenshots, original diagrams, or public-safe architecture sketches.
- Do not post raw trace JSON, private corpus text, generated tutor prose, held-out eval text, secrets, or
  generated quiz screenshots.
- If using screenshots from course slides, confirm attribution and permission first. Safer default:
  recreate the idea in your own words and diagrams.
- When quoting model latency, pricing, or provider comparisons, re-check current sources on the day of
  posting.

## Series Outline

| # | Working title | Hook | Concept | Project story | Anchor | Suggested visual |
|---|---|---|---|---|---|---|
| 1 | I Built a Tutor That Knows When to Stop | "I did not build a smarter chatbot." | Grounded-or-refuse | Teach only from citeable spans; unsupported topics go to mentor review. | `README.md`, `src/genacademy_coach/escalation.py` | Trust-boundary diagram or redacted refusal card. |
| 2 | One-Shot RAG Answers, Tutors Loop | "A RAG answer stops at output. A tutor observes the learner." | Agent loop | Teach -> check -> grade -> runtime choose `advance`, `drill`, or `re_explain_differently`. | `src/genacademy_coach/teach_types.py`, `docs/architecture-diagrams.md` | Teach-loop flow with safe trace card. |
| 3 | Teach Is Agentic; Quiz Is Not | "Calling everything an agent makes the architecture worse." | Agent vs workflow | Teach uses runtime decisions; Quiz and Skill-Gap are deterministic pull-ins. | `src/genacademy_coach/quiz_session.py`, `src/genacademy_coach/skillgap_session.py` | Three-lane diagram: Teach, Quiz, Skill-Gap. |
| 4 | I Used LangGraph Without Hand-Writing a Graph | "The right graph was the one I did not build yet." | MINT / earned complexity | LangChain `create_agent` uses LangGraph-backed runtime; explicit graph authoring is deferred. | `specs/tech-stack.md`, `src/genacademy_coach/teach_agent.py` | `create_agent` boundary diagram. |
| 5 | The Best Tool Design Decision Was Deleting Tools | "More tools made the system less reliable." | Tool selection | One source-prioritized retriever beat separate slide/handout/transcript tools for MVP. | `docs/decisions.md`, `src/genacademy_coach/foundation.py` | Source-priority stack. |
| 6 | Citations Are Data Lineage | "A citation should be captured, not invented later." | Grounding and provenance | Retrieved spans carry citation metadata into answers and traces. | `src/genacademy_coach/grounding.py`, `src/genacademy_coach/teach_types.py` | Span -> citation -> response chain. |
| 7 | A Held-Out Set Is Sacred | "A test set is not held out if the retriever can see it." | Eval hygiene | Eval questions are split, checksummed, and never indexed or used for prompt tuning. | `src/genacademy_coach/eval_split.py`, `scripts/check_eval_leak.py` | Eval boundary diagram. |
| 8 | Your Model's Confidence Is Not a Confidence Signal | "The model saying it is sure is not evidence." | Confidence bands | STOP/CONFIRM/PROCEED come from retrieval scores and citation checks. | `docs/teach-loop-threshold-calibration.md`, `src/genacademy_coach/settings.py` | Threshold bar. |
| 9 | Let the Model Teach. Make Python Grade. | "Creativity and correctness belong on different sides of the boundary." | Deterministic verification | Model drafts check/quiz items; Python owns grades, answer keys, and locks. | `src/genacademy_coach/grounding.py`, `src/genacademy_coach/quiz_types.py` | Split-brain diagram: model drafts, Python verifies. |
| 10 | The Failure Path Is the Demo | "The happy path is table stakes." | HITL / escalation | Unsupported topics refuse and write a mentor review queue row. | `src/genacademy_coach/teach_tools.py`, `docs/teach-loop-status.md` | Refusal path flow. |
| 11 | Raw Traces Are Not Demo Artifacts | "Proof must be safe and legible." | Observability and redaction | UI renders allow-listed trace cards instead of raw JSON. | `src/genacademy_coach/web/gradio_app.py`, `src/genacademy_coach/privacy.py` | Before/after trace surface. |
| 12 | Quiz Worked Because It Was Not Another Agent | "The second feature reused the core instead of adding another loop." | Bounded pull-ins | Provider drafts MCQs; Python validates and grades selected option IDs. | `src/genacademy_coach/quiz_session.py`, `src/genacademy_coach/quiz_items.py` | Quiz workflow diagram. |
| 13 | Memory Is for Learner State, Not Course Facts | "Personalization is not permission to store everything." | Memory design | Optional Mem0 stores safe state only and never supplies citations. | `src/genacademy_coach/memory.py`, `scripts/check_memory_leak.py` | Safe memory vs never-store table. |
| 14 | Skill-Gap Diagnosis Is Trace Analytics | "The next feature was deterministic composition, not another LLM judge." | Signal composition | Skill-Gap reads traces and review events, then retrieves cited next steps. | `src/genacademy_coach/skillgap_session.py` | Teach/quiz/review -> ranked gaps. |
| 15 | Why I Did Not Build Multi-Agent Yet | "Not adding a supervisor was an architecture decision." | Multi-agent restraint | Runtime is single-agent plus workflows; subagents are development helpers only. | `AGENTS.md`, `specs/tech-stack.md` | Current architecture vs deferred architecture. |
| 16 | The Agent Development Lifecycle in Practice | "The lifecycle is less glamorous than the demo, and more important." | ADLC | Scope, prototype, build, evaluate, deploy, monitor all showed up in the project. | `docs/build-learnings.md`, `README.md` | Timeline of project decisions. |

## Suggested Publishing Cadence

Start with 5 posts in week one, then continue if the audience responds:

| Day | Post |
|---|---|
| Monday | 1. I Built a Tutor That Knows When to Stop |
| Tuesday | 2. One-Shot RAG Answers, Tutors Loop |
| Wednesday | 3. Teach Is Agentic; Quiz Is Not |
| Thursday | 4. I Used LangGraph Without Hand-Writing a Graph |
| Friday | 5. The Best Tool Design Decision Was Deleting Tools |

Then publish posts 6-16 as a slower follow-up series.

## Post 1 Draft

I did not build a smarter chatbot.

I built a tutor that knows when to stop.

That became the most important design decision in GenAcademy Coach. The product promise is not "the
model knows the course." The promise is: if the system can retrieve citeable course evidence, it teaches;
if it cannot, it refuses and escalates to a mentor.

That boundary changed the whole architecture:

- the Teach flow is agentic because the model chooses the next teaching move at runtime
- the retrieval and citation checks are deterministic Python gates
- Quiz and Skill-Gap are workflows, not extra agents
- traces are safe, redacted evidence cards, not raw debug dumps
- memory can personalize learner state, but it cannot become a source of facts

The lesson I took from building it:

An agent is not trustworthy because it sounds confident. It becomes useful when the system around it
knows what the agent is allowed to decide, what it must prove, and when it must stop.

## Reusable Template

Use this structure for each post:

```text
Hook:
One sentence that names the surprise.

Project moment:
What happened while building GenAcademy Coach?

Concept:
What agentic AI idea does this illustrate?

Design decision:
What did we choose, defer, or simplify?

Reusable lesson:
What should another builder remember?
```

## One-Line Series Summary

GenAcademy Coach is a practical case study in bounded agent design: one agentic Teach loop, deterministic
workflow pull-ins, strong grounding gates, safe memory, human escalation, and traceable evidence.
