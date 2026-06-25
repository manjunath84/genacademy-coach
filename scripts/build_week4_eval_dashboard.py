# ruff: noqa: E501

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


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def seconds(ms: float | int) -> str:
    return f"{float(ms) / 1000:.2f}s"


def integer(value: float | int) -> str:
    return f"{float(value):,.0f}"


def dollars(value: float) -> str:
    return f"${value:.2f}"


def status_class(status: str) -> str:
    return {
        "win": "status-win",
        "held": "status-held",
        "caveat": "status-caveat",
        "risk": "status-risk",
        "open": "status-risk",
        "watch": "status-caveat",
    }.get(status, "status-neutral")


def bar_width(value: float, max_value: float) -> str:
    if max_value <= 0:
        return "0%"
    return f"{max(4.0, min(100.0, value / max_value * 100)):.1f}%"


def render_kpis(data: dict[str, Any]) -> str:
    cards: list[str] = []
    for item in data["kpis"]:
        cls = status_class(str(item.get("status", "")))
        label = esc(item["label"])
        cards.append(
            f"""
            <article class="kpi {cls}" aria-label="{label}: current {esc(item['current'])}, delta {esc(item['delta'])}">
              <div class="kpi-label">{label}</div>
              <div class="kpi-main">{esc(item['current'])}</div>
              <div class="kpi-sub"><span>Baseline {esc(item['baseline'])}</span><strong>{esc(item['delta'])}</strong></div>
              <p>{esc(item['note'])}</p>
            </article>
            """
        )
    return "\n".join(cards)


def render_metric_rows(data: dict[str, Any]) -> str:
    rows: list[str] = []
    for item in data["metric_deltas"]:
        cls = status_class(str(item.get("status", "")))
        rows.append(
            f"""
            <tr>
              <th scope="row">{esc(item['metric'])}</th>
              <td>{esc(item['baseline'])}</td>
              <td>{esc(item['current'])}</td>
              <td><span class="pill {cls}">{esc(item['delta'])}</span></td>
              <td>{esc(item['note'])}</td>
            </tr>
            """
        )
    return "\n".join(rows)


def render_run_rows(data: dict[str, Any]) -> str:
    max_latency = max(float(run["turn_p95_ms"]) for run in data["runs"])
    rows: list[str] = []
    for run in data["runs"]:
        rows.append(
            f"""
            <tr>
              <th scope="row">{esc(run['run_id'])}</th>
              <td>{float(run['citation_f1']):.3f}</td>
              <td>{pct(float(run['task_completion_rate']))}</td>
              <td>{float(run['refusal_precision']):.3f}</td>
              <td>{seconds(float(run['turn_p95_ms']))}</td>
              <td>
                <div class="bar-track" aria-label="Turn p95 {seconds(float(run['turn_p95_ms']))}">
                  <span class="bar-fill" style="width:{bar_width(float(run['turn_p95_ms']), max_latency)}"></span>
                </div>
              </td>
            </tr>
            """
        )
    return "\n".join(rows)


def render_tool_latency(data: dict[str, Any]) -> str:
    max_ms = max(float(tool["total_ms_per_run"]) for tool in data["tool_latency"])
    rows: list[str] = []
    for tool in data["tool_latency"]:
        rows.append(
            f"""
            <div class="tool-row">
              <div>
                <strong>{esc(tool['tool'])}</strong>
                <span>{integer(tool['total_ms_per_run'])} ms total per run / {float(tool['share']) * 100:.1f}% share</span>
              </div>
              <div class="bar-track" aria-label="{esc(tool['tool'])} total tool time per run">
                <span class="bar-fill amber" style="width:{bar_width(float(tool['total_ms_per_run']), max_ms)}"></span>
              </div>
            </div>
            """
        )
    return "\n".join(rows)


def render_guardrails(data: dict[str, Any]) -> str:
    cards: list[str] = []
    for item in data["guardrails"]:
        cards.append(
            f"""
            <article class="mini-card {status_class(str(item.get('status', '')))}">
              <strong>{esc(item['label'])}</strong>
              <span>{esc(item['value'])}</span>
              <p>{esc(item['note'])}</p>
            </article>
            """
        )
    return "\n".join(cards)


def render_failures(data: dict[str, Any]) -> str:
    rows: list[str] = []
    for item in data["remaining_failures"]:
        rows.append(
            f"""
            <tr>
              <th scope="row"><code>{esc(item['case_id'])}</code></th>
              <td>{esc(item['summary'])}</td>
              <td><span class="pill {status_class(str(item.get('status', '')))}">{esc(item['status_label'])}</span></td>
            </tr>
            """
        )
    return "\n".join(rows)


def render_class_balance(data: dict[str, Any]) -> str:
    total = sum(int(v) for v in data["class_balance"].values())
    parts: list[str] = []
    for label, value in data["class_balance"].items():
        width = int(value) / total * 100
        parts.append(
            f'<span style="width:{width:.1f}%" title="{esc(label)}: {value}"></span>'
        )
    labels = ", ".join(f"{label} {value}" for label, value in data["class_balance"].items())
    return (
        f'<div class="stacked-bar" aria-label="Dataset mix: {esc(labels)}">'
        + "\n".join(parts)
        + "</div>"
    )


def render_improvement_levers(data: dict[str, Any]) -> str:
    levers = data.get("improvement_levers", [])
    if not levers:
        return ""
    rows: list[str] = []
    for item in levers:
        cls = status_class(str(item.get("status", "")))
        status_label = esc(item.get("status", "")) or "n/a"
        rows.append(
            f"""
            <tr>
              <th scope="row">{esc(item['lever'])}</th>
              <td>{esc(item['change'])}</td>
              <td>{esc(item['cluster'])}</td>
              <td>{esc(item['predicted_impact'])}</td>
              <td><span class="pill {cls}">{status_label}</span> {esc(item['measured'])}</td>
            </tr>
            """
        )
    body = "\n".join(rows)
    return f"""
    <section class="panel">
      <h2>Improvement Levers: Predicted vs Measured</h2>
      <p>Each shipped change maps to a standard improvement lever, the failure cluster it targeted, the impact predicted before the run, and the measured delta. The dominant cluster was post-retrieval citation mismatch, so most levers act after retrieval rather than on the index.</p>
      <table>
        <thead><tr><th>Lever</th><th>Change</th><th>Failure cluster targeted</th><th>Predicted</th><th>Measured</th></tr></thead>
        <tbody>{body}</tbody>
      </table>
      <p style="margin-top:12px;">Levers deliberately not pulled: retrieval tuning (retrieval recall@5 was already 1.000, so the bottleneck was post-retrieval, not the index) and model upgrade (deferred to a governed provider/model bakeoff gated on data-egress and cost).</p>
    </section>
"""


def render_failure_analysis(data: dict[str, Any]) -> str:
    per_scenario = data.get("per_scenario", [])
    distribution = data.get("failure_distribution", [])
    open_axial = data.get("open_axial", [])
    if not (per_scenario or distribution or open_axial):
        return ""
    ps_rows = "\n".join(
        f"""<tr><th scope="row">{esc(r['scenario_type'])}</th><td>{esc(r['support'])}</td>"""
        f"""<td><span class="pill {status_class(str(r.get('status', '')))}">{esc(r['task_pass'])}</span></td>"""
        f"""<td>{esc(r['citation_f1'])}</td><td>{esc(r['false_refusals'])}</td></tr>"""
        for r in per_scenario
    )
    max_runs = max((int(r["case_runs"]) for r in distribution), default=1) or 1
    dist_rows = "\n".join(
        f"""<div class="tool-row"><div><strong>{esc(r['category'])}</strong>"""
        f"""<span>{esc(r['case_runs'])} case-runs / {esc(r['distinct_cases'])} cases - {esc(r['kind'])}</span></div>"""
        f"""<div class="bar-track" aria-label="{esc(r['category'])} {esc(r['case_runs'])} case-runs">"""
        f"""<span class="bar-fill amber" style="width:{bar_width(float(r['case_runs']), float(max_runs))}"></span></div></div>"""
        for r in distribution
    )
    oa_rows = "\n".join(
        f"""<tr><th scope="row"><code>{esc(r['case'])}</code></th><td>{esc(r['open_code'])}</td><td>{esc(r['axial_code'])}</td></tr>"""
        for r in open_axial
    )
    return f"""
    <section class="grid-2">
      <div class="panel">
        <h2>Per-Scenario Breakdown</h2>
        <p>Support, 3-run task pass, teachable citation F1, and false refusals by scenario type. Every task failure is a false refusal; adversarial is perfect.</p>
        <table>
          <thead><tr><th>Scenario type</th><th>Support</th><th>Task pass</th><th>Citation F1</th><th>False refusals</th></tr></thead>
          <tbody>{ps_rows}</tbody>
        </table>
      </div>
      <div class="panel">
        <h2>Failure And Quality-Issue Distribution</h2>
        <p>Across three runs (120 case-runs). Over-conservative refusal is every task failure; citation-span mismatch is a quality issue where the case still passes.</p>
        {dist_rows}
      </div>
    </section>

    <section class="panel">
      <h2>Open-Code To Axial-Code Analysis</h2>
      <p>Per-failure qualitative coding: the observed open code grouped into an axial category. Synthetic case labels only.</p>
      <table>
        <thead><tr><th>Case</th><th>Open code (what went wrong)</th><th>Axial code (category)</th></tr></thead>
        <tbody>{oa_rows}</tbody>
      </table>
    </section>
"""


def render_production_monitoring(data: dict[str, Any]) -> str:
    monitoring = data.get("production_monitoring", [])
    if not monitoring:
        return ""
    rows = "\n".join(
        f"""
        <tr>
          <th scope="row">{esc(item['signal'])}</th>
          <td>{esc(item['metric'])}</td>
          <td>{esc(item['threshold'])}</td>
          <td>{esc(item['rationale'])}</td>
        </tr>
        """
        for item in monitoring
    )
    return f"""
    <section class="panel">
      <h2>Production Monitoring</h2>
      <p>Batch eval catches regressions before release; these are the live signals we would alert on for the grounded teach loop.</p>
      <table>
        <thead><tr><th>Signal</th><th>Metric</th><th>Alert threshold</th><th>Why</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
"""


def render_dashboard(data: dict[str, Any]) -> str:
    validate_public_snapshot(data)
    provenance = data["provenance"]
    title = esc(data["title"])
    metric_rows = render_metric_rows(data)
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f5f7fa;
      --panel: #ffffff;
      --text: #172033;
      --muted: #5d6b7c;
      --line: #dbe3ec;
      --teal: #2f6f73;
      --teal-soft: #e7f2ef;
      --amber: #9a5a16;
      --amber-soft: #fff2dc;
      --red: #a43f45;
      --red-soft: #fde8ea;
      --slate: #506274;
      --slate-soft: #eef3f7;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px 20px 42px; }}
    header {{
      display: grid;
      grid-template-columns: 1.5fr .8fr;
      gap: 18px;
      align-items: stretch;
      margin-bottom: 18px;
    }}
    section {{ margin-top: 18px; }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }}
    .eyebrow {{ color: var(--teal); font-size: 12px; font-weight: 760; letter-spacing: .08em; text-transform: uppercase; }}
    h1 {{ font-size: clamp(30px, 5vw, 56px); line-height: 1.02; margin: 8px 0 12px; letter-spacing: 0; }}
    h2 {{ font-size: 22px; margin: 0 0 12px; letter-spacing: 0; }}
    h3 {{ font-size: 17px; margin: 0 0 10px; letter-spacing: 0; }}
    p {{ margin: 0; color: var(--muted); }}
    .verdict {{ color: #26364a; font-size: 17px; max-width: 820px; }}
    .hero-meta {{ display: grid; gap: 10px; }}
    .meta-item {{ background: var(--slate-soft); border-radius: 8px; padding: 12px; }}
    .meta-item strong {{ display: block; color: var(--text); font-size: 20px; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .kpi {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; min-height: 154px; }}
    .kpi-label {{ color: var(--muted); font-size: 13px; font-weight: 700; }}
    .kpi-main {{ font-size: 33px; font-weight: 800; margin: 6px 0; letter-spacing: 0; }}
    .kpi-sub {{ display: flex; justify-content: space-between; gap: 8px; color: var(--muted); font-size: 13px; }}
    .kpi-sub strong {{ color: var(--text); }}
    .kpi p {{ margin-top: 10px; font-size: 13px; }}
    .status-win {{ border-color: #a8d1c7; background: var(--teal-soft); }}
    .status-held {{ border-color: #b8d1df; background: #eef7fa; }}
    .status-caveat {{ border-color: #edcf9b; background: var(--amber-soft); }}
    .status-risk {{ border-color: #efb8bd; background: var(--red-soft); }}
    .status-neutral {{ border-color: var(--line); background: var(--panel); }}
    .grid-2 {{ display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(320px, .9fr); gap: 18px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 10px 8px; text-align: left; vertical-align: top; }}
    th {{ color: #243246; }}
    td {{ color: var(--muted); }}
    .pill {{ display: inline-flex; border: 1px solid currentColor; border-radius: 999px; padding: 2px 8px; font-size: 12px; font-weight: 760; }}
    .bar-track {{ height: 10px; background: #e6edf3; border-radius: 999px; overflow: hidden; min-width: 90px; }}
    .bar-fill {{ display: block; height: 100%; background: var(--teal); border-radius: inherit; }}
    .bar-fill.amber {{ background: var(--amber); }}
    .tool-row {{ display: grid; grid-template-columns: minmax(180px, .8fr) 1fr; gap: 12px; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--line); }}
    .tool-row strong, .tool-row span {{ display: block; }}
    .tool-row span {{ color: var(--muted); font-size: 13px; }}
    .mini-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .mini-card {{ border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
    .mini-card strong, .mini-card span {{ display: block; }}
    .mini-card span {{ font-size: 24px; font-weight: 780; color: var(--text); margin: 3px 0; }}
    .mini-card p {{ font-size: 13px; }}
    .stacked-bar {{ display: flex; height: 14px; overflow: hidden; border-radius: 999px; background: var(--slate-soft); margin-top: 12px; }}
    .stacked-bar span:nth-child(1) {{ background: var(--teal); }}
    .stacked-bar span:nth-child(2) {{ background: #5a7d96; }}
    .stacked-bar span:nth-child(3) {{ background: var(--amber); }}
    .stacked-bar span:nth-child(4) {{ background: var(--red); }}
    code {{ background: var(--slate-soft); border-radius: 5px; padding: 2px 5px; color: #243246; }}
    .perspectives {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .note-list {{ margin: 0; padding-left: 20px; color: var(--muted); }}
    footer {{ color: var(--muted); font-size: 13px; margin-top: 22px; }}
    a {{ color: var(--teal); }}
    @media (max-width: 840px) {{
      main {{ padding: 18px 12px 28px; }}
      header, .grid-2, .perspectives {{ grid-template-columns: 1fr; }}
      .kpi-grid, .mini-grid {{ grid-template-columns: 1fr; }}
      .tool-row {{ grid-template-columns: 1fr; }}
      table {{ font-size: 13px; }}
      th, td {{ padding: 8px 5px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div class="panel">
        <div class="eyebrow">GenAcademy Coach / Week-4 Eval</div>
        <h1>{title}</h1>
        <p class="verdict">{esc(data['hero']['verdict'])}</p>
      </div>
      <aside class="panel hero-meta" aria-label="Dashboard provenance">
        <div class="meta-item"><span>Snapshot</span><strong>{esc(provenance['snapshot_date'])}</strong></div>
        <div class="meta-item"><span>Dataset</span><strong>40 cases</strong>{render_class_balance(data)}</div>
        <div class="meta-item"><span>Model</span><strong>{esc(provenance['model_id'])}</strong></div>
      </aside>
    </header>

    <section class="kpi-grid" aria-label="Key metrics">
      {render_kpis(data)}
    </section>

    <section class="grid-2">
      <div class="panel">
        <h2>Baseline vs Current Mean</h2>
        <p>Current is the mean of three full current-main runs. Task baseline excludes two infra errors; current runs had no infra exclusions.</p>
        <table>
          <thead><tr><th>Metric</th><th>Baseline</th><th>Current</th><th>Delta</th><th>Readout</th></tr></thead>
          <tbody>{metric_rows}</tbody>
        </table>
      </div>
      <div class="panel">
        <h2>Three-Run Variance</h2>
        <p>N=3 runs. Use this as a stability lens, not a population estimate.</p>
        <table>
          <thead><tr><th>Run</th><th>Citation F1</th><th>Task</th><th>Refusal P</th><th>Turn p95</th><th>Latency</th></tr></thead>
          <tbody>{render_run_rows(data)}</tbody>
        </table>
      </div>
    </section>

    {render_improvement_levers(data)}

    <section class="grid-2">
      <div class="panel">
        <h2>Latency And Tool Attribution</h2>
        <p>Measured total tool time per full run is dominated by check generation and retrieval. Turn latency still includes model inference around these calls.</p>
        {render_tool_latency(data)}
      </div>
      <div class="panel">
        <h2>Quality And Safety Guardrails</h2>
        <div class="mini-grid">{render_guardrails(data)}</div>
      </div>
    </section>

    {render_failure_analysis(data)}

    {render_production_monitoring(data)}

    <section class="grid-2">
      <div class="panel">
        <h2>Remaining Failure Modes</h2>
        <p>Case IDs are synthetic scenario labels. They carry no learner text and no corpus text.</p>
        <table>
          <thead><tr><th>Case</th><th>What remains</th><th>Status</th></tr></thead>
          <tbody>{render_failures(data)}</tbody>
        </table>
      </div>
      <div class="panel">
        <h2>User And Builder Perspective</h2>
        <div class="perspectives">
          <article>
            <h3>User view</h3>
            <p>{esc(data['perspectives']['user'])}</p>
          </article>
          <article>
            <h3>Builder view</h3>
            <p>{esc(data['perspectives']['builder'])}</p>
          </article>
        </div>
      </div>
    </section>

    <section class="panel">
      <h2>Evidence And Caveats</h2>
      <ul class="note-list">
        {"".join(f"<li>{esc(note)}</li>" for note in data["notes"])}
      </ul>
    </section>

    <footer>
      snapshot_date: {esc(provenance['snapshot_date'])} /
      dataset_version: {esc(provenance['dataset_version'])} /
      generator_git_sha: {esc(provenance['generator_git_sha'])} /
      source: <a href="week4-eval-progress-handoff.md">docs/week4-eval-progress-handoff.md</a>
    </footer>
  </main>
</body>
</html>
"""
    html_text = "\n".join(line.rstrip() for line in html_text.splitlines()) + "\n"
    validate_public_snapshot(html_text)
    return html_text


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
    data_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    html_text = render_dashboard(data)
    out_path = root / args.out
    out_path.write_text(html_text, encoding="utf-8")
    if args.write_private_appendix:
        write_private_appendix(data, repo_root=root)
    print(out_path)


if __name__ == "__main__":
    main()
