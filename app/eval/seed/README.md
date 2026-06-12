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
  "label_status": "agent_drafted",
  "expected_gaps": [
    { "gap": "offline sync silently drops edits", "severity_range": [4, 5] }
  ]
}
```

- `idea` / `target_gap` — fed straight into `POST /runs`-equivalent pre-flight.
- `category` — the seed-set bucket (operator metadata), **not** the LLM-derived
  pre-flight category.
- `label_status` — `"agent_drafted"` (default) or `"human_reviewed"`. Records who
  authored the labels; copied into every report so a recall number is never read
  without knowing whether its labels are vetted. See below.
- `expected_gaps[].gap` — the labelled pain text the gap-recall matcher scores
  against output gap texts (fuzzy token-set, threshold pinned in `metrics.py`).
- `expected_gaps[].severity_range` — `[lo, hi]` the labeller expects; recorded in
  the report for manual review. (Run-level severity calibration is scored from
  `quality_signals.severity_distribution`, not per-gap.)

## Labelling is a human task — these labels are agent-drafted

Per spec §4 the labels themselves are authored/maintained by the owner. The five
files checked in here were **drafted by the agent** from the pre-flight validation
set ([findings.md](../../../planning/prototypes/preflight/findings.md)) and are
flagged `"label_status": "agent_drafted"` — pending human confirmation. They are
starter labels: review and refine each `expected_gaps` list against real pipeline
output, then flip the field to `"human_reviewed"`, before treating a report's
recall number as meaningful. An unmarked file defaults to `agent_drafted` so a
vetted seed must be marked explicitly.

The idea per category is drawn from the validation set: consumer-app =
note-taking (#1), productivity = habit tracker (#2), mobile-game = roguelike
deckbuilder (#7), creator-tool = short-form video editor (#12), low-signal =
prompt-manager tool (#14, correctly graded low-signal there).

## Run

```
python -m app.eval.harness consumer_app
```

writes `app/eval/reports/consumer_app.json`.
