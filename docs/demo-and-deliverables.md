# Demo & Deliverables Playbook

How the project gets *judged*: the Builder-of-the-Week criteria (Consistency · Creativity · Execution ·
Technical thinking · Initiative) reward the **builder's own strategic reasoning**, not the AI's output.
So the writeup + demo are structured as a **decision story**, not a feature list. (Synthesized from the
pre-build adversarial review; the demo script supersedes the stale §9 in the brainstorm-archive spec.)

## The one memorable hook

> **"It explained attention three different ways until it clicked — and refused to answer what it couldn't cite."**

"Three different ways" = personalization, concrete and demoable. "Refused to answer" = the integrity
moment. The framing is a low-stakes mastery loop: the learner can keep trying while every teaching move
stays grounded in cited course evidence. Use this exact phrasing in the Google Doc opening and the video's
first 10 seconds.

## Project delivery status for PR #22

PR #22 is the local recording polish pass. It does not change the core agent contract; it makes the demo
surface reliable enough to record:

- The Gradio app is local-first: `share=False`, local bind by default, and no public tunnel in the
  recording path.
- `app.py` loads a local `.env` when present, so the recording command does not need a manual `source`
  step.
- The expensive `Foundation` runtime is cached per process. The first live provider call can still be
  slow, but repeated takes no longer reload the embedder/foundation every click.
- Teach controls are visible above the fold on laptop-sized recording viewports.
- The Teach trace is no longer a raw markdown table. It is a compact decision-trace card: action, band,
  score, strategy, faithfulness, citation count, and tool-call count. Full safe metadata stays collapsed.
- Quiz defaults to the reliable recording path: topic `agent harness`, `1` question, answer `A`, and
  "Show generated quiz questions" unchecked.
- Quiz generated question/option text is hidden by default. Only the generated count, score, and safe
  trace metadata should be visible in the video.
- Safe UI baseline screenshots are committed for future visual refinement in
  `docs/ui-screenshot-inventory.md` and `docs/assets/pr22-ui-screenshots/`.
- If the browser still shows orange default tabs, stacked quiz buttons, or `Questions = 3` after a
  restart, hard-refresh. That is the stale pre-PR #22 UI.

## 5-minute video script (builder-thinking-forward)

| Time | Content | Why |
|---|---|---|
| 0:00–0:30 | Hook (above) + "this is Week 3 of my agentic-AI arc, built on my Week-2 RAG." | The human story |
| 0:30–1:00 | "Before the code — here's what I **cut** and why." (show `roadmap.md` cut list) | Initiative + scope discipline |
| 1:00–2:30 | **Teach loop in the local UI:** click `Grounded preset` → `Run teach`. Topic `agent harness` retrieves citeable course evidence, explains, asks a grounded check, sees the wrong learner answer, and **re-explains differently**. Show the decision-trace cards: turn 1 action, turn 2 `re_explain_differently`, confirm band, citation counts, and tool-call counts. | The agenticity proof |
| 2:30–3:15 | **Deliberate failure in the local UI:** click `Refusal preset` → `Run teach`. Out-of-corpus topic `Gen Academy cafeteria menu` → **refuses + escalation queue row**. Show refusal text and safe trace/refusal status only. | Won't-bluff brand |
| 3:15–4:00 | **Honest eval:** "I did not touch the held-out test split. On the redacted dev eval, the latest evidence is `7/10` overall and `7/8` teachable. Two failures are safe refusals; the original grade-boundary bug is fixed, and the remaining teachable variance is a conservative escalation case." | Technical thinking + integrity |
| 4:00–4:45 | **Standout move:** same learner asks for the same concept through two teaching lenses — low-code/no-code workflow explanation, then code-heavy implementation lens. Show `demo-lens-low-code-20260616` and `demo-lens-code-heavy-20260616`, both grounded and faithful. | Creativity + personalization |
| 4:45–5:00 | **First pull-in in the local UI:** Quiz Mode generates a grounded hidden MCQ and grades answer `A` deterministically. Keep question text hidden; show score, trace cards, and collapsed metadata. Close with "Next: interview, admin upload, and voice — same engine, after the text tutor works." | Forward momentum |

## Exact evidence to show

Use these artifacts in the video and written submission. They are redacted metadata surfaces; do not paste
private eval questions or raw corpus snippets.

| Moment | Artifact | What to say |
|---|---|---|
| Grounded teach loop | `traces/demo-grounded-main-final-20260616.jsonl` | "The model chose `drill`, then after the learner's wrong answer chose `re_explain_differently`; Python only enforced grounding and safety." |
| Refusal path | `traces/demo-refusal-main-final-20260616.jsonl` + `review_queue.jsonl` | "No citeable course material means refusal and one mentor-review queue row, not a model-prior answer." |
| Honest eval | `eval/runs/teach-loop-dev-main-final-20260616.json` + `eval/runs/teach-loop-dev-grade-boundary.json` | "`7/10` dev scenarios passed, `7/8` teachable scenarios passed, with two safe refusals. The grade-boundary bug is fixed; one conservative escalation variance remains." |
| Same-topic lens switch | `traces/demo-lens-low-code-20260616.jsonl` + `traces/demo-lens-code-heavy-20260616.jsonl` | "The topic and learner answer stay constant; only the track lens changes. Both runs cite evidence and re-explain after the same wrong answer. The grounding metadata stays stable as the control; the on-screen explanation is what changes by lens." |
| Grounded quiz | Local UI hidden-question run + `traces/demo-quiz-agent-harness-reviewfix2-20260616.jsonl` as fallback evidence | "Quiz Mode is not the agenticity proof; it is the first deterministic assessment pull-in. The UI demo uses one hidden question for recording reliability. The model generates cited MCQs from retrieved spans; Python grades option IDs. The trace stores `topic_hash` and metadata only, not raw topic or quiz text." |
| Safety guard | `scripts/check_eval_leak.py` output in `docs/teach-loop-status.md` | "The held-out `test` split stays frozen and unused; leak checks pass locally." |
| Scope discipline | `specs/roadmap.md` | "Quiz, interview, admin upload, and voice were intentionally kept as pull-ins until the teach loop worked." |
| Instructor review | `review_queue.jsonl` + redacted traces | "The failure path already creates the human-review surface; no admin UI is needed for the demo." |
| Reproducibility | `eval/split_manifest.json` + source checksums | "Same split, same source hashes, same ingest path. I did not tune on the held-out test split." |

## Two-Day Score-Lift Plan

With two days left, the demo can improve more by raising the floor than by adding flashy scope. The
current plan is captured in `docs/two-day-score-lift-plan.md`:

1. Fix or explain the remaining teachable dev diagnostic.
2. Capture a same-topic lens-switch demo before any larger pull-in. Done: both lens traces are captured.
3. Build grounded Quiz Mode as the first real pull-in. Done: the reviewed slice generates 3 cited MCQs,
   grades selected option IDs deterministically, writes a redacted quiz trace, and refuses if retrieval is
   not citeable.
4. Treat cross-session memory as a personalization roadmap item, not a two-day build item. The safe next
   memory step is a separate plan comparing first-party persisted profile, LangMem, Mem0 open source, and
   Zep Cloud after the core floor is green.
5. Treat mock interview as a Day-2 stretch only; skip voice, explicit LangGraph, GraphRAG, multimodal, and
   admin upload for this demo window.

The grading fix landed for the original scenario, but the raw dev eval stayed at `7/10` and `7/8`
because a different confirm-band scenario escalated. Say that directly: "the deterministic grade-boundary
bug is fixed; the remaining variance is the tutor being conservative when evidence is marginal."

## Commands for the recording

Prefer the local UI for the video. It now auto-loads `.env` when present:

```bash
PORT=7861 uv run python app.py
```

Open `http://127.0.0.1:7861`. Before recording, hard-refresh and verify the fixed UI: Teach has
`Grounded preset`, `Refusal preset`, and `Run teach` in one row; Quiz defaults to `1` question, answer
`A`, and hidden generated questions.

Grounded demo:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_teach_demo.py \
    --session-id demo-grounded-main-final-20260616 \
    --topic "agent harness" \
    --style analogy \
    --track-lens code_heavy \
    --learner-answer "It is just one prompt with no tool checks or feedback."
```

Refusal demo:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_teach_demo.py \
    --session-id demo-refusal-main-final-20260616 \
    --topic "Gen Academy cafeteria menu" \
    --style concise \
    --track-lens low_code_no_code
```

Same-topic lens switch:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_teach_demo.py \
    --session-id demo-lens-low-code-20260616 \
    --topic "agent harness" \
    --style analogy \
    --track-lens low_code_no_code \
    --learner-answer "It is just one prompt with no tool checks or feedback."

GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_teach_demo.py \
    --session-id demo-lens-code-heavy-20260616 \
    --topic "agent harness" \
    --style analogy \
    --track-lens code_heavy \
    --learner-answer "It is just one prompt with no tool checks or feedback."
```

Grounded quiz, matching the reliable local UI path:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_quiz_demo.py \
    --session-id demo-quiz-agent-harness-ui-20260617 \
    --topic "agent harness" \
    --question-count 1 \
    --answers A
```

Optional deeper quiz fallback evidence, if you want to show the three-question capability outside the
live UI flow:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/run_quiz_demo.py \
    --session-id demo-quiz-agent-harness-reviewfix2-20260616 \
    --topic "agent harness" \
    --question-count 3 \
    --answers A,B,C
```

Dev eval:

```bash
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/eval_teach_loop.py \
    --split dev \
    --limit 10 \
    --json-out eval/runs/teach-loop-dev-main-final-20260616.json
```

Do not run `--split test` for demo preparation.

## Google Doc outline (the human-reasoning version)

Current packaging item: `docs/submission-packaging-item.md`. Recording script:
`docs/video-demo-script.md`. Full repo draft: `docs/submission-google-doc-draft.md`. Sanitized prompt
appendix: `docs/vibe-coding-prompt-appendix.md`. Hugging Face deployment plan:
`docs/hugging-face-deployment-plan.md`.

1. **Problem framing** (1 p) — "Cohort members re-watch lectures and still don't get it. The gap is
   personalization, not content."
2. **Options I considered** (½ p) — the scorecard from `genacademy-coach-brainstorm-options.md`; why the
   adaptive tutor beat the mock-interviewer on *genuine agentic behavior* (what the rubric weights).
3. **Hard trade-offs** (1 p) — why I kept quiz, interview, memory, admin upload, and ElevenLabs voice as
   pull-ins; why `create_agent` on LangGraph's runtime won for a Thursday ship instead of adding an
   explicit graph/checkpointer/store layer. (show the cut list)
4. **The eval-honesty fix** (½ p) — "my first design reused the same questions for seed and test — a
   classic leak; here's how I caught it and the hard-split protocol I built." (show `split_manifest.json`)
5. **What I built** (2 p) — architecture, code snippets, prompt samples.
6. **Honest numbers** (½ p) — `7/10` dev, `7/8` teachable, two safe refusals, one conservative
   escalation variance, held-out `test` split untouched.
7. **What I learned** (½ p) — use `docs/build-learnings.md`: eval splits must be frozen, diagnostics
   should reuse runtime truth, locks need identity, demo defaults are product decisions, and safe traces
   still need camera-readable design.

> **Make the builder's voice visible** (the review's weakest-scoring dimension, "human-reasoning
> legibility"): include the wrong turns, the "I tried X, it was too slow," and the option-vs-option
> reasoning. Polished-but-impersonal reads as well-prompted AI; the messy reasoning is what scores
> Initiative.

## Standout moves (cheap, high-impact, no ship risk)

| # | Move | Effort | Payoff |
|---|---|---|---|
| S1 | Same learner switches track lens for one concept: low-code/no-code workflow, then code-heavy implementation | ~10 min prompt change | Creativity + "actually adapts" |
| S2 | Honest eval numbers on screen — show the failures and why | ~0 build | Technical thinking + integrity |
| S3 | "What I cut and why" — 30-sec scope-cut narrative | ~0 build | Initiative + human reasoning |
| S4 | Corpus version-pin + SHA shown in the demo UI | ~1 hr | Technical thinking + reproducibility |
| S5 | Flagged-item → review queue, captured live during the eval run | ~1 hr | HITL + realness |
| S6 | Memory roadmap slide: within-session now, persisted profile later, LangMem/Mem0/Zep after review | ~0 build | Personalization ambition without demo risk |

## Builder-of-the-Week Alignment

| Criterion | What to show | Repo proof |
|---|---|---|
| Consistency | Week 3 compounds Week 2: Week 2 built grounded RAG; Week 3 adds agentic teaching, state, failure handling, and HITL. | `docs/genacademy-rag-foundation.md`, `AGENTS.md` |
| Creativity | Same learner can switch teaching lenses for one topic: low-code/no-code workflow mental model, code-heavy implementation detail, or bridge between them. | teach-loop trace + demo script |
| Execution | Live teach loop with refusal, escalation, and trace, not a static prompt demo. | `traces/demo-grounded-main-final-20260616.jsonl`, `traces/demo-refusal-main-final-20260616.jsonl`, `review_queue.jsonl` |
| Technical thinking | Held-out chat-question eval, citation-resolves checks, deterministic grader, and calibrated retrieval thresholds. | `specs/tech-stack.md`, `docs/decisions.md` |
| Initiative | The project shows reviewed trade-offs: one retriever, JSON/CLI trace, text-first MVP, and quiz/interview/admin/voice as pull-ins. | `docs/decisions.md`, `specs/roadmap.md` |

Biggest risk: the project can look like "just a RAG tutor" if the demo only shows a happy-path answer.
The defense is the trace: show the model seeing the learner's actual wrong answer and choosing a
different `next_action` + `strategy` without changing Python control flow.

## Build-in-public beats (LinkedIn)

1. **"I asked three AI reviewers to critique my hackathon idea before writing a line of code."** — the
   scope cut + the eval-leak fix. Frame: design first, code second.
2. **"My AI tutor refused to answer my own question."** — the refusal clip; inherently shareable.
3. **"What I cut from my hackathon project to ship on time."** — the cut list; demonstrates maturity.

## Deliverables readiness (handout requirements)

| Requirement | Status | Action |
|---|---|---|
| Google Doc (overview, datasets, prompts, iterations, learnings) | ✅ repo draft packaged; external Doc still to create | Use `docs/submission-google-doc-draft.md`; keep private corpus/eval text out |
| Datasets | ✅ narrative ready | Describe `corpus/notes`, `corpus/slides`, `corpus/handouts`, `corpus/transcripts`, and the never-indexed `corpus/eval-questions` test source |
| Prompts used during vibe-coding | ✅ sanitized appendix packaged | Use `docs/vibe-coding-prompt-appendix.md`; do not add secrets or private corpus/eval text |
| Iterations tried | ✅ narrative ready | Use `docs/teach-loop-status.md`, `docs/build-learnings.md`, and the PR sequence from roadmap |
| Learnings | ✅ narrative ready | Use `docs/build-learnings.md` plus `docs/decisions.md` |
| ≤5-min video | ✅ script packaged / ⚠️ video not recorded | Use `docs/video-demo-script.md`; record through the local Gradio UI presets, with CLI commands as fallback |
| GitHub | ✅ private repo | Flip to public at submission (`gh repo edit --visibility public`) |
| Architecture diagram | ✅ `docs/architecture-diagrams.md` | Export Diagram 2 (teach loop) to PNG/SVG for the Doc/video |
| Hugging Face deployment | ✅ private Space HTTP smoke passed / ⚠️ corpus click smoke pending | URL: `https://huggingface.co/spaces/Manjunath84/genacademy-coach`; no private corpus/index uploaded; UI marks this as a deployment shell |
