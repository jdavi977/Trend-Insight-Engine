# Current Codebase vs PRD v2.1 — Comparison & Transition Plan

| | |
|---|---|
| **Date** | 2026-05-16 |
| **Compares** | `master` HEAD (`e730864 feat(pipeline): automatic pipeline runs once per week`) |
| **Against** | [docs/PRD.md](PRD.md) v2.1 (idea-first flow, pre-launch review) |
| **Status** | Recommendation memo — no code changes yet |

---

## 1. Framing

Today the product is a **URL-in, problems-out** analyzer: paste a YouTube video or App Store app URL, get a ranked list of problems for *that single source*. A weekly cron does the same thing across the top-N items in a few hard-coded categories and writes them to a "trending" table that powers the Home page.

The PRD reframes the product as an **idea-in, gaps-out** decision-support tool: submit an idea, the system grounds-searches to find ~5 apps + ~5 videos as competitors, the user edits that list, then a parallel pipeline extracts pain per source and **synthesizes cross-competitor gaps** that must cite verbatim quote IDs.

This is not an incremental change. The unit of work, the schema, the URL surface, the storage model, and the frontend all change. Roughly 60–70 % of the existing backend is reusable as *internal primitives* (ingestion, cleaning, the LLM client, the App Store and YouTube clients, the RAG layer if we keep it). The rest — `automatic_table`, the trending pipeline, the weekly cron, the `/analyze/*` endpoints, the `/get/homePage*` endpoints, all four current frontend pages — is replaced.

---

## 2. Side-by-side delta

### 2.1 Unit of work

| Dimension | Current | PRD v2.1 |
|---|---|---|
| Input | YouTube URL **or** App Store URL (one at a time) | Free-text **idea** (+ optional `target_gap`) |
| Output | Per-source `problems[]` (ranked 1-5 severity/frequency) | Cross-source `gaps[]` with quote-grounded evidence, plus per-source pain blocks |
| Granularity | One source per request | 10 sources per run (5 apps + 5 videos) |
| Persistence | Manual runs **not** persisted to Supabase ([app/services/persistence_service.py:5](../app/services/persistence_service.py#L5) writes to local FS only). Only the weekly cron persists. | Every run is persisted to `idea_runs` + `gaps` + `feedback_events` |
| Identity | None (results returned in response, gone afterwards) | Stable `run_id`, public URL, `noindex` headers |

### 2.2 HTTP surface

| Endpoint | Current | PRD v2.1 | Action |
|---|---|---|---|
| `POST /analyze/youtube` | [app/api/youtube.py:10](../app/api/youtube.py#L10) | **removed** — logic moves to internal `services/` | Demote to internal function, drop the router |
| `POST /analyze/appStore` | [app/api/appstore.py:10](../app/api/appstore.py#L10) | **removed** | Same |
| `GET /get/homePage` | [app/api/home.py:10](../app/api/home.py#L10) | **removed** (weekly trending gone) | Delete |
| `GET /get/homePageAppStore` | [app/api/home.py:36](../app/api/home.py#L36) | **removed** | Delete |
| `GET /get/homePageStats` | [app/api/home.py:63](../app/api/home.py#L63) | **removed** | Delete |
| `GET /insights/similar` | [app/api/insights.py:10](../app/api/insights.py#L10) | not in PRD; RAG out of scope for v1 (§12) | Keep behind feature flag (already gated by `RAG_READ_ENABLED`); do not surface in UI |
| `POST /data/send` | [app/api/internal.py:9](../app/api/internal.py#L9) | not in PRD | Delete — internal dev tool, writes to local FS |
| `POST /runs` | — | **new** | Create + pre-flight (synchronous, ≤10s) |
| `POST /runs/:id/approve` | — | **new** | User-edited competitor list + low-signal ack |
| `POST /runs/:id/feedback` | — | **new** | Append-only §4 indicators |
| `POST /runs/:id/report` | — | **new** | Abuse flag |
| `GET /runs/:id` | — | **new** | Poll status + read result |
| `GET /runs` | — | **new** | Public feed (drives Home) |

### 2.3 Data model

| Current store | Used for | PRD verdict |
|---|---|---|
| `automatic_table` (Supabase) | Weekly YouTube trending; one row per (video, problem) | **Removed** (§14.1 resolved) |
| `automatic_apple_table` (Supabase) | Weekly App Store trending | **Removed** |
| `insights` table (pgvector) | RAG embeddings + `enrich_problems` on every run | **Out of scope for v1** (§12). Don't migrate, keep table dormant or drop |
| `data/manually_change.json` (local FS) | `/data/send` ad-hoc save | Delete |
| — | — | **New:** `idea_runs` (durable run row) |
| — | — | **New:** `gaps` (promoted out of JSON blob for cross-run analytics) |
| — | — | **New:** `feedback_events` (append-only) |

### 2.4 Pipeline shape

Current ([app/jobs/automaticPipeline.py:49](../app/jobs/automaticPipeline.py#L49) and the manual `*_service.py`):
```
URL → ingest → clean → LLM extract → LLM refine (with RAG context) → persist (cron only) → return
```
Sequential, one source at a time. Two LLM calls per source (extract + refine). RAG read on every refinement.

Target (§7.3):
```
Idea
  → Pre-flight (1 LLM call + grounded search → competitors + signal_strength)
  → User approves edited competitor list
  → 10 sources fan out concurrently (OpenAI cap 5):
       per source: ingest → clean → PII redact → LLM extract → per-source pain[]
  → 1 synthesis LLM call across all pain items
       → quote-ID grounding validation; drop gaps with 0 cited quotes
  → optional idea-match LLM call (if target_gap supplied)
  → persist full result
```

The per-source path inside the fan-out is structurally what `youtube_service.py` and `appstore_service.py` do today — *minus* the second refinement call, *plus* a PII redaction step and quote-ID tagging. The novel components are pre-flight, parallel fan-out, and synthesis.

### 2.5 Schema delta (problem → gap)

| Current `YoutubeProblemItem` / `AppStoreProblemItem` ([app/schemas/llm.py:7](../app/schemas/llm.py#L7)) | PRD `GapItem` (§7.4) |
|---|---|
| `problem: str` | `gap: str` |
| `type: str` (complaint / feature_request / usability / performance / pricing) | — (dropped) |
| `severity: int` (1–5, no rubric) | `severity: int` (1–5, **anchored rubric in prompt**) |
| `frequency: int` (1–5, LLM-assigned) | `frequency: int` (**raw count** of supporting items, not 1–5) |
| `total_likes` (YT) / `vote_count`+`average_rating` (App Store) | — (collapsed into per-quote `like_count`) |
| `example_reviews` (App Store) | — (replaced by `evidence_quote_ids` pointing into shared `quotes` collection) |
| `similar_insights[]`, `recurrence` (RAG enrichment) | — (RAG out of scope v1) |
| — | `gap_id` (stable, for thumbs-up tracking) |
| — | `spread` (distinct competitors) |
| — | `competitors_present[]` |
| — | `evidence_quote_ids[]` (mandatory, ≥2, validated at synthesis) |

The shared `quotes` collection (§7.4) is entirely new and is the load-bearing piece of the §7.7 quote-then-claim defense.

### 2.6 Frontend pages

| Current page | File | PRD verdict |
|---|---|---|
| **Home** (weekly trending) | [frontend/src/HomePage.jsx](../frontend/src/HomePage.jsx) | **Replace.** PRD Home is a public feed of completed runs |
| **Insights** (browse `automatic_*_table`) | [frontend/src/InsightsPage.jsx](../frontend/src/InsightsPage.jsx) | **Delete.** Trending is gone |
| **YouTube analysis** (paste URL) | [frontend/src/YouTubePage.jsx](../frontend/src/YouTubePage.jsx) | **Delete.** Folded into the "New Run" flow |
| **App Store analysis** (paste URL) | [frontend/src/AppStorePage.jsx](../frontend/src/AppStorePage.jsx) | **Delete.** Same |
| — | — | **New:** New Run (submit form → pre-flight loading → competitor editor + signal-strength panel) |
| — | — | **New:** Run Status / Result (live progress, gap list with verbatim quotes, thumbs-up, direction prompt, report link) |
| — | — | **New:** My Runs (frontend-only filter of `GET /runs` against `localStorage` run_ids) |

### 2.7 Cross-cutting requirements not present today

The PRD adds several non-functional requirements that have **no current implementation**:

- **PII redaction at persist time** (§8): regex strip emails / phones / `@handles` + NER pass for person names. Raw text never stored. Current code stores raw `Text` / `content` straight through.
- **Per-IP rate limit + daily OpenAI budget cap** (§8): 3 runs/hour, 10/day per IP; configurable global $ cap returning `429 budget_exhausted`.
- **Server-restart recovery** (§7.1, §8): in-memory runs in `running` state must transition to `failed` on next read with `failure_reason: server_restart`.
- **Partial completion threshold** (§8): ≥70 % of sources must succeed for a run to complete as `done` with a `partial_sources` banner; otherwise `failed`.
- **`X-Robots-Tag: noindex, nofollow`** on all `/runs/:id` responses.
- **Abuse flow:** `POST /runs/:id/report` hides public view, queues for admin review.
- **Concurrency control:** single active run per server instance; second submission returns `429 busy`.
- **Per-category engagement filters** (§7.5): pre-flight category drives default YouTube `min_likes` and App Store `min_vote_count`. Current preprocessing has these as module-level constants in [app/config/preprocessing.py](../app/config/preprocessing.py), not category-driven.

---

## 3. What is reusable as-is (or with light refactoring)

These modules are internal primitives the new pipeline still needs. Don't rewrite them — wrap them.

| Module | Role in new world |
|---|---|
| [app/clients/youtube.py](../app/clients/youtube.py) | Comment fetch (`list_comment_threads`) becomes one fan-out worker. `list_most_popular` is unused after trending dies. **Add:** YouTube Data API `search.list` for pre-flight competitor discovery |
| [app/clients/appstore.py](../app/clients/appstore.py) | `list_reviews` becomes one fan-out worker. `list_top_apps` is unused after trending dies. **Add:** App Store Search API call for pre-flight |
| [app/clients/openai.py](../app/clients/openai.py) | Reused. Add a concurrency-limiting wrapper (semaphore of 5) to honor §8 |
| [app/clients/supabase.py](../app/clients/supabase.py) | Reused for the new tables. Drop `automatic_*_table` helpers ([app/clients/supabase.py:12-75](../app/clients/supabase.py#L12-L75)) |
| [app/ingestion/](../app/ingestion/) | Reused. These are thin wrappers around the clients |
| [app/preprocessing/reviewPipeline.py](../app/preprocessing/reviewPipeline.py) | Reused. Engagement filter / dedup / normalization still needed. Inject per-category thresholds rather than reading module-level constants |
| [app/preprocessing/validateUrl.py](../app/preprocessing/validateUrl.py) | Reused for validating user-pasted competitor URLs in the editor (§7.6) |
| [app/llm/extractInsights.py](../app/llm/extractInsights.py) | Reused as the per-source extractor — but the output schema changes (drop `severity 1-5 LLM-assigned`, add `quote_id` tagging on each pain item) |
| [app/utilities/textCleaning.py](../app/utilities/textCleaning.py), [app/utilities/getDate.py](../app/utilities/getDate.py) | Reused |
| [app/api/errors.py](../app/api/errors.py) | Reused; extend with `429 busy`, `429 budget_exhausted`, `429 rate_limited` handlers |
| [app/main.py](../app/main.py) | App factory pattern survives; just swap routers |
| [app/rag/rag.py](../app/rag/rag.py) | Cold-storage. Keep behind `RAG_*_ENABLED` flag (already plumbed). Not used by v1 idea flow |

---

## 4. What goes away

| What | Why | Disposition |
|---|---|---|
| `POST /analyze/youtube`, `POST /analyze/appStore` | §7.2: "removed. Their logic moves into internal `services/` functions called directly by the pipeline. (Internal primitives should not be public surface.)" | Demote `youtube_service.youtube_manual` and `appstore_service.app_store_manual` to internal `extract_one_source(...)` helpers used by the fan-out worker. **Delete** the routers |
| `POST /data/send` | Not in PRD; writes to local FS; appears to be a dev ad-hoc tool | Delete |
| `GET /get/homePage*` (3 endpoints) | Weekly trending removed (§14.1) | Delete after frontend Home is replaced |
| Manual refinement call (second `extract_insights` in [app/services/youtube_service.py:49](../app/services/youtube_service.py#L49), [app/services/appstore_service.py:59](../app/services/appstore_service.py#L59)) | New flow has a single synthesis call across all sources; per-source refinement is redundant and burns budget | Delete |
| Weekly cron jobs ([app/jobs/automaticYoutube.py](../app/jobs/automaticYoutube.py), [app/jobs/automaticAppStore.py](../app/jobs/automaticAppStore.py), [app/jobs/automaticPipeline.py](../app/jobs/automaticPipeline.py)) | Weekly trending pipeline removed (§14.1, §12) | Delete after first idea-flow release ships and is verified. **Keep the GitHub Actions workflow files disabled (or delete) at the same time** — see [.github/workflows/weekly-youtube.yml](../.github/workflows/weekly-youtube.yml), `weekly-appstore.yml` |
| [ops/scripts/weeklyYoutube.py](../ops/scripts/weeklyYoutube.py), `weeklyAppStore.py` | Cron entrypoints for the trending pipeline | Delete with the jobs |
| `automatic_table`, `automatic_apple_table` (Supabase) | §14.1 resolved | Drop after data is no longer queried. Snapshot first if there's anything worth archiving |
| `recurrence` / `similar_insights` fields on problems | RAG out of scope for v1 | Strip from output schema; underlying RAG code stays gated |
| Frontend `HomePage.jsx`, `InsightsPage.jsx`, `YouTubePage.jsx`, `AppStorePage.jsx` | All four current pages are replaced by Home (feed) / New Run / Run Status / My Runs | Delete |
| `RetrievedContextAccordion`, `RecurrenceTag` components | RAG enrichment UI; not in PRD | Delete |
| Hard-coded category IDs in [app/config/constants.py](../app/config/constants.py) (`GAME_CATEGORY_ID`, `APPLE_GAMES_GENRE_ID`, etc.) | Trending used these to slice the home page; the idea flow drives categories from pre-flight | Delete |

---

## 5. Recommended transition plan

This is **not** a refactor; it's a parallel build with a single cut-over. The new flow shares ~30 % of its surface with the old (the clients and preprocessing primitives) but everything user-facing is different. Trying to incrementally morph the existing endpoints would leave both halves broken for weeks.

### Phase 0 — Lock in scope (1–2 days, no code)

1. Resolve open questions the PRD leaves implicit:
   - Does pre-flight call OpenAI's grounded-search-capable model, or do we do "App Store search API + YouTube search API → feed candidates to a plain LLM rank step"? (PRD §7.3 implies the latter; confirm.)
   - What's the chosen background-task primitive? Plain `asyncio.create_task` is enough for §8 ("v1: in-process background tasks, single active run per server instance"). No need for Celery / RQ / Arq yet.
   - Where does the PII NER pass run — `spacy`, a small local model, or another OpenAI call? Cost + dependency footprint differs by 10×.
2. Decide RAG fate explicitly: **freeze** (keep code, gate disabled, do not migrate) vs **delete** (rip out `app/rag/`, `app/clients/pgvector.py`, `insights` table, the `enrich_*` calls). Recommendation: **freeze**. Code is well-isolated and there's a reasonable v1.1 case for it.
3. Write the §15 v1.1 golden eval set ticket *now* even though it ships later — without it, "quote-grounding works" is an assertion, not a measurement.

### Phase 1 — Backend foundations (parallel to current API, no routes wired)

Build the new pipeline behind a feature flag (`IDEA_FLOW_ENABLED=false`) so master stays deployable.

1. **New tables.** Migration for `idea_runs`, `gaps`, `feedback_events`. Keep `automatic_*_table` untouched.
2. **New schemas** (`app/schemas/run.py`): `RunStatus` enum, `Competitor`, `Quote`, `PainItem`, `GapItem`, `RunResult`, `FeedbackEvent`. Pydantic at every boundary, per §8.
3. **Pre-flight service** (`app/services/preflight_service.py`): single LLM call + App Store Search API + YouTube `search.list` → returns `{category, signal_strength, signal_reasoning, competitors[]}`. Latency target: ≤10s.
4. **PII redactor** (`app/preprocessing/pii.py`): regex pass for emails / phones / `@handles` + NER for person names. Stable function: `redact(text) → text`. Unit tests with known PII fixtures.
5. **Per-source extraction worker** (`app/services/extract_source.py`): wraps existing ingest → clean → redact → LLM extract. Output is `(pain_items[], quotes[])`. Each pain item carries `quote_ids` referencing the quotes list. **Reuses** ingestion/preprocessing/llm/clients modules without touching them.
6. **Synthesis service** (`app/services/synthesize_service.py`): single LLM call over the pooled `(pain_items, quotes)` set. Validates every returned `GapItem` has ≥2 `quote_id`s that exist in the input pool. Drop violators.
7. **Run orchestrator** (`app/services/run_service.py`): owns the state machine, `asyncio.gather` over 10 sources with a `Semaphore(5)` on OpenAI calls, 70 % partial-success threshold, server-restart-to-failed transition.
8. **Rate limit + budget middleware** (`app/api/middleware/`): per-IP token bucket, global daily spend tracker (read from Supabase counter row, increment atomically).

Tests at every layer using the existing pytest setup. Mock external APIs as today ([app/CONTEXT.md:48](../app/CONTEXT.md#L48)).

### Phase 2 — New routes (still flagged off in prod)

1. Add `app/api/runs.py` with all 6 endpoints from §7.2. Wire only when `IDEA_FLOW_ENABLED=true`.
2. Add `X-Robots-Tag` middleware for `/runs/*` paths.
3. Add `POST /runs/:id/report` admin-side: hide from `GET /runs` and `GET /runs/:id`.
4. Manual end-to-end test with a real OpenAI key against staging.

### Phase 3 — Frontend rebuild

The current four pages share almost no DOM with the target. Build the new pages from scratch in a parallel route tree (e.g. introduce `react-router` if not present yet — the current App.jsx is a manual `currentPage` switch ([frontend/src/App.jsx:51](../frontend/src/App.jsx#L51)) which won't scale to deep-linkable run URLs):

1. `/` → public feed (`GET /runs`)
2. `/new` → idea + target_gap submit → pre-flight loading → competitor editor + signal-strength panel
3. `/runs/:id` → live progress → result (signal banner, partial_sources banner, ranked gaps with verbatim quotes inline, thumbs-up, direction prompt, report link)
4. `/mine` → filter `GET /runs` by `localStorage` run_ids

The PRD is explicit (§7.6) that quotes are rendered **inline next to gaps, not in a drill-down**. This is a deliberate framing choice ("hypothesis, not verdict"); don't relegate them to an accordion the way `RetrievedContextAccordion` does today.

### Phase 4 — Cut over

1. Flip `IDEA_FLOW_ENABLED=true` in prod.
2. Replace frontend bundle.
3. Disable `.github/workflows/weekly-youtube.yml` and `weekly-appstore.yml`.
4. Leave old routes responding for 1 week with a deprecation header (`Sunset: <date>`, `Deprecation: true`) — there are no external consumers but this is cheap insurance.
5. Delete old routes, jobs, scripts, frontend pages, and constants after the deprecation window.

### Phase 5 — Cleanup

1. Drop `automatic_table` and `automatic_apple_table` (snapshot first if any insights are worth archiving).
2. Delete unused helpers in [app/clients/supabase.py](../app/clients/supabase.py).
3. Rename legacy `TBN` identifiers (PRD §13: "legacy `TBN` references in code/comments to be migrated").
4. Update [CLAUDE.md](../CLAUDE.md), [app/CONTEXT.md](../app/CONTEXT.md), [ops/CONTEXT.md](../ops/CONTEXT.md) — the Module Map, API Endpoints, and Weekly Pipeline sections all become wrong the moment Phase 4 ships.

---

## 6. Recommendations on previous features

| Previous feature | Recommendation | Reasoning |
|---|---|---|
| **Single-URL `/analyze/*` endpoints** | **Demote, don't delete (yet).** Convert the service functions to internal `extract_one_source(source_type, url, category)` and call them from the fan-out worker. Drop the public routers. | The mechanics (ingest → clean → extract) are exactly what the new per-source path needs. The only thing being removed is the *public HTTP surface*, which the PRD explicitly forbids |
| **Weekly trending pipeline** (jobs/cron/Supabase tables/Home/Insights pages) | **Delete entirely after Phase 4.** Don't try to keep it running in parallel | §14.1 is resolved. Maintaining two pipelines splits attention and pays double for OpenAI calls. The "trending" framing is also at odds with the PRD's idea-first positioning |
| **RAG layer** (`app/rag/`, `app/clients/pgvector.py`, `insights` table, `/insights/similar`) | **Freeze** — keep code, keep flag off, do not delete | §12 lists RAG as out-of-scope but the v1.1 roadmap (§15) doesn't explicitly bring it back. Code is clean and feature-flagged ([app/config/secrets.py:19](../app/config/secrets.py#L19)), so cost of keeping it is near zero and it's a head-start if a future "cross-run memory" requirement appears |
| **`/insights/similar` endpoint** | **Keep but undocumented.** Already gated by `RAG_READ_ENABLED` | Same logic as RAG freeze. No frontend surface |
| **`POST /data/send` + `data/manually_change.json`** | **Delete.** | Looks like a dev convenience that escaped into the API. No PRD justification |
| **Per-source severity/frequency 1–5 LLM scores** | **Drop the per-source frequency (1–5); replace with raw-count frequency at synthesis time.** Keep per-source severity but rewrite the prompt around the §7.4 anchored rubric | PRD §7.4 explicitly changes frequency semantics from "1–5 LLM judgement" to "raw count of supporting items". Severity stays 1–5 but with a published rubric the current prompts don't have |
| **`example_reviews` field (App Store)** | **Replace with `quote_id` references into the shared `quotes` collection.** Same data, different addressing scheme | Required for §7.7 quote-then-claim validation |
| **`type` field on problems** (complaint / feature_request / usability / performance / pricing) | **Drop unless we have a reason to keep it.** PRD `GapItem` (§7.4) doesn't have `type` | The PRD's "gap" framing is type-agnostic; users get the type implicitly from the verbatim quote. If we want to keep it, propose it as a v1 addition and update the PRD — don't just smuggle it back in |
| **Hard-coded category IDs / genre IDs in [app/config/constants.py](../app/config/constants.py)** | **Delete.** Categories now come from pre-flight | The fixed taxonomy was a trending-era constraint |
| **`automatic_table` / `automatic_apple_table` data** | **Snapshot once, then drop.** Export to a CSV in `ops/archive/` for posterity, then drop the tables | Cheap insurance; some of the extracted problems may be useful as eval-set seeds for §15's golden set |
| **Existing tests under `tests/`** | **Keep tests for primitives** (preprocessing, clients, extractInsights happy-path). **Delete tests for `/analyze/*` and `/get/homePage*` routes** along with the routes | Tests on internal primitives are still load-bearing; route tests die with the routes |
| **GitHub Actions weekly workflows** | **Delete** at Phase 4 | They invoke `ops/scripts/weekly*.py` which are themselves being deleted |
| **`TBN` legacy identifiers** | **Rename to Trend Insight Engine** during Phase 5 | PRD §13 calls this out explicitly |

---

## 7. Risks and open questions

1. **Latency budget for full run is tight.** §8 sets p50 ≤ 5 min with 10 parallel sources behind a Semaphore(5). One slow YouTube `commentThreads.list` call (the current client is synchronous — [app/clients/youtube.py:24](../app/clients/youtube.py#L24)) can stall a worker. Either (a) move clients to `httpx.AsyncClient`, or (b) run the synchronous clients in a thread pool. Option (b) is cheaper; option (a) is cleaner.
2. **Synthesis prompt is the hardest LLM call in the system.** It receives the entire pool of pain items + quotes (could be hundreds of items, thousands of quotes) and must emit ranked gaps with valid quote-ID citations. Token budget needs explicit modeling; might need to truncate or summarize per-source pain items before synthesis.
3. **PII NER is the most ambiguous spec.** "Obvious proper-noun person names" (§8) is judgment-loaded. Pick a deterministic library (e.g. `spacy`'s `en_core_web_sm`) and accept the false-positive/false-negative rate it gives you. Document it in an ADR.
4. **Public-by-URL with `noindex` is the privacy model.** Acceptable for v1 but means every shared run URL is enumerable if `run_id`s are sequential. Use UUIDs, not integers.
5. **Pre-flight depends on App Store Search API quota and YouTube `search.list` (100 quota units per call).** The current YouTube quota usage doc isn't tracked; check the daily quota margin before assuming this works in steady state.
6. **No queue UX in v1** means second-submitter-while-running gets `429 busy` (§8). Frontend needs to handle this politely. The §15 v1.1 queue work is worth scoping early so we don't paint into a corner with the run state machine.
7. **Severity rubric needs spot-check coverage before v1.1's golden eval set lands.** Without it, "severity 4 means X" is just a prompt assertion the LLM can ignore.

---

## 8. TL;DR

- **30 % stays, 70 % goes.** Clients, ingestion, preprocessing, the LLM extraction primitive, and `app/main.py` survive. Everything user-facing — routes, schemas, frontend pages, the weekly cron, both trending Supabase tables — is replaced.
- **Build new in parallel, single cut-over.** Don't try to morph `/analyze/*` into `/runs`. Flag the new flow off, build it end-to-end, cut over once.
- **Freeze RAG, delete trending.** RAG is well-isolated and cheap to keep dormant. Trending is irreconcilable with the idea-first framing and should go.
- **The two novel pieces are pre-flight (grounded search) and synthesis (quote-ID grounding).** Everything else is reshuffling existing primitives. Spend prototyping budget there first.
