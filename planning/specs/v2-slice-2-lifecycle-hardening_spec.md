# v2 Slice 2 — Lifecycle Hardening (Safe to Expose)

| | |
|---|---|
| **Status** | Draft |
| **Created** | 2026-06-02 |
| **Owner** | John Lowen David |
| **Parent** | [PRD v2.2](../../docs/PRD.md) |
| **Slice** | 2 of 3 (slice 1 = end-to-end happy path ✅; slice 3 = eval + v1 removal) |
| **Goal** | Take the slice-1 tracer bullet and make it safe to put in front of a real, untrusted user — every sad path in PRD §6/§8 is handled, feedback/report close the loop, and runs live at shareable URLs. |

---

## 1. Purpose of This Slice

Slice 1 proved the v2 *shape* works: an idea goes in, grounded gaps come out, every PRD layer ran once on the happy path. It is explicitly **not shippable** — a single flaky API call fails the whole run, a server restart strands a `running` row forever, there are no rate limits or budget cap, the feedback loop (§4 leading indicators) is never written, and runs can't be bookmarked or shared.

Slice 2 closes exactly that gap. The bar is: **the moment a real user — not the developer — touches the system, nothing here is missing.** Concretely that means PRD §6 sad paths US-S1…US-S7 are handled, the §8 non-functional requirements (rate limiting, budget cap, partial completion, restart transition) hold, the §4 indicators are actually collected, and the §7.6 frontend controls (thumbs-up, direction prompt, report link, My Runs) exist on routed, shareable pages.

This slice is **corrective and additive over slice 1, not a rewrite.** The pipeline internals (extraction, synthesis, grounding validation, model routing) are settled. What changes is the *envelope* around them: retries, thresholds, guards, the feedback/report tables and endpoints, and the client router.

What this slice is **not**: the evaluation harness, `quality_signals`, or removal of the legacy v1 surface — those are slice 3 (see §3).

## 2. What Ships in This Slice

**Reliability hardening (PRD §8):**
- **Source retry-with-backoff:** each source retries once with exponential backoff on failure (PRD §7.3, §8).
- **Partial-completion threshold:** ≥70% of sources succeeding → `done` + `partial_sources` banner naming the failures; below 70% → `failed` (US-S3). Populates `partial_sources_json`.
- **Server-restart → `failed`:** a row left `running` with no live in-memory job transitions to `failed` with `failure_reason: server_restart` on next read (US-S4).
- **`failure_reason` promoted to an enum** (slice-1 open question #3): `{ server_restart, budget_exhausted, sources_below_threshold, internal_error }`.

**Abuse / cost guards (PRD §8):**
- **Per-IP rate limiter:** 3 runs/hour, 10 runs/day → `429 rate_limited` with `Retry-After` (US-S6).
- **Daily OpenAI budget cap:** env-configurable spend ceiling; `POST /runs` returns `429 budget_exhausted` when exhausted (US-S5).
- **Concurrency guard:** single active run per server instance; a second concurrent submission returns `429 busy` with `Retry-After` (PRD §8; queue UX stays v1.1).

**Feedback & report loop (PRD §4, §7.6, §9):**
- **`POST /runs/:id/feedback`** — append-only write to `feedback_events` (the table created-but-unwritten in slice 1). Valid only when `done`. Records the three §4 indicators.
- **`POST /runs/:id/report`** — hides the run (`reported`, admin-hidden), sets `reported_at`, queues for admin review (US-S7).
- New terminal-ish state **`reported`** in the lifecycle; `GET /runs/:id` and `GET /runs` exclude reported runs from the public view.

**Sad-path pre-flight (PRD §6):**
- **US-S1 (zero competitors):** pre-flight returning 0 candidates surfaces a "No public sources found" state with the option to paste competitor URLs, instead of producing an unrunnable `preflight_ready`.
- **US-S2 (low-signal ack):** already enforced server-side in slice 1; slice 2 keeps the gate and ensures the routed New Run page renders it.

**Frontend (PRD §7.6) — router first, then the new controls:**
- **`react-router-dom` migration** (ADR [2026-06-01](../decisions/2026-06-01-frontend-routing-state-vs-router.md)): real routes `/`, `/runs/new`, `/runs/:id` replace the `currentPage` + `activeRunId` state nav. Done **first**, before the controls below, so the new UI is built once on routed pages. Delivers US-4 (leave/return via URL) and US-5 (share).
- **Thumbs-up control** per gap → `POST /runs/:id/feedback` (`new_to_me_gap_ids`).
- **Direction prompt** after the gap list (continue / shift / drop / need more research) — non-blocking, dismissible → feedback.
- **"Report this run"** link → `POST /runs/:id/report`.
- **`partial_sources` banner** on the Result page, naming failed sources.
- **My Runs** page — frontend-only filter of the public feed against `localStorage` `run_id`s.

## 3. Out of Scope (Deferred to Slice 3)

**Deferred to slice 3 (eval + cleanup):**
- Eval harness + 5-idea seed set (PRD §7.9).
- `quality_signals` field (PRD §7.9) — quote-source diversity, severity distribution, single-source gap count, extraction yield.
- Removal of `/analyze/youtube`, `/analyze/appStore`, the weekly jobs, `automatic_table*`, and the unlinked v1 frontend pages. They stay mounted through slice 2; slice 3 deletes them (and the residual `currentPage` switch the router replaces).
- ADRs for any slice-2 decisions whose shape is still settling.

**Pre-flight robustness (deferred from the slice-2 review of `preflight_service.run`):**
- **`generate_queries` output validation.** `generate_queries` returns a raw `json.loads` dict with no Pydantic model. Missing `category` / `signal_strength` / `signal_reasoning` raises a bare `KeyError` out of `preflight_service.run`, while missing query lists silently degrade via `.get(..., [])` — an undocumented asymmetry. Slice 3 wraps the LLM response in a schema so a malformed grade maps to a clean `internal_error` (§5.3) instead of a `KeyError`. Folds naturally into the slice-3 `signal_strength`-**gate** rework (PRD §15 note), which already changes how that grade is consumed.
- **Pre-flight latency / fan-out parallelization.** `preflight_service.run` runs its two source fan-outs (App Store, YouTube) and the 2–3 searches within each *sequentially*, inside the synchronous request. Accepted as ≤10s for slice 2 (§6, open question #2). Slice 3 may parallelize the independent search I/O (`asyncio.gather`) **only if** the ≤10s budget is breached — an optimization, no behaviour change.
- **Orphaned `pending` on pre-flight failure — _pull-forward candidate to slice 2._** `create_run` writes a `pending` row, then calls the synchronous `preflight_service.run` with no `try/except`; a pre-flight LLM/network exception strands the row at `pending` forever. Slice 2's restart contract (§5.2) only reconciles `running` rows, and slice 2 builds the `internal_error` reason (§5.3) but never wires it to the synchronous pre-flight path. **Because a real user hits pre-flight pre-approve, this is arguably in-scope for slice 2's "nothing missing" bar (§1) — flagged for the author to confirm placement before slice 2 closes.** If kept here, slice 3 wraps `create_run`'s pre-flight call so a failure transitions the row to `failed` + `failure_reason: internal_error` instead of stranding it.

**Admin tooling for reported runs is out of scope.** `report` hides the row and stamps `reported_at`; the actual admin restore/hard-delete workflow (a queue, an auth'd admin surface) is **not** built here. Review is manual against the table. Naming an admin UI as a deliverable would pull in the auth that PRD §5 explicitly defers.

**Queue UX with ETA** stays v1.1 (PRD §15). Slice 2 ships the blunt `429 busy`, not accept-and-queue.

**Hard out of scope:** anything in PRD §12 (RAG, accounts, additional sources, real-time, public API), and per-run engagement-filter tuning.

## 4. Data Model Changes (slice 2)

All three tables already exist (slice 1 migration). Slice 2 **writes** `feedback_events` and **populates** two columns left empty in slice 1. No new tables; one small additive migration if any column is missing.

```
idea_runs  (existing — slice 2 starts writing these)
  partial_sources_json (jsonb, nullable)   -- { failed:[{source,name,reason}], succeeded_count, total_count }
  reported_at (timestamptz, nullable)        -- set by POST /runs/:id/report
  status enum gains 'reported'               -- pending|preflight_ready|running|done|failed|reported
  failure_reason                             -- now constrained to the §2 enum set

feedback_events  (created in slice 1; FIRST WRITES in slice 2)
  id (uuid, pk)
  run_id (uuid, fk → idea_runs.id)
  submitted_at (timestamptz)
  new_to_me_gap_ids_json (jsonb, nullable)
  direction (text, nullable)                 -- continue | shift | drop | need_more_research
  time_saved_estimate_minutes (int, nullable)
  -- APPEND-ONLY: never updated or deleted (PRD §9). Multiple rows per run allowed.
```

**Rate-limit + budget counters** are operational state, not run data. Slice 2 keeps them out of the run tables:
- Per-IP counters: in-process for v1 (single instance, PRD §8). A small TTL-bucketed counter keyed by client IP. Lost on restart is acceptable — restart resets the window, which is lenient, not unsafe.
- Daily OpenAI spend: a single in-process running total reset at UTC midnight, seeded from a configurable ceiling. (If a future multi-instance deploy lands, both move to a shared store — noted, not built.)

**In-memory job state** (slice 1) gains the restart contract: its *absence* for a `running` row is the signal the row is orphaned (§5).

## 5. Reliability Hardening

### 5.1 Source retry + partial-source threshold (US-S3)

In [run_pipeline_service.py](../../app/services/run_pipeline_service.py), `_process_source` currently lets any exception bubble up through `asyncio.gather` and fail the whole run. Slice 2:

1. Wrap each source in **retry-once with exponential backoff** (PRD §8: "one retry with exponential backoff"). A source that fails twice is recorded as failed, not raised.
2. Switch the gather to `return_exceptions=True` (or wrap each task so it returns a `SourceResult` discriminated union) so one source failing doesn't cancel the siblings.
3. After fan-out, compute `succeeded_count / total_count`. If `succeeded / total >= 0.70` → continue to synthesis with the surviving pain items + quotes, and populate `partial_sources_json` with the failures. Else → `failed` with `failure_reason: sources_below_threshold`.
4. The `partial_sources` block flows into the `RunResult` and drives the frontend banner.

The 70% threshold lives in [app/config/constants.py](../../app/config/constants.py), not hardcoded in the pipeline.

### 5.2 Server-restart → failed (US-S4)

In-memory `_jobs` is lost on restart (slice-1 design). The fix is **on-read reconciliation**, not a background sweeper:

- When `idea_run_service.get_run` reads a row whose `status == 'running'` **and** there is no live entry in `_jobs` for that `run_id`, it transitions the row to `failed` with `failure_reason: server_restart` before returning the state.
- This is loud and deterministic: the next `GET /runs/:id` poll (the frontend polls every 5s) surfaces the failure. No silent partial `done`.
- The reconciliation write is conditional (`status='running'` guard) so a genuinely-live run on another code path can't be clobbered.

Decision to confirm in §10: does reconciliation live in `idea_run_service.get_run` (read-time) or in a startup hook that sweeps all `running` rows once on boot? Read-time is simpler and matches "on next read" wording in PRD US-S4; lean read-time.

### 5.3 `failure_reason` enum

Promote from freeform (slice-1 open question #3) to `{ server_restart, budget_exhausted, sources_below_threshold, internal_error }`. `internal_error` is the catch-all the slice-1 `except Exception` path now maps to. Surfaced to the frontend so the Result page can show a human-readable failure message per reason.

## 6. Abuse / Cost Guards

New module: **`app/services/rate_limit_service.py`** (or `app/lib/`), consulted by the router *before* `idea_run_service.create_run` does any work. Layer rule holds: router → service.

| Guard | Check | Response | Spec |
|---|---|---|---|
| **Per-IP rate limit** | 3 runs/hour AND 10 runs/day per client IP | `429 rate_limited` + `Retry-After` | PRD §8, US-S6 |
| **Daily budget cap** | Running OpenAI spend ≥ `OPENAI_DAILY_BUDGET_USD` | `429 budget_exhausted` | PRD §8, US-S5 |
| **Concurrency guard** | An active run already `running` on this instance | `429 busy` + `Retry-After` | PRD §8 |

- Order of checks at `POST /runs`: concurrency → rate limit → budget. (Cheapest/most-likely-to-reject first; all are cheap.)
- Client IP comes from the standard proxy header chain (`X-Forwarded-For` first hop), falling back to the socket peer. Document the trust assumption — behind a single known proxy in the v1 deploy (PRD §8).
- Budget accounting: the OpenAI transport (`app/clients/openai.py`) is the single choke point — increment the running spend total there from usage tokens × per-model price, so every stage's spend counts without each call site knowing about the budget. Prices live in config alongside `MODEL_ROUTING`.
- The concurrency guard reuses the `_jobs` registry: "is any job `running`?" The guard is set at `approve` (when the pipeline is enqueued), not at `POST /runs` — pre-flight is synchronous and short. Reconfirm in §10 whether the guard counts active *pipelines* (post-approve) only, which matches PRD §8 "single active run" wording.

## 7. Feedback & Report Endpoints

Add to [app/api/runs.py](../../app/api/runs.py); orchestrated through `idea_run_service`. Both are slice-2-new (slice 1 explicitly excluded them).

| Method | Path | Body | Behaviour |
|---|---|---|---|
| POST | `/runs/:id/feedback` | `RunFeedback { new_to_me_gap_ids?: list[str], direction?: str, time_saved_estimate_minutes?: int }` | **Append-only** insert into `feedback_events`. Valid only when run is `done` (else 409). Returns `{ ok: true }`. No upsert — repeat submissions add rows (PRD §9). |
| POST | `/runs/:id/report` | `RunReport { reason: str }` | Transition status → `reported`, set `reported_at`, store reason. Immediately hides from `GET /runs/:id` (returns 410/404-style hidden) and from the `GET /runs` feed. Returns `{ ok: true }`. |

Validation: `direction ∈ {continue, shift, drop, need_more_research}`; `new_to_me_gap_ids` must reference gap_ids that exist on the run; `time_saved_estimate_minutes >= 0`. Pydantic at the boundary.

`GET /runs` and `GET /runs/:id` gain a `status != 'reported'` filter so hidden runs disappear from the public surface while the row is retained for admin review (PRD §8 — "not deleted, hidden pending decision").

## 8. Pydantic Schema Additions

In [app/schemas/runs.py](../../app/schemas/runs.py):

- `RunFeedback { new_to_me_gap_ids: list[str] | None, direction: Direction | None, time_saved_estimate_minutes: int | None }` where `Direction` is a `Literal`/enum of the four values.
- `RunReport { reason: str }` (non-empty).
- `PartialSources { failed: list[FailedSource], succeeded_count: int, total_count: int }`, `FailedSource { source, name, reason }`.
- `FailureReason` enum (§5.3).
- `RunStateResponse` / `RunResult` gain `partial_sources: PartialSources | None`. (`coverage`, `idea_match` already present from slice 1.)
- Pre-flight: a `no_sources: bool` (or candidate-count-driven) signal so the frontend can render the US-S1 state.

## 9. Frontend (slice 2)

**Sequencing is load-bearing (ADR 2026-06-01): the router migration lands first.**

### 9.1 Router migration (do this first)
- Introduce `react-router-dom`. Routes: `/` (Home feed), `/runs/new` (New Run), `/runs/:id` (Run Status / Result). This requires lifting the `frontend/CONTEXT.md` "no new routing libraries" constraint — update CONTEXT.md as part of this PR (the ADR is the authority for the exception).
- Replace the `App.jsx` `currentPage` switch + `activeRunId` + `openRun(runId)` callback with route navigation. `openRun(runId)` becomes `navigate(\`/runs/${runId}\`)`. The three pages read `:id` from the route instead of props.
- The legacy v1 pages stay mounted but unlinked (their removal is slice 3); only the three v2 routes are wired into the new nav.
- Exit check: a `/runs/:id` URL pasted into a fresh tab loads that run's Result page directly (US-4, US-5).

### 9.2 Result page controls — [frontend/src/RunResult.jsx](../../frontend/src/RunResult.jsx)
- **`partial_sources` banner** when present: "Completed with N of M sources. Failed: …".
- **Thumbs-up** on each gap card → marks `new_to_me_gap_ids`, debounced `POST /runs/:id/feedback`.
- **Direction prompt** below the gap list: four choices, dismissible, non-blocking → feedback.
- **"Report this run"** link → confirm → `POST /runs/:id/report` → routes home with a "reported" acknowledgement.
- **Failure rendering** per `failure_reason` enum (server_restart, sources_below_threshold, budget_exhausted, internal_error) — a clear human message, not a raw string.

### 9.3 New Run page — [frontend/src/NewRun.jsx](../../frontend/src/NewRun.jsx)
- **US-S1 state:** when pre-flight returns no candidates, render "No public sources found for this idea" with a paste-competitor-URLs affordance, instead of an empty competitor editor.
- **`429` handling:** `rate_limited` / `budget_exhausted` / `busy` from `POST /runs` each render a distinct, friendly message with the `Retry-After` hint. (Slice 1 assumed the developer; slice 2 assumes a stranger.)

### 9.4 My Runs — new page/route
- Frontend-only filter of `GET /runs` against `localStorage` `run_id`s collected at submit time. No backend change.

## 10. Open Questions

1. **Restart reconciliation location** — read-time in `get_run` vs. a one-shot startup sweep of `running` rows. Lean read-time (matches PRD "on next read"); confirm before §5.2 PR.
2. **Concurrency guard granularity** — count active *pipelines* (post-approve) only, or also count an in-flight synchronous pre-flight? PRD §8 says "single active run"; pre-flight is ≤10s and synchronous, so counting pipelines is likely sufficient. Confirm.
3. **Budget price table source** — hardcode per-model USD/1K-token prices in config, or read from an env/secret? Start in config next to `MODEL_ROUTING`; revisit if prices churn.
4. **`X-Forwarded-For` trust** — the v1 deploy's proxy topology determines which hop is the real client IP. Pin this to the actual deploy (PRD §8) before shipping the rate limiter, or the limit is trivially bypassed.
5. **Reported-run read response** — `GET /runs/:id` on a `reported` run: 404 (pretend it never existed) vs. 410 Gone vs. a neutral "unavailable" state. Lean 404 to avoid confirming a report happened. Confirm.
6. **Does `report` require auth/ack to prevent griefing?** v1 has no auth (PRD §5). Anyone can hide any run. Accept for v1 (rate-limit the report endpoint per IP); flag as a known weakness. Confirm acceptable.

## 11. Slice Exit Criteria

Slice 2 is **done** when, on a fresh `git pull` against a clean Supabase:

1. **Partial sources:** force 2 of 10 sources to fail → run completes `done` with a `partial_sources` banner naming both; force 4 of 10 to fail → run ends `failed` with `failure_reason: sources_below_threshold`.
2. **Retry:** a source that fails once then succeeds is retried and contributes to the result (verified by log/inspection).
3. **Restart transition:** start a run, kill the server mid-`running`, restart, `GET /runs/:id` → `failed` with `failure_reason: server_restart`. No row stuck `running`.
4. **Rate limit:** the 4th `POST /runs` from one IP within an hour returns `429 rate_limited` with `Retry-After`.
5. **Budget cap:** with `OPENAI_DAILY_BUDGET_USD` set low, an over-budget `POST /runs` returns `429 budget_exhausted`.
6. **Concurrency:** a second submission while a run is `running` returns `429 busy` with `Retry-After`.
7. **Feedback:** thumbs-up + a direction selection on a `done` run writes ≥1 `feedback_events` row; submitting again appends another (append-only verified).
8. **Report:** reporting a run sets `reported_at`, flips status to `reported`, and the run vanishes from both `GET /runs` and `GET /runs/:id` while the row remains in the table.
9. **Routing:** `/runs/:id` pasted into a fresh browser tab loads that run's Result page directly; `/` and `/runs/new` resolve; browser back/forward work.
10. **My Runs:** a run submitted in this browser appears in My Runs; one that wasn't does not.
11. **US-S1:** an idea for which pre-flight finds zero competitors renders the "no public sources" + paste-URL state, not a broken approve flow.
12. **Slice-1 invariants still hold:** grounded gaps (≥2 citations), idea-blinding, model-routing-via-resolver, `X-Robots-Tag` on `/runs/:id`, PII redaction — unchanged and re-verified by the slice-1 exit checks.

A passing slice 2 does **not** require: the eval harness, `quality_signals`, removal of v1 endpoints/pages, or an admin UI for reported runs.

## 12. Sub-Milestones (each PR independently mergeable)

Ordered so reliability/guards (backend) and the router migration (frontend) can proceed in parallel after the schema PR.

1. **Schema + migration.** `failure_reason` enum, `reported` status, `RunFeedback`/`RunReport`/`PartialSources` schemas, `feedback_events` write path. Boundary tests. No behaviour change yet.
2. **Source retry + partial-source threshold.** `_process_source` retry-once + `return_exceptions`; 70% threshold; `partial_sources_json`. Tests with injected source failures.
3. **Restart → failed.** Read-time reconciliation in `get_run`. Test: simulate orphaned `running` row (no `_jobs` entry) → `failed`.
4. **Rate limiter + concurrency guard.** `rate_limit_service`; wire into `POST /runs` / `approve`. Tests for 429s + `Retry-After`.
5. **Budget cap.** Spend accounting in `app/clients/openai.py`; price config; `429 budget_exhausted`. Test with a low cap.
6. **Feedback + report endpoints.** `POST /runs/:id/feedback` (append-only), `POST /runs/:id/report` (hide). Feed/state filters exclude `reported`. Tests.
7. **Frontend: router migration.** `react-router-dom`; `/`, `/runs/new`, `/runs/:id`; CONTEXT.md exception. Done before #8–#10 (ADR). Deep-link walkthrough.
8. **Frontend: Result-page controls.** Thumbs-up, direction prompt, report link, `partial_sources` banner, per-reason failure rendering — built on routed pages.
9. **Frontend: New Run sad paths.** US-S1 no-sources state; 429 handling messages.
10. **Frontend: My Runs.** localStorage feed filter + route. Exit-criteria walkthrough.

PRs 1–6 are backend, additive over slice 1. PRs 7–10 are frontend, gated on PR 7 landing first. PRs 1 and 7 unblock the rest and should land early.

## 13. Risks Specific to This Slice

- **Restart reconciliation can clobber a live run** if the `_jobs` check races a just-enqueued pipeline. Mitigation: the transition write is conditional on `status='running'` AND there's a grace consideration for runs whose `approve` just registered the job; keep the read-time check, and only reconcile rows older than a small threshold if a race shows up in testing.
- **In-process rate-limit + budget counters reset on restart**, so a crash-loop could let a client exceed limits. Accepted for v1 single-instance (PRD §8); the lenient direction (resets *open* the gate, never falsely close it) is the safe failure mode. Flagged for the multi-instance move.
- **`X-Forwarded-For` spoofing** makes the per-IP limiter useless if the trust boundary is wrong. Mitigation: pin to the actual deploy proxy (open question #4) — this is a correctness prerequisite, not a nicety.
- **Router migration touches three already-merged pages a second time** (the cost the ADR accepted). Mitigation: the pages centralize nav through `App.jsx` callbacks, so the change is mostly swapping `currentPage`/`openRun` for route params; do it as one focused PR (#7) before any new UI.
- **`report` with no auth is grief-able** — anyone can hide any run. Accepted for v1 (open question #6); rate-limit the report endpoint and rely on the retained row + manual admin review. Becomes a real problem only at scale, which v1 isn't built for.
- **Append-only feedback can be spammed** to inflate §4 indicators. Low stakes (indicators are leading, not validated — PRD §4); rate-limit shares the per-IP budget. Not worth more in v1.

## 14. References

- [PRD v2.2](../../docs/PRD.md) — §4 (indicators), §6 (US-S1…S7), §7.6 (frontend), §8 (non-functional), §9 (data model), §15 (router is slice 2).
- [v2 Slice 1 spec](v2-slice-1-end-to-end_spec.md) — §3 "Deferred to slice 2" is the source list for this slice; §11 invariants must still hold.
- [ADR 2026-06-01 — frontend routing](../decisions/2026-06-01-frontend-routing-state-vs-router.md) — router migration sequenced first in slice 2.
- [run_pipeline_service.py](../../app/services/run_pipeline_service.py) — where retry / partial-source / restart logic lands (replaces the slice-1 "any failure fails the run").
- [idea_run_service.py](../../app/services/idea_run_service.py) — restart reconciliation + reported/feed filtering.
- [app/api/runs.py](../../app/api/runs.py) — feedback/report endpoints + guard wiring.
- [app/CONTEXT.md](../../app/CONTEXT.md), [frontend/CONTEXT.md](../../frontend/CONTEXT.md) — layer rules; frontend CONTEXT's "no new routing library" rule is lifted in PR 7.
</content>
</invoke>
