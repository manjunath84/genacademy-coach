# Architecture Pitch Artifacts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the two July-11/12 pitch artifacts from the approved spec
`docs/superpowers/specs/2026-07-04-architecture-pitch-design.md`: the architecture one-pager
(HTML → PNG) and the modular spoken script.

**Architecture:** Static, self-contained artifacts in `docs/assets/pitch/`. The one-pager is a
single HTML file (no external requests) rendered to PNG via the repo's established mockup pipeline
(local `http.server` + Playwright MCP screenshot). The script is a markdown file with an extractable
M0 block for automated word-count verification. A verification task string-matches every quoted
number against `docs/week4-eval-dashboard-data.json` before the PR.

**Tech Stack:** HTML/CSS (system fonts only), Python `http.server`, Playwright MCP browser tools,
`jq`/`grep` for verification, `gh` + Codex CLI for the review gate.

## Global Constraints

- **Numbers:** every figure quoted in either artifact must appear verbatim in
  `docs/week4-eval-dashboard-data.json` and carry its caveat where the dashboard has one
  (task-completion baseline is infra-excluded 36/38; cost is a per-run reference from runs 2/3
  only). Use ASCII hyphens for minus signs so grep checks work. Never hand-edit a number — re-pull
  from the JSON.
- **Status tags:** every diagram element is marked `●` (shipped) or `◐` (Phase-1 build slice —
  design merged, not built); the scale-out strip is marked `○` (scoped). Panel, chips, and strict
  week/session filters MUST carry `◐`. Never write "always runs" next to panel/chips.
- **Public-safe:** no corpus text or filenames, no team names/emails, no `localdocs/` references,
  no private URLs. HTML is fully self-contained: no CDN links, no Google Fonts (system sans-serif
  + ui-monospace only).
- **Palette (workspace-mockup product theme — extracted from `docs/assets/mockups/tutor-workspace-evidence.html`):**
  page `#eef1f6`/`#f7f8fb`, card `#ffffff` with borders `#d8dee9`/`#cfd8e8`, ink `#1b2130`,
  muted `#475069`/`#6b7280`, primary blue `#2f4b7c`, blue tints `#dbe6f7`/`#eaf0fb`, success
  `#1c7a3f` on `#cdeedd`/`#e7f6ec`, highlight `#fff3bf`, dark slate `#28303f`. No paper-grid
  overlay — this is the product-app look, so the one-pager reads as the same product as the demo
  mockups. *(Amended 2026-07-04: the original constraint wrongly pinned the parent study-notes
  cream/electric-yellow theme; caught by the owner on the first render.)*
- **Gates:** work on branch `docs/pitch-artifacts` off `main`; Codex second-model review posted to
  the PR before merge; `python` is never on PATH — always `uv run python`; `codex exec` must be
  launched with stdin closed (`</dev/null`) when backgrounded.

---

### Task 1: Pitch script (`pitch-script.md`)

**Files:**
- Create: `docs/assets/pitch/pitch-script.md`

**Interfaces:**
- Produces: the M0 verbatim text whose thesis/caption lines Task 2 reuses on the one-pager
  (thesis: "Freedom in the middle. Gates at the edges."; gate line: "refusal recall on adversarial
  questions: 1.000, held across every run — and that number gates release").

- [ ] **Step 1: Create the directory and write the file**

```bash
mkdir -p docs/assets/pitch
```

Write `docs/assets/pitch/pitch-script.md` with exactly this content:

````markdown
# Architecture Pitch — Spoken Script (modular)

**Source spec:** `docs/superpowers/specs/2026-07-04-architecture-pitch-design.md`
**Numbers:** all figures from `docs/week4-eval-dashboard-data.json` (dataset `2026-06-24-plan1`,
snapshot 2026-06-25, mean of three current-main runs).
**How to use:** M0 alone = 90-second cut. M0+M1+M2 ≈ 5 minutes. All modules + Q&A ammo ≈ 10
minutes. Never rewrite a module to fit time — drop whole modules instead.

---

## M0 — the core (deliver verbatim, ≤ 95 seconds)

<!-- M0-START -->
Every learner in this cohort has done this: to understand one concept you open the slides, scrub
the session recording, and search the handout — three tabs, zero provenance. GenAcademy Coach
replaces that with one grounded tutor: ask it anything from the course and it teaches, with the
exact slide, transcript, and handout evidence beside the answer.

Here is the architecture in one picture. The agent has freedom in the middle and gates at the
edges.

Gate one — deterministic intake. One retrieval per turn over the tagged corpus, slides and
handouts first. An evidence score maps to a band: below 0.40 the system stops, and the model
never gets a vote. Citations are captured right here, at retrieval — never reconstructed from the
answer.

The middle — the teaching brain. This is where the model is genuinely agentic: it picks the
teaching move — explain, step-by-step, quiz, re-explain differently — and the explanation lens —
low-code, code-heavy, or bridge. Every choice is logged, per turn.

Gate two — projection. The evidence panel and next-step suggestions are projections of that same
single retrieval, so the answer and its evidence can never disagree, and the system never
suggests something it would refuse.

And the number that gates release: refusal recall on adversarial questions — 1.000, held across
every run. If it cannot cite the course, it refuses and hands you to a mentor. That is the
product.
<!-- M0-END -->

---

## M1 — agentic features (adds ~90 seconds)

What does the agent actually decide? Six teaching moves, three lenses, the re-explain strategy
after a failed check — analogy, simpler steps, or a contrastive example — and which check-question
to ask. Across turns it adapts through the session profile: what you know, where you struggled.

Why is that autonomy and not a workflow? Because the path is chosen at runtime from observations —
grade results and struggle signals — not from a fixed script. Two learners asking the same
question take different paths.

And there is a receipt. Every choice is logged per turn — today's shipped UI shows it as
decision-trace cards, and the Phase-1 workspace surfaces it as a "behind this answer" disclosure.
Our trajectory eval scores the *chosen action*, not just the final prose.

Where does this go next? The Personal Coach direction is the same sandwich at multi-agent scale:
interviewer, evaluator, coach, and curriculum-planner agents behind a deterministic orchestrator —
and the study planner follows one rule: the LLM proposes, a deterministic scheduler validates and
repairs. Feasible, or flag. One pattern at every layer. That's scoped, not built — and it slots
into the same grounded core.

## M2 — eval receipts (adds ~90 seconds)

How do we know any of this works? A frozen, hand-labeled golden set: forty cases — sixteen happy,
nine edge, five known-failure, ten adversarial — frozen before the improvement work, with the
held-out test split never indexed; a leak-check script enforces that. Three evaluator types:
deterministic code checks, trajectory eval on the agent's path, and human review. Pass bars were
fixed at design time — never reverse-engineered to pass.

The wins: citation F1 went 0.444 to 0.594 — up 0.150, clearing our 0.50 floor, still honest about
the 0.90 bar. Turn p95 latency went 11.33 seconds to 8.28 — 27 percent faster. Refusal recall and
retrieval recall held at 1.000.

The misses — and we publish these: refusal precision moved 0.833 to 0.791, and task completion
went from 94.7 percent on the infra-excluded baseline to 93.3 percent mean over all forty cases.
Cause analysis is on the dashboard: over-conservative refusals, three named cases.

And my favorite: we almost shipped a citation fallback predicted to gain up to 0.20 of citation
F1. Measured: minus 0.044, and task completion down 5.2 points. It was rejected. The eval was our
debugger.

## M3 — scale + close (adds ~60 seconds)

Status, honestly, in three states. Built and evaluated: the grounded engine — teach loop, quiz,
skill-gap diagnosis, escalation, tracing, the eval harness and public dashboard. The build slice
for this week's demo: the Tutor Workspace — evidence panel with real slide images and next-step
suggestions, design merged after independent second-model review. Scoped into the same core:
voice tutoring, a current-docs lane, controlled ingestion, cohort access, progress analytics, and
the Personal Coach. Every layer ships through the same gates: grounded-or-refuse, privacy review,
evals before release.

## Q&A ammo (one line each — 10-minute cut / prep)

| Likely question | Answer |
|---|---|
| Why not fine-tune? | Corpus changes weekly; retrieval + citations give provenance fine-tuning can't. Design choice: a 30B open model (Qwen3-30B via Nebius) with strong deterministic scaffolding — the receipts are the point, not model size. |
| How do you know citations are real? | Captured at retrieval, never reconstructed; faithfulness measured as F1; the Phase-1 panel renders only cited spans. |
| Isn't refusal recall 1.000 just refusing everything? | That's why refusal *precision* is its balancing pair — 0.791, a disclosed miss with named cases. |
| What stops hallucinated suggestions? | Chips carry corpus anchors validated before render; stale chips are dropped, never allowed to bypass refusal. |
| Why multi-agent for the Personal Coach? | Interviewer, evaluator, and coach have conflicting objectives in one prompt; role separation under a deterministic orchestrator is the same sandwich pattern. |
| Cost / latency? | ~$0.14 per full 40-case eval run (current reference, runs 2/3 only — baseline pricing env was unset); case p95 ~21.96s; turn p95 8.28s — inside the 10s production alert SLA; five production monitoring signals with alert thresholds defined. |
````

- [ ] **Step 2: Verify the M0 word count (≤ 240 words ≈ 95 s at ~150 wpm)**

Run:
```bash
sed -n '/<!-- M0-START -->/,/<!-- M0-END -->/p' docs/assets/pitch/pitch-script.md | wc -w
```
Expected: a number ≤ 240. If over, trim M0 prose (never the numbers) and re-run.

- [ ] **Step 3: Commit**

```bash
git add docs/assets/pitch/pitch-script.md
git commit -m "docs: pitch script — modular M0-M3 + Q&A ammo"
```

---

### Task 2: Architecture one-pager (`architecture-pitch-onepager.html` + `.png`)

**Files:**
- Create: `docs/assets/pitch/architecture-pitch-onepager.html`
- Create: `docs/assets/pitch/architecture-pitch-onepager.png` (rendered output)

**Interfaces:**
- Consumes: thesis + gate lines from Task 1's M0.
- Produces: the PNG the owner presents; Task 3 verifies its numbers.

- [ ] **Step 1: Write the HTML**

Write `docs/assets/pitch/architecture-pitch-onepager.html` with exactly this content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>GenAcademy Coach — Architecture One-Pager</title>
<style>
  :root{ --paper:#FDFCEF; --ink:#0F1419; --accent:#EAFF00; --dark:#1E3A5F;
         --muted:#666; --rule:#d9d4b8; --warn:#C00; }
  *{box-sizing:border-box; margin:0; padding:0;}
  body{
    background:var(--paper);
    background-image:linear-gradient(rgba(232,228,208,.4) 1px, transparent 1px),
                     linear-gradient(90deg, rgba(232,228,208,.4) 1px, transparent 1px);
    background-size:40px 40px;
    color:var(--ink); width:1440px; margin:0 auto; padding:44px 56px 36px;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
  }
  .mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;}
  .eyebrow{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px;
           letter-spacing:.16em; color:var(--muted); text-transform:uppercase;}
  h1{font-size:46px; line-height:1.08; margin:10px 0 8px; letter-spacing:-.01em;}
  h1 .hl{background:var(--accent); padding:0 10px;}
  .sub{font-size:17px; margin-bottom:12px;}
  .legend{display:flex; gap:26px; font-size:13px; margin:6px 0 24px;
          font-family:ui-monospace,SFMono-Regular,Menlo,monospace;}
  .flow{display:grid; grid-template-columns:1fr 330px; gap:22px; align-items:start;}
  .band{border:2px solid var(--ink); padding:16px 20px 14px; margin-bottom:0;}
  .band h2{font-size:15px; letter-spacing:.08em; text-transform:uppercase; margin-bottom:8px;
           font-family:ui-monospace,SFMono-Regular,Menlo,monospace;}
  .band ol{list-style:none;}
  .band li{font-size:14.5px; line-height:1.45; margin:5px 0;}
  .band li .mod{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11.5px;
                opacity:.75; white-space:nowrap;}
  .det{background:var(--ink); color:var(--paper);}
  .det h2{color:var(--accent);}
  .agent{background:var(--accent); color:var(--ink);}
  .agent h2{color:var(--ink);}
  .arrow{text-align:center; font-size:20px; line-height:1; padding:6px 0;}
  .sidecard{border:2px solid var(--ink); padding:14px 16px; margin-bottom:16px; font-size:14px;
            line-height:1.45;}
  .refusal{background:var(--dark); color:var(--paper);}
  .refusal h3{color:var(--accent);}
  .loopcard{border-style:dashed; background:transparent;}
  .sidecard h3{font-size:13px; letter-spacing:.08em; text-transform:uppercase; margin-bottom:6px;
               font-family:ui-monospace,SFMono-Regular,Menlo,monospace;}
  .strip{margin-top:26px;}
  .strip h2{font-size:16px; letter-spacing:.1em; text-transform:uppercase; margin-bottom:10px;
            font-family:ui-monospace,SFMono-Regular,Menlo,monospace;}
  .kpis{display:grid; grid-template-columns:repeat(6,1fr); gap:12px;}
  .kpi{border:2px solid var(--ink); padding:10px 12px; background:#fffef7;}
  .kpi .label{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px;
              letter-spacing:.06em; text-transform:uppercase; color:var(--muted);}
  .kpi .value{font-size:21px; font-weight:700; margin:3px 0 1px;}
  .kpi .note{font-size:11px; color:var(--muted); line-height:1.35;}
  .tag{display:inline-block; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
       font-size:10px; letter-spacing:.08em; padding:1px 6px; margin-left:4px; vertical-align:2px;}
  .tag.win{background:var(--accent); color:var(--ink);}
  .tag.held{background:var(--dark); color:var(--paper);}
  .tag.miss{background:var(--warn); color:#fff;}
  .lever{border:2px solid var(--ink); background:var(--ink); color:var(--paper);
         padding:14px 18px; margin-top:12px; font-size:14.5px; line-height:1.5;}
  .lever b{color:var(--accent);}
  .scoped{border:2px dashed var(--ink); padding:14px 18px; margin-top:26px; font-size:14.5px;
          line-height:1.55;}
  .footer{margin-top:22px; display:flex; justify-content:space-between; align-items:baseline;
          border-top:2px solid var(--ink); padding-top:12px;}
  .gates{font-size:15px; font-weight:700;}
  .prov{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11.5px; color:var(--muted);}
</style>
</head>
<body>
  <div class="eyebrow">GenAcademy Coach · Architecture one-pager · Demo days July 11–12</div>
  <h1><span class="hl">Freedom in the middle.</span> <span class="hl">Gates at the edges.</span></h1>
  <div class="sub">One grounded core — <b>agentic in teaching, deterministic in grounding</b>.
    If it can't cite the course, it refuses and routes to a mentor.</div>
  <div class="legend"><span>● shipped &amp; evaluated</span>
    <span>◐ Phase-1 build slice (design merged)</span><span>○ scoped, same core</span></div>

  <div class="flow">
    <div>
      <div class="band det">
        <h2>Gate 1 · Deterministic intake — the model never gets a vote</h2>
        <ol>
          <li>● One retrieval per turn, source-prioritized: slides &amp; handouts lead
              <span class="mod">corpus.py · foundation.py</span></li>
          <li>◐ Strict week/session/source filters — never silently widened</li>
          <li>● Evidence score → band: STOP &lt; 0.40 · CONFIRM 0.40–0.85 · PROCEED &gt; 0.85
              <span class="mod">grounding.py</span></li>
          <li>● Citations captured at retrieval — never reconstructed from the answer</li>
        </ol>
      </div>
      <div class="arrow">▼ <span class="mono" style="font-size:12px;">band ≥ floor</span></div>
      <div class="band agent">
        <h2>The teaching brain — the agent's call, logged every turn</h2>
        <ol>
          <li>● Teaching move: explain / step-by-step / clarify / quiz / re-explain / refuse+escalate
              <span class="mod">teach_agent.py</span></li>
          <li>● Explanation lens: low-code · code-heavy · bridge</li>
          <li>● Grounded check-question from a cited span; deterministic grade feeds the next move
              <span class="mod">semantic_grading.py</span></li>
        </ol>
      </div>
      <div class="arrow">▼</div>
      <div class="band det">
        <h2>Gate 2 · Deterministic projection</h2>
        <ol>
          <li>◐ Evidence panel = projection of the <i>same</i> retrieval: cited spans by lane +
              the real slide image — answer and evidence can never disagree</li>
          <li>◐ Next-step chips, corpus-anchored only — never suggest what you'd refuse</li>
          <li>● Trace + eval capture → the dashboard numbers
              <span class="mod">trace.py · eval_runner.py</span></li>
        </ol>
      </div>
    </div>
    <div>
      <div class="sidecard refusal">
        <h3>band = STOP → refusal path ●</h3>
        Refuse + mentor escalation (review queue) + recovery suggestions ◐ routing back into the
        course. <b>Refusal is a feature with its own metric — not an error page.</b>
        <div class="mod" style="margin-top:6px;">escalation.py</div>
      </div>
      <div class="sidecard loopcard">
        <h3>The next-turn loop ●</h3>
        The deterministic grade updates <span class="mono">known[] / struggled[]</span>; the agent
        <i>observes</i> that and may re-explain differently — analogy, simpler steps, contrastive
        example. Same question, different learners, different paths. <b>That loop is the autonomy.</b>
      </div>
      <div class="sidecard">
        <h3>○ Personal Coach — same sandwich, multi-agent</h3>
        Interviewer · evaluator · coach · curriculum-planner agents behind a <b>deterministic
        orchestrator</b>; study planner: LLM proposes, scheduler validates &amp; repairs —
        <i>feasible or flag</i>.
      </div>
    </div>
  </div>

  <div class="strip">
    <h2>Receipts — frozen 40-case golden set · 16 happy / 9 edge / 5 known-failure / 10 adversarial · bars fixed before runs · mean of 3 runs</h2>
    <div class="kpis">
      <div class="kpi"><div class="label">Citation F1</div>
        <div class="value">0.444 → 0.594<span class="tag win">WIN</span></div>
        <div class="note">+0.150 · clears 0.50 floor · honest about the 0.90 bar</div></div>
      <div class="kpi"><div class="label">Turn p95 latency</div>
        <div class="value">11.33s → 8.28s<span class="tag win">WIN</span></div>
        <div class="note">-27% from loop caps + reuse</div></div>
      <div class="kpi"><div class="label">Refusal recall</div>
        <div class="value">1.000<span class="tag held">GATE</span></div>
        <div class="note">held on all adversarial cases — gates release</div></div>
      <div class="kpi"><div class="label">Retrieval recall@5</div>
        <div class="value">1.000<span class="tag held">HELD</span></div>
        <div class="note">failures are post-retrieval behavior</div></div>
      <div class="kpi"><div class="label">Task completion</div>
        <div class="value">94.7% → 93.3%<span class="tag miss">-1.4pp</span></div>
        <div class="note">baseline infra-excluded (36/38); current mean, all 40 — disclosed</div></div>
      <div class="kpi"><div class="label">Refusal precision</div>
        <div class="value">0.833 → 0.791<span class="tag miss">MISS</span></div>
        <div class="note">over-conservative refusals, 3 named cases — disclosed</div></div>
    </div>
    <div class="lever"><b>THE EVAL WAS OUR DEBUGGER.</b> A broad citation fallback was predicted to
      gain +0.10–0.20 citation F1. Measured: <b>-0.044</b> and task completion <b>-5.2pp</b> —
      rejected, not shipped. Bars before runs; numbers published even when they lose.</div>
  </div>

  <div class="scoped">○ <b>Scoped into the same grounded core:</b> voice tutoring (consent-gated
    tutor voice) · current-docs lane (separately cited) · controlled ingestion with
    eval-contamination checks · cohort access · progress analytics · <b>Personal Coach</b>
    (multi-agent mock-interview studio · MCQ placement · gap-driven flash cards + quiz drills ·
    mastery levels · learner-editable study planner).</div>

  <div class="footer">
    <div class="gates">Every layer ships through the same gates: grounded-or-refuse · privacy
      review · evals before release.</div>
    <div class="prov">figures: docs/week4-eval-dashboard-data.json · dataset 2026-06-24-plan1 ·
      snapshot 2026-06-25</div>
  </div>
</body>
</html>
```

- [ ] **Step 2: Serve and render**

```bash
uv run python -m http.server 8756
```
Run in background from the repo root. Then with the Playwright MCP tools:
1. `browser_navigate` → `http://localhost:8756/docs/assets/pitch/architecture-pitch-onepager.html`
2. `browser_resize` → width 1440, height 1200
3. `browser_take_screenshot` → `fullPage: true`, filename `architecture-pitch-onepager.png`
4. Copy the file out of the Playwright output dir:
   `cp .playwright-mcp/architecture-pitch-onepager.png docs/assets/pitch/`
5. Kill the server (exit code 143 is the expected SIGTERM).

- [ ] **Step 3: Visual check**

Read `docs/assets/pitch/architecture-pitch-onepager.png` and confirm: three bands render in order
with the yellow agent band between two dark bands; the refusal/loop/coach side cards sit to the
right; all six KPI cards on one row; legend shows ●/◐/○; no text overflow or clipping. Fix CSS and
re-render if anything is off.

- [ ] **Step 4: Commit**

```bash
git add docs/assets/pitch/architecture-pitch-onepager.html docs/assets/pitch/architecture-pitch-onepager.png
git commit -m "docs: architecture pitch one-pager (HTML + rendered PNG)"
```

---

### Task 3: Number + privacy verification

**Files:**
- Modify (only if a check fails): the two Task-1/Task-2 artifacts

**Interfaces:**
- Consumes: both artifacts; `docs/week4-eval-dashboard-data.json`.

- [ ] **Step 1: String-match every quoted figure against the dashboard JSON**

```bash
for n in "0.444" "0.594" "+0.150" "11.33" "8.28" "1.000" "94.7" "93.3" "0.833" "0.791" \
         "-5.2" "-0.044" "36/38" "0.40" "0.85" "21.96" "0.14"; do
  jq -r 'tostring' docs/week4-eval-dashboard-data.json | grep -qF -- "$n" \
    && echo "OK   $n (in dashboard)" || echo "FAIL $n (NOT in dashboard)"
done
```
Expected: every line `OK`. Any `FAIL` means an artifact quotes a figure the dashboard doesn't
carry — fix the artifact (never the JSON), then re-run.

- [ ] **Step 2: Confirm the caveats are attached in the artifacts**

```bash
grep -c "infra-excluded" docs/assets/pitch/*.html docs/assets/pitch/*.md
grep -c "runs 2/3" docs/assets/pitch/pitch-script.md
grep -c "◐" docs/assets/pitch/architecture-pitch-onepager.html
```
Expected: `infra-excluded` ≥ 1 in each artifact; `runs 2/3` ≥ 1; `◐` ≥ 4 (strict filters, panel,
chips, recovery suggestions).

- [ ] **Step 3: Privacy scan**

```bash
grep -RInEf localdocs/private-scan-patterns.txt docs/assets/pitch/ ; echo "exit=$?"
```
Expected: no matches, `exit=1`. The pattern file is gitignored (lives under `localdocs/`) and holds
the private denylist — team personal names, corpus filename fragments, private hosts and email
addresses. The tokens themselves must never appear in any committed file, **including this plan**;
that is why the list is external.

- [ ] **Step 4: Commit any fixes**

```bash
git add -u docs/assets/pitch/ && git commit -m "docs: pitch artifacts — verification fixes" || echo "nothing to fix"
```

---

### Task 4: PR + Codex review gate + merge

**Files:**
- Create: `tmp/codex-review-pitch-prompt.md` (gitignored, operational)

- [ ] **Step 1: Push and open the PR**

```bash
git push -u origin docs/pitch-artifacts
gh pr create --title "docs: architecture pitch artifacts (one-pager + modular script)" --body "Implements docs/superpowers/specs/2026-07-04-architecture-pitch-design.md (merged, PR #69). One-pager (HTML->PNG, sandwich flow with shipped/build-slice legend, receipts strip, scoped strip, gates footer) + modular spoken script (M0 <=240 words verified, M1-M3, Q&A ammo). All figures string-matched against docs/week4-eval-dashboard-data.json; privacy scan clean. Codex review to follow as a comment."
```

- [ ] **Step 2: Run the Codex review (stdin closed) and post it**

Write `tmp/codex-review-pitch-prompt.md` asking Codex to verify, against the spec's acceptance
criteria: (1) every number + caveat vs `docs/week4-eval-dashboard-data.json`; (2) status-tag
correctness (`◐` on panel/chips/filters, `●` only on shipped modules, `○` scoped strip);
(3) M0 word count ≤ 240; (4) privacy scan; (5) claim falsifiability vs the repo. Then:

```bash
codex exec -s read-only -C "$PWD" "$(cat tmp/codex-review-pitch-prompt.md)" </dev/null > tmp/codex-review-pitch-out.md 2> tmp/codex-review-pitch-err.log
sed 's#/Users/[^ )]*/genacademy-coach/##g' tmp/codex-review-pitch-out.md > tmp/codex-review-pitch-posted.md
gh pr comment <PR#> --body-file tmp/codex-review-pitch-posted.md
```

- [ ] **Step 3: Fix blocking findings (or record skip rationale), then merge**

Apply meaningful findings, push, post a resolution comment. Then:

```bash
gh pr merge <PR#> --merge --delete-branch
```
If "Base branch was modified": `sleep 3` and retry once.

- [ ] **Step 4: Report evidence**

Report to the owner: PNG path, M0 word count, verification outputs, Codex verdict + resolution,
merge SHA.
