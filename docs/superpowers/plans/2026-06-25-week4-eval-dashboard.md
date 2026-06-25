# Week-4 Eval Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public-safe static Week-4 eval dashboard plus a local-only private appendix without changing agent, eval, scorer, or product behavior.

**Architecture:** Commit a redacted JSON snapshot under `docs/`, render it into a self-contained static HTML dashboard with a small Python generator, and keep private LangSmith/local artifact context in ignored `localdocs/`. The generator validates the public snapshot with an explicit denylist before writing HTML.

**Tech Stack:** Python 3.12 stdlib (`json`, `html`, `re`, `pathlib`, `subprocess`), vanilla HTML/CSS/JS, existing `pytest`/`ruff`, existing `scripts/check_eval_leak.py`.

---

## File Structure

- Create `docs/week4-eval-dashboard-data.json`
  - Public-safe committed snapshot.
  - Contains aggregate metrics, run IDs, provenance, guardrails, caveats, and sanitized failure labels.
  - Does not include raw learner text, tutor prose, retrieved spans, raw traces, secrets, private URLs, or frozen `test` data.
- Create `scripts/build_week4_eval_dashboard.py`
  - Loads and validates the committed JSON snapshot.
  - Renders `docs/week4-eval-dashboard.html`.
  - Writes/updates `localdocs/docs/week4-eval-dashboard-private-appendix.md` only when `localdocs/INDEX.md` exists.
- Create `tests/test_week4_eval_dashboard.py`
  - Unit tests for public-snapshot validation, formatting, HTML rendering, and localdocs no-op behavior.
- Create generated `docs/week4-eval-dashboard.html`
  - Self-contained public-safe static dashboard.
  - No external dependencies.
- Modify `localdocs/INDEX.md`
  - Add the local-only appendix entry if the appendix is generated.
- Optionally create `localdocs/docs/week4-eval-dashboard-private-appendix.md`
  - Ignored local-only artifact. It may name private local artifact paths and private LangSmith context guidance.

## Task 1: Add Focused Tests For Dashboard Validation

**Files:**
- Create: `tests/test_week4_eval_dashboard.py`

- [ ] **Step 1: Create the test module with import helper and minimal snapshot factory**

```python
import importlib.util
from pathlib import Path

import pytest


def load_dashboard_module():
    script_path = Path("scripts/build_week4_eval_dashboard.py").resolve()
    spec = importlib.util.spec_from_file_location("build_week4_eval_dashboard", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def minimal_snapshot():
    return {
        "schema_version": 1,
        "title": "Week-4 Eval Dashboard",
        "provenance": {
            "snapshot_date": "2026-06-25",
            "generator_git_sha": "test-sha",
            "baseline_artifact": "golden-baseline-20260624.json",
            "current_run_ids": [
                "current-main-full-langsmith-r1",
                "current-main-full-langsmith-r2",
                "current-main-full-langsmith-r3",
            ],
            "dataset_version_note": "40-case golden; 16 happy / 9 edge / 5 known_failure / 10 adversarial",
            "model_id": "Qwen/Qwen3-30B-A3B-Instruct-2507",
            "thresholds": {"stop": 0.40, "confirm_upper": 0.85},
            "source_handoff_doc": "docs/week4-eval-progress-handoff.md",
            "privacy_reviewed": True,
            "redaction_policy": "Committed dashboard data contains only aggregate metrics and synthetic case IDs.",
        },
        "hero": {
            "verdict": "Citation F1 +0.150 and turn p95 -27%; refusal precision and task completion regressed slightly.",
            "primary_question": "Did Week-4 improvements help without breaking refusal safety?",
        },
        "class_balance": {"happy": 16, "edge": 9, "known_failure": 5, "adversarial": 10},
        "baseline": {"label": "baseline", "task_completion_rate": 0.947, "citation_f1": 0.444},
        "current_mean": {"label": "current mean", "task_completion_rate": 0.933, "citation_f1": 0.594},
        "kpis": [
            {
                "id": "citation_f1",
                "label": "Citation F1",
                "baseline": "0.444",
                "current": "0.594",
                "delta": "+0.150",
                "status": "win",
                "note": "Below 0.90 plan pass bar.",
            }
        ],
        "runs": [
            {"run_id": "r1", "citation_f1": 0.539, "turn_p95_ms": 8102, "task_completion_rate": 0.925},
            {"run_id": "r2", "citation_f1": 0.667, "turn_p95_ms": 8356, "task_completion_rate": 0.950},
            {"run_id": "r3", "citation_f1": 0.578, "turn_p95_ms": 8368, "task_completion_rate": 0.925},
        ],
        "tool_latency": [
            {"tool": "generate_check_item", "mean_ms": 49793, "share": 0.66},
            {"tool": "retrieve_course_corpus", "mean_ms": 27046, "share": 0.34},
        ],
        "guardrails": [
            {"label": "Refusal recall", "value": "1.000", "status": "held"},
            {"label": "Retrieval recall@5", "value": "1.000", "status": "held"},
        ],
        "remaining_failures": [
            {"case_id": "happy_014", "summary": "Stable false refusal", "status": "open"}
        ],
        "notes": [
            "Cost delta vs baseline is not meaningful because baseline pricing env vars were unset."
        ],
    }
```

- [ ] **Step 2: Add validation tests**

```python
def test_validate_public_snapshot_accepts_clean_data():
    module = load_dashboard_module()
    module.validate_public_snapshot(minimal_snapshot())


@pytest.mark.parametrize(
    "bad_key",
    ["user_query", "answer_text", "trace_id", "retrieved_span_text", "langsmith_url"],
)
def test_validate_public_snapshot_rejects_forbidden_exact_keys(bad_key):
    module = load_dashboard_module()
    data = minimal_snapshot()
    data[bad_key] = "private"
    with pytest.raises(ValueError, match=bad_key):
        module.validate_public_snapshot(data)


def test_validate_public_snapshot_rejects_forbidden_key_pattern():
    module = load_dashboard_module()
    data = minimal_snapshot()
    data["nested"] = {"learner_text": "private"}
    with pytest.raises(ValueError, match="learner_text"):
        module.validate_public_snapshot(data)


def test_validate_public_snapshot_rejects_langsmith_url_values():
    module = load_dashboard_module()
    data = minimal_snapshot()
    data["notes"].append("https://smith.langchain.com/o/private")
    with pytest.raises(ValueError, match="smith.langchain.com"):
        module.validate_public_snapshot(data)
```

- [ ] **Step 3: Add rendering and localdocs no-op tests**

```python
def test_render_dashboard_includes_honest_verdict_and_footer():
    module = load_dashboard_module()
    html = module.render_dashboard(minimal_snapshot())
    assert "Citation F1 +0.150" in html
    assert "refusal precision" in html
    assert "snapshot_date" in html
    assert "docs/week4-eval-progress-handoff.md" in html
    assert "langsmith.com" not in html
    assert "user_query" not in html
    assert "answer_text" not in html
    assert "trace_id" not in html


def test_write_private_appendix_noops_without_localdocs(tmp_path):
    module = load_dashboard_module()
    written = module.write_private_appendix(minimal_snapshot(), repo_root=tmp_path)
    assert written is None
```

- [ ] **Step 4: Run the focused test and verify it fails before implementation**

Run:

```bash
uv run pytest tests/test_week4_eval_dashboard.py -q
```

Expected: fail with `FileNotFoundError` or import failure because `scripts/build_week4_eval_dashboard.py` does not exist yet.

## Task 2: Add Public-Safe Data Snapshot

**Files:**
- Create: `docs/week4-eval-dashboard-data.json`

- [ ] **Step 1: Create the redacted JSON snapshot**

Use this shape and populate from the already-reviewed handoff metrics:

```json
{
  "schema_version": 1,
  "title": "Week-4 Eval Dashboard",
  "provenance": {
    "snapshot_date": "2026-06-25",
    "generator_git_sha": "filled-by-render-command",
    "baseline_artifact": "golden-baseline-20260624.json",
    "current_run_ids": [
      "current-main-full-langsmith-r1",
      "current-main-full-langsmith-r2",
      "current-main-full-langsmith-r3"
    ],
    "dataset_version_note": "40-case golden; 16 happy / 9 edge / 5 known_failure / 10 adversarial; splits seed/dev/negative_control, no frozen test split",
    "model_id": "Qwen/Qwen3-30B-A3B-Instruct-2507",
    "thresholds": {
      "stop": 0.40,
      "confirm_upper": 0.85
    },
    "source_handoff_doc": "docs/week4-eval-progress-handoff.md",
    "privacy_reviewed": true,
    "redaction_policy": "Committed dashboard data contains aggregate metrics, synthetic case IDs, and public-safe caveats only; no raw learner text, tutor prose, retrieved spans, raw traces, private URLs, secrets, or frozen test data."
  },
  "hero": {
    "primary_question": "Did the Week-4 improvements measurably help without breaking grounded refusal safety?",
    "verdict": "Citation F1 improved by +0.150 and turn p95 latency improved by 27%; retrieval recall and refusal recall held at 1.000. Tradeoffs: refusal precision fell from 0.833 to 0.791 and task completion moved from 94.7% infra-excluded baseline to 93.3% current mean; citation F1 remains about 0.31 below the 0.90 plan pass bar."
  }
}
```

- [ ] **Step 2: Add the full metric arrays**

Add:

- `kpis`: citation F1, turn p95, refusal recall, retrieval recall@5, task completion, refusal precision.
- `metric_deltas`: baseline/current/delta table rows for task completion, teachable completion, refusal P/R/F1, citation F1, tool F1, retrieval recall@5, latency, tokens, and cost caveat.
- `runs`: r1/r2/r3 rows.
- `tool_latency`: aggregate mean ms and share for `generate_check_item`, `retrieve_course_corpus`, `escalate_to_mentor`, `grade_understanding`, and `update_profile`.
- `guardrails`: deterministic scorer, no threshold lowering, no scorer hacks, no frozen test split, no public raw traces.
- `remaining_failures`: `happy_014`, `known_failure_001`, `edge_002`, `edge_008`.
- `perspectives`: user and builder notes.
- `sources`: public-safe references to design spec and handoff doc.

- [ ] **Step 3: Run a direct forbidden-string scan on the snapshot**

Run:

```bash
rg -n "langsmith\\.com|user_query|answer_text|trace_id|retrieved_span_text|raw_prompt|system_prompt" docs/week4-eval-dashboard-data.json
```

Expected: no output.

## Task 3: Implement The Static HTML Generator

**Files:**
- Create: `scripts/build_week4_eval_dashboard.py`

- [ ] **Step 1: Add constants, file paths, and validation helpers**

Implementation outline:

```python
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
from pathlib import Path
from typing import Any

FORBIDDEN_KEYS = {
    "user_query",
    "answer_text",
    "predicted_text",
    "final_text",
    "assistant_text",
    "tutor_text",
    "retrieved_span",
    "retrieved_span_text",
    "raw_span",
    "raw_prompt",
    "system_prompt",
    "trace",
    "trace_id",
    "trace_json",
    "langsmith_url",
    "langsmith_experiment_url",
}
FORBIDDEN_KEY_RE = re.compile(
    r"(langsmith|trace|prompt|span|tutor_?text|learner_?text|user_?query|answer_?text)",
    re.IGNORECASE,
)
FORBIDDEN_URL_RE = re.compile(r"https://(smith\.langchain\.com|eu\.smith\.langchain\.com)")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def current_git_sha(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def validate_public_snapshot(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS or FORBIDDEN_KEY_RE.search(key):
                raise ValueError(f"forbidden public dashboard key at {path}.{key}: {key}")
            validate_public_snapshot(child, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            validate_public_snapshot(child, f"{path}[{index}]")
        return
    if isinstance(value, str) and FORBIDDEN_URL_RE.search(value):
        raise ValueError(f"forbidden private LangSmith URL at {path}: {value}")
```

- [ ] **Step 2: Add formatting helpers**

```python
def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def format_seconds(ms: float | int) -> str:
    return f"{float(ms) / 1000:.2f}s"


def status_class(status: str) -> str:
    return {
        "win": "status-win",
        "held": "status-held",
        "caveat": "status-caveat",
        "risk": "status-risk",
        "open": "status-risk",
    }.get(status, "status-neutral")
```

- [ ] **Step 3: Add `render_dashboard(data)`**

The renderer must:

- call `validate_public_snapshot(data)` first
- create KPI cards with `aria-label`
- create baseline/current delta table
- create r1/r2/r3 table plus sparkline-like bars
- create tool latency horizontal bars
- create guardrail and remaining-failure sections
- create footer with `snapshot_date`, `generator_git_sha`, and handoff link
- use no external CSS, JS, fonts, or images
- include no private URL or raw text fields

Keep CSS in the returned HTML string. Use 8px card radius, a neutral background, teal/amber/slate/red palette, and responsive CSS for narrow screens.

- [ ] **Step 4: Add private appendix writer**

```python
def write_private_appendix(data: dict[str, Any], *, repo_root: Path) -> Path | None:
    index_path = repo_root / "localdocs" / "INDEX.md"
    if not index_path.exists():
        return None
    appendix_path = repo_root / "localdocs" / "docs" / "week4-eval-dashboard-private-appendix.md"
    appendix_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_lines = "\n".join(
        f"- `{run_id}`" for run_id in data["provenance"]["current_run_ids"]
    )
    appendix_path.write_text(
        "# Week-4 Eval Dashboard Private Appendix\n\n"
        "Local-only companion for the public dashboard. Do not commit this file.\n\n"
        "## Private Links\n\n"
        "Private LangSmith project and dataset URLs belong here or in submission notes. "
        "They are intentionally not stored in the public dashboard JSON or generator.\n\n"
        "## Public Snapshot Run IDs\n\n"
        f"{artifact_lines}\n",
        encoding="utf-8",
    )
    return appendix_path
```

- [ ] **Step 5: Add CLI entry point**

```python
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="docs/week4-eval-dashboard-data.json")
    parser.add_argument("--out", default="docs/week4-eval-dashboard.html")
    parser.add_argument("--write-private-appendix", action="store_true")
    args = parser.parse_args()

    root = repo_root()
    data_path = root / args.data
    data = json.loads(data_path.read_text(encoding="utf-8"))
    data.setdefault("provenance", {})["generator_git_sha"] = current_git_sha(root)
    validate_public_snapshot(data)
    html_text = render_dashboard(data)
    out_path = root / args.out
    out_path.write_text(html_text, encoding="utf-8")
    if args.write_private_appendix:
        write_private_appendix(data, repo_root=root)
    print(out_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the focused test**

Run:

```bash
uv run pytest tests/test_week4_eval_dashboard.py -q
```

Expected: pass.

## Task 4: Generate The Public Dashboard And Local Appendix

**Files:**
- Create: `docs/week4-eval-dashboard.html`
- Create: `localdocs/docs/week4-eval-dashboard-private-appendix.md`
- Modify: `localdocs/INDEX.md`

- [ ] **Step 1: Run the generator**

Run:

```bash
uv run python scripts/build_week4_eval_dashboard.py --write-private-appendix
```

Expected: prints `docs/week4-eval-dashboard.html` and writes the ignored local appendix only if `localdocs/INDEX.md` exists.

- [ ] **Step 2: Add the localdocs index entry**

Add one bullet to `localdocs/INDEX.md`:

```markdown
- `docs/week4-eval-dashboard-private-appendix.md` - local-only companion for the public Week-4 eval
  dashboard; keeps private LangSmith/link and local artifact context out of committed dashboard files.
```

- [ ] **Step 3: Open the generated dashboard**

Open:

```text
docs/week4-eval-dashboard.html
```

Expected: the first viewport shows the honest hero verdict, KPI cards, and no text overlap at desktop width.

## Task 5: Validate Privacy, Rendering, And Repo Health

**Files:**
- Validate committed public files and ignored local appendix.

- [ ] **Step 1: Run focused tests**

Run:

```bash
uv run pytest tests/test_week4_eval_dashboard.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run leak check**

Run:

```bash
uv run python scripts/check_eval_leak.py
```

Expected: no eval test IDs/checksums or n-grams found where sources are available.

- [ ] **Step 3: Run static forbidden-string scans on committed dashboard artifacts**

Run:

```bash
rg -n "langsmith\\.com|user_query|answer_text|trace_id|retrieved_span_text|raw_prompt|system_prompt" docs/week4-eval-dashboard.html docs/week4-eval-dashboard-data.json
```

Expected: no output.

- [ ] **Step 4: Run formatter/lint checks**

Run:

```bash
uv run ruff check scripts/build_week4_eval_dashboard.py tests/test_week4_eval_dashboard.py
git diff --check
```

Expected: Ruff clean and no whitespace errors.

- [ ] **Step 5: Inspect generated HTML**

Manual check:

- first viewport answers the dashboard question without scrolling on a normal desktop viewport
- narrow/mobile width has no obvious text overlap
- KPI cards, run table, guardrails, and tool latency bars render
- footer shows snapshot date, generator git SHA, and handoff link

- [ ] **Step 6: Confirm the public privacy flag before commit**

Open `docs/week4-eval-dashboard-data.json` and verify:

```json
"privacy_reviewed": true
```

Expected: this field is present because the public snapshot has passed the explicit scans above. The
generator must not set this value automatically; it is a reviewed data-file field.

- [ ] **Step 7: Commit the implementation**

Stage only public implementation files plus the ignored local index if intentionally tracked is not possible because `localdocs/` is ignored. Do not stage `.kimchi/`, `.superpowers/`, `eval/runs/`, or `localdocs/`.

Run:

```bash
git add docs/week4-eval-dashboard-data.json docs/week4-eval-dashboard.html scripts/build_week4_eval_dashboard.py tests/test_week4_eval_dashboard.py
git commit -m "docs: add Week 4 eval dashboard"
```

Expected: one implementation commit with the public-safe dashboard, generator, and tests.
