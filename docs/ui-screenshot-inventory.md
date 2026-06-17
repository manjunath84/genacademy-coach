# UI Screenshot Inventory

UI baselines and function-state captures for future PR reviewers and implementation agents. These
screenshots are committed so the local Gradio demo polish can be inspected without rerunning the private
corpus-backed app.

## PR #22 Baselines

All PR #22 screenshots below are empty/default UI states. They do not include generated tutor prose, raw
corpus text, eval questions, quiz question/option text, API keys, `.env` content, or raw trace payloads.

| Viewport target | Screenshot | What to inspect |
|---|---|---|
| Desktop `1440x1000` | [desktop-1440x1000-teach-empty.png](assets/pr22-ui-screenshots/desktop-1440x1000-teach-empty.png) | Header hierarchy, paper-grid background, Teach card layout, action-row placement, and empty trace-card placeholders. |
| Laptop `1280x800` | [laptop-1280x800-teach-empty.png](assets/pr22-ui-screenshots/laptop-1280x800-teach-empty.png) | Recording viewport density, above-the-fold Teach controls, collapsed redacted metadata, and CTA discoverability. |
| Mobile `390x844` | [mobile-390x844-quiz-empty.png](assets/pr22-ui-screenshots/mobile-390x844-quiz-empty.png) | Quiz default state, `1`-question recording preset, unchecked generated-question reveal, touch target size, and stacked mobile layout. |

## PR #22 Functionality Captures

The Teach-output screenshots include the owner-approved `agent harness` demo topic and are intended for
this private repo's implementation context. Treat them as local demo references, not public-safe corpus
artifacts. Quiz screenshots still avoid generated quiz question/option text.

| Flow | Screenshot | What to inspect |
|---|---|---|
| Teach grounded run | [desktop-1440x1000-teach-grounded-output.png](assets/pr22-ui-screenshots/desktop-1440x1000-teach-grounded-output.png) | Grounded answer layout, two-turn adaptation, large-response wrapping, citation labels, and decision-trace cards. |
| Teach refusal run | [desktop-1440x1000-teach-refusal-output.png](assets/pr22-ui-screenshots/desktop-1440x1000-teach-refusal-output.png) | Refusal copy, `refuse_escalate` trace card, zero-citation state, and no raw metadata exposure. |
| Quiz hidden-output run | [desktop-1440x1000-quiz-hidden-output.png](assets/pr22-ui-screenshots/desktop-1440x1000-quiz-hidden-output.png) | Hidden-question recording path, generated count, deterministic score, selected answer ID, and safe quiz trace card. |
| Quiz local reveal control | [desktop-1440x1000-quiz-reveal-control-no-output.png](assets/pr22-ui-screenshots/desktop-1440x1000-quiz-reveal-control-no-output.png) | Local-only reveal checkbox state before running; no generated quiz text is committed. |

## Safety Notes

- Empty/default captures may be reused broadly inside the repo.
- Teach-output captures are private-repo demo references for the approved `agent harness` topic. Review
  them again before using them in any public artifact.
- Do not commit screenshots that show held-out eval prompts, generated quiz question/option text, `.env`
  values, API keys, full trace JSON, or unreviewed source excerpts.
- Provider-backed smoke-test screenshots may be useful for local review, but keep them in `/private/tmp`
  unless a reviewer confirms they are safe for the intended audience.
- For public/video artifacts, keep `Show generated quiz questions (local/private only)` unchecked unless
  the generated quiz text has been separately approved as safe.

## Regeneration Checklist

Use this checklist if a future UI refinement changes the baseline:

1. Start the app locally only:

   ```bash
   PORT=7861 uv run python app.py
   ```

2. Open `http://127.0.0.1:7861` and hard-refresh.
3. Run the Playwright capture script when Playwright is available to Node:

   ```bash
   node scripts/capture_pr22_ui_screenshots.cjs
   ```

   To capture only one side while debugging:

   ```bash
   GENACADEMY_COACH_CAPTURE_MODES=teach node scripts/capture_pr22_ui_screenshots.cjs
   GENACADEMY_COACH_CAPTURE_MODES=quiz node scripts/capture_pr22_ui_screenshots.cjs
   ```

4. Capture default/empty states before running provider-backed Teach or Quiz actions.
5. If capturing post-run states, verify the image contains only approved demo-topic output or
   safe/redacted fields before committing.
6. Replace or add screenshots under `docs/assets/pr22-ui-screenshots/` and update this inventory in the
   same commit.
