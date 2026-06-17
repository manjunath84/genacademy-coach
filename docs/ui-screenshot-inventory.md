# UI Screenshot Inventory

Safe UI baselines for future PR reviewers and implementation agents. These screenshots are committed so
the local Gradio demo polish can be inspected without rerunning the private corpus-backed app.

## PR #22 Baselines

All PR #22 screenshots below are empty/default UI states. They do not include generated tutor prose, raw
corpus text, eval questions, quiz question/option text, API keys, `.env` content, or raw trace payloads.

| Viewport target | Screenshot | What to inspect |
|---|---|---|
| Desktop `1440x1000` | [desktop-1440x1000-teach-empty.png](assets/pr22-ui-screenshots/desktop-1440x1000-teach-empty.png) | Header hierarchy, paper-grid background, Teach card layout, action-row placement, and empty trace-card placeholders. |
| Laptop `1280x800` | [laptop-1280x800-teach-empty.png](assets/pr22-ui-screenshots/laptop-1280x800-teach-empty.png) | Recording viewport density, above-the-fold Teach controls, collapsed redacted metadata, and CTA discoverability. |
| Mobile `390x844` | [mobile-390x844-quiz-empty.png](assets/pr22-ui-screenshots/mobile-390x844-quiz-empty.png) | Quiz default state, `1`-question recording preset, unchecked generated-question reveal, touch target size, and stacked mobile layout. |

## Safety Notes

- Commit only empty/default UI captures or screenshots that have been reviewed as fully redacted.
- Do not commit screenshots that show generated tutor answers, retrieved source excerpts, raw corpus text,
  held-out eval prompts, generated quiz question/option text, `.env` values, API keys, or full trace JSON.
- Provider-backed smoke-test screenshots may be useful for local review, but keep them in `/private/tmp`
  unless a reviewer confirms they are public-safe.
- For public/video artifacts, keep `Show generated quiz questions (local/private only)` unchecked unless
  the generated quiz text has been separately approved as safe.

## Regeneration Checklist

Use this checklist if a future UI refinement changes the baseline:

1. Start the app locally only:

   ```bash
   PORT=7861 uv run python app.py
   ```

2. Open `http://127.0.0.1:7861` and hard-refresh.
3. Capture default/empty states before running provider-backed Teach or Quiz actions.
4. If capturing post-run states, verify the image contains only safe/redacted fields before committing.
5. Replace or add screenshots under `docs/assets/pr22-ui-screenshots/` and update this inventory in the
   same commit.
