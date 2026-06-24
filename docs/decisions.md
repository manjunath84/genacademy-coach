# Architecture Decisions

The load-bearing, settled decisions behind GenAcademy Coach. Reopening one needs a new entry here plus
a note in the affected spec. Status: post-MVP, aligned to the Week-3 project handout on 2026-06-15 and
refreshed after the shipped Teach/Quiz/Skill-Gap/auth/memory slices on 2026-06-18.

---

### AD-1 - Direction: Adaptive, Grounded Tutor on `genacademy-rag`
**Decision.** Build a bring-your-own adaptive AI tutor layered on the author's Week-2 `genacademy-rag`
system.
**Why.** It compounds prior work, targets a real cohort learning problem, and avoids replicating the
handout's solution kits. The Week-2 foundation already provides retrieval, citation, refusal, provider,
and eval machinery.
**Rejected.** One of the six pre-scoped handout projects as the main project. ElevenLabs voice remains a
pull-in idea, not the headline.

### AD-2 - MVP: Text Teach Loop First
**Decision.** The Thursday MVP is the text teach loop: explain a concept, check understanding, and
re-explain differently when the learner stumbles.
**Why.** This is the clearest personalization beat and the strongest end-to-end task completion story.
**Rejected.** Quiz-only, interview-only, admin-upload-first, or voice-first scope.

### AD-3 - Build Track: LangChain `create_agent` on LangGraph Runtime
**Decision.** Use LangChain `create_agent` for the Week-3 build. Do not hand-author an explicit
LangGraph graph this week.
**Why.** The handout's Track 2 is LangChain + LangGraph. The Week-3 LangGraph materials teach
`create_agent` as the pre-assembled, LangGraph-backed agent path for a single-agent model/tool loop,
and current LangChain docs describe LangChain agents as built on LangGraph. That gives the project the
required agent runtime while keeping MVP scope small and reserving explicit graph authoring for a
feature that needs it.
**Trigger to promote.** Durable cross-session memory, HITL pause/resume, or multi-mode coordination
becoming demo-core.
**Rejected.** Direct `StateGraph` from day 1.

### AD-4 - Retrieval: One Source-Prioritized Course Retriever
**Decision.** Use one retriever over the extended Week-2 collection. Tag every chunk with `source_type`
and prioritize slides/handouts for teaching, notes for gaps, transcripts as support/fallback.
**Why.** One retriever reduces sparse-index and wrong-tool risk for the MVP. Source priority preserves
the desired learning-material hierarchy without forcing the model to route among brittle tool buckets.
**Trigger to split.** Add source-specific tools only if eval shows a measured recall gap the single
retriever cannot solve through metadata/ranking.
**Rejected.** Three separate `retrieve_lectures`, `retrieve_assignments`, and `retrieve_student_qa`
tools. Those were tied to a CohortBrain partition that is not the MVP foundation.

### AD-5 - Corpus and Eval Source
**Decision.** Index local course corpus under `corpus/notes`, `corpus/slides`, `corpus/handouts`, and
`corpus/transcripts`. Never index `corpus/eval-questions`.
**Why.** The corpus is available locally and can be extended through the Week-2 ingestion path. Real
student chat questions are the strongest held-out eval source because they were asked live and are not
authored from the notes.
**Rejected.** A nonexistent `student_questions.jsonl` as the binding eval source; CohortBrain as a
required MVP dependency; NotebookLM exports as test data. NotebookLM or "Quiz Yourself" items may be
dev/seed only.

### AD-6 - Grading: Deterministic Gate, LLM Judge as Audit
**Decision.** The deterministic grounded grader is the pass/fail gate. The inherited Week-2 LLM judge is
available only as a secondary faithfulness audit.
**Why.** The MVP needs repeatable grading and a clear "won't bluff" boundary. Using the inherited judge
as audit avoids throwing away Week-2 infrastructure while keeping pass/fail deterministic.
**Rejected.** LLM self-ratings or LLM-judge pass/fail for the teach-loop MVP.

### AD-7 - Agenticity Proof: Model-Chosen Action + Strategy
**Decision.** The `create_agent` loop must emit structured `next_action` and `strategy` values chosen
from observations: `advance`, `re_explain_differently`, `drill`, `refuse_escalate`, or `stop`.
**Why.** A hardcoded branch can fake a single demo. The judge-facing proof is two different learner
answers producing different model-chosen strategies without changing Python control flow.
**Rejected.** A Python state machine where `if wrong: re_explain()` is the core adaptation.

### AD-8 - Trace Artifact: Local First, LangSmith Optional
**Decision.** The primary runtime trace is local JSON plus a CLI pretty print/screenshot. The local
Gradio demo renders an allow-listed card projection: `Decision basis`, labeled `action ...` and
`band ...` status chips, score, strategy, citation summaries, and tool-call summaries. LangSmith is an
optional companion when credentials are configured. A custom HTML viewer is deferred.
**Why.** The trace is required to prove agenticity, but the proof cannot depend on external auth,
network, or private-corpus trace exposure. The UI card makes the safe trace readable in a recording
without publishing raw trace JSON, learner inputs, tutor prose, retrieved spans, or secrets. LangSmith
is useful for debugging and a polished backup.
**Rejected.** HTML trace viewer as MVP-critical; LangSmith as the only proof artifact.

### AD-9 - State: Within-Session Profile
**Decision.** Store learner style, switchable track lens, optional bridge source, known concepts,
struggled concepts, coverage, turn budget, and transcript within the session.
**Why.** The handout calls state one of the hard parts; this is enough to drive adaptation without
pulling in durable memory infrastructure. Track is a teaching lens, not an identity: the same learner can
ask for a no-code/low-code explanation, a code-heavy explanation, or a bridge for the same topic.
**Rejected.** Cross-session memory in the MVP. Mem0 is a rollout pull-in.

### AD-10 - Human-in-the-Loop and Failure Path
**Decision.** Low confidence, out-of-corpus questions, tool failure, and learner flags route to refusal
plus a review-queue record. The demo must show at least one failure path.
**Why.** The handout explicitly says a happy-path-only agent is unfinished. Won't-bluff refusal is also
the product brand.
**Rejected.** Silent fallback to model priors, fabricated citations, or webhook-heavy mentor workflows
for the MVP.

### AD-11 - Pull-Ins: Shipped Bounded Pull-Ins vs. Future Pull-Ins
**Decision.** Quiz, Skill-Gap, cohort auth/admin, and privacy-first memory are shipped bounded pull-ins
because the teach loop, refusal/eval path, and trace work end-to-end. Mock interview, admin upload,
ElevenLabs voice, explicit LangGraph, public corpus hosting, and memory hardening remain future slices.
**Why.** This preserves the long-term cohort-product architecture while keeping the judged agenticity
proof anchored in Teach. Quiz and Skill-Gap reuse retrieval, citations, deterministic grading/ranking,
typed traces, and refusal rather than adding new agent loops. Auth/memory make per-user state honest
without letting memory become a knowledge source.
**Rejected.** Treating Quiz or Skill-Gap as the agenticity proof; starting voice/interview/admin upload
without a separate plan and privacy review.

### AD-12 - LangSmith Data-Egress Scoping for Evaluation
**Decision.** Adopt LangSmith for Week 4 evaluation in a default-private workspace, but **scoped**: only
synthetic / corpus-derived **cloud-safe** golden/dev rows are traced or sent to RAGAS / an LLM-judge, with
input/output masking and a retention TTL enabled. The frozen held-out `test` split and any run over raw
learner text stay on the local harness; the held-out number always comes from local artifacts. Recorded
2026-06-21.
**Why.** LangSmith workspaces are private-by-default, but that is **access control, not data egress**:
auto-instrumentation uploads raw LLM inputs/outputs — which include retrieved private-corpus spans and
real learner questions — to a third party. That collides with the guardrail that private-corpus trace
leakage is unacceptable. Scoping to cloud-safe rows plus masking lets the project use LangSmith's
dataset/trace/run-comparison convenience without egressing private content, and keeps the local notebook
harness as the source of truth. See `docs/week4-eval-plan.md`.
**Rejected.** Auto-instrumenting raw LLM inputs/outputs to LangChain's cloud; treating workspace privacy
as sufficient for private content; sending the frozen `test` split or raw learner text through any
third-party judge or tracer.
