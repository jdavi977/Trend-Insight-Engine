# v2 Slice 3 — Eval Harness + v1 Removal (Completes v1)

| | |
|---|---|
| **Status** | Shipped 2026-06-11 |
| **Created** | 2026-06-06 |
| **Owner** | John Lowen David |
| **Parent** | [PRD v2.2](../../docs/PRD.md) |
| **Slice** | 3 of 3 (slice 1 = end-to-end happy path ✅; slice 2 = lifecycle hardening ✅; this slice closes v1) |
| **Goal** | Ship the measurement layer (eval harness + 5-idea seed + `quality_signals`), make the low-signal gate key off observed evidence instead of an LLM guess, finish the pre-flight robustness deferred from slice 2, and delete the dead v1 surface — leaving the codebase as exactly the v2.2 PRD target with nothing legacy still mounted. |

---

## 1. Purpose of This Slice

Slices 1–2 built and hardened the v2 pipeline; what they did **not** ship is the
ability to *measure* whether a run is any good, and they left the v1 codebase
mounted alongside v2 "until v2 is exercised" (slice-1 spec §3). v2 is now
exercised. Slice 3 does three distinct things, in rough order of value:

1. **Measurement (PRD §7.9).** The eval harness, the 5-idea seed set, and the
   per-run `quality_signals` field. This is the prerequisite for every
   cost-increasing quality improvement catalogued in PRD §15 — without
   measurement, no mitigation (adversarial pass, cold-model critique, stratified
   sampling) can be justified. Shipping the harness now means v1.1 improvements
   are data-driven from day one.

2. **Correctness of the low-signal gate (PRD §15 note).** Today the gate keys off
   an LLM-*guessed* `signal_strength` produced *before any search runs* — a guess
   that can pass a 0-candidate run or block one with 8 real competitors. Slice 3
   re-keys the acknowledgement on the **observed candidate count**, the same
   evidence US-S1 already uses. `signal_reasoning` stays as displayed copy; the
   LLM grade stops being load-bearing.

3. **Removal of the dead v1 surface.** The `/analyze/*` endpoints, the weekly
   trending jobs + `automatic_table*`, the `create_response` helper, and the
   unlinked legacy frontend pages all stay mounted today behind the v2 surface.
   They serve a workflow the PRD removed (Background, §7.2, §9). Slice 3 deletes
   them so the repo *is* the PRD, not the PRD plus a fossil layer.

It also finishes the **pre-flight robustness** explicitly deferred from the
slice-2 review (slice-2 spec §3): Pydantic-validate the `generate_queries`
output, wrap the synchronous pre-flight call so a failure can't strand a
`pending` row, and (only if the ≤10s budget is breached) parallelize the search
fan-out.

This slice is **additive (measurement, robustness) + subtractive (v1 removal)**,
not a rewrite. The v2 pipeline behaviour is unchanged except for the gate re-key.
When it lands, the PRD §15 status table flips all three slices to **Shipped** and
v1 is complete.

## 2. What Ships in This Slice

**Evaluation harness + seed set (PRD §7.9):**
- A runner script that takes an idea + hand-labelled expected gaps, executes the
  full pipeline, and scores output against the four PRD §7.9 metrics: **gap
  recall**, **hallucination rate**, **citation ratio**, **severity calibration**.
- Structured **JSON report per idea**. No CI gate (deferred to v1.1) — runs are
  manual, reviewed by hand.
- **5-idea seed set**, one per category (consumer-app, mobile-game, creator-tool,
  productivity, low-signal), each hand-labelled with 3–5 expected gaps + expected
  severity ranges, drawn from the pre-flight validation set (PRD §14.18, §7.9).

**Per-run quality signals (PRD §7.9):**
- New `quality_signals` field computed on **every production run** (not just eval
  runs), persisted, and **logged — not surfaced in the v1 UI**:
  `quote_source_diversity` (0–1), `severity_distribution` ([int×5]),
  `single_source_gap_count` (gaps where `spread == 1`), `extraction_yield`
  (`[{source, comment_count, pain_item_count}]`).

**Low-signal gate re-key (PRD §15 note):**
- The approve-time gate stops reading the LLM `signal_strength` and keys the
  acknowledgement on the **observed candidate count** from pre-flight.
- `signal_reasoning` is **retained** as displayed pre-flight copy (PRD §7.6).
- US-S1 (zero candidates) and the low-signal acknowledgement now share one
  evidence source: the count.

**Pre-flight robustness (deferred from slice 2 §3):**
- **`generate_queries` output validation** — wrap the raw `json.loads` in a
  Pydantic model so a malformed grade maps to a clean `internal_error`, not a
  bare `KeyError` out of `preflight_service.run`.
- **Orphaned-`pending` fix** — wrap `create_run`'s synchronous `preflight_service.run`
  call so a pre-flight exception transitions the row to `failed` +
  `failure_reason: internal_error` instead of stranding it at `pending` forever.
- **Optional fan-out parallelization** — parallelize the independent App Store /
  YouTube search I/O **only if** the ≤10s budget is breached. Optimization, no
  behaviour change.

**v1 removal (PRD §7.2, §9, §15):**
- Backend: `/analyze/youtube`, `/analyze/appStore`, the weekly trending pipeline
  (`app/jobs/automatic*`), the weekly-feed Home endpoint, `automatic_table` /
  `automatic_apple_table` + their Supabase accessors, and the v1-only
  `create_response` LLM helper + its `extractInsights` caller.
- Frontend: the unlinked legacy pages (`HomePage`, `InsightsPage`, `YouTubePage`,
  `AppStorePage`) + their CSS + legacy-only components + the `/legacy/*` routes in
  `App.jsx`.
- The RAG / pgvector surface is removed too (decision 2026-06-06 — §3, §9.1).

## 3. Out of Scope (Deferred / Decisions)

**Deferred to v1.1 (PRD §15):**
- **Full golden eval set** (15–20 ideas) + **CI regression gate** (block on >15%
  recall drop or >5% hallucination). Slice 3 ships the *harness* + *5-idea seed*
  only; the corpus and the gate are v1.1.
- **Active selection-bias mitigations** — stratified sampling, "what's missing"
  adversarial pass, cold-model critique, multi-framing extraction (PRD §15). The
  harness shipped here is the prerequisite that justifies them; none are built
  now.
- **Surfacing `quality_signals` in the UI.** v1 logs them only (PRD §7.9). The
  field is persisted + logged; no Result-page rendering.

**RAG / pgvector surface — decided 2026-06-06: remove it all.** The PRD §15
slice-3 list names the `/analyze/*` endpoints, weekly jobs, `automatic_table*`,
and legacy frontend pages — it does not explicitly name RAG, but the RAG stack
(`app/rag/`, `rag_service.py`, `app/api/insights.py`, `clients/pgvector.py`,
`schemas/rag.py`, `InsightsPage`, the embeddings helper + `RAG_*` config) is
dormant v1.x/v3 experiment code (RAG is PRD §12 out-of-scope for v1; v3
canonical-ledger work is deferred — PRD Background). It is reaped in this slice
so v1 ships with no dead retrieval layer. **Coupling caveat (audited 2026-06-06):**
`app/rag/` + `pgvector` are imported only by v1 modules already on the removal
list (`youtube_service`, `appstore_service`, the `automatic*` jobs) — clean — but
`schemas/rag.py:RetrievedInsight` leaks into two **shared** files v2 still uses
(`schemas/llm.py`, `config/promptTemplates.py`). So RAG removal is **surgical**:
prune the v1-only symbols *inside* those shared files before deleting
`schemas/rag.py` (§9.1), not a set of whole-file deletes.

**Hard out of scope:** anything in PRD §12 (RAG re-introduction, accounts,
additional sources, real-time, public API), per-run engagement-filter tuning,
and admin tooling for reported runs (slice-2 §3 — still manual).

## 4. Eval Harness (PRD §7.9)

New surface under `app/eval/` (a runner + seed data + report schema), kept out of
the request-serving `api/ → services/` path — it *drives* the pipeline like a
test harness, it is not part of it.

```
app/eval/
  harness.py        # runner: idea + labels → full pipeline → scored JSON report
  metrics.py        # the four §7.9 scorers (pure functions, unit-tested)
  seed/             # 5 hand-labelled ideas (one per category)
    consumer_app.json
    mobile_game.json
    creator_tool.json
    productivity.json
    low_signal.json
  reports/          # gitignored output dir for per-idea JSON reports
```

**Runner contract.** The harness reuses the real pipeline (it must score the same
code production runs use — no parallel reimplementation). It invokes pre-flight +
the background pipeline stages directly through the services, captures the
resulting `RunResult` + `quality_signals`, and scores it against the seed labels.
It bypasses the HTTP layer, rate limits, and the budget cap (it is a developer
tool, not a user) but **must** route LLM calls through the same `resolve(stage)`
config so eval reflects production model routing.

**Metrics (PRD §7.9 table):**

| Metric | Definition | Implementation note |
|---|---|---|
| **Gap recall** | Did each labelled expected gap surface? | Fuzzy-match each labelled gap string against output `gap` texts; hit/miss per expected gap. Threshold + matcher pinned in `metrics.py` (Open Question 2). |
| **Hallucination rate** | Gaps with broken/missing grounding | Count gaps whose `evidence_quote_ids` reference IDs not in the quote pool, or with `<2` citations. (Production already rejects these pre-persist — in eval this should read ~0; a non-zero count means the validator regressed.) |
| **Citation ratio** | Fraction of retrieved evidence used | `coverage.citation_ratio`, already in the `RunResult` (PRD §7.4). Logged per idea for trend tracking. |
| **Severity calibration** | Rubric applied consistently | Flag a run where >80% of gaps are severity 4–5 (inflation) or >80% are 1–2 (deflation). Reads `quality_signals.severity_distribution`. |

**Report shape (per idea):** structured JSON written to `app/eval/reports/` —
`{ idea, category, expected_gaps, output_gaps, gap_recall: {hit, miss, per_gap},
hallucination_count, citation_ratio, severity_flag, quality_signals }`. No
aggregate scoring, no pass/fail gate in v1 — the operator reads the JSON.

**Seed-set authoring.** Each seed file: `{ idea, target_gap?, category,
expected_gaps: [{ gap, severity_range: [lo, hi] }] }`. Ideas chosen one per
category per PRD §7.9, drawn from the pre-flight validation set
([planning/prototypes/preflight/](../prototypes/preflight/)). Hand-labelling is a
human task — the spec defines the file format and selection criteria; the labels
themselves are authored by the owner.

## 5. Quality Signals (PRD §7.9)

`quality_signals` is computed in the pipeline after synthesis (it needs the final
gap list + the per-source extraction yields) and persisted to `idea_runs`. It is
**logged, not rendered** (PRD §7.9).

```
quality_signals: {
  quote_source_diversity: float,   // 0–1; 1 = cited quotes spread evenly across sources
  severity_distribution: [int],    // length-5: count of gaps at severity [1,2,3,4,5]
  single_source_gap_count: int,    // gaps where spread == 1
  extraction_yield: [{ source: str, comment_count: int, pain_item_count: int }]
}
```

- **Where computed.** [run_pipeline_service.py](../../app/services/run_pipeline_service.py),
  in the same post-synthesis block that already computes `coverage`, `spread`,
  `frequency`, and `competitors_present`. `extraction_yield` is collected per
  source during fan-out (each `_process_source` already knows its comment count
  and emitted pain-item count) and folded in.
- **`quote_source_diversity`.** Normalised entropy (or a simpler max-share metric
  — Open Question 3) over the source distribution of *cited* quotes. Flags when
  synthesis over-indexes on one source.
- **Schema.** New `QualitySignals` Pydantic model in
  [app/schemas/runs.py](../../app/schemas/runs.py); `RunResult` /
  `RunStateResponse` gain `quality_signals: QualitySignals | None`. Persisted to a
  new `quality_signals_json` column on `idea_runs` (§7).
- **Not in UI.** No `RunResult.jsx` change. The field exists in the API response
  (cheap, and the eval harness reads it) but is not rendered in v1.

## 6. Low-Signal Gate Re-key (PRD §15 note)

Today [run_pipeline_service.py:139](../../app/services/run_pipeline_service.py#L139)
gates approve on `row.get("signal_strength") == "low"` — an LLM guess from
`generate_queries`, produced before any search ran. PRD §15 details why it's
biased and redundant. Slice 3:

1. **Re-key the gate on observed candidate count.** Replace the
   `signal_strength == "low"` check with a count-based check: a run whose
   pre-flight produced **fewer than `LOW_SIGNAL_CANDIDATE_THRESHOLD`** total
   candidates requires `acknowledged_low_signal=true` to approve (else 400). The
   threshold lives in [app/config/constants.py](../../app/config/constants.py)
   (Open Question 4 — proposed value below).
2. **Fold US-S1 into the same evidence.** Zero candidates is already the
   count-based "no public sources" sad path (slice-2 §9.3). The low-signal gate is
   now the same axis at a higher threshold — `0` → US-S1 no-sources state,
   `1..threshold-1` → low-signal acknowledgement, `>=threshold` → proceed freely.
3. **Retain `signal_reasoning` as display copy.** The New Run signal panel keeps
   showing `signal_reasoning` (PRD §7.6) — useful UX. `signal_strength` is no
   longer load-bearing; keep it in the response for display but stop gating on it.
4. **Frontend.** The New Run low-signal acknowledgement (slice 1/2) now triggers
   on the count-derived flag the backend returns, not on `signal_strength`. A new
   boolean on the pre-flight response (e.g. `low_signal: bool`, count-derived)
   drives the panel so the frontend doesn't re-implement the threshold.

Proposed `LOW_SIGNAL_CANDIDATE_THRESHOLD`: a small integer (e.g. **4** total
candidates across both sources) — confirm in Open Question 4 against the
pre-flight validation data, where the per-idea candidate floor was 15/15.

## 7. Pre-flight Robustness (deferred from slice 2 §3)

### 7.1 `generate_queries` output validation
[generate_queries](../../app/llm/preflight.py#L26) returns a raw `json.loads`
dict; [preflight_service.run](../../app/services/preflight_service.py#L96) then
does `queries["category"]` / `["signal_strength"]` / `["signal_reasoning"]`
(bare `KeyError` on a malformed grade) while the query lists silently degrade via
`.get(..., [])` — an undocumented asymmetry. Wrap the response in a
`GenerateQueriesResult` Pydantic model (`{ appstore: list[str], youtube:
list[str], category: str, signal_strength: SignalStrength, signal_reasoning:
str }`) so a malformed payload raises `ValidationError`, caught and mapped to
`internal_error` (§7.2) instead of an unstructured `KeyError`. Folds into the
§6 gate rework, which already changes how the grade is consumed.

### 7.2 Orphaned-`pending` on pre-flight failure
[create_run](../../app/services/idea_run_service.py#L39) writes a `pending` row,
then calls the synchronous `preflight_service.run` with **no `try/except`** — a
pre-flight LLM/network exception (or the §7.1 `ValidationError`) strands the row
at `pending` forever. Slice 2's restart contract only reconciles `running` rows;
this path is uncovered (the slice-2 §3 pull-forward candidate was *not* taken).
Wrap the pre-flight call: on exception, transition the row to `failed` +
`failure_reason: internal_error` (the enum slice 2 already defined) and re-raise
as a clean error response, so the New Run page renders a failure instead of a
spinner that never resolves.

### 7.3 Optional fan-out parallelization
[preflight_service.run](../../app/services/preflight_service.py#L82) runs both
source fan-outs and the 2–3 searches within each **sequentially**, inside the
synchronous request. Accepted as ≤10s through slice 2. **Only if** the ≤10s
budget (PRD §8) is breached in practice, parallelize the independent search I/O
(`asyncio.gather`). Optimization, no behaviour change — and explicitly *not* done
speculatively (measure first).

## 8. Data Model Changes (slice 3)

One small additive migration; **additive/idempotent** per the slice-1 migration
note ([[slice1-tables-no-checked-in-migration]]).

```
idea_runs  (existing)
  quality_signals_json (jsonb, nullable)   -- §5; { quote_source_diversity, severity_distribution,
                                           --       single_source_gap_count, extraction_yield }
```

**Removed (v1 teardown):**
- `automatic_table` / `automatic_apple_table` and their Supabase accessors
  (`get_weekly_ids`, `get_weekly_apple_ids`, `get_all_ids`, `get_all_apple_ids`,
  `get_insights_count` in [app/clients/supabase.py](../../app/clients/supabase.py)).
- The pgvector insight collection + `app/clients/pgvector.py` (RAG removal, §9.1).

No change to `gaps` or `feedback_events`. The `signal_strength` column on
`idea_runs` is **retained** (still displayed; just not gated on — §6).

## 9. v1 Removal Inventory

**Discipline: audit imports before each deletion.** Some v1 modules share clients
and ingestion code the v2 pipeline carries over (per-source extraction logic,
App Store / YouTube client wrappers, PII redaction — PRD Background "what carries
over"). For each file below, `grep -rn` the symbol across `app/` and confirm no
v2 path imports it before removing. Removal lands as its own PR(s) *after* the
measurement + gate + robustness PRs, so a v2 regression is never entangled with
new behaviour.

**Backend — remove:**
| Target | Why it's v1 | Carry-over risk |
|---|---|---|
| [app/api/youtube.py](../../app/api/youtube.py), [app/api/appstore.py](../../app/api/appstore.py) | `/analyze/*` single-URL endpoints (PRD §7.2 removed) | Low — thin routers |
| [app/services/youtube_service.py](../../app/services/youtube_service.py), [app/services/appstore_service.py](../../app/services/appstore_service.py) | `*_manual` single-URL orchestration | **Audit** — confirm v2 per-source extraction does not import these (it uses `per_source_extraction_service`) |
| [app/jobs/automaticPipeline.py](../../app/jobs/automaticPipeline.py), `automaticYoutube.py`, `automaticAppStore.py` | Weekly trending pipeline (PRD §7.2, §9 removed) | Low. **Keep** `app/jobs/preflight_smoke.py` (v2 tool) |
| [app/api/home.py](../../app/api/home.py) | Weekly-feed Home (`/get/homePage`) — replaced by `GET /runs` | Note: also serves `GET /` root; drop or repoint |
| [app/api/internal.py](../../app/api/internal.py) + `persistence_service.data_save` | `/data/send` weekly-ingest sink | **Audit** — confirm v2 persistence uses `clients/supabase` directly, not `persistence_service` |
| [app/llm/extractInsights.py](../../app/llm/extractInsights.py) + [openai.py:create_response](../../app/clients/openai.py#L93) | v1-only extractor + its hardcoded-model helper (slice-1 §9 carve-out, issue #54) | Low — only reached by `/analyze/*`. Removing it closes the last hardcoded-model exception |
| [app/schemas/api.py](../../app/schemas/api.py) | v1 request shapes (`YoutubeAnalyzeRequest`, `AppStoreAnalyzeRequest`, `DataSave`) | **Audit** — remove only the v1-only models; keep anything v2 still imports |
| RAG stack: `app/rag/`, `rag_service.py`, `app/api/insights.py`, `clients/pgvector.py` | Dormant v1.x/v3 retrieval (PRD §12 out of scope) — remove (§3) | Whole-file deletes — only v1 importers (all on this list) |
| `schemas/rag.py:RetrievedInsight`, `RAG_*` in `constants.py`, `RAG_READ/WRITE_ENABLED` in `secrets.py`, embeddings helper + `text-embedding-3-small` price in `openai.py`/`constants.py` | RAG config + the shared-file leak | **Surgical** — see §9.1 below |

**Surgical RAG pruning (§9.1, audited 2026-06-06).** `RetrievedInsight` reaches
two shared v2 files. Sever it *before* deleting `schemas/rag.py`:
- [schemas/llm.py](../../app/schemas/llm.py) — drop the v1-only `YoutubeProblemItem` /
  `AppStoreProblemItem` classes (their `similar_insights: List[RetrievedInsight]`
  field is the only consumer) and the `RetrievedInsight` import. **Keep**
  `LLMExtraction` and any class the v2 pipeline imports — verify with a grep first.
- [config/promptTemplates.py](../../app/config/promptTemplates.py) — drop the v1
  prompt builders (`build_youtube_prompt`, `build_appstore_prompt`, their
  `*_refinement` variants, `_prior_insights_block`) and the `RetrievedInsight`
  import. **Keep** the `PREFLIGHT_*` constants v2 pre-flight depends on.
- [clients/openai.py](../../app/clients/openai.py) — drop the embeddings helper +
  `_EMBEDDING_MODEL`; remove the `text-embedding-3-small` entry from the
  `constants.py` price table and the `RAG_*` constants + `RAG_READ/WRITE_ENABLED`
  secrets.

**`app/main.py` router mounts to drop:** `youtube`, `appstore`, `home`,
`internal`, `insights`. After teardown `create_app` includes only `runs`
(+ `errors`).

**Frontend — remove:**
- Pages: [HomePage.jsx](../../frontend/src/HomePage.jsx) + `.css`,
  [InsightsPage.jsx](../../frontend/src/InsightsPage.jsx) + `.css`,
  [YouTubePage.jsx](../../frontend/src/YouTubePage.jsx) + `.css`,
  [AppStorePage.jsx](../../frontend/src/AppStorePage.jsx) + `.css`.
- Legacy-only components: [components/RecurrenceTag.jsx](../../frontend/src/components/RecurrenceTag.jsx),
  [components/RetrievedContextAccordion.jsx](../../frontend/src/components/RetrievedContextAccordion.jsx)
  — audited 2026-06-06: imported only by `AppStorePage`/`YouTubePage` (both removed
  here), so they delete cleanly.
- [App.jsx](../../frontend/src/App.jsx): delete the `/legacy/*` `<Route>`s, the
  legacy imports, and the `LegacyHomePage` adapter. Nav already points only at v2
  routes — no nav change. The `currentPage` switch the PRD §15 note mentions was
  already replaced by the router in slice 2; nothing residual remains there.

## 10. Pydantic Schema Additions

In [app/schemas/runs.py](../../app/schemas/runs.py):
- `QualitySignals { quote_source_diversity: float, severity_distribution: list[int]
  (len 5), single_source_gap_count: int, extraction_yield: list[ExtractionYield] }`,
  `ExtractionYield { source: str, comment_count: int, pain_item_count: int }`.
- `RunResult` / `RunStateResponse` gain `quality_signals: QualitySignals | None`.
- Pre-flight response gains a count-derived `low_signal: bool` (§6) so the
  frontend reads the flag, not the threshold.

In [app/llm/preflight.py](../../app/llm/preflight.py) (or `schemas/llm.py`):
- `GenerateQueriesResult` (§7.1) wrapping the `generate_queries` payload.

## 11. Open Questions

1. **~~Reap the RAG surface?~~ RESOLVED 2026-06-06 — remove it all** (§3, §9.1).
   `app/rag/`, `rag_service`, `/insights/similar`, `pgvector`, `InsightsPage`, the
   embeddings helper + `RAG_*` config all go. Audit confirmed the only importers
   are v1 modules already on the removal list, with one surgical caveat:
   `RetrievedInsight` must be pruned from the shared `schemas/llm.py` and
   `promptTemplates.py` before `schemas/rag.py` is deleted (§9.1).
2. **Gap-recall matcher (§4).** Fuzzy string match (token-set ratio over a
   threshold) vs. an LLM-judged semantic match. Lean fuzzy for v1 (cheap,
   deterministic, no judge-model variance); pin the threshold in `metrics.py` and
   eyeball the seed set to calibrate. LLM-judge is a v1.1 option once the corpus
   grows.
3. **`quote_source_diversity` formula (§5).** Normalised Shannon entropy over
   cited-quote source counts vs. a simpler `1 - max_source_share`. Lean the
   simpler max-share for v1 (interpretable: "no single source > X% of citations");
   revisit if it proves too blunt against the seed set.
4. **`LOW_SIGNAL_CANDIDATE_THRESHOLD` value (§6).** Proposed 4 total candidates.
   Validate against the pre-flight findings (per-idea floor was 15/15 candidates)
   so the threshold flags genuinely thin runs without false-flagging healthy ones.
5. **`GET /` root after `home.py` removal (§9).** Drop the FastAPI root route
   entirely, or repoint `/` to a minimal health/version response? Lean a tiny
   health route so the deploy has a liveness target; confirm.
6. **Does the eval harness count against the budget cap?** It bypasses the §8
   guards as a dev tool (§4) but still spends real OpenAI tokens. Confirm it's run
   manually/off-prod so its ~$15–30/cycle (PRD §15) isn't drawn from the
   production daily cap.

## 12. Slice Exit Criteria

Slice 3 is **done** when, on a fresh `git pull` against a clean Supabase:

1. **Eval harness runs.** `python -m app.eval.harness <seed_idea>` executes the
   full pipeline and writes a JSON report scoring all four §7.9 metrics for that
   idea.
2. **Seed set present.** 5 hand-labelled seed ideas exist, one per category
   (consumer-app, mobile-game, creator-tool, productivity, low-signal), each with
   3–5 expected gaps + severity ranges.
3. **Quality signals persisted.** A completed run has a populated
   `quality_signals_json` (all four sub-fields) on `idea_runs`, present in the
   `GET /runs/:id` response, and **absent from the rendered Result page** (logged,
   not surfaced).
4. **Gate re-key.** Approve no longer reads `signal_strength`: a run with `>= threshold`
   candidates approves without acknowledgement regardless of the LLM grade; a run
   below threshold requires `acknowledged_low_signal=true` (else 400); a 0-candidate
   run still renders the US-S1 no-sources state. `signal_reasoning` still displays.
5. **Pre-flight validation.** A malformed `generate_queries` payload yields a clean
   `internal_error` failure (not a `KeyError` traceback), and the `idea_runs` row
   does not strand at `pending` — it transitions to `failed`.
6. **v1 backend gone.** `/analyze/youtube`, `/analyze/appStore`, `/get/homePage`,
   `/data/send`, `/insights/similar` return 404; `app/jobs/automatic*`,
   `extractInsights.py`, `create_response`, `app/rag/`, and `pgvector` are deleted;
   `RetrievedInsight` no longer imported anywhere; `create_app` mounts only the v2
   router(s).
7. **No hardcoded models remain.** A grep for hardcoded model strings in `app/`
   returns **only** `app/config/constants.py` (`MODEL_ROUTING`) — the
   slice-1 `create_response` exception is now gone (slice-1 §9 / issue #54 closed).
8. **v1 frontend gone.** The four legacy pages, their CSS, legacy-only components,
   and the `/legacy/*` routes are deleted; the app builds and all three v2 routes
   (`/`, `/runs/new`, `/runs/:id`, `/runs/mine`) still work.
9. **Slice 1–2 invariants hold.** Grounded gaps (≥2 citations), idea-blinding,
   model-routing-via-resolver, `X-Robots-Tag` on `/runs/:id`, PII redaction,
   retry/partial-source, restart→failed, rate limit, budget cap, feedback/report —
   all unchanged, re-verified by the slice-1 and slice-2 exit checks.
10. **PRD status updated.** PRD §15 slice table flips all three slices to
    **Shipped**; this spec's reference list and the planning CONTEXT "Current
    Priorities" reflect v1-complete.

A passing slice 3 does **not** require: the full 15–20 idea eval corpus, a CI
regression gate, `quality_signals` in the UI, or any active selection-bias
mitigation (all v1.1).

## 13. Sub-Milestones (each PR independently mergeable)

Ordered so the **additive** measurement/robustness work lands and is verified
*before* the **subtractive** v1 teardown — never entangle new behaviour with
deletion.

1. **Schema + migration.** `QualitySignals` schema, `quality_signals_json`
   column, `GenerateQueriesResult` model. Boundary tests. No behaviour change.
2. **Quality signals computation.** Compute + persist `quality_signals` in
   `run_pipeline_service` post-synthesis; `extraction_yield` collected during
   fan-out. Tests on a fixture run.
3. **Pre-flight robustness.** `generate_queries` validation (§7.1) + orphaned-
   `pending` wrap (§7.2). Tests: malformed payload → `internal_error`, no stranded
   `pending`. (Fan-out parallelization §7.3 only if a latency test shows >10s.)
4. **Low-signal gate re-key.** Count-based gate in `run_pipeline_service.approve`;
   `LOW_SIGNAL_CANDIDATE_THRESHOLD` in config; `low_signal` flag on the pre-flight
   response. Backend + New Run frontend. Tests for the 0 / below / at-threshold cases.
5. **Eval harness + metrics.** `app/eval/harness.py` + `metrics.py` (the four
   scorers, unit-tested as pure functions) + report writer.
6. **Seed set.** 5 hand-labelled seed files (human-authored labels) + a smoke run
   of the harness over all five.
7. **v1 backend teardown.** Drop `/analyze/*`, weekly jobs, `home`/`internal`
   routers, `extractInsights` + `create_response`, `automatic_table*` accessors,
   and the RAG surface (whole-file deletes + surgical `RetrievedInsight`/`RAG_*`
   pruning per §9.1). Import audit per §9. `create_app` trimmed. *Consider
   splitting RAG pruning into its own PR if the shared-file surgery is sizeable.*
8. **v1 frontend teardown.** Delete legacy pages/CSS/components + `/legacy/*`
   routes. Build + v2-route walkthrough.
9. **Docs + PRD status.** Flip PRD §15 to v1-complete; update planning CONTEXT.

PRs 1–6 are additive (safe alongside the live v1 surface). PRs 7–8 are the
teardown, gated on 1–6 being green. PR 9 closes v1.

## 14. Risks Specific to This Slice

- **v1 removal silently breaks a v2 carry-over.** The biggest risk: a v2 path
  imports an ingestion/client/service module that *looks* v1. Mitigation: the §9
  import-audit discipline (`grep` each symbol before deleting), teardown PRs land
  *after* and *separate from* the additive work, and exit criterion 9 re-runs the
  full slice-1/2 checks post-teardown.
- **Eval harness drifts from production.** If the harness reimplements pipeline
  steps, it scores a fiction. Mitigation: §4 requires it to invoke the real
  services and route through the same `resolve(stage)` config — it is a driver,
  not a parallel pipeline.
- **Gate re-key changes who gets warned.** Moving from an LLM guess to a count
  threshold reclassifies some ideas. Mitigation: validate the threshold against
  the pre-flight findings (OQ4) before shipping; the change is *more* correct by
  construction (PRD §15 note) but the threshold value is the lever to get right.
- **`quality_signals` computation adds a failure surface to a `done` path.** A bug
  in the diversity/yield math could fail an otherwise-successful run at persist.
  Mitigation: compute defensively (the field is nullable; a computation error logs
  + persists `null` rather than failing the run) — quality signals are
  observability, never load-bearing for completion.
- **Seed labels are subjective.** Hand-labelled expected gaps encode the author's
  judgment; recall scores inherit that. Accepted for v1 — the seed set proves the
  harness works and sets a baseline (PRD §7.9), it is not claimed to be
  statistically meaningful. The v1.1 corpus is where calibration matters.

## 15. References

*All three slices are shipped (PRD §15 status table) — v1 is complete; pointers
below reflect the shipped state.*

- [PRD v2.2](../../docs/PRD.md) — §7.9 (eval harness, seed set, quality signals),
  §7.2 / §9 (v1 removal), §10.1 (model routing — last hardcoded exception closed
  here), §15 (slice-3 scope + `signal_strength`-gate note + v1.1 deferrals).
- [v2 Slice 1 spec](v2-slice-1-end-to-end_spec.md) — §9 `create_response` carve-out
  (issue #54) retired here; §11 invariants re-verified at slice exit.
- [v2 Slice 2 spec](v2-slice-2-lifecycle-hardening_spec.md) — §3 deferred items
  (pre-flight robustness, orphaned `pending`) were pulled into this slice and
  shipped here; §11 invariants re-verified at slice exit.
- [app/eval/](../../app/eval/) — shipped harness (`harness.py`), the four §7.9
  metric scorers (`metrics.py`), 5-idea seed set (`seed/`), report output
  (`reports/`).
- [run_pipeline_service.py](../../app/services/run_pipeline_service.py) —
  count-based gate re-key (§6) + `quality_signals` computation (§5).
- [preflight_service.py](../../app/services/preflight_service.py),
  [app/llm/preflight.py](../../app/llm/preflight.py) — `generate_queries`
  validation + robustness work (§7).
- [idea_run_service.py](../../app/services/idea_run_service.py) — orphaned-`pending`
  wrap (§7.2).
- [app/main.py](../../app/main.py) — post-teardown, mounts only the health + v2
  `runs` routers (§9).
- [memory: slice1-tables-no-checked-in-migration](../../../.claude/projects/-home-john-Dev-Projects-Trend-Insight-Engine/memory/slice1-tables-no-checked-in-migration.md)
  — migrations must be additive/idempotent.
