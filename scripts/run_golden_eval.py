from __future__ import annotations

import argparse
import json
import os
import sys
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


def warn_if_zero_prices(price_table: PriceTable) -> None:
    if all(
        input_price == 0.0 and output_price == 0.0
        for input_price, output_price in price_table.prices.values()
    ):
        print(
            "warning: cost_usd will be 0 because GENACADEMY_NEBIUS_INPUT_USD_PER_1M "
            "and GENACADEMY_NEBIUS_OUTPUT_USD_PER_1M are unset or zero",
            file=sys.stderr,
        )


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def validate_langsmith_eval_egress(cases) -> None:
    if not _env_truthy("LANGSMITH_TRACING"):
        return
    project = os.environ.get("LANGSMITH_PROJECT", "")
    if project != "genacademy-coach-week4-eval":
        raise SystemExit(
            "LANGSMITH_TRACING is enabled; set LANGSMITH_PROJECT=genacademy-coach-week4-eval "
            "for the approved private eval workspace"
        )
    if not _env_truthy("GENACADEMY_LANGSMITH_EVAL_EGRESS_OK"):
        raise SystemExit(
            "LANGSMITH_TRACING is enabled; set GENACADEMY_LANGSMITH_EVAL_EGRESS_OK=true "
            "to confirm intentional private seed/dev eval egress"
        )
    test_cases = [case.case_id for case in cases if getattr(case, "split", None) == "test"]
    if test_cases:
        raise SystemExit("refusing to trace frozen test cases: " + ", ".join(test_cases))
    cloud_safe_count = sum(1 for case in cases if case.cloud_safe)
    splits = sorted({str(case.split) for case in cases})
    print(
        "LangSmith eval tracing enabled: "
        f"project={project}, cases={len(cases)}, splits={','.join(splits)}, "
        f"cloud_safe={cloud_safe_count}, raw_private_text_may_trace=true",
        file=sys.stderr,
    )


def select_cases(cases, *, cloud_safe_only: bool = False, limit: int | None = None):
    selected = list(cases)
    if cloud_safe_only:
        selected = [case for case in selected if case.cloud_safe]
        if not selected:
            raise SystemExit("--cloud-safe-only selected 0 golden cases; refusing to run")
        splits = sorted({str(case.split) for case in selected})
        print(
            "cloud-safe golden eval enabled: "
            f"cases={len(selected)}, splits={','.join(splits)}",
            file=sys.stderr,
        )
    if limit is not None:
        selected = selected[:limit]
    if not selected:
        raise SystemExit("selected 0 golden cases; refusing to run")
    return selected


def main() -> None:
    load_local_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="baseline")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--cloud-safe-only",
        action="store_true",
        help="Run only golden cases explicitly marked cloud_safe.",
    )
    args = parser.parse_args()

    settings = CoachSettings.from_env()
    foundation = Foundation.build(settings)
    golden_cases_path = settings.eval_dir / "golden" / "golden_cases.jsonl"
    cases = load_golden_cases(golden_cases_path)
    cases = select_cases(
        cases,
        cloud_safe_only=args.cloud_safe_only,
        limit=args.limit,
    )
    validate_langsmith_eval_egress(cases)
    model_id = foundation.rag_settings.gen_model or DEFAULT_NEBIUS_MODEL
    price_table = price_table_for_model(model_id)
    warn_if_zero_prices(price_table)
    result = run_golden_eval(
        settings=settings,
        foundation=foundation,
        cases=cases,
        tag=args.tag,
        run_id=args.run_id,
        price_table=price_table,
        golden_cases_path=golden_cases_path,
    )
    print(
        json.dumps(
            {
                "output_path": result["output_path"],
                "run_id": result["run_id"],
                "n": result["n"],
                "metrics": result["metrics"],
                "anchor_counterfactual": result["anchor_counterfactual"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
