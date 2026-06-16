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
        print(
            f"turn {row['turn']}: {row['next_action']} / {row['strategy']} "
            f"evidence={row['evidence_score']:.2f} {row['evidence_band']} citations={citations}"
        )
        print(f"  {row['learner_message']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace_path", type=Path)
    args = parser.parse_args()
    print_trace(args.trace_path)


if __name__ == "__main__":
    main()
