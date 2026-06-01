# v2 Slice 1 — Idea → Grounded Gaps (End-to-End)

| | |
|---|---|
| **Status** | Draft |
| **Created** | 2026-05-28 |
| **Owner** | John Lowen David |
| **Parent** | [PRD v2.2](../../docs/PRD.md) |
| **Slice** | 1 of 3 (see PRD task list — slice 2 = lifecycle hardening, slice 3 = abuse/eval) |
| **Goal** | One idea, submitted via the UI, produces a Supabase-persisted run with grounded gaps the user can read — exercising every PRD-shaped layer once. |

---

## 1. Purpose of This Slice

The point is to **prove the v2 shape works end-to-end** before investing in hardening (retries, partial-source handling, rate limits, eval harness). Every architectural commitment in the PRD — quote-then-claim grounding, idea-blinded extraction, model routing, the `idea_runs / gaps / feedback_events` schema — gets exercised in a real run that a user can drive in the browser.

What this slice is **not**: a shippable v1. The hardening that makes the system safe to expose to the public (rate limits, budget cap, abuse handling, partial-source banner, eval harness) is slice 2/3. A successful slice 1 means *we are confident the architecture works and the remaining slices are additive, not corrective*.

This is a **tracer bullet that goes all the way through**, per PRD §10 architecture diagram — every box in the diagram has working code by the end of this slice, even if some boxes only handle the happy path.

## 2. What Ships in This Slice

**Pipeline (happy path only):**
- Pre-flight: classify → signal_strength → propose 5 apps + 5 videos
- User edits competitor list, approves (TODO: user can remove or add links but is limited to 10 for all sources)
- Background job: per-source extraction fans out across 10 sources in parallel
- Quote-then-claim synthesis produces grounded `GapItem`s
- Optional idea-match step when `target_gap` is supplied
- Persist to Supabase (`idea_runs`, `gaps`, `feedback_events` tables exist; only the first two are written in this slice)

**API endpoints (slice 1 subset):**
- `POST /runs` — synchronous pre-flight
- `POST /runs/:id/approve` — kicks off background pipeline
- `GET /runs/:id` — poll for state + final result
- `GET /runs` — public feed (drives Home)

**Frontend (slice 1 subset):**
- Home: public feed of completed runs + "Start a new run" CTA
- New Run: submit form → pre-flight loading → pre-flight review (signal panel + competitor editor + low-signal ack)
- Run Status / Result: polls `GET /runs/:id`; renders signal banner, ranked gap list with verbatim quotes inline, coverage line, citation count per gap

**Cross-cutting:**
- Model-routing resolver in place; every LLM call goes through it; v1 config maps every stage to `gpt-4o`
- `X-Robots-Tag: noindex, nofollow` middleware on `/runs/:id`
- PII redaction at persist (regex + NER)
- Idea-blinded per-source extraction (prompt construction enforces it)
- Coverage + citation-count fields populated in output

## 3. Out of Scope (Deferred to Later Slices)

**Deferred to slice 2 (lifecycle hardening):**
- `POST /runs/:id/feedback` and `POST /runs/:id/report` endpoints (the `feedback_events` table exists in slice 1 but is not written)
- Thumbs-up control + direction prompt + report link in UI
- Per-IP rate limiter (3/hour, 10/day)
- Daily OpenAI budget cap
- Concurrency guard (`429 busy` on second active submission)
- Source retry-with-backoff and `partial_sources` ≥70% threshold
- Server-restart → `failed` transition
- `My Runs` page (localStorage filter)
- `partial_sources` banner

**Deferred to slice 3 (eval + cleanup):**
- Eval harness + 5-idea seed set (PRD §7.9)
- `quality_signals` field
- Removal of `/analyze/*` endpoints, weekly jobs, `automatic_table*` (these stay alongside v2 endpoints during slice 1–2; removed once v2 is exercised)
- ADRs

**Hard out of scope for slice 1:**
- Anything in PRD §12 (RAG, accounts, additional sources, real-time, public API)
- Per-run engagement-filter tuning (defaults from PRD §7.5 baked into config)

## 4. Data Model (slice 1)

Create all three tables in Supabase now (per PRD §9), even though `feedback_events` isn't written until slice 2. One migration; no schema churn between slices.

```
idea_runs
  id (uuid, pk)
  idea (text)
  target_gap (text, nullable)
  status (enum: pending | preflight_ready | running | done | failed)
  category (text, nullable until preflight done)
  signal_strength (enum: high | medium | low, nullable)
  signal_reasoning (text, nullable)
  competitors_json (jsonb)         -- approved competitor list
  quotes_json (jsonb)              -- { quote_id: { source, source_id, text_redacted, like_count } }
  partial_sources_json (jsonb, nullable)  -- column exists; populated in slice 2
  coverage_json (jsonb, nullable)  -- { quotes_retrieved, quotes_cited, citation_ratio }
  idea_match_json (jsonb, nullable)
  failure_reason (text, nullable)
  reported_at (timestamptz, nullable)  -- column exists; populated in slice 2
  created_at (timestamptz)
  updated_at (timestamptz)

gaps
  gap_id (text, pk)
  run_id (uuid, fk → idea_runs.id)
  gap (text)
  severity (int 1..5)
  frequency (int)
  spread (int)
  competitors_present_json (jsonb)
  evidence_quote_ids_json (jsonb)
  ordinal (int)  -- preserves rank order from synthesis

feedback_events  -- created in slice 1, written in slice 2
  id (uuid, pk)
  run_id (uuid, fk)
  submitted_at (timestamptz)
  new_to_me_gap_ids_json (jsonb, nullable)
  direction (text, nullable)
  time_saved_estimate_minutes (int, nullable)
```

**In-memory job state** (lost on restart by design; slice 2 adds the restart-→-failed transition):

```python
{ run_id: { status, stage, started_at, future } }
```

## 5. Pydantic Schemas

New module: [app/schemas/runs.py](../../app/schemas/runs.py). Existing [app/schemas/llm.py](../../app/schemas/llm.py) keeps the per-source `LLMExtraction` shape but gains the quote-grounding fields.

**Request bodies:**
- `RunCreate { idea: str, target_gap: str | None }`
- `RunApprove { competitors: list[Competitor], acknowledged_low_signal: bool | None }`

**Domain models:**
- `Competitor { source: 'youtube' | 'appstore', url: str, name: str, identifier: str }`
- `Quote { quote_id, source, source_id, text_redacted, like_count }`
- `PainItem { source, source_id, text, quote_ids: list[str] }`  — emitted by per-source extractor; not surfaced in UI directly
- `GapItem { gap_id, gap, severity (1..5), frequency, spread, competitors_present, evidence_quote_ids }`
- `Coverage { quotes_retrieved, quotes_cited, citation_ratio }`
- `IdeaMatch { gap_id, verdict, evidence_quote_ids }`

**Pre-flight response:**
- `PreflightResult { category, signal_strength, signal_reasoning, candidates: list[Competitor] }`

**Run output (response of `GET /runs/:id` when `done`):**
- `RunResult { run_id, idea, target_gap, created_at, category, signal_strength, signal_reasoning, competitors, gaps, quotes, coverage, idea_match }`

**Validation rule** enforced post-synthesis (PRD §7.7): any `GapItem` whose `evidence_quote_ids` references an ID not in the pool, or with `len(evidence_quote_ids) < 2`, is rejected before persistence.

## 6. API Endpoints (slice 1)

Add new router: [app/api/runs.py](../../app/api/runs.py). Mount at `/runs`. Follows layer rule (PRD §10): router → `idea_run_service` → pipeline stages.

| Method | Path | Body | Behaviour |
|---|---|---|---|
| POST | `/runs` | `RunCreate` | Insert row in `pending`. Run pre-flight synchronously (≤10s). Update row to `preflight_ready` with pre-flight result. Return `{ run_id, status, preflight }`. |
| POST | `/runs/:id/approve` | `RunApprove` | Validate competitor list. If pre-flight was `low` and `acknowledged_low_signal != true`, return 400. Transition `preflight_ready` → `running`. Enqueue background task. Return `{ run_id, status: 'running' }`. |
| GET | `/runs/:id` | — | Return current row state. When `done`, include full `RunResult`. Sets `X-Robots-Tag: noindex, nofollow`. |
| GET | `/runs` | query: `?limit=20&before=<iso>` | Paginated feed of `done` runs (idea text + completed_at + run_id). |

Slice 1 does **not** include `POST /runs/:id/feedback` or `POST /runs/:id/report`. Sad-path responses (rate limit, budget, busy) are deferred to slice 2 — slice 1 assumes the user is the developer.

## 7. Pre-flight Stage

Reuses the prototype work in [planning/prototypes/preflight/run_preflight.py](../prototypes/preflight/run_preflight.py). Productionise into:

- [app/clients/appstore.py](../../app/clients/appstore.py) — add `itunes_search(query, limit)` (PRD §14.18 prereq).
- [app/services/preflight_service.py](../../app/services/preflight_service.py) — orchestrates: generate queries → call App Store Search + YouTube Data search.list → rank candidates → return `PreflightResult`.
- [app/llm/preflight.py](../../app/llm/preflight.py) — the two LLM calls (`generate_queries`, `rank_candidates`), routed via the model-routing resolver (§9).
- Tighten YouTube ranker prompt to filter gameplay-only let's-plays (PRD §14.18 prereq) — prompt change in [app/config/promptTemplates.py](../../app/config/promptTemplates.py).

Per-category engagement filters (PRD §7.5) live in [app/config/constants.py](../../app/config/constants.py) and are consumed by the per-source extractors in §8, not pre-flight itself.

## 8. Background Pipeline

New module: [app/services/run_pipeline_service.py](../../app/services/run_pipeline_service.py). Triggered by `/runs/:id/approve` via FastAPI `BackgroundTasks`.

```
approve()
  → spawn background task
     → fan out 10 sources concurrently via asyncio.gather (cap 5 concurrent OpenAI calls via a semaphore)
        per source:
          ingestion (YouTube comments / iTunes RSS reviews)
          → engagement filter (PRD §7.5 thresholds by category)
          → PII redaction (regex emails / phones / @handles + NER person names)
          → per-source LLM extraction (idea-blinded — prompt does NOT see idea/target_gap)
          → returns (PainItem[], Quote[])
     → pool all quotes + pain items
     → synthesis LLM call (sees idea + target_gap + entire quote pool + pain items)
     → validate every GapItem: ≥2 citations, all quote_ids in pool — reject failures
     → compute coverage (quotes_retrieved, quotes_cited, citation_ratio)
     → spread (distinct competitors), frequency (raw count), competitors_present per gap
     → if target_gap supplied: idea_match LLM call
     → persist idea_runs update + gaps inserts
     → status = done
```

**Happy path only in slice 1:**
- Any source failure → whole run fails. (Slice 2 adds retry-once + ≥70% threshold + `partial_sources_json`.)
- Server restart during `running` → row stays `running` forever. (Slice 2 adds the on-read transition.)

**Idea-blinding** is enforced by the prompt builder: per-source extraction prompts are constructed from `(comments, source_metadata)` only — there is no parameter for `idea`. The pipeline orchestrator does not pass it. This is a code-structure guarantee, not a discipline guarantee.

## 9. Model Routing (PRD §10.1)

New module: [app/llm/router.py](../../app/llm/router.py).

```python
def resolve(stage: str) -> ModelConfig:
    """stage ∈ {'preflight_classify', 'preflight_rank', 'per_source_extract',
                'synthesis', 'idea_match'}"""
```

Config lives in [app/config/constants.py](../../app/config/constants.py):

```python
MODEL_ROUTING = {
    "preflight_classify":  {"model": "gpt-4o", "temperature": 0.2, "max_tokens": 1500},
    "preflight_rank":      {"model": "gpt-4o", "temperature": 0.2, "max_tokens": 2000},
    "per_source_extract":  {"model": "gpt-4o", "temperature": 0.3, "max_tokens": 4000},
    "synthesis":           {"model": "gpt-4o", "temperature": 0.3, "max_tokens": 6000},
    "idea_match":          {"model": "gpt-4o", "temperature": 0.2, "max_tokens": 1500},
}
```

**Every** v2 LLM call in slice 1 resolves its config through `resolve(stage)` before calling the SDK — no call site hardcodes a model. `resolve()` returns config only; the SDK call itself stays in the stage module. This is the architecture-as-config bet (PRD §14.21).

## 10. Frontend (slice 1)

Three new pages. Existing v1 pages (Home, Insights, YouTube, AppStore) stay in the codebase but are unlinked from the new nav. Removal is slice 3.

### Home — [frontend/src/HomeV2.jsx](../../frontend/src/HomeV2.jsx)
- Lists recent `done` runs from `GET /runs`: idea text + relative completed-at + link to result page.
- Prominent "Start a new run" CTA → New Run page (via the App nav callback `onNewRun`).

### New Run — [frontend/src/NewRun.jsx](../../frontend/src/NewRun.jsx)
- Submit form: `idea` (required textarea) + `target_gap` (optional).
- On submit → `POST /runs` (synchronous wait, ≤10s) → renders pre-flight review inline.
- **Signal-strength panel:** shows `signal_strength` + `signal_reasoning`.
  - If `low`: prominent warning + checkbox *"I understand the signal will be thin"* (gates the Approve button).
- **Competitor list editor:** add / remove / paste URL. Each candidate shows the search query that surfaced it.
- "Approve and run" → `POST /runs/:id/approve` → open the Result page via the App `openRun(runId)` callback.

### Run Status / Result — [frontend/src/RunResult.jsx](../../frontend/src/RunResult.jsx)
- Polls `GET /runs/:id` every 5s while `status in {pending, preflight_ready, running}`; stops on `done` / `failed`. Transient fetch errors keep retrying rather than stranding a running page.
- While running: progress shell ("Running across 10 sources…").
- When `done`:
  - **Signal-strength banner** at top.
  - **Coverage line:** `"12 of 184 retrieved quotes were cited (6%)"`.
  - **Ranked gap list.** Each card:
    - gap text + severity badge + `frequency` + `spread`
    - `competitors_present` chips
    - **verbatim quotes inline** (not in drill-down), citation count next to severity
  - **`idea_match`** card at top of list if present.
- `X-Robots-Tag` header is server-side (§6); no frontend work needed.

Navigation is **state-based** in [frontend/src/App.jsx](../../frontend/src/App.jsx) — `currentPage` selects the active page and `activeRunId` (set by the `openRun(runId)` callback) drives the Result page. No router library is introduced: pages #51/#52/#53 all landed on the existing `currentPage` + callback pattern, and `frontend/CONTEXT.md` forbids new state/routing libraries. Pages live flat in `frontend/src/` (there is no `src/pages/` directory). Old v1 pages remain mounted but the nav links only point to the new ones. Shareable/deep-linkable run URLs are out of scope for slice 1; the `react-router-dom` migration (`/`, `/runs/new`, `/runs/:id`) is scheduled for **slice 2**, done before slice 2's feedback/report UI so that UI isn't built twice on the interim nav. See [../decisions/2026-06-01-frontend-routing-state-vs-router.md](../decisions/2026-06-01-frontend-routing-state-vs-router.md) and PRD §15.

## 11. Slice Exit Criteria

Slice 1 is **done** when all of the following hold for a fresh `git pull` on a clean Supabase:

1. From the browser, the developer can submit `"note-taking app with better offline sync"`, edit the competitor list, approve, wait, and see ≥3 grounded gaps with inline quotes within 5 minutes.
2. Every gap shown has ≥2 citations referencing quote IDs present in the run's quote pool. Pick any gap → quote IDs exist in `quotes_json`.
3. `idea_runs` has one new row with `status='done'`, populated `coverage_json`, `competitors_json`, `quotes_json`. `gaps` has ≥3 corresponding rows.
4. Per-source extraction prompts do **not** contain the idea string (verified by logging the constructed prompt for one source).
5. Every v2 LLM call site obtains its `(model, temperature, max_tokens)` from `router.resolve(stage)` before calling the OpenAI SDK. `router.py` is a **config resolver** — it does not itself make SDK calls; the `.chat.completions.create` call lives in the stage module (e.g. `app/llm/preflight.py`) using the resolved config. Verify by reading each v2 call site, not by grepping for SDK calls outside `router.py`. (Note: `app/clients/openai.py:create_response` is a v1-only helper that hardcodes its model and is **not** routed — out of scope for slice 1; reconcile or remove when v1 endpoints are retired in slice 3.)
6. `GET /runs/:id` returns `X-Robots-Tag: noindex, nofollow`.
7. PII redaction is applied: persist a row where the source comment contains `john@example.com` and verify `text_redacted` does not contain it.
8. The submit-to-result path works for one B2B idea (e.g. `"tool for prompt engineers to manage prompts"`) with the low-signal warning + ack flow exercised.

A passing slice 1 does **not** require: retries, partial-source handling, rate limits, budget caps, eval harness, feedback/report endpoints, or removal of v1 endpoints.

## 12. Sub-Milestones (avoid a 3-week dark branch)

Suggested PR sequence; each PR mergeable on its own:

1. **Data model + schemas.** Supabase migration + `app/schemas/runs.py`. Tests at boundary. No behaviour change.
2. **Model-routing resolver.** `app/llm/router.py` + config. Migrate existing pre-flight prototype LLM calls to route through it. Smoke test.
3. **Pre-flight productionised.** `itunes_search` in `clients/appstore.py`; `services/preflight_service.py`; tightened YouTube ranker prompt. Standalone test that runs pre-flight against one idea and prints the result.
4. **`POST /runs` + `GET /runs/:id`.** Synchronous pre-flight wired up. No background pipeline yet — approve returns 501.
5. **Per-source extraction refactor.** Move existing extraction logic into `services/`, enforce idea-blinding by prompt-builder signature, emit `(PainItem[], Quote[])`. Tests against fixture comments.
6. **PII redaction at persist.** New module `app/preprocessing/redact.py`. Tested in isolation.
7. **Synthesis + grounding validator.** `app/llm/synthesis.py` + post-processing validator. Returns `GapItem[]` + `Coverage`.
8. **Background pipeline wiring + `POST /runs/:id/approve`.** Fan-out, semaphore, persistence. Happy path only.
9. **Frontend: New Run page** (submit + pre-flight review + competitor editor + low-signal ack).
10. **Frontend: Run Result page** (polling, banners, gap list with inline quotes, coverage line).
11. **Frontend: Home V2** (public feed + nav rewire). Exit-criteria walkthrough.

PRs 1–3 are pure additions and don't break v1. PRs 4–11 add new routes and pages alongside v1. Slice 3 removes v1.

## 13. Risks Specific to This Slice

- **Synthesis prompt is the riskiest single component.** It receives the full pooled quote set and must produce grounded, ranked gaps. Mitigation: write the synthesis prompt early (PR 7) against a hand-crafted fixture quote pool before the full pipeline can produce one. Don't wait for PR 8 to discover the prompt doesn't work.
- **Idea-blinding by convention erodes.** If a developer adds an `idea` parameter to the extraction prompt builder six months from now, blinding is silently lost. Mitigation: the per-source extractor's function signature physically does not accept `idea`. The pipeline orchestrator that calls it doesn't have `idea` in scope at that call site.
- **Background tasks in FastAPI lose state on restart.** Slice 1 accepts this — a server restart during a run leaves a `running` row forever. This is loud, not silent. Slice 2 fixes it.
- **No retry / partial-source handling** means a single flaky API call fails the whole run. Acceptable for slice 1 because the developer can re-submit. Becomes unacceptable the moment a real user touches it — which is why slice 2 ships before any public exposure.
- **PRs 9–11 are sequential against PR 8.** If PR 8 slips, frontend work stalls. Mitigation: PR 8 can be split — stub `approve` to fake-complete a hard-coded fixture run, unblocking PRs 9–10 against fake data.

## 14. Open Questions

1. **Polling interval for `GET /runs/:id`** — 5s feels right; revisit if it creates load. WebSockets / SSE are slice-2+ if needed.
2. **Where does the synthesis prompt live?** Single string in [app/config/promptTemplates.py](../../app/config/promptTemplates.py), or its own module under `app/llm/`? Lean toward the latter (prompt is long and stage-specific) but defer until PR 7.
3. **Do we keep `failure_reason` as freeform text or enum?** PRD examples (`server_restart`, `budget_exhausted`) suggest enum-able. Start freeform in slice 1; promote to enum in slice 2 when the set is known.
4. **Should pre-flight persist its raw API search results** (the 30 candidates before LLM ranking) for debugging? Cheap to store, useful for slice 3 eval harness. Recommend yes — add `preflight_raw_json` to `idea_runs`.
5. **Quote retrieval — top-N by likes or full set?** PRD §7.5 implies engagement filtering happens at ingestion; everything that passes goes into the pool. Confirm before PR 5 — if the pool is large enough to blow the synthesis prompt's context, we need a per-source cap.

## 15. References

- [PRD v2.2](../../docs/PRD.md) — sections 7, 9, 10 are the binding spec for this slice
- [Pre-flight prototype findings](../prototypes/preflight/findings.md) — validated the pre-flight stage on 15 ideas
- [Pre-flight prototype script](../prototypes/preflight/run_preflight.py) — code reused in §7 productionisation
- [app/CONTEXT.md](../../app/CONTEXT.md) — layer rules and module map (target shape; some entries refer to v1)
