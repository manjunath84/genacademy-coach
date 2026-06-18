from __future__ import annotations

import argparse
import json
from pathlib import Path


def print_trace(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        citations = ", ".join(row.get("retrieved_citation_ids", [])) or "none"
        tools = ", ".join(row.get("tool_calls", [])) or "none"
        faithful = row.get("faithfulness_ok")
        faithful_label = "unknown" if faithful is None else str(bool(faithful)).lower()
        print(
            f"turn {row['turn']}: {row['next_action']} / {row['strategy']} "
            f"evidence={row['evidence_score']:.2f} {row['evidence_band']} "
            f"faithful={faithful_label}"
        )
        print(
            f"  session={row.get('session_id', 'unknown')} "
            f"topic_hash={row.get('topic_hash', 'unknown')} "
            f"learner_input_hash={row.get('learner_input_hash', 'unknown')}"
        )
        print(f"  citations={citations}")
        print(f"  tools={tools}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace_path", type=Path)
    args = parser.parse_args()
    print_trace(args.trace_path)


if __name__ == "__main__":
    main()
