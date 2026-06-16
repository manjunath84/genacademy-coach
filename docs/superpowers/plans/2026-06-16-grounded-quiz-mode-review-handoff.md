# Grounded Quiz Mode Plan Review Handoff

You are the required fresh-context / different-model reviewer for the proposed Grounded Quiz Mode
implementation plan. Review the current PR/branch only. Do not edit files, commit, push, or merge.

## Inputs

- Constitution / guardrails: `AGENTS.md`
- Roadmap: `specs/roadmap.md`
- Score-lift plan: `docs/two-day-score-lift-plan.md`
- Proposed plan: `docs/superpowers/plans/2026-06-16-grounded-quiz-mode.md`
- Existing reusable code:
  - `src/genacademy_coach/foundation.py`
  - `src/genacademy_coach/grounding.py`
  - `src/genacademy_coach/check_items.py`
  - `src/genacademy_coach/teach_types.py`
  - `src/genacademy_coach/teach_session.py`
  - `src/genacademy_coach/teach_tools.py`
  - `src/genacademy_coach/trace.py`
  - `src/genacademy_coach/escalation.py`

## Review Questions

1. Does the plan preserve all `AGENTS.md` guardrails?
   - grounded-or-refuse;
   - retrieval-derived evidence only, no model self-confidence;
   - citations captured at retrieval, not reconstructed;
   - no direct `langgraph.*` imports;
   - pure core / thin view;
   - Week-2 foundation reuse;
   - held-out `test` split untouched.
2. Is the scope small enough for the final two-day demo window?
3. Does deterministic grading stay fully in Python after the model generates the item?
4. Are the planned validators sufficient to prevent unsupported citation IDs, empty answer keys, and
   hallucinated correct options?
5. Are tests adequate for refusal, trace redaction, deterministic grading, and generation validation?
6. Does the plan avoid overclaiming Quiz Mode as the agenticity proof? The teach loop remains the
   agentic surface; Quiz Mode is a grounded deterministic assessment pull-in.
7. Is the plan ready to approve for implementation? If not, list blockers first.

## Output Format

Return:

- Verdict: `APPROVE`, `APPROVE WITH REQUIRED FOLLOW-UP`, or `REQUEST CHANGES`
- Critical blockers
- Important issues
- Minor suggestions
- Verified OK
- Recommended action

Do not quote private corpus or eval text. Scenario IDs, trace IDs, file names, aggregate counts, and
reason codes are safe.
