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
- **Optional local-only context:** `AGENTS.md` §7 "Optional local-only context"; ignored `localdocs/`
  files are private inputs only and must not be committed or quoted into public artifacts unless
  explicitly requested.

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

## Optional Graphify navigation

Some local workspaces have a generated knowledge graph under `graphify-out/`. This is optional,
gitignored context and is not available in fresh clones, CI, or remote agents.

Rules:
- When both the `graphify` command and `graphify-out/graph.json` exist, codebase questions may start
  with `graphify query "<question>"`. Use `graphify path "<A>" "<B>"` for relationships and
  `graphify explain "<concept>"` for focused concepts.
- If either prerequisite is absent, continue with the normal repository-navigation workflow.
- When available, prefer `graphify-out/wiki/index.md` for broad navigation. Read
  `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when query/path/explain do not
  surface enough context.
- After modifying code, run `graphify update .` only when both prerequisites are present.
