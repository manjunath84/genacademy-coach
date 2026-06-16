# Teach Loop Threshold Calibration

Date: 2026-06-16

## Decision

Set the default Coach STOP threshold to `0.40`.

The initial `0.60` value was a seed threshold from the design phase. After ingesting the expanded,
transcript-heavy Coach corpus, seed/dev diagnostics showed that `0.60` filtered out many plausible
course questions after retrieval. A calibrated `0.40` default preserves the grounded-or-refuse guardrail
while recovering useful teach-loop coverage.

## Calibration Evidence

Command:

```bash
set -a; source .env; set +a
uv run python scripts/calibrate_teach_threshold.py \
  --seed-limit 20 \
  --dev-limit 10 \
  --json-out eval/runs/teach-threshold-calibration.json
```

Observed, redacted:

- Positive scenarios: `30` total (`20` seed, `10` dev).
- Non-private negative controls: `10` total.
- Negative-control max score: `0.3809`.
- At threshold `0.40`:
  - dev positives at or above STOP: `9/10`
  - seed positives at or above STOP: `15/20`
  - negative controls at or above STOP: `0/10`
- At threshold `0.60`:
  - dev positives at or above STOP: `1/10`
  - seed positives at or above STOP: `4/20`
  - negative controls at or above STOP: `0/10`

No held-out `test` split items were used. No raw eval question text or corpus snippets were printed or
written by the calibration payload.

## Live Dev Eval Check

Command:

```bash
set -a; source .env; set +a
GENACADEMY_PROVIDER=nebius GENACADEMY_COACH_STOP_THRESHOLD=0.40 \
  uv run python scripts/eval_teach_loop.py \
    --split dev \
    --limit 10 \
    --json-out eval/runs/teach-loop-dev-threshold-040.json
```

Observed, redacted:

- Overall: `3/10` passed, `pass_rate=0.3`.
- Teachable subset: `3/8` passed, `teachable_pass_rate=0.375`.
- Safe refusals: `2`.
- Retrieval coverage: `8` scenarios with spans, `2` without spans.
- Score bands: `8` confirm, `0` proceed, `2` stop.

This confirms the threshold change addresses the retrieval-coverage bottleneck but does not finish the
MVP demo. The next bottleneck is teach-loop behavior on recovered scenarios:

- `grade_not_correct`: `3`
- `missing_strategy_change`: `3`
- `missing_runtime_decision_trace`: `3`
- `citation_ids_not_resolved`: `1`

## Next Step

Keep `0.40` as the calibrated default and continue by fixing teach-loop behavior on the recovered
teachable scenarios. Do not lower the threshold further without adding stronger non-private negative
controls and re-running calibration.
