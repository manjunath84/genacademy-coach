from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from genacademy_coach.eval_golden import load_golden_cases
from genacademy_coach.eval_metrics import PriceTable
from genacademy_coach.eval_runner import run_golden_eval
from genacademy_coach.foundation import Foundation
from genacademy_coach.settings import CoachSettings
from genacademy_coach.teach_agent import DEFAULT_NEBIUS_MODEL


def load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_path, override=False)


def _env_price_per_token(name: str) -> float:
    raw = os.environ.get(name, "0")
    return float(raw or "0") / 1_000_000


def price_table_for_model(model_id: str) -> PriceTable:
    return PriceTable(
        prices={
            model_id: (
                _env_price_per_token("GENACADEMY_NEBIUS_INPUT_USD_PER_1M"),
                _env_price_per_token("GENACADEMY_NEBIUS_OUTPUT_USD_PER_1M"),
            )
        }
    )


def main() -> None:
    load_local_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="baseline")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    settings = CoachSettings.from_env()
    foundation = Foundation.build(settings)
    cases = load_golden_cases(settings.eval_dir / "golden" / "golden_cases.jsonl")
    if args.limit is not None:
        cases = cases[: args.limit]
    model_id = foundation.rag_settings.gen_model or DEFAULT_NEBIUS_MODEL
    result = run_golden_eval(
        settings=settings,
        foundation=foundation,
        cases=cases,
        tag=args.tag,
        price_table=price_table_for_model(model_id),
    )
    print(
        json.dumps(
            {
                "output_path": result["output_path"],
                "n": result["n"],
                "metrics": result["metrics"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
