# Eval seed set (PRD §7.9 / slice 3 §4)

Five hand-labelled ideas, one per category (consumer-app, mobile-game,
creator-tool, productivity, low-signal), drawn from the pre-flight validation set
([planning/prototypes/preflight/](../../../planning/prototypes/preflight/)). The
harness scores a real pipeline run against these labels.

## File format

```json
{
  "idea": "note-taking app with better offline sync",
  "target_gap": null,
  "category": "consumer-app",
  "expected_gaps": [
    { "gap": "offline sync silently drops edits", "severity_range": [4, 5] }
  ]
}
```

- `idea` / `target_gap` — fed straight into `POST /runs`-equivalent pre-flight.
- `category` — the seed-set bucket (operator metadata), **not** the LLM-derived
  pre-flight category.
- `expected_gaps[].gap` — the labelled pain text the gap-recall matcher scores
  against output gap texts (fuzzy token-set, threshold pinned in `metrics.py`).
- `expected_gaps[].severity_range` — `[lo, hi]` the labeller expects; recorded in
  the report for manual review. (Run-level severity calibration is scored from
  `quality_signals.severity_distribution`, not per-gap.)

## Labelling is a human task

Per spec §4 the labels themselves are authored/maintained by the owner. The gaps
checked in here are **starter labels** — review and refine them against real
output before treating a report's recall number as meaningful.

## Run

```
python -m app.eval.harness consumer_app
```

writes `app/eval/reports/consumer_app.json`.
