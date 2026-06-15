# Demo & Deliverables Playbook

How the project gets *judged*: the Builder-of-the-Week criteria (Consistency · Creativity · Execution ·
Technical thinking · Initiative) reward the **builder's own strategic reasoning**, not the AI's output.
So the writeup + demo are structured as a **decision story**, not a feature list. (Synthesized from the
pre-build adversarial review; the demo script supersedes the stale §9 in the brainstorm-archive spec.)

## The one memorable hook

> **"It explained attention three different ways until it clicked — and refused to answer what it couldn't cite."**

"Three different ways" = personalization, concrete and demoable. "Refused to answer" = the integrity
moment. Use this exact phrasing in the Google Doc opening and the video's first 10 seconds.

## 5-minute video script (builder-thinking-forward)

| Time | Content | Why |
|---|---|---|
| 0:00–0:30 | Hook (above) + "this is Week 3 of my agentic-AI arc, built on my Week-2 RAG." | The human story |
| 0:30–1:00 | "Before the code — here's what I **cut** and why." (show `roadmap.md` cut list) | Initiative + scope discipline |
| 1:00–2:30 | **Teach loop:** learner says "I don't get attention" → retrieves span → explains with an analogy → check-question → learner half-right → **re-explains differently, same citation** → it clicks. Show the **local JSON/CLI trace** side-by-side; show LangSmith only if already configured. | The agenticity proof |
| 2:30–3:15 | **Deliberate failure:** out-of-corpus question → **refuses + escalation card** + a line in `review_queue.jsonl`. | Won't-bluff brand |
| 3:15–4:00 | **Honest eval:** "Here's my held-out test set, the split, what passed and what didn't." Say the real fraction. | Technical thinking + integrity |
| 4:00–4:45 | **Standout move:** same learner asks for the same concept through two teaching lenses — low-code/no-code workflow explanation, then code-heavy Python/LangGraph explanation. | Creativity + personalization |
| 4:45–5:00 | "Next: quiz, interview, admin upload, and voice — same engine, after the text tutor works." + architecture thumbnail. | Forward momentum |

## Google Doc outline (the human-reasoning version)

1. **Problem framing** (1 p) — "Cohort members re-watch lectures and still don't get it. The gap is
   personalization, not content."
2. **Options I considered** (½ p) — the scorecard from `genacademy-coach-brainstorm-options.md`; why the
   adaptive tutor beat the mock-interviewer on *genuine agentic behavior* (what the rubric weights).
3. **Hard trade-offs** (1 p) — why I kept quiz, interview, admin upload, and ElevenLabs voice as
   pull-ins; why `create_agent` on LangGraph's runtime won for a Thursday ship. (show the cut list)
4. **The eval-honesty fix** (½ p) — "my first design reused the same questions for seed and test — a
   classic leak; here's how I caught it and the hard-split protocol I built." (show `split_manifest.json`)
5. **What I built** (2 p) — architecture, code snippets, prompt samples.
6. **Honest numbers** (½ p) — the eval results. If it's 6/10, say 6/10 and why.
7. **What I learned** (½ p) — e.g. "if I did Week 3 again, I'd define the local trace artifact on day 1."

> **Make the builder's voice visible** (the review's weakest-scoring dimension, "human-reasoning
> legibility"): include the wrong turns, the "I tried X, it was too slow," and the option-vs-option
> reasoning. Polished-but-impersonal reads as well-prompted AI; the messy reasoning is what scores
> Initiative.

## Standout moves (cheap, high-impact, no ship risk)

| # | Move | Effort | Payoff |
|---|---|---|---|
| S1 | Same learner switches track lens for one concept: low-code/no-code, then code-heavy | ~10 min prompt change | Creativity + "actually adapts" |
| S2 | Honest eval numbers on screen — show the failures and why | ~0 build | Technical thinking + integrity |
| S3 | "What I cut and why" — 30-sec scope-cut narrative | ~0 build | Initiative + human reasoning |
| S4 | Corpus version-pin + SHA shown in the demo UI | ~1 hr | Technical thinking + reproducibility |
| S5 | Flagged-item → review queue, captured live during the eval run | ~1 hr | HITL + realness |

## Builder-of-the-Week Alignment

| Criterion | What to show | Repo proof |
|---|---|---|
| Consistency | Week 3 compounds Week 2: Week 2 built grounded RAG; Week 3 adds agentic teaching, state, failure handling, and HITL. | `docs/genacademy-rag-foundation.md`, `AGENTS.md` |
| Creativity | Same learner can switch teaching lenses for one topic: low-code/no-code workflow mental model, code-heavy Python/LangGraph detail, or bridge between them. | teach-loop trace + demo script |
| Execution | Live teach loop with refusal, escalation, and trace, not a static prompt demo. | `traces/<session_id>.json`, `review_queue.jsonl`, eval output |
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
| Google Doc (overview, datasets, prompts, iterations, learnings) | ❌ not created | Build the skeleton **now** from the outline above; paste prompts as you write them |
| Datasets | ⚠️ local/private corpus staged | Describe `corpus/notes`, `corpus/slides`, `corpus/handouts`, `corpus/transcripts`, and the never-indexed `corpus/eval-questions` test source |
| Prompts used during vibe-coding | ⚠️ capture as you go | Keep a running `docs/prompts.md` during the build |
| Iterations tried | ⚠️ reframe | The board worklog → a "what I tried and changed" narrative |
| Learnings | ⚠️ reframe | `decisions.md` → a narrative section in the Doc |
| ≤5-min video | ❌ not created | Use the script above (not the stale archive §9) |
| GitHub | ✅ private repo | Flip to public at submission (`gh repo edit --visibility public`) |
| Architecture diagram | ✅ `docs/architecture-diagrams.md` | Export Diagram 2 (teach loop) to PNG/SVG for the Doc/video |
