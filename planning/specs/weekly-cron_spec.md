---
name: Weekly Cron for automaticYoutube Pipeline
description: Schedule the existing automaticYoutube.py pipeline to run every Sunday so weekly insights land in Supabase without manual invocation.
type: spec
---

# Weekly Cron — Spec

## Goal
Run `app/scripts/automaticYoutube.py` automatically once a week so the
three category runs (Games, Science & Tech, How-to & Style) populate
`automatic_table` and the Insights page stays fresh without a human in
the loop.

## Scope
- In:
  - A scheduled trigger that fires every Sunday and invokes the pipeline
    for all three categories in a single run.
  - A single callable entrypoint (the current `__main__` only runs
    HOW_TO_STYLE, with the other two commented out).
  - Secrets/env handling for the scheduler context.
- Out:
  - Manual `/analyze/youtube` flow (separate path, no Supabase write).
  - App Store reviews (no automated weekly job exists for them yet).
  - Backfill of historical data.

## Decisions

### Scheduler: GitHub Actions scheduled workflow
A `.github/workflows/weekly-youtube.yml` with `on: schedule: cron` runs
the pipeline on GitHub-hosted runners. Secrets via Actions secrets, logs
in the Actions tab. Chosen over OS cron, cloud-scheduler-on-deploy-target,
in-process APScheduler, and Supabase pg_cron because the deploy target
is not yet pinned and the pipeline is a self-contained Python script —
keeping the schedule decoupled from the API host means we can move the
API later without touching the cron. Trade-off accepted: Actions cron
can drift ~15min and may skip runs under platform load; acceptable for a
weekly job.

### Entrypoint: `ops/scripts/weeklyYoutube.py`
A new thin wrapper script that imports `youtube_automatic` from
`app/scripts/automaticYoutube.py` and invokes it once per category
(Games, Science & Tech, How-to & Style) using the existing prompt /
keyword / category-ID pairings. The Action runs
`python -m ops.scripts.weeklyYoutube`. Exit code propagates so failures
turn the run red. Chosen over editing `automaticYoutube.py`'s `__main__`
because it preserves the `/app` = pure pipeline vs `/ops` = orchestration
boundary already documented in `ops/CONTEXT.md`. The existing `__main__`
in `automaticYoutube.py` stays as a developer-only single-category
smoke-test.

### Schedule: `0 8 * * 0` (Sundays, 08:00 UTC)
GitHub Actions cron is UTC-only. 08:00 UTC = 04:00 EDT / 03:00 EST in
America/Toronto, so the run completes overnight local time and results
are in Supabase before Monday morning. Sunday is fully elapsed in
NA/Europe by then, so the YouTube trending snapshot reflects a full
Sunday of activity. Off-peak window minimises GitHub runner queue
delays. **Do not rewrite to local time** — DST will shift the local-time
view by ±1hr twice a year; this is expected and accepted, not a bug to
fix.

### Failure handling: per-category isolation + default GitHub email
The wrapper script wraps each of the three category invocations in
`try/except`, logs the exception with category name, and continues to
the next category. The script exits 1 if any category raised (so the
Action turns red and GitHub's built-in scheduled-workflow failure email
fires to the repo owner), exits 0 otherwise. Per-video isolation is
explicitly **not** added — a category that fails on every video should
fail loudly, not silently skip. Manual re-runs are already idempotent
via the existing `check_youtube_id` skip in
`app/scripts/automaticYoutube.py:17`, so re-triggering the workflow on
the same Sunday is safe. No Slack/Discord alerting in v1 — revisit only
if the email channel proves too quiet.

### Secrets and runner
Repository secrets (not environment secrets — an approval gate would
block the unattended run): `YOUTUBE_API`, `OPENAI_KEY`, `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`. `LOG_LEVEL` is a literal `INFO` in the
workflow file, not a secret. Workflow declares
`permissions: contents: read` (least privilege on `GITHUB_TOKEN`; the
job only reads code and writes to Supabase via the service-role key).
Runner pinned to `ubuntu-24.04`, not `ubuntu-latest`, to avoid silent
runner-image drift on a job nobody watches week-to-week.

**Public-repo constraint (load-bearing).** This repo is public. Forked
PRs cannot read secrets, so the scheduled run is safe. However, **any
future workflow added to this repo that triggers on `pull_request`
(rather than `pull_request_target`) and runs untrusted code with access
to secrets would leak the Supabase service-role key.** Future workflow
authors must either (a) avoid exposing secrets to PR-triggered jobs, or
(b) move to a narrower Supabase key with RLS-enforced inserts. Re-open
this decision the moment a second workflow is added.

### Manual trigger: `workflow_dispatch`, no inputs
The workflow declares both `on: schedule:` and `on: workflow_dispatch:`,
giving a "Run workflow" button in the Actions UI for off-schedule runs
(testing, recovering a failed Sunday, demos). Manual runs use the same
runner image, secrets, and entrypoint as scheduled runs, so behaviour
is identical. No per-category input in v1 — re-running all three is
cheap thanks to the existing `check_youtube_id` skip; revisit only if
real failed-Sunday recoveries make the full re-run noticeably wasteful.

### Python environment: pinned `requirements.txt` + Python 3.11
Generate `requirements.txt` from the current `venv/` (`pip freeze`),
commit it at the repo root, and the workflow installs with
`pip install -r requirements.txt`. Python pinned to `3.11` via
`actions/setup-python@v5` with `cache: pip` so weekly cold-starts stay
fast. Chosen over an inline package list in the YAML so the workflow
file and any future deploy target share a single source of truth for
dependencies. **Prerequisite work** for this feature: produce
`requirements.txt` from the venv before the workflow can be merged —
treat as part of the spec's deliverables, not a follow-up.

### Cost & quota controls
- **Hard cap: 5 videos per category per run.** Enforced in
  `ops/scripts/weeklyYoutube.py` by slicing the list returned from
  `getMostPopularVideos` before passing it to `youtube_automatic`.
  Keeps the cap as an orchestration concern; `automaticYoutube.py`
  stays unaware of it. 5 × 3 categories = 15 OpenAI calls/run, ~$1.50
  weekly envelope, well inside YouTube's 10k/day quota.
- **Job timeout: `timeout-minutes: 30`** in the workflow. Normal run is
  ~5–15 min; 30 leaves headroom while bounding a stuck OpenAI call so a
  hang turns the run red instead of running for hours.
- **OpenAI billing hard limit** set in the OpenAI dashboard (suggested
  $25/month). Out-of-band of this workflow but recorded as a deploy
  checklist item in `ops/deploy/checklist.md`.

### Downstream-consumer context (not in this spec's scope)
The Insights page will switch from a weekly view to a **monthly rollup**
under a separate spec. The cron stays weekly — `automaticYoutube` runs
every Sunday as designed here — and the display layer aggregates the
last ~4 Sundays. This affects nothing in the cron, but informs sizing:
the weekly 5-per-category cap is the right knob to tune if monthly
volume turns out to be too thin or too noisy, since it directly drives
how many rows accumulate per month.

### Observability
- **`print` stays for v1.** Existing pipeline code uses `print` heavily;
  converting to `logging` is a cross-cutting refactor that doesn't
  belong in this spec. Tracked as a separate future cleanup.
- **`LOG_LEVEL` removed from the required env vars** in
  `ops/CONTEXT.md` — the code never reads it, so listing it as required
  is misleading. Re-add when the `logging` migration happens.
- **Per-run job summary via `$GITHUB_STEP_SUMMARY`.**
  `ops/scripts/weeklyYoutube.py` (when running under Actions, i.e.
  when the env var is set) appends a Markdown block listing each
  category with ✅/❌, video count, skipped count
  (`check_youtube_id` hits), and zero-problem count. Visible on the
  run's summary page without expanding the log.

### Concurrency: queue, don't cancel
Workflow declares
`concurrency: { group: weekly-youtube, cancel-in-progress: false }`.
A second invocation (typically a manual retry while the scheduled run
is in-flight) waits for the first to finish instead of running in
parallel or cancelling it. Reasons:
- The pipeline has no transactional rollback; cancelling mid-run leaves
  Supabase in a partial state and OpenAI calls already in flight still
  bill regardless.
- Without a concurrency guard, two overlapping runs would
  double-process unprocessed videos (`check_youtube_id` only protects
  already-written rows), wasting OpenAI spend and YouTube quota.
- Queue cost is bounded at 30min by the job timeout, so the manual
  retry is never stuck waiting indefinitely.

## Verification

Pre-merge dry-run: push the workflow on a feature branch, trigger via
`workflow_dispatch` against that branch with the real production
secrets. This exercises the exact runner/secret/install/code path the
Sunday run will use. Writes go to the real `automatic_table`; this is
acceptable because `check_youtube_id` makes the eventual scheduled run
a no-op on those rows.

Post-merge: manually trigger the workflow once on `master` before the
first scheduled Sunday so the first cron firing isn't also the first
real run.

## Acceptance

- [x] `requirements.txt` produced from current `venv/` and committed at
      repo root.
- [x] `ops/scripts/weeklyYoutube.py` exists and runs all 3 categories.
      The 5/category cap is enforced upstream by `getMostPopularVideos`
      (`maxResults=5`); no slice in the wrapper.
- [x] `.github/workflows/weekly-youtube.yml` exists with: `on: schedule`
      (`0 8 * * 0`) + `on: workflow_dispatch`,
      `permissions: contents: read`, `concurrency` group with
      `cancel-in-progress: false`, `timeout-minutes: 30`,
      `actions/setup-python@v5` pinned to 3.14 with `cache: pip`,
      runner pinned to `ubuntu-24.04`. (Pinned 3.14 not 3.11 to match
      the venv the requirements were frozen from.)
- [x] Branch dry-run via `workflow_dispatch` produced a green Action.
- [x] Per-category failure isolation verified (deliberately break one
      category locally — e.g. invalid prompt or bad category id — and
      confirm the wrapper continues to the next, exits 1 at the end).
- [x] Post-merge manual `workflow_dispatch` on `master` succeeds before
      the first scheduled Sunday.
- [ ] First scheduled Sunday at 08:00 UTC lands rows in `automatic_table`
      for all 3 categories.
- [x] OpenAI dashboard hard-cap (~$25/month) configured; deploy
      checklist updated to reference it.
