# Skill-Gap UI Wrapper Plan

Status: implementation PR in progress. This is a thin-view follow-up to the shipped Skill-Gap
CLI/core slice, not a new agent loop.

## Purpose

Make Skill-Gap Diagnosis demoable from the local Gradio UI without changing the core algorithm. The UI
accepts existing teach/quiz trace session IDs, runs `SkillGapSession`, and shows a camera-readable gap
report plus redacted trace cards.

## Scope

- Add a third Gradio tab: `Skill-Gap`.
- Input: comma- or newline-separated source session IDs.
- Output: ranked gaps, deterministic signals, cited next-step IDs, refusal/escalation reason when no
  citeable span exists.
- Metadata: allow-listed `SkillGapTraceRow` fields only.
- Preset: local demo session IDs already used by the submission walkthrough.

## Non-Goals

- No new retrieval path, memory provider, or direct `langgraph.*` import.
- No raw trace JSON, learner answers, corpus span text, quiz prompts/options, rationales, or review
  queue free text in the UI metadata.
- No public corpus upload and no Space behavior change beyond the UI shell.
- No admin/gradebook surface.

## Safety Details

- Validate source session IDs before reading local trace files.
- Reuse `safe_trace_rows` with an explicit `SAFE_SKILLGAP_TRACE_FIELDS` tuple.
- Render trace summary cards from safe fields only.
- Keep the user-facing report compact: gap ID, priority, deterministic signal counts, action, citation
  IDs, and reason code. Do not render raw span text.

## Verification

- UI tests prove Skill-Gap metadata omits planted raw fields.
- UI tests prove trace summary cards do not expose citation samples or private review text.
- Core test rejects unsafe source session IDs.
- `pytest`, `ruff`, `git diff --check`, and `check_eval_leak.py` pass.
