# Submission Hardening Plan

Date: 2026-06-17

This plan hardens evidence, packaging, and grader visibility. It does not authorize outward actions such
as recording, public repo changes, Space config changes, or corpus upload. Those are runbooks for a human
go/no-go.

## P0 - Must Finish Before Submission

| Item | Outcome | Owner action | Verification |
|---|---|---|---|
| Grader 5-minute path | First README screen links the core proof: UI walkthrough, dev eval JSON, runnable teach command, Space URL with shell limitation, screenshot inventory, and hardening docs. | Done in PR #24. | README links resolve; no raw private trace JSON committed. |
| Overclaim micro-fixes | Web chat, HF shell, personalization, Mock Interview, and dev-only metrics are worded precisely. | Done in PR #24. | AGY review returned GO for PRs #23/#24 with no nits. |
| Verification evidence | PR body includes `pytest`, `ruff`, leak guard, and dev eval output. | Done in PR #24. | Outputs pasted; `--split test` not run. |
| Video script | Canonical script stays `docs/demo-walkthrough-with-screenshots.docx`; README links it instead of duplicating. | Human records after PR review. | Video under time cap; no generated quiz text or raw corpus snippets visible. |
| Live URL framing | Space is either honestly labeled as deployment shell or backed by a public-safe corpus subset. | Done as deployment-shell framing; public-safe corpus upload remains gated. | Cold click is framed as shell, not grounded live tutor. |

## P1 - Strong Follow-Up If Time Allows

| Item | Outcome | Guardrail |
|---|---|---|
| Skill-Gap Diagnosis workflow | Deterministic, cited next-step plan from traces + quiz grades + review queue; demoable in under 60 seconds. | Separate spec/review/build; no LLM mastery grading; no new deps or memory provider. |
| Prompt-injection / unsupported-advice eval scenario | Show that the tutor refuses or escalates unsupported course claims and unsafe instruction overrides. | Add only dev/seed scenario unless official final reporting authorizes `test`; do not leak prompt text. |
| Leak guard fails loud on missing eval sources | Avoid false confidence when private eval files are absent locally. | Test missing-source behavior without committing private eval files. |
| Diagram shipped-vs-planned labels | Architecture diagrams match current shipped UI and pull-in roadmap. | No claims that voice, memory, admin, or interview shipped. |

## P2 - Post-Submission / Product Direction

| Item | Why it matters | Required gate |
|---|---|---|
| Cross-session memory | Personalization beyond one session. | Separate plan covering privacy, deletion, provider choice, and citation boundary. |
| Quiz + Skill-Gap on live Space | Turns deployment shell into interactive public demo. | Public-safe corpus subset approved and uploaded; no private corpus/eval text. |
| End-to-end multi-mode test | Regression guard across teach -> quiz -> gap report. | Core remains pure; no browser dependency in core tests. |
| Rubric-aware project feedback | The tutor can review a learner's project against a rubric. | Official rubric available and citeable; no invented grading criteria. |

## Runbook: Record the <=5-Minute Video

Stop if `.env` is missing, the local UI cannot boot, or the browser shows generated quiz text by default.

1. Start the local UI from the repo root:

   ```bash
   PORT=7861 uv run python app.py
   ```

2. Open `http://127.0.0.1:7861` locally. Do not use `share=True` or a public tunnel.
3. Follow `docs/demo-walkthrough-with-screenshots.docx` as the canonical flow:
   grounded teach, safe refusal, hidden quiz, local reveal only if needed.
4. Keep generated quiz question/option text hidden for the public recording unless the topic and output
   have been re-reviewed as public-safe.
5. Use CLI commands in `docs/demo-and-deliverables.md` only as fallback evidence if the live provider call
   stalls.
6. Save only public-safe screenshots or clips. Re-review any frame that shows teach output before posting
   publicly.

## Runbook: Create External Google Doc

Stop if any copied text includes raw corpus snippets, held-out eval prompts, `.env` values, raw trace JSON,
or generated quiz question/option text.

1. Start from `docs/submission-google-doc-draft.md`.
2. Add public-safe screenshots from `docs/assets/pr22-ui-screenshots/` and the screenshot inventory.
3. Link the GitHub repo, PRs, Space URL, and video.
4. Include the dev metrics as dated dev evidence only: `7/10` overall, `7/8` teachable, two safe
   refusals, held-out `test` split unrun.
5. State that the live Space is a private deployment shell unless the public-safe corpus runbook has been
   completed.

## Runbook: Upload Public-Safe Corpus Subset to Space

This is gated and must not run during documentation-only hardening.

1. Select a small public-safe subset that does not include private course PDFs/transcripts, held-out eval
   questions, generated quiz text, or secrets.
2. Re-ingest with the same embedder contract: `all-MiniLM-L6-v2`, 384 dimensions, same collection schema.
3. Upload only the approved Chroma/data artifacts to the private Space persistent storage.
4. Smoke test two paths:
   - Grounded teach on approved public topic.
   - Safe refusal on out-of-corpus topic.
5. Record URL, corpus limitation, smoke date, and failure mode in README/deploy docs.
6. If the public-safe subset is not ready, keep the Space framed as a deployment shell.

## Runbook: Pre-Public Secret, Screenshot, and Repo Flip Review

This is gated and must happen immediately before any public repo flip.

1. Verify secrets are not tracked:

   ```bash
   git log --all -- .env .env.local '*.key'
   ```

2. Verify private content is not tracked:

   ```bash
   uv run python scripts/check_eval_leak.py
   ```

3. Re-review screenshots, DOCX, Google Doc, README, and demo docs for:
   - Raw corpus snippets.
   - Held-out eval questions, IDs, checksums, or n-grams.
   - Generated quiz question/option text.
   - Raw trace JSON.
   - API keys, tokens, provider URLs with secrets, or local absolute paths that expose private data.
4. Only after review, flip repo visibility if required by the submission.

## Before Submission Checklist

| Check | Status |
|---|---|
| Status table + grader path added to README | Done in PR #24 |
| <=5-minute video recorded from canonical DOCX | Pending human action |
| External Google Doc created from repo draft | Pending human action |
| Public-safe screenshots only | Pending human review |
| Live URL shows grounded teach + safe refusal, or is clearly framed as deployment shell | Done as deployment-shell framing; grounded public subset remains gated |
| Public-safe corpus uploaded if live grounded Space is required | Gated; not executed |
| Overclaims reconciled: web chat, HF shell, personalization, Mock Interview, dev-only metrics | Done in PR #24 |
| Injection/unsupported-advice test added | P1 |
| Leak guard fails loud on missing eval sources | P1 |
| `pytest`, `ruff`, leak guard green | Done for PR #24; rerun before final public submission |
| Held-out `test` split remains unrun | Required |
| Pre-public secret and screenshot scans complete | Pending human action |
| Skill-Gap Diagnosis demoable in under 60 seconds | Spec only; pending review/build |
| Repo public flip and all links resolve | Pending human action |
