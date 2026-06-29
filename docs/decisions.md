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

### AD-6 - Grading: Deterministic MVP Gate, Evidence-Bound Ladder Deferred
**Decision.** The current MVP pass/fail gate is the deterministic grounded grader. The inherited Week-2
LLM judge is available only as a secondary faithfulness audit, not as the active pass/fail gate.
**Why.** The MVP needs repeatable grading and a clear "won't bluff" boundary. Using the inherited judge
as audit avoids throwing away Week-2 infrastructure while keeping the current scorer reproducible.
**Evolution path.** Open-answer teach checks may become more semantic through deterministic concept
groups, supported synonyms, optional embedding similarity against the cited expected answer/source span,
and eventually evidence-bound model grading when earned by labeled eval evidence. Any scorer change must
be scorer-versioned and re-evaluated. AD-13 governs when a model verifier or model grader may influence
behavior.
**Rejected.** LLM self-ratings or immediate LLM-judge pass/fail for the teach-loop MVP.

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
optional companion when credentials are configured. Week-4 eval-time LangSmith usage is governed
separately by AD-12. A custom HTML viewer is deferred.
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
**Decision.** Adopt LangSmith for Week 4 evaluation in a private workspace, with **owner-approved eval
egress**: seed/dev golden eval runs may be uploaded to the private LangSmith project, including raw
learner questions, generated tutor prose, retrieved citation IDs/text, tool calls, scores, latency, and
token counts, when the upload is intentional and documented. The frozen held-out `test` split still stays
local-only and never enters LangSmith, prompts, examples, tuning, RAGAS, or an LLM judge. Public/committed
artifacts remain redacted; secrets are never uploaded. RAGAS and any LLM-judge evaluation remain
cloud-safe-only for seed/dev unless a separate judge-egress decision is approved. Recorded 2026-06-21;
revised 2026-06-24 after explicit project-owner approval to use LangSmith as the full Week-4 eval trace
workspace.
**Why.** The course corpus covers a bounded Gen Academy project context, and the owner wants the Week-4
submission to show the full golden-set evaluation in LangSmith rather than only a cloud-safe subset.
LangSmith is still data egress, not merely local storage, so uploads must be deliberate: use a private
project, avoid secrets, keep the frozen `test` split local, mask fields not needed for submission or
evaluators by default, and delete/retire traces after the submission window unless the owner records a
retention reason. Local JSON artifacts remain the reproducible source of truth, while LangSmith is the
review and observability surface.
**Rejected.** Publicly posting raw traces or screenshots that expose raw learner/corpus text; committing
raw traces or private source files; uploading secrets; sending the frozen `test` split through any
third-party tracer or judge; sending seed/dev raw text to RAGAS or an LLM judge without a separate
judge-egress decision; accidental auto-tracing outside the named eval project.

### AD-13 - Evidence-Bound Verification and Grading Ladder
**Decision.** Separate answerability/refusal from learner-understanding grading, and use the narrowest
reliable scorer for each decision. Deterministic floors remain non-overridable. Evidence-bound model
verification or grading is deferred until evals show the deterministic path is insufficient, data egress
is approved, and the new scorer/verifier is versioned and re-evaluated.

**Answerability/refusal.** The tutor answers only from retrieved, citeable evidence. Below the STOP
threshold, or with no citeable span, it refuses and queues for review. Refusal recall on
negative-control/adversarial cases stays a hard tripwire: any change that lowers it is reverted. The
CONFIRM-band false-refusal slice must first use a deterministic conjunction: CONFIRM band, citation
resolves, span is on topic, and the case is not adversarial. A future evidence-bound sufficiency
verifier may be added only as an advisory input inside that conjunction, only after the deterministic
slice leaves a measured residual false-refusal gap. It judges retrieved spans only, cites span IDs, never
uses model priors, never operates below STOP, and never converts a deterministic refusal into teaching by
its own authority.

**Learner grading.** Closed-form and short conceptual checks use deterministic scoring first: exact
matching, keyword/concept groups, supported synonyms, and optional embedding similarity against the cited
expected answer or source span. A genuinely open-ended conceptual answer may use an evidence-bound,
rubric-bound model grader only after deterministic plus embedding scoring is shown insufficient on a
labeled dev disagreement set that covers false negatives, false positives, negation, and parroting. A
model grader may correct deterministic misses only when the answer is entailed by cited course evidence;
the rubric alone is not enough to advance the learner.

**Why.** "Deterministic forever" is too blunt for open-ended tutoring, but "the model thinks it is
correct" is not a safety story. This ladder keeps the grounded/refusal promise while leaving a measured
path to semantic judgment when the answer type earns it.

**Data and eval rules.** External model verifier or grader use is data egress and requires recorded
egress approval plus seed/dev cloud-safe scope unless separately approved. Every model verifier or
grader, local or external, must exclude the frozen `test` split, keep committed artifacts redacted, use
scorer/verifier versioning, and report before/after evals as new runs.

**Rejected.** A single all-purpose model judge for both answerability and grading; model self-confidence
as a gate; model verification below STOP; model grading before a labeled insufficiency set exists;
sending the frozen `test` split to a judge; treating CRAG, Self-RAG, or explicit graph vocabulary as a
reason to add model layers before the evals earn them.
