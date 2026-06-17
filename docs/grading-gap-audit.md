# Grading Gap Audit

Date: 2026-06-17

Purpose: make the grader's proof path obvious without changing product behavior. This audit uses the
Week-2 score breakdown as the working frame because the official Week-3 rubric weights are not in this
repo. Treat this as a submission-hardening checklist, not as new implementation approval.

## Audit Matrix

| Category | Current evidence (file:line) | Grading risk | Highest-impact fix | Effort | File(s) | Verification |
|---|---|---|---|---|---|---|
| Scope Definition | MVP and pull-ins are explicit in `README.md:24`; roadmap says every step must stay demoable in `specs/roadmap.md:5`; risk caps protect scope in `specs/roadmap.md:185`. | Grader may read quiz/interview/voice/memory as unfinished promises rather than deliberate cuts. | Put a shipped-vs-roadmap table at the top of the README and make Mock Interview a roadmap item, not a current mode. | S | `README.md`, `specs/roadmap.md` | Link from README to roadmap and demo playbook; no code required. |
| Architecture | LangChain `create_agent` on LangGraph runtime is stated in `README.md:64`; system diagram shows one agent loop and one retriever in `docs/architecture-diagrams.md:31`; pure-core rules live in `AGENTS.md:96`. | The architecture depth can be hidden behind "RAG tutor" framing. | Add a grader path that links the runtime trace, eval JSON, and architecture diagram in the first screen of README. | S | `README.md`, `docs/architecture-diagrams.md` | `uv run pytest -q`; `uv run ruff check .`; no `langgraph.*` direct import. |
| Creativity/Originality | Personalization/lens switch is described in `README.md:34`; same-topic lens evidence is listed in `README.md:93`; demo hook is in `docs/demo-and-deliverables.md:8`. | "Never the same answer to everyone" can overclaim ML clustering or durable personalization. | Clarify that current personalization is switchable teaching lens plus within-session profile; cross-session memory is roadmap. | S | `README.md`, `docs/demo-and-deliverables.md` | README language says lens/profile, not learner clustering. |
| Documentation | Canonical docs are listed in `README.md:39`; submission draft and prompt appendix are listed in `README.md:50`; demo DOCX exists via `docs/demo-and-deliverables.md:35`. | Proof is spread across many docs; graders may miss the fastest path. | Add a "Grader's 5-minute path" that points to the exact script, eval artifact, live shell URL, screenshots, and hardening docs. | S | `README.md` | Link check by inspection; no private trace JSON committed. |
| Presentation/Walkthrough | Video script is already packaged in `docs/demo-and-deliverables.md:41`; local UI recording command is in `docs/demo-and-deliverables.md:90`; screenshots are catalogued in `docs/demo-and-deliverables.md:35`. | A terminal-heavy story can undersell the shipped UI and agent trace. | Lead with the local Gradio walkthrough DOCX and screenshot inventory, then use CLI commands as fallback evidence. | S | `README.md`, `docs/demo-and-deliverables.md` | Local app smoke or screenshot inventory; no generated quiz text in public artifacts. |
| Bonus | Quiz Mode shipped as first pull-in in `README.md:28`; deterministic quiz trace evidence is in `README.md:98`; instructor-review surface is `review_queue.jsonl` in `docs/demo-and-deliverables.md:67`. | Bonus value is diffuse: quiz, HITL, refusal, deployment shell, and eval diagnostics are not grouped as bonus. | Summarize the bonus stack in one README status table and reserve the standout next workflow for Skill-Gap Diagnosis. | S | `README.md`, `docs/superpowers/plans/2026-06-17-skill-gap-diagnosis.md` | PR review confirms no overclaim and no code before plan approval. |
| Security/Safety | Held-out test protection is explicit in `README.md:158`; leak guard is referenced in `docs/demo-and-deliverables.md:65`; `.env` remains untracked and `.gitignore` covers env/secrets. | Safety may look implied instead of proved; reviewers may re-flag `.env` despite no leak. | State that `.env` is not a leak, keep secret/public flip runbook, and include leak-guard output in PR 2 body. | S | `docs/submission-hardening-plan.md`, `README.md` | `uv run python scripts/check_eval_leak.py`; `git log --all -- .env` should not show committed secrets. |
| Evaluation/Testing | Dev eval command is in `README.md:148`; latest artifact is `eval/runs/teach-loop-dev-main-final-20260616.json`; roadmap preserves test split in `specs/roadmap.md:119`. | `7/10` and `7/8` can sound like final test performance if not dated and labeled dev-only. | Keep numbers dated, label as dev, explicitly say held-out `test` split remains unrun. | S | `README.md`, `docs/demo-and-deliverables.md` | `uv run python scripts/eval_teach_loop.py --split dev`; do not run `--split test`. |
| Deployment Reliability | Private HF Space shell is documented in `README.md:13`; roadmap records HTTP 200 and shell limits in `specs/roadmap.md:96`; deliverables table records corpus smoke pending in `docs/demo-and-deliverables.md:252`. | Live URL can look broken if a cold visitor expects grounded behavior without corpus. | Keep the shell limitation first-class, then use a gated runbook for public-safe corpus upload and live smoke. | M | `docs/submission-hardening-plan.md`, `docs/hugging-face-deployment-plan.md` | Human-run only: upload public-safe subset, run grounded teach + safe refusal, record URL and limits. |

## Strict Overclaim Checks

- **"Web chat" is now backed, but diagrams should label shipped versus planned.** The local Gradio UI is
  shipped, and the private Space shell is live-smoked. Diagrams that still read like a pre-build design
  artifact should add a note that CLI + Gradio are shipped, while voice/admin/interview/memory remain
  planned pull-ins.
- **Hugging Face is a live shell, not a live grounded tutor yet.** README and deployment docs should point
  to the live private URL and say no private corpus/index is uploaded. The provider/corpus-backed click
  smoke is pending by design.
- **"Adaptive" means switchable teaching lens plus within-session profile today.** It does not mean
  durable per-learner clustering, provider memory, or cross-session personalization. Keep the clause in
  README and demo docs.
- **Mock Interview is a pull-in.** Keep it under roadmap/pull-ins, not as a shipped mode.
- **Metrics are dev metrics.** Keep `7/10` overall and `7/8` teachable dated to the latest dev evidence.
  Do not claim held-out `test` performance; `test` remains unrun unless final reporting explicitly uses it.
- **`.env` is not a leak.** `.env` is not tracked or committed on any branch, and `.gitignore` covers env
  and secret patterns. Keep pre-public hygiene in the runbook, but do not describe local credentials as a
  committed leak.

## Rubric Inputs Still Needed

No official Week-3 rubric document is present in this repo. The working frame is:

- Week-2 score breakdown: Scope Definition /10, Architecture /25, Creativity and Originality /20,
  Documentation /10, Presentation and Walkthrough /10, Bonus /25.
- Bootcamp criteria referenced in the demo playbook: Consistency, Creativity, Execution, Technical
  thinking, Initiative.

Confirm before final submission:

- Official Week-3 weights and whether they differ from Week 2.
- Whether Security/Safety, Evaluation/Testing, and Deployment Reliability are scored separately or folded
  into Architecture/Bonus.
- Required deliverable formats: live URL required or optional, Google Doc structure, video time cap, and
  whether screenshots may reference a private repo/local corpus.
- Whether a public repo flip is mandatory before grading and whether private HF Space links are acceptable.
