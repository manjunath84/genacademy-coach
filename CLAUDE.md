# CLAUDE.md

This file is a thin mirror. The tool-neutral source of truth is **[`AGENTS.md`](AGENTS.md)** — read it
first and follow it. Rules do not change with the tool.

Quick pointers:
- **What we're building + the gates + guardrails:** `AGENTS.md`
- **Mission / audience / scope:** `specs/mission.md`
- **Stack + what's deferred:** `specs/tech-stack.md`
- **Roadmap (MUST vs SHOULD):** `specs/roadmap.md`
- **Architecture, visualized:** `docs/architecture-diagrams.md`
- **Demo trace/privacy boundary:** `AGENTS.md` §3 plus `README.md` Safety & Privacy

**No code until the plan is approved** (`AGENTS.md` §2, gate 1).

## Skill routing

This project runs on the **`ai-dev-workflow`** skill (the tool-neutral umbrella binding superpowers +
gstack). When a request matches a skill, invoke it via the Skill tool; when in doubt, invoke. Use the
canonical command per workflow (from the user's global `~/.claude/CLAUDE.md` — do **not** invoke
alternatives alongside these):

- **Plan / brainstorm** → `superpowers:brainstorm` → `superpowers:write-plan` → `superpowers:execute-plan`
  (design + implementation plans land in `docs/superpowers/{specs,plans}/`).
- **PR / code review** → `/pr-review-toolkit:review-pr`; **simplify** → `/pr-review-toolkit:review-pr simplify`.
- **Different-model challenge / second opinion** (builder ≠ reviewer — `AGENTS.md` §2 gate 2) → `/codex`.
- **Bugs / errors** → `/investigate`; **"does it work?" / evidence** (gate 3) → `/qa`, `/health`, `/verify`.
- **Commit / push / PR** → `/commit-commands:commit-push-pr`.
