# Trend Insight Engine — Product Requirements Document

| | |
|---|---|
| **Version** | 2.1 |
| **Status** | Draft |
| **Last updated** | 2026-05-16 |
| **Owner** | John Lowen David |
| **Supersedes** | v2.0 (idea-first run flow, pre-launch review) |

---

## 1. Overview

**Trend Insight Engine** takes a builder's idea — vague (*"2.5d survivor-like game"*) or specific (*"note-taking app with better offline sync"*) — and returns a ranked list of **evidence-backed candidate gaps** drawn from real user complaints across the relevant competitors. Each ranked gap is anchored to verbatim quotes retrieved from the source data; the synthesis step is not allowed to claim a gap that isn't grounded in retrieved evidence.

The product is explicitly **decision support, not a verdict.** The output is a structured starting point for interviews and landing-page tests, not a substitute for them. The UI is built to reinforce this framing: signal-strength banners, prominent verbatim quotes next to every claim, and a "report this run" affordance.

**Scope honesty:** the tool works best for consumer apps, mobile games, and creator-facing tools — categories where users actually post publicly on App Store and YouTube. For B2B SaaS, devtools, or enterprise software, public review signal is thin; the tool will warn before running and require explicit acknowledgement.

## 2. Problem Statement

A solo founder or indie dev usually doesn't lack ideas — they lack a *quick, structured first pass* on whether an idea addresses real user pain. The hypothesised workflow today (not yet validated through user research — see §15):

1. Notice a personal frustration, form an idea.
2. Ask an LLM: *"is this already solved?"* The LLM lists competitors with marketing-derived feature claims. Hallucinations frequent, no real user-pain signal.
3. Manually skim App Store reviews and YouTube comments for the top competitors, trying to spot what users actually complain about.
4. Mentally cross-reference: *"does my idea address something all of those competitors fail at?"*

Step 2 is shallow (marketing copy, no user data). Step 3 is slow. Step 4 happens in the user's head with no structure.

Serious founders eventually move to interviews, surveys, or landing-page tests — and they should. Trend Insight Engine is **not a replacement for those.** It targets the *first* step: a fast, structured scan of public complaint surfaces so the builder enters interviews with sharper hypotheses instead of a blank page.

Existing tools cover adjacent ground: enterprise feedback platforms (Enterpret, Productboard) serve in-house PM teams; horizontal listening tools (GummySearch, AppFollow, AnswerThePublic) return raw mentions from single sources. None take an *idea* as input and return a *cross-competitor synthesis* of unaddressed complaints packaged for indie builders. That's the niche.

## 3. Target Audience

**Primary user: a solo founder or indie dev who has an idea (or a category interest) and needs a fast first pass on whether it addresses real user pain — before committing to interviews or a build.**

- Solo founders pre-coding, deciding whether an idea fills a real gap.
- Indie devs picking their next side-project from a vague category interest.

**Best-fit idea categories:** consumer apps, mobile games, creator tools, productivity apps — anywhere users post publicly. The tool will warn (and require acknowledgement) when an idea looks B2B/devtools/enterprise, where the source signal is thin.

**Excluded for v1:** in-house PMs analyzing their own product, sentiment dashboarders, real-time monitoring users, product strategists at orgs with established research functions (they need governance and rigor this tool doesn't provide).

**User profile:** comfortable with a short text input, willing to wait minutes for the analysis, can read structured output, will treat the result as one input among several rather than a verdict.

## 4. Leading Indicators (not success metrics)

These are **session-level leading indicators**, not validated success measures. They tell us a run produced something the user engaged with — they do not tell us whether the user acted on it, or whether the surfaced gap proved real. Longitudinal validation (did the user build? did the gap turn out real?) is deferred; see §15.

| Indicator | What "good" looks like | How we measure it |
|---|---|---|
| **Non-obvious gap surfaced** | The run surfaces at least one cross-source pain pattern the user marks as "new to me" | User marks ≥1 gap as "new to me" via a thumbs-up control on the result page |
| **Direction declared** | The user leaves the result page with a stated direction — pursue, pivot, drop, or "need more research" | One-question prompt: *"After this run, are you (a) continuing, (b) shifting, (c) dropping, (d) need more research?"* — any non-empty answer recorded; (d) is not failure |
| **Time-to-result** | A run completes in ≤5 minutes p50 so it can replace ad-hoc review-skimming | Pipeline duration measured server-side; user-reported time-saved captured as a secondary, optional signal |

These signals are weak on their own. A run that hits all three indicators with a hallucinated gap is still a failure — the §7.4 quote-grounding rule and the §7.7 golden eval set (deferred to v1.1) are what actually defend against bad output.

## 5. Non-Goals

Trend Insight Engine is explicitly **not**:

- **Not a sentiment dashboard.** No NPS scores, no positive/negative ratios. Structured pain only.
- **Not real-time.** Each run is a fresh on-demand pull; no streaming, no alerts.
- **Not a general-purpose social listener.** Only YouTube comments and App Store reviews in v1.
- **Not in-house PM tooling.** Serves outsiders studying a category, not teams analyzing their own product.
- **Not authenticated / multi-tenant.** v1 has no user accounts; runs are public by URL (see §8 for abuse mitigations).
- **Not editorial.** Result pages aggregate public review data; they are not curated commentary about any specific product.

## 6. User Stories

### Happy path

| # | As a... | I want to... | So that... |
|---|---|---|---|
| US-1 | indie dev with a specific idea | submit *"note-taking app with offline sync"* and get cross-competitor pain | I learn whether "offline sync" is a real gap or already solved |
| US-2 | side-project builder with a vague concept | submit *"2.5d survivor-like game"* and see what nobody in the category has fixed | I can pick the gap that interests me as my next project |
| US-3 | user who knows their competitors | edit the LLM's proposed competitor list before the expensive run starts | I get coverage of the apps/videos *I* care about, not what the API returned |
| US-4 | user who started a run | leave the tab, come back via a saved URL, see the result | I don't have to babysit a multi-minute job |
| US-5 | user reviewing past work | revisit prior runs from a public feed | I can compare ideas or share a result with a collaborator |

### Sad paths (must be designed for, not bolted on)

| # | Scenario | Expected behavior |
|---|---|---|
| US-S1 | Pre-flight returns 0 competitors for a niche idea | Show a "no public sources found" error with the option to manually paste competitor URLs |
| US-S2 | Pre-flight classifies the idea as low-signal (B2B/devtools/enterprise) | Show a prominent warning + require explicit `acknowledged_low_signal: true` to proceed |
| US-S3 | A source fails mid-pipeline (App Store throttles, video deleted, OpenAI 5xx) | Run completes as `done` with a banner listing which sources failed, provided ≥70% of sources succeeded; otherwise `failed` |
| US-S4 | Server restarts while a run is in `running` | The run transitions to `failed` on next read with reason `server_restart`. No partial `done` states |
| US-S5 | Daily OpenAI budget cap exhausted | New `POST /runs` returns `429 budget_exhausted` with a retry-after-tomorrow message |
| US-S6 | Per-IP rate limit hit | `429 rate_limited` with retry-after seconds |
| US-S7 | User believes a run is abusive (e.g. names a single product, leaks PII the redactor missed) | `POST /runs/:id/report` flags the run; result page is hidden pending review |

## 7. Functional Requirements

### 7.1 Run lifecycle

A *run* is the unit of work. One submission = one run.

```
pending → preflight_ready → running → done | failed
                                    ↘ reported (admin-hidden)
```

`failed` is terminal and carries a structured `failure_reason`. `reported` hides the public view but keeps the row; an out-of-band admin process decides whether to restore or hard-delete.

### 7.2 Endpoints

- **`POST /runs`** — body: `{ idea: str, target_gap?: str }`. Creates a run in `pending`, returns `{ run_id, status }` immediately. The pre-flight call runs synchronously in the request and the response is held until pre-flight finishes (≤10s target per §8) before flipping the status to `preflight_ready`. Rate-limited per IP.
- **`POST /runs/:id/approve`** — body: `{ competitors: [{ source, url, name }], acknowledged_low_signal?: bool }`. Validates the edited competitor list; transitions `preflight_ready` → `running` and enqueues the background pipeline. If pre-flight returned `signal_strength: "low"`, the request must include `acknowledged_low_signal: true` or the server returns 400.
- **`POST /runs/:id/feedback`** — body: `{ new_to_me_gap_ids?: [str], direction?: "continue" | "shift" | "drop" | "more_research", time_saved_estimate_minutes?: int }`. Records §4 indicators. **Append-only** (each submission stored as a separate event; prior feedback is never overwritten). Only valid when run is `done`.
- **`POST /runs/:id/report`** — body: `{ reason: str }`. Hides the run from public views and queues it for admin review.
- **`GET /runs/:id`** — returns current state + (when `done`) full results. Public.
- **`GET /runs`** — returns a public feed of recent completed runs (idea text, status, created_at, run_id). Paginated. Doubles as the Home page content.

The legacy `/analyze/youtube` and `/analyze/appStore` HTTP endpoints are **removed**. Their logic moves into internal `services/` functions called directly by the pipeline. (Internal primitives should not be public surface.)

All `/runs/:id` HTML responses set `X-Robots-Tag: noindex, nofollow` so result pages don't accrue SEO surface area.

### 7.3 Pipeline stages

```
Idea text
  → Pre-flight (single LLM call + grounded search):
      (a) classify idea category
          → consumer-app / mobile-game / creator-tool / productivity
            / b2b-saas / devtools / enterprise / other
      (b) emit signal_strength: "high" | "medium" | "low"
          + signal_reasoning (short, user-readable explanation)
      (c) propose competitors using grounded search:
            - App Store Search API → 5 candidate apps for the category
            - YouTube Data API search → 5 candidate review/discussion videos
            - LLM ranks + writes a one-line justification per candidate
          (fewer if APIs return fewer; explicit error if 0)

  → User reviews pre-flight result:
      - if signal_strength == "low": prominent warning + explicit
        acknowledge-and-continue or cancel choice
      - competitor list (add / remove / paste URL)

  → User approves (POST /runs/:id/approve)

  → Background job starts. Pipeline runs sources in parallel:
        all 10 sources fan out concurrently;
        within each source, stages remain sequential.
      For each App Store app:
        ingestion → preprocessing → PII strip → LLM extract → per-app pain list
      For each YouTube video:
        ingestion → preprocessing → PII strip → LLM extract → per-video pain list

      If a source fails:
        - retry once with backoff
        - if it still fails, mark that source as failed and continue
        - if ≥70% of sources fail, fail the whole run

  → Quote-then-claim synthesis (single LLM call):
        - input: every per-source pain item, each with retrieved quote IDs
        - synthesizer outputs ranked gaps; each gap MUST cite quote IDs
          drawn from the per-source pain items
        - a gap with no cited quotes is rejected and dropped

  → If target_gap was supplied: idea-match LLM call

  → Persist full result to Supabase

  → Status → done (or done with `partial_sources` banner)

  → Post-run: result page collects §4 indicators non-blockingly
    via POST /runs/:id/feedback
```

Defaults: 5 apps + 5 videos per run. Engagement filters default per category (§7.6). Low-signal runs are not blocked — the user can proceed after acknowledging the warning.

### 7.4 Output schema

A completed run returns:

```
{
  run_id, idea, target_gap?, created_at,
  category,                     // pre-flight classification
  signal_strength,              // "high" | "medium" | "low"
  signal_reasoning,             // short LLM-written explanation, shown as a
                                //  banner on the result page so readers can
                                //  weight the output appropriately
  competitors: [...],
  gaps: [GapItem],              // headline output
  per_app_pain: [AppPainBlock],
  per_video_pain: [VideoPainBlock],
  idea_match?: { gap_id, verdict, evidence_quote_ids },
  partial_sources?: {           // present iff some sources failed
    failed: [{ source, name, reason }],
    succeeded_count: int,
    total_count: int
  },
  feedback_events?: [           // append-only list of feedback submissions
    { submitted_at, new_to_me_gap_ids, direction, time_saved_estimate_minutes }
  ]
}
```

Each `GapItem`:

| Field | Type | Notes |
|---|---|---|
| `gap_id` | str | Stable ID for thumbs-up tracking |
| `gap` | str | Short description of the unaddressed pain |
| `severity` | 1–5 | **Anchored rubric, see below.** Assigned by synthesis LLM |
| `frequency` | int | **Raw count** of supporting per-source pain items (not 1–5) |
| `spread` | int | Distinct *competitors* (not platforms) where this pain surfaced |
| `competitors_present` | list of names | Competitors whose reviews/comments surfaced this pain. **Not** "competitors failing" — that framing implied editorial judgment |
| `evidence_quote_ids` | list of str | IDs of retrieved quotes that ground this gap. **The synthesizer cannot invent quotes — only cite from the retrieval set.** |

**Severity rubric** (baked into the synthesis prompt; published for transparency):

| Level | Meaning |
|---|---|
| 1 | Minor annoyance; user mentions in passing |
| 2 | Noticeable friction; core use still works |
| 3 | Significant friction; user actively works around it |
| 4 | Blocks an important use case |
| 5 | Blocks core use; users abandon or 1-star because of this |

Quotes themselves live in a separate `quotes` collection in the response, keyed by `quote_id`, so the schema doesn't duplicate the text:

```
quotes: {
  "q_abc123": { source, source_id, text_redacted, like_count }
}
```

`text_redacted` has emails, phone numbers, `@handles`, and obvious proper-noun person names stripped at persistence time (see §8 privacy).

`AppPainBlock` and `VideoPainBlock` carry per-source pain items, each also tagged with the `quote_id`s that grounded them.

### 7.5 Engagement filters (per-category defaults)

The pre-flight category drives default engagement thresholds:

| Category | YouTube min likes | App Store min vote_count |
|---|---|---|
| consumer-app | 50 | 6 |
| mobile-game | 30 | 4 |
| creator-tool | 25 | 3 |
| productivity | 50 | 6 |
| b2b-saas / devtools / enterprise | 10 | 2 |
| other | 50 | 6 |

Thresholds are not exposed in the v1 UI; they're applied server-side based on category. Per-run tuning is a v1.1 candidate if defaults prove wrong.

### 7.6 Frontend pages

- **Home** — public global feed of recent completed runs (idea text, completed-at, link to result) + "Start a new run" CTA. Replaces the old weekly-trending Home.
- **New Run** — submit form (idea + optional target gap) → pre-flight loading → **pre-flight review step**:
  - **Signal-strength panel.** Shows `signal_strength` and `signal_reasoning`. If `low`, the panel is prominent and the primary CTA reads *"Continue anyway — I understand the signal will be thin"* with a secondary *"Cancel and refine my idea"*. Required acknowledgement gates the `approve` call.
  - **Competitor list editor.** Add / remove / paste URL. Each pre-flight candidate shows the search-API source ("found via App Store search for X") rather than implying LLM omniscience.
  - User confirms to start the run.
- **Run Status / Result** — stable URL; live progress while `running`, full result when `done`. Headers include `X-Robots-Tag: noindex, nofollow`. When `done`, the page shows:
  - A **signal-strength banner** at the top.
  - A **`partial_sources` banner** if any sources failed, naming them.
  - The ranked gap list with **verbatim evidence quotes prominent next to each claim** (not hidden in a drill-down), reinforcing the "hypothesis, not verdict" framing from §1.
  - A **thumbs-up control** on each `GapItem` → records `new_to_me_gap_ids` via `POST /runs/:id/feedback`.
  - A **single-question direction prompt** after the gap list: *"After this run, are you continuing, shifting to a surfaced gap, dropping it, or do you need more research?"* — submission is non-blocking and dismissible.
  - A **"Report this run"** link in the footer → `POST /runs/:id/report`.
- **My Runs** — visitor's recent runs, filtered from the public feed by `run_id`s in `localStorage`. Stateless on the server.

### 7.7 Quote-then-claim retrieval (v1)

The single largest defence against synthesis hallucination. Implementation outline:

1. Per-source extraction produces structured **pain items** *and* a flat list of **retrieved quotes** (the verbatim source text underlying each pain item). Each quote gets a stable `quote_id`.
2. The cross-source synthesis prompt receives the entire pool of quotes and pain items. The prompt requires every output `GapItem` to cite ≥2 `quote_id`s drawn from the pool.
3. Post-processing rejects any `GapItem` whose cited `quote_id`s aren't present in the input pool (hallucinated IDs) or that has zero citations.
4. The frontend renders quotes inline next to gaps; users see grounding, not LLM prose.

A formal golden eval set (15–20 ideas with expected gaps, measured against hallucination rate) is **deferred to v1.1** (§15). v1 relies on the structural grounding above plus manual spot-checks during development.

## 8. Non-Functional Requirements

| Area | Requirement |
|---|---|
| **Latency (pre-flight)** | ≤ 10 seconds. User waits on the page. |
| **Latency (full run)** | ≤ 5 minutes p50 with per-source parallelism. Concurrency cap of 5 simultaneous OpenAI calls to respect rate limits. |
| **Concurrency** | v1: in-process background tasks, single active run per server instance. Second submission while one is running returns `429 busy` with retry-after seconds. (Queue UX with ETA deferred to v1.1, §15.) |
| **Rate limiting** | Per-IP: 3 runs/hour, 10 runs/day. Global daily OpenAI spend cap configurable via env; new `POST /runs` returns `429 budget_exhausted` when exceeded. |
| **Reliability** | Server restart while `running` → run transitions to `failed` with `failure_reason: server_restart` on next read. No silent partial `done` states. |
| **Partial completion** | A run with ≥70% sources succeeding completes as `done` with a `partial_sources` banner. Below 70%, run is `failed`. |
| **External API limits** | Respect YouTube Data API v3 daily quota, iTunes RSS rate limits, App Store Search API rate limits, OpenAI rate limits. All external calls have one retry with exponential backoff. |
| **Validation** | All inputs and LLM outputs validated by Pydantic at module boundaries. Synthesis output additionally validated for quote-ID grounding (§7.7). |
| **Secrets** | All keys loaded via `python-dotenv`. Never hardcoded. |
| **Privacy / PII** | Verbatim review text passes through a redaction step at persist time: regex strip of emails, phone numbers, `@handles`, and a named-entity pass for obvious person names. Redacted text is what's stored and rendered. Raw text is never persisted. |
| **SEO surface** | `/runs/:id` pages set `X-Robots-Tag: noindex, nofollow`. The Home feed is indexable but lists only idea text + timestamp, not gap content. |
| **Abuse handling** | `POST /runs/:id/report` hides the public view immediately and queues for admin review. Reported runs are not deleted; they're hidden pending decision. |

## 9. Data Model

| Store | Used for | Notes |
|---|---|---|
| **Supabase `idea_runs`** | One row per submitted run | Columns: `id`, `idea`, `target_gap`, `status`, `category`, `signal_strength`, `signal_reasoning`, `competitors_json`, `quotes_json`, `partial_sources_json`, `created_at`, `updated_at`, `failure_reason`, `reported_at`. Durable source of truth. |
| **Supabase `gaps`** | One row per gap surfaced | Columns: `gap_id`, `run_id` (FK), `gap`, `severity`, `frequency`, `spread`, `competitors_present_json`, `evidence_quote_ids_json`. Promoted out of the run blob so we can do cross-run analytics (e.g. "which categories produce gaps with highest spread?"). |
| **Supabase `feedback_events`** | Append-only feedback log | Columns: `id`, `run_id` (FK), `submitted_at`, `new_to_me_gap_ids_json`, `direction`, `time_saved_estimate_minutes`. Never overwritten — every submission is a new row. |
| **In-memory job state** | Background task progress for an active run | Lost on restart; active runs transition to `failed` on next read. |

The legacy `automatic_table` and `automatic_apple_table` (weekly trending) are **removed** from the v2 flow (resolved decision, §14.1).

## 10. Architecture (high level)

```
┌──────────┐   POST /runs              ┌────────────┐
│ Frontend │ ─────────────────────────►│  FastAPI   │
│  (React) │ ◄─────────────────────────│  routers   │
└──────────┘                           └─────┬──────┘
       ▲                                     │
       │ GET /runs/:id (poll)         ┌──────▼──────┐
       └──────────────────────────────│ idea_run_   │──── rate-limit
                                      │ service     │      + budget
                                      └──────┬──────┘
                                             │
              ┌──────────────────────────────┼────────────────────────┐
              ▼                              ▼                        ▼
       pre-flight (LLM +              parallel per-source       quote-then-claim
       App Store / YouTube            extraction workers          synthesis
       search APIs)                   (ingest → PII strip          (validates
                                       → LLM extract)              quote-ID grounding)
                                             │
                                             ▼
                                     Supabase: idea_runs
                                     + gaps + feedback_events
```

Layer rule (unchanged): `api/` → `services/` only. Pipeline modules don't import each other.

## 11. Alternatives Considered

| Alternative | Why a user would pick it | Why Trend Insight Engine is different / where the alternative wins |
|---|---|---|
| **Asking ChatGPT** *"is my idea already done?"* | Free, instant | Free wins on speed. We win on grounding: every claim cites a verbatim quote from a real user, not a marketing-derived summary. |
| **Reading App Store reviews + YouTube comments by hand** | Authoritative source, no synthesis layer | Manual wins on nuance and judgment. We win on coverage and speed — and we cite the same quotes back, so the user can still apply their judgment. |
| **Reddit / HN search** | Often the actual founder default; rich qualitative signal | Reddit/HN win where category discussion lives there. We win for app-rated categories (mobile, consumer apps) where App Store + YouTube carry the signal. v2 may add Reddit. |
| **GummySearch / F5Bot** | Cheap, builder-focused, polished | Strong for single-source listening. We win on cross-source synthesis: idea → gap, not idea → mention list. |
| **AppFollow / AppBot / Sensor Tower** | Mature App Store review tooling | Mature wins on App Store depth and historical data. We win on idea-first framing and cross-source (App Store *and* YouTube) synthesis. |
| **Enterprise feedback tools (Enterpret, Productboard)** | Polished, deep, governance | Priced and shaped for in-house PM teams analyzing one product. We serve outsiders studying a category. |

## 12. Out of Scope (v1)

Explicitly deferred:

- **RAG / cross-run memory.** A chatbot that answers questions over the corpus of past runs, with a list of prior queries.
- **Weekly trending category pipeline.** The Sunday cron and trending Home page do not serve the idea-first flow. Resolved in §14.1: removed.
- **User accounts.** No auth, no per-user namespace. Runs are public by URL (with §8 abuse mitigations).
- **Additional sources.** No Reddit, X, Discord, forums, support tickets.
- **Real-time / streaming.** No scheduled re-runs, no alerts.
- **Multi-idea comparison UI.** Each run stands alone.
- **Public API / SDK.**
- **Pricing / monetization.**
- **Longitudinal outcome tracking.** No follow-up email asking "did the gap prove real?" — see §15.

## 13. Glossary

- **Trend Insight Engine** — Product name. The codebase still uses some internal abbreviations (e.g. legacy `TBN`); these should be migrated.
- **Idea** — Free-text input describing what the user wants to build. May be specific (*"note-taking app with offline sync"*) or vague (*"2.5d survivor-like game"*).
- **Target gap** *(optional)* — A specific pain the user thinks their idea addresses. Triggers an idea-match step at the end of the run.
- **Competitor** — An app or video selected (by grounded search + the user) as a source of user pain about the idea's category.
- **Pre-flight** — Cheap LLM call + grounded API search that turns an idea into a candidate competitor list for user approval.
- **Pain item** — One problem extracted from one source (per-app or per-video), tagged with the `quote_id`s grounding it.
- **Quote** — A verbatim user comment retrieved during extraction, with PII redacted, addressable by a stable `quote_id`.
- **Gap** — A cross-source synthesized problem: pain that appears across multiple competitors, ranked by combined severity + frequency + spread signal, and grounded in cited quote IDs.
- **Quote-then-claim** — The architectural rule that every gap must cite ≥2 retrieved quote IDs. Hallucinated quote IDs are rejected at validation.
- **Signal strength** — Pre-flight classification of how informative public review data is likely to be for the idea's category: high / medium / low.
- **Run** — One end-to-end submission, identified by `run_id`, persisted at a stable URL.
- **Severity** — 1–5 with anchored rubric (§7.4).
- **Frequency** — Raw count of supporting pain items (not 1–5).
- **Spread** — Count of distinct competitors that surfaced a given gap.

## 14. Resolved Decisions

Decisions resolved during the v2.1 revision (all of these were open in earlier drafts):

1. **Weekly trending pipeline + old Home page** — Removed. Replaced by the public-feed Home in §7.6.
2. **Run privacy default** — Public by URL, with `noindex` headers and a report-link affordance (§7.6, §8).
3. **Submit-form shape** — Two-field form: `idea` + optional `target_gap`.
4. **Product name** — Trend Insight Engine throughout. Legacy `TBN` references in code/comments to be migrated.
5. **Cost / abuse model** — Per-IP rate limit + daily OpenAI budget cap. No auth, no BYO-key in v1.
6. **B2B / devtools / enterprise scope** — Warn + allow with explicit acknowledgement; not refused.
7. **Competitor discovery** — Grounded search via App Store Search API + YouTube Data API, then LLM ranks. User edits.
8. **Severity / frequency** — Severity is 1–5 with anchored rubric in the prompt. Frequency is raw count, not 1–5.
9. **Engagement filters** — Per-category defaults (§7.5). Not user-tunable in v1.
10. **PII handling** — Redact at persist; raw text never stored.
11. **Concurrency UX** — v1: 429 busy with retry-after. v1.1: queue with ETA.
12. **Adversarial submissions** — `noindex` + `Report this run` link. No proactive named-brand blocking.
13. **History** — Public global feed via `GET /runs` (drives Home page). "My Runs" is a frontend-only filter of the feed against `localStorage` `run_id`s.
14. **Partial completion** — `done` with `partial_sources` banner if ≥70% sources succeed; otherwise `failed`.
15. **Pipeline parallelism** — Per-source parallelism (10 sources fan out concurrently); stages within a source remain serial. Cap of 5 concurrent OpenAI calls.
16. **Data model** — Top-level + `gaps` table promoted out of the JSON blob; `feedback_events` is append-only.
17. **Success measurement honesty** — §4 metrics reframed as leading indicators, not validated success. Longitudinal validation deferred to v1.1.

## 15. v1.1 Roadmap & Known Limitations

Deferred from v1 but planned, in rough priority order:

1. **Golden evaluation set.** 15–20 representative ideas with hand-labelled expected gaps. Run before every release to measure hallucination rate and gap-recall regressions. Without this, v1's quality guarantees are structural (quote-grounding) but not statistical.
2. **Queue UX with ETA.** Replaces v1's `429 busy` response with an accept-and-queue model showing position and estimated start time.
3. **Longitudinal outcome tracking.** Optional email collected at submit; 14-day follow-up asking *"did the gap prove real / did you act on it?"* Until this exists, the §4 indicators are session-only and can't distinguish "ran successfully" from "produced something the user actually built on."
4. **User research on the problem statement.** §2's four-step workflow is a hypothesis, not a validated finding. Pre-v1.1 we should interview 5–10 indie devs to confirm the assumed pain.
5. **Per-run engagement-filter tuning.** If §7.5 per-category defaults prove wrong for some categories.
6. **Reddit + HN sources.** Significantly broadens signal for B2B/devtools and developer-tool categories where App Store + YouTube are thin.

**Known v1 weaknesses we are explicitly accepting:**

- The §4 indicators are weak signals on their own. We are shipping with them anyway because longitudinal tracking requires email collection and follow-up infrastructure that isn't justified pre-product-market-fit.
- Quote-then-claim grounding defends against pure hallucination but not against *selection bias* — the LLM still chooses which quotes ground the synthesis. v1.1's golden eval set is the primary mitigation.
- The grounded competitor search depends on App Store and YouTube returning useful results for the idea's category. For very niche or very new categories, US-S1 (zero-competitors error) is the expected outcome.
