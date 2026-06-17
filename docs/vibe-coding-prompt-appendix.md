# Vibe-Coding Prompt Appendix

> Sanitized appendix for the Week 3 submission. These are representative prompts from the build and
> review workflow, grouped by intent. They intentionally omit API keys, private corpus text, held-out
> eval questions, raw generated quiz content, and uncommitted transcript excerpts.

## Working Agreement

The project started with a tool-neutral working agreement in `AGENTS.md`. That file functioned as the
standing system prompt for every builder and reviewer:

- Grounded or refuse.
- Citations captured at retrieval, never reconstructed.
- Held-out `test` split is sacred.
- No direct `langgraph.*` imports this week.
- Builder is never the sole judge.
- Show tests, lint, leak checks, and runtime traces before calling work done.

## Planning And Review Prompts

Representative prompts used to keep design ahead of implementation:

```text
Provide a prompt to review docs/superpowers/plans/2026-06-15-teach-loop-agent.md with another AI.
```

```text
Provide a prompt to get it reviewed with Kimchi.
```

```text
Provide concise prompt to get Claude fixes reviewed again for PR #10.
```

```text
Provide a prompt to review the PR by another AI acting as a Staff AI engineer and also as a hackathon judge. Add more roles if required.
```

```text
Provide a prompt to get it reviewed with Claude also.
```

The review prompts consistently asked the reviewer to check:

- `AGENTS.md` guardrails.
- Whether claims were backed by source files or runtime evidence.
- Whether private corpus/eval text could leak.
- Whether the held-out test split was untouched.
- Whether scope matched the two-day demo window.
- Whether the feature improved the hackathon/judging narrative without destabilizing the floor.

## Implementation Steering Prompts

Representative prompts used to drive code changes:

```text
Gemini review comments. fix the issues if you agree and proceed with implementation.
```

```text
Claude review comments. can you fix what you agree and then merge the PR.
```

```text
Work on this now - Next item: use the new diagnostics to triage why 9/10 dev teach-loop scenarios had zero retrieval coverage.
```

```text
Can you make the suggested changes if you agree and also remove dead branch/comment.
```

```text
Claude review comments. fix everything if you agree.
```

```text
Fix as much issues as possible in this PR itself and then merge the PR and start working on next task.
```

This pattern was deliberate: the human supplied reviewer findings, and the builder agent fixed only the
findings it agreed with after reading the code and tests.

## Verification And Merge Prompts

Representative prompts used to enforce the "evidence before done" gate:

```text
Once fixed, merge the PR and suggest next step.
```

```text
Merge the PR.
```

```text
Also make sure after every PR, roadmap is updated.
```

```text
Create a PR.
```

```text
Can the PR be reviewed by Claude using PR review toolkit?
```

The repeated merge instruction was paired with verification in the repo:

- `uv run pytest -q`
- focused pytest commands for the changed slice
- `uv run ruff check .`
- `git diff --check`
- `uv run python scripts/check_eval_leak.py`
- live Nebius demo runs for the agent loop and quiz pull-in

## Product Strategy Prompts

Representative prompts used to keep the project aligned with the judging window:

```text
I still have 2 more days for the demo. Thinking of pulling in somethings from the pull-in list of roadmap.md file. I can increase my score.
```

```text
My personal interest to add memory. Can check other options for memory other than mem0 like langmem or other free providers for now.
```

```text
If we add memory, we can give more personalization to teaching experience.
```

```text
Do you think its a good idea to add LangGraph also? Act as a Staff AI engineer and suggest but also keep the 2 days time window in mind.
```

The conclusion was to defer durable memory and explicit LangGraph. The demo already had within-session
personalization and same-topic lens switching. Adding persistence before the submission would introduce
privacy, deletion, and uncited-memory risk.

## External Reference Prompts

Representative prompt used after reviewing public AI-tutor examples:

```text
These files contain some ideas on how to create an AI teacher or tutor. Any idea worth incorporating into our plan?
```

The adopted ideas were principles, not copied surfaces:

- Low-stakes within-session mastery framing.
- Deterministic quiz criteria pinned from cited spans.
- Instructor-review surface via `review_queue.jsonl` and redacted traces.
- Reproducibility via split manifest, checksums, and idempotent ingest.

The deferred ideas were explicitly documented:

- Hardcoded hint ladders.
- Admin/gradebook UI.
- Vector database swap.
- Equation/image/multimodal tooling.

## ChatGPT Research Agent Brainstorm Prompt

This block is a representative prompt artifact, not final project prose. It is prepared for optional
future research and was not used to tune the held-out eval split.

```text
Act as a Staff AI engineer, AI education product lead, privacy reviewer, and hackathon judge.

Context:
- I built GenAcademy Coach, a grounded adaptive AI tutor over my local Gen Academy course corpus.
- It builds on my Week 2 RAG project and reuses the embedder, Chroma schema, retrieval/citation path, provider boundary, and eval discipline.
- Week 3 MVP is a teach loop: retrieve cited course evidence, explain in a learner style, check understanding, grade deterministically where possible, re-explain differently on a stumble, and refuse/escalate when it cannot cite evidence.
- Quiz Mode now exists as a grounded deterministic pull-in: generated cited MCQs, Python option-ID grading, redacted trace.
- Constraints: two-day demo window, no held-out test split use, no private corpus excerpts in public output, no direct langgraph.* imports this week, no provider-backed memory without privacy/deletion plan.

Task:
Brainstorm high-leverage improvements for an AI teaching assistant that would increase judging score without destabilizing the demo.

Please produce:
1. Ranked ideas by score lift vs implementation risk.
2. Which rubric dimension each idea helps: execution, technical thinking, creativity, consistency, or initiative.
3. What to explicitly avoid in a two-day window.
4. Memory/personalization ideas that do not become a hidden source of uncited course facts.
5. A demo narrative that makes the builder's human decisions visible.
6. Review-blocker risks under grounded-or-refuse, eval privacy, and scope discipline.

Do not ask for or infer private course content. Use only the abstract project description above.
```

## Sanitization Rule

Anything copied into the external submission should pass this test:

- It names artifacts, commands, IDs, scores, bands, and safe metadata.
- It does not include raw corpus snippets, private eval questions, generated quiz text, API keys, or
  local-only transcript excerpts.
- It does not claim held-out test performance unless the held-out test split is explicitly run for final
  reporting.
