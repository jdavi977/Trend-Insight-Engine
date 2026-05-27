# Trend Insight Engine — Product Requirements Document

| | |
|---|---|
| **Version** | 2.2 |
| **Status** | Draft (pre-flight validated 2026-05-22) |
| **Last updated** | 2026-05-27 |
| **Owner** | John Lowen David |
| **Supersedes** | v2.1 — added §7.8 selection-bias mitigations, `coverage` field in §7.4, §15 cost-tradeoff table |
| **Pre-flight validation** | PASS — see [findings memo](../planning/prototypes/preflight/findings.md) |

---

## 1. Overview

**Trend Insight Engine** takes a builder's idea — vague (*"2.5d survivor-like game"*) or specific (*"note-taking app with better offline sync"*) — and returns a ranked list of **evidence-backed candidate gaps** drawn from real complaints across relevant competitors. Every gap is anchored to verbatim quotes from the source data; synthesis cannot claim a gap that isn't grounded in retrieved evidence.

The product is **decision support, not a verdict.** Output is a structured starting point for interviews and landing-page tests, not a substitute. The UI reinforces this with signal-strength banners, verbatim quotes next to every claim, and a "report this run" affordance.

**Scope honesty:** the tool works best for consumer apps, mobile games, and creator-facing tools — where users post publicly. For B2B SaaS, devtools, or enterprise software, public signal is thin; the tool warns before running and requires explicit acknowledgement.

## 2. Problem Statement

A solo founder or indie dev doesn't lack ideas — they lack a *quick, structured first pass* on whether an idea addresses real user pain. The hypothesised workflow today (not yet user-validated — see §15):

1. Notice a personal frustration; form an idea.
2. Ask an LLM *"is this already solved?"* — gets marketing-derived feature claims, frequent hallucinations, no user-pain signal.
3. Manually skim App Store reviews and YouTube comments for top competitors.
4. Mentally cross-reference: *"does my idea address something all competitors fail at?"*

Step 2 is shallow. Step 3 is slow. Step 4 happens in the user's head with no structure.

Serious founders eventually move to interviews, surveys, or landing-page tests — and should. Trend Insight Engine is **not a replacement.** It targets the *first* step: a fast scan of public complaint surfaces so the builder enters interviews with sharper hypotheses.

Adjacent tools cover different ground: enterprise feedback platforms (Enterpret, Productboard) serve in-house PMs; horizontal listeners (GummySearch, AppFollow, AnswerThePublic) return raw mentions from single sources. None take an *idea* as input and return a *cross-competitor synthesis* for indie builders. That's the niche.

## 3. Target Audience

**Primary user:** a solo founder or indie dev with an idea (or category interest) who needs a fast first pass on whether it addresses real user pain — before committing to interviews or a build.

- Solo founders pre-coding, deciding whether an idea fills a real gap.
- Indie devs picking their next side-project from a vague category interest.

**Best-fit categories:** consumer apps, mobile games, creator tools, productivity apps. The tool warns when an idea looks B2B/devtools/enterprise.

**Excluded for v1:** in-house PMs, sentiment dashboarders, real-time monitoring users, product strategists at orgs with established research functions.

**User profile:** comfortable with text input, willing to wait minutes, reads structured output, treats results as one input among several.

## 4. Leading Indicators (not success metrics)

**Session-level leading indicators**, not validated success. They tell us a run produced something the user engaged with — not whether they acted on it or whether the gap proved real. Longitudinal validation is deferred (§15).

| Indicator | What "good" looks like | How we measure |
|---|---|---|
| **Non-obvious gap surfaced** | Run surfaces ≥1 cross-source pain pattern the user marks "new to me" | Thumbs-up control on each gap |
| **Direction declared** | User leaves with a stated direction | One-question prompt: continue / shift / drop / need more research |
| **Time-to-result** | ≤5 minutes p50 | Server-side duration; optional user-reported time-saved |

These signals are weak on their own. A run hitting all three with a hallucinated gap is still a failure — §7.4 quote-grounding and the v1.1 golden eval set (§15) are the real defence.

## 5. Non-Goals

- **Not a sentiment dashboard.** Structured pain only — no NPS, no positive/negative ratios.
- **Not real-time.** Each run is on-demand; no streaming, no alerts.
- **Not a general listener.** Only YouTube comments and App Store reviews in v1.
- **Not in-house PM tooling.** Serves outsiders studying a category.
- **Not authenticated.** v1 has no accounts; runs are public by URL (§8 abuse mitigations).
- **Not editorial.** Aggregates public review data, not curated commentary.

## 6. User Stories

### Happy path

| # | As a... | I want to... | So that... |
|---|---|---|---|
| US-1 | indie dev with a specific idea | submit *"note-taking app with offline sync"* and get cross-competitor pain | I learn whether "offline sync" is a real gap |
| US-2 | side-project builder with a vague concept | submit *"2.5d survivor-like game"* and see what nobody has fixed | I can pick a gap as my next project |
| US-3 | user who knows their competitors | edit the LLM's proposed competitor list before the run | I get coverage of the apps/videos *I* care about |
| US-4 | user who started a run | leave and return via a saved URL | I don't babysit a multi-minute job |
| US-5 | user reviewing past work | revisit prior runs from a public feed | I can compare ideas or share results |

### Sad paths

| # | Scenario | Expected behavior |
|---|---|---|
| US-S1 | Pre-flight returns 0 competitors | "No public sources" error; option to paste competitor URLs |
| US-S2 | Pre-flight classifies as low-signal | Prominent warning; require `acknowledged_low_signal: true` |
| US-S3 | Source fails mid-pipeline | `done` + `partial_sources` banner if ≥70% succeeded; else `failed` |
| US-S4 | Server restarts during `running` | Transitions to `failed` with `failure_reason: server_restart` on next read |
| US-S5 | Daily OpenAI budget cap exhausted | `POST /runs` returns `429 budget_exhausted` |
| US-S6 | Per-IP rate limit hit | `429 rate_limited` with retry-after |
| US-S7 | User reports a run as abusive | `POST /runs/:id/report` hides the result pending review |

## 7. Functional Requirements

### 7.1 Run lifecycle

One submission = one run.

```
pending → preflight_ready → running → done | failed
                                    ↘ reported (admin-hidden)
```

`failed` is terminal with a structured `failure_reason`. `reported` hides the public view but keeps the row; admin decides restore or hard-delete.

### 7.2 Endpoints

- **`POST /runs`** — `{ idea, target_gap? }`. Creates run in `pending`. Pre-flight runs synchronously; response held until pre-flight finishes (≤10s, §8), then flips to `preflight_ready`. Per-IP rate-limited.
- **`POST /runs/:id/approve`** — `{ competitors: [{ source, url, name }], acknowledged_low_signal? }`. Validates edited list; `preflight_ready` → `running`; enqueues background pipeline. If pre-flight was `low` signal and the ack flag is missing, returns 400.
- **`POST /runs/:id/feedback`** — `{ new_to_me_gap_ids?, direction?, time_saved_estimate_minutes? }`. Records §4 indicators. **Append-only**. Valid only when `done`.
- **`POST /runs/:id/report`** — `{ reason }`. Hides run; queues for admin review.
- **`GET /runs/:id`** — current state + (when `done`) full results. Public.
- **`GET /runs`** — paginated public feed of recent completed runs. Drives Home.

Legacy `/analyze/youtube` and `/analyze/appStore` are **removed**; their logic moves to internal `services/`.

All `/runs/:id` HTML responses set `X-Robots-Tag: noindex, nofollow`.

### 7.3 Pipeline stages

```
Idea text
  → Pre-flight (single LLM call + grounded search):
      (a) classify category → consumer-app / mobile-game / creator-tool /
          productivity / b2b-saas / devtools / enterprise / other
      (b) signal_strength: high | medium | low + signal_reasoning
      (c) propose competitors via grounded search:
            - App Store Search API → 5 candidates
            - YouTube Data API → 5 candidates
            - LLM ranks + writes one-line justifications

  → User reviews pre-flight:
      - if low signal: prominent warning + explicit acknowledge-or-cancel
      - edit competitor list (add / remove / paste URL)

  → User approves (POST /runs/:id/approve)

  → Background job. Sources fan out concurrently (10 in parallel);
    within each source, stages are sequential:
        ingestion → preprocessing → PII strip → LLM extract → per-source pain list

    Source-failure policy: retry once with backoff; if still failing,
    mark source failed and continue. If ≥70% of sources fail, the run fails.

  → Quote-then-claim synthesis (single LLM call):
        - input: every per-source pain item + retrieved quote IDs
        - output: ranked gaps, each citing quote IDs from the input pool
        - gaps with no cited quotes are rejected

  → If target_gap supplied: idea-match LLM call

  → Persist to Supabase → status `done` (or `done` + `partial_sources` banner)

  → Result page non-blockingly collects §4 indicators
```

Defaults: 5 apps + 5 videos. Engagement filters per category (§7.5). Low-signal runs are not blocked; the user can proceed after acknowledging.

Pre-flight was prototyped and graded against 15 ideas on 2026-05-22 — PASS on all three criteria (90.7% aggregate, 15/15 per-idea floor, signal-strength correct on every flagged idea). See [findings memo](../planning/prototypes/preflight/findings.md).

### 7.4 Output schema

```
{
  run_id, idea, target_gap?, created_at,
  category, signal_strength, signal_reasoning,
  competitors: [...],
  gaps: [GapItem],
  per_app_pain: [AppPainBlock],
  per_video_pain: [VideoPainBlock],
  idea_match?: { gap_id, verdict, evidence_quote_ids },
  coverage: { quotes_retrieved, quotes_cited, citation_ratio },  // §7.8
  partial_sources?: { failed: [{source, name, reason}],
                      succeeded_count, total_count },
  feedback_events?: [ { submitted_at, new_to_me_gap_ids,
                        direction, time_saved_estimate_minutes } ]
}
```

Each `GapItem`:

| Field | Type | Notes |
|---|---|---|
| `gap_id` | str | Stable ID for thumbs-up tracking |
| `gap` | str | Short description of the unaddressed pain |
| `severity` | 1–5 | Anchored rubric below; assigned by synthesis LLM |
| `frequency` | int | **Raw count** of supporting pain items (not 1–5) |
| `spread` | int | Distinct *competitors* (not platforms) where the pain surfaced |
| `competitors_present` | list of names | Competitors whose reviews surfaced this pain (not "competitors failing" — avoids editorial framing) |
| `evidence_quote_ids` | list of str | IDs of retrieved quotes grounding this gap. Synthesizer can only cite from the retrieval set |

**Severity rubric** (baked into synthesis prompt):

| Level | Meaning |
|---|---|
| 1 | Minor annoyance; mentioned in passing |
| 2 | Noticeable friction; core use still works |
| 3 | Significant friction; user actively works around it |
| 4 | Blocks an important use case |
| 5 | Blocks core use; users abandon or 1-star |

Quotes live in a separate collection keyed by `quote_id`:

```
quotes: { "q_abc123": { source, source_id, text_redacted, like_count } }
```

`text_redacted` has emails, phone numbers, `@handles`, and obvious person names stripped at persist time (§8).

`AppPainBlock` and `VideoPainBlock` carry per-source pain items tagged with grounding `quote_id`s.

### 7.5 Engagement filters (per-category defaults)

| Category | YouTube min likes | App Store min vote_count |
|---|---|---|
| consumer-app | 50 | 6 |
| mobile-game | 30 | 4 |
| creator-tool | 25 | 3 |
| productivity | 50 | 6 |
| b2b-saas / devtools / enterprise | 10 | 2 |
| other | 50 | 6 |

Applied server-side based on category; not exposed in v1 UI. Per-run tuning is a v1.1 candidate.

### 7.6 Frontend pages

- **Home** — public feed of recent completed runs (idea text, completed-at, link) + "Start a new run" CTA. Replaces the old weekly-trending Home.
- **New Run** — submit form (idea + optional target gap) → pre-flight loading → **pre-flight review:**
  - **Signal-strength panel.** Shows `signal_strength` + `signal_reasoning`. If `low`, prominent: primary CTA *"Continue anyway — I understand the signal will be thin"*, secondary *"Cancel and refine"*. Acknowledgement gates `approve`.
  - **Competitor list editor.** Add / remove / paste URL. Each candidate shows its search-API source ("found via App Store search for X").
- **Run Status / Result** — stable URL; live progress while `running`, full result when `done`. `X-Robots-Tag: noindex, nofollow`. When `done`:
  - **Signal-strength banner** at the top.
  - **`partial_sources` banner** if any sources failed, naming them.
  - **Ranked gap list** with **verbatim quotes prominent next to each claim** (not hidden in drill-down) — reinforces §1 framing.
  - **Thumbs-up control** per gap → `POST /runs/:id/feedback`.
  - **Direction prompt** after the list: *"continuing / shifting / dropping / need more research?"* — non-blocking, dismissible.
  - **"Report this run"** link → `POST /runs/:id/report`.
- **My Runs** — frontend-only filter of the public feed against `localStorage` `run_id`s.

### 7.7 Quote-then-claim retrieval (v1)

The single largest defence against synthesis hallucination:

1. Per-source extraction emits structured **pain items** + a flat list of **retrieved quotes** with stable `quote_id`s.
2. Synthesis sees the entire quote pool and pain items. Every output `GapItem` must cite ≥2 `quote_id`s from the pool.
3. Post-processing rejects any gap citing IDs not in the pool, or with zero citations.
4. Frontend renders quotes inline next to gaps — users see grounding, not LLM prose.

A formal golden eval set (15–20 ideas, hallucination-rate measured) is **deferred to v1.1** (§15). v1 relies on structural grounding above + manual spot-checks.

### 7.8 Selection-bias mitigations (v1)

§7.7 ensures every gap is *grounded* but does not constrain *which* quotes the synthesizer picks. Known bias vectors:

- Articulate, emotionally-loaded complaints win over quiet but frequent friction.
- The LLM's prior over "what categories of pain exist" shapes clustering.
- If the per-source extractor sees `idea` or `target_gap`, it can over-promote pain matching the user's hypothesis (confirmation bias).

v1 ships three near-zero-cost mitigations:

1. **Idea-blinded extraction.** Per-source prompts exclude `idea` and `target_gap`. Only synthesis sees them; `idea_match` runs after synthesis (§7.3). Removes confirmation bias at zero LLM cost.
2. **Coverage metrics in output.** `coverage: { quotes_retrieved, quotes_cited, citation_ratio }`. UI renders one line: *"12 of 184 retrieved quotes were cited (6%)"*. A run discarding 95% of evidence is structurally weaker than one citing 40%.
3. **Citation count per gap.** UI shows `len(evidence_quote_ids)` next to severity — 2 citations is weaker than 12.

These reduce one bias vector (idea-leakage) and make the rest *visible*, consistent with §1's "decision support, not verdict" framing. They do not *measure* selection bias — that requires the v1.1 golden eval (§15). Higher-cost active mitigations are catalogued in §15.

## 8. Non-Functional Requirements

| Area | Requirement |
|---|---|
| **Latency (pre-flight)** | ≤ 10 seconds. User waits on the page. |
| **Latency (full run)** | ≤ 5 minutes p50 with per-source parallelism. Concurrency cap: 5 simultaneous OpenAI calls. |
| **Concurrency** | v1: in-process background tasks, single active run per server instance. Second submission returns `429 busy` with retry-after. Queue UX deferred to v1.1. |
| **Rate limiting** | Per-IP: 3 runs/hour, 10 runs/day. Daily OpenAI spend cap (env-configurable); excess returns `429 budget_exhausted`. |
| **Reliability** | Server restart while `running` → `failed` with `failure_reason: server_restart` on next read. No silent partial `done`. |
| **Partial completion** | ≥70% sources succeeding → `done` + `partial_sources` banner. Below 70% → `failed`. |
| **External API limits** | Respect YouTube Data API v3, iTunes RSS, App Store Search, OpenAI rate limits. One retry with exponential backoff. |
| **Validation** | Pydantic at module boundaries. Synthesis output additionally validated for quote-ID grounding (§7.7). |
| **Secrets** | All keys via `python-dotenv`. Never hardcoded. |
| **Privacy / PII** | Persist-time redaction: regex strip of emails, phone numbers, `@handles`; NER pass for obvious person names. Raw text never persisted. |
| **SEO surface** | `/runs/:id` set `X-Robots-Tag: noindex, nofollow`. Home feed is indexable but only lists idea text + timestamp, not gap content. |
| **Abuse handling** | `POST /runs/:id/report` immediately hides; queues for admin. Not deleted, hidden pending decision. |

## 9. Data Model

| Store | Used for | Notes |
|---|---|---|
| **Supabase `idea_runs`** | One row per run | `id`, `idea`, `target_gap`, `status`, `category`, `signal_strength`, `signal_reasoning`, `competitors_json`, `quotes_json`, `partial_sources_json`, `created_at`, `updated_at`, `failure_reason`, `reported_at`. Source of truth. |
| **Supabase `gaps`** | One row per surfaced gap | `gap_id`, `run_id` (FK), `gap`, `severity`, `frequency`, `spread`, `competitors_present_json`, `evidence_quote_ids_json`. Promoted out of the run blob for cross-run analytics. |
| **Supabase `feedback_events`** | Append-only feedback log | `id`, `run_id` (FK), `submitted_at`, `new_to_me_gap_ids_json`, `direction`, `time_saved_estimate_minutes`. Never overwritten. |
| **In-memory job state** | Background task progress for active runs | Lost on restart; active runs → `failed` on next read. |

Legacy `automatic_table` and `automatic_apple_table` (weekly trending) are **removed** in v2.

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

Layer rule: `api/` → `services/` only. Pipeline modules don't import each other.

## 11. Alternatives Considered

| Alternative | Why a user would pick it | Where Trend Insight Engine differs |
|---|---|---|
| **Ask ChatGPT** *"is my idea already done?"* | Free, instant | We win on grounding: every claim cites a verbatim quote, not a marketing summary |
| **Read App Store + YouTube by hand** | Authoritative, no synthesis layer | We win on coverage and speed; we cite the same quotes so users keep their judgment |
| **Reddit / HN search** | Rich qualitative signal where the category lives there | We win for app-rated categories (mobile, consumer). v2 may add Reddit |
| **GummySearch / F5Bot** | Cheap, builder-focused | We win on cross-source synthesis: idea → gap, not idea → mention list |
| **AppFollow / AppBot / Sensor Tower** | Mature App Store tooling | We win on idea-first framing + cross-source (App Store + YouTube) |
| **Enterpret / Productboard** | Polished, deep, governance | Priced for in-house PM teams; we serve outsiders studying a category |

## 12. Out of Scope (v1)

- **RAG / cross-run memory.** Chatbot over past runs.
- **Weekly trending pipeline.** Removed in v2.
- **User accounts.** No auth, no per-user namespace.
- **Additional sources.** No Reddit, X, Discord, forums, support tickets.
- **Real-time / streaming.** No scheduled re-runs or alerts.
- **Multi-idea comparison UI.**
- **Public API / SDK.**
- **Pricing / monetization.**
- **Longitudinal outcome tracking.** No "did the gap prove real?" follow-ups (see §15).

## 13. Glossary

- **Trend Insight Engine** — Product name. Legacy `TBN` references in code to be migrated.
- **Idea** — Free-text input describing what to build. May be specific or vague.
- **Target gap** *(optional)* — A specific pain the user thinks their idea addresses. Triggers idea-match step.
- **Competitor** — App or video selected (by grounded search + user) as a source of user pain.
- **Pre-flight** — Cheap LLM + grounded API search that turns an idea into a candidate competitor list.
- **Pain item** — One problem extracted from one source, tagged with grounding `quote_id`s.
- **Quote** — Verbatim user comment retrieved during extraction, PII-redacted, addressable by stable `quote_id`.
- **Gap** — Cross-source synthesized problem ranked by severity + frequency + spread, grounded in cited quote IDs.
- **Quote-then-claim** — Architectural rule: every gap cites ≥2 retrieved quote IDs. Hallucinated IDs rejected.
- **Signal strength** — Pre-flight classification of likely informativeness: high / medium / low.
- **Run** — One end-to-end submission, identified by `run_id`, at a stable URL.
- **Severity** — 1–5 with anchored rubric (§7.4).
- **Frequency** — Raw count of supporting pain items.
- **Spread** — Count of distinct competitors surfacing a gap.

## 14. Resolved Decisions

Major decisions from earlier drafts, resolved in v2.1–2.2 (details in referenced sections):

1. Weekly trending pipeline + old Home — removed; replaced by public feed (§7.6).
2. Run privacy — public by URL with `noindex` + report link (§7.6, §8).
3. Submit form — two fields: `idea` + optional `target_gap`.
4. Product name — Trend Insight Engine throughout; legacy `TBN` to migrate.
5. Cost / abuse — per-IP rate limit + daily OpenAI budget cap. No auth, no BYO-key in v1 (§8).
6. B2B / devtools scope — warn + allow with explicit acknowledgement.
7. Competitor discovery — grounded search + LLM ranks; user edits (§7.3).
8. Severity / frequency — severity 1–5 with anchored rubric; frequency is raw count (§7.4).
9. Engagement filters — per-category defaults, not user-tunable in v1 (§7.5).
10. PII handling — redact at persist; raw text never stored (§8).
11. Concurrency — v1: 429 busy + retry-after. v1.1: queue + ETA.
12. Adversarial submissions — `noindex` + report link. No proactive named-brand blocking.
13. History — public feed (`GET /runs`); "My Runs" is a frontend filter against `localStorage`.
14. Partial completion — `done` + banner if ≥70% sources succeed; else `failed` (§8).
15. Pipeline parallelism — 10 sources fan out concurrently; sequential within source. Cap 5 OpenAI calls.
16. Data model — `gaps` table promoted out of run blob; `feedback_events` append-only (§9).
17. Success metrics framed honestly — §4 indicators are leading, not validated. Longitudinal validation deferred.
18. **Pre-flight prototype validation** — Graded on 15 ideas on 2026-05-22 ([findings](../planning/prototypes/preflight/findings.md)). PASS on all three criteria. Confirmed failure modes: qualifier loss (mitigated by §7.6 competitor editor) and shallow App Store results for B2B devtools (mitigated by §7.5 low-signal warning). Grades were LLM-applied; pass margin is wide enough that grader optimism does not flip outcomes.

    **Build prerequisites (before v1):**
    - Productionise `itunes_search()` into `app/clients/appstore.py`.
    - Tighten YouTube ranker prompt to filter gameplay-only let's-plays (~1 in 10 slip through).
    - *Optional:* extend validation set with an industrial/enterprise idea and re-run before v1 ship.

19. **Selection-bias mitigations (v1)** — Quote-then-claim constrains *grounding* but not *which* quotes. v1 ships three near-zero-cost mitigations (§7.8): idea-blinded extraction, coverage metrics, citation count per gap. Higher-cost active mitigations catalogued in §15.

## 15. v1.1 Roadmap & Known Limitations

Deferred from v1, in rough priority:

1. **Golden evaluation set.** 15–20 ideas with hand-labelled expected gaps; run before every release to measure hallucination and gap-recall regressions. Without it, v1 quality guarantees are structural, not statistical.
2. **Queue UX with ETA.** Replaces `429 busy` with accept-and-queue showing position + estimated start.
3. **Longitudinal outcome tracking.** Optional email at submit; 14-day follow-up: *"did the gap prove real?"* Until this exists, §4 indicators can't distinguish "ran successfully" from "user built on it."
4. **User research on §2.** The four-step workflow is a hypothesis. Interview 5–10 indie devs pre-v1.1.
5. **Per-run engagement-filter tuning** if §7.5 defaults prove wrong.
6. **Reddit + HN sources.** Broadens signal for B2B/devtools/developer-tool categories where App Store + YouTube are thin.

### Selection-bias mitigations beyond v1

§7.8 ships the cheap measures. Higher-cost alternatives below, ordered by cost-to-value ratio.

Cost is *additional LLM work per run* against a v1 baseline of ~12 calls (1 pre-flight + 10 per-source extraction + 1 synthesis; +1 if `target_gap` triggers `idea_match`). Token volume — not call count — drives spend: per-source extraction dominates (each call digests hundreds of comments), and synthesis is the single largest call (sees the entire pooled quote set). The §8 daily OpenAI budget cap is the binding constraint.

| Alternative | Extra work / run | Cost impact | Value |
|---|---|---|---|
| **Stratified sampling at extraction.** Replace top-N-by-likes input with stratified sampling across length, like_count, recency. | 0 (input construction only) | None | Reduces "articulate complaint wins" bias. Best cost/benefit. Promote to v1 if refactor is small. |
| **"What's missing" adversarial pass.** Post-synthesis call: given gap list + stratified sample of un-cited quotes, ask *"what patterns are missed?"* Surface as a banner. | +1 synthesis-sized call | ~15–25% | Visible acknowledgement of misses beats false confidence. Pairs with golden eval. |
| **Cold-model critique.** Second model (different family, low temperature) audits synthesis. | +1 synthesis-sized call, different model | ~15–50% (doubles with a stronger reasoner) | Catches errors a same-family critique would miss. Pairs with adversarial pass. |
| **Multi-framing extraction.** Run per-source extraction twice with different prompts; union pain items. | +10 extraction calls | ~70–80% — will push some runs over §8 cap | Adopt only if golden eval shows multi-framing measurably reduces missed-gap rate. |
| **Golden evaluation set.** 15–20 ideas, hand-labelled; run before every release. | 0 per-run; ~$15–30 per cycle | Off per-run budget | The only mitigation that *measures* selection bias. Prerequisite for justifying any cost-increasing alternative above. |

**Recommended sequencing:**

1. Stratified sampling — free; promote if refactor is clean.
2. Golden eval + "what's missing" together — the eval is what proves the pass is worth ~20%.
3. Cold-model critique — adopt if golden eval shows residual synthesis errors.
4. Multi-framing extraction — last; only after cheaper mitigations plateau measurably.

**Known v1 weaknesses we are accepting:**

- §4 indicators are weak alone. Longitudinal tracking requires email + follow-up infra not justified pre-PMF.
- Quote-then-claim defends against hallucination but not selection bias. v1 reduces one vector and surfaces the rest (§7.8); v1.1 adds measurement (golden eval) and active defence (adversarial pass).
- Grounded competitor search depends on App Store + YouTube returning useful results. For niche/new categories, US-S1 (zero competitors) is the expected outcome.
- YouTube ranker keeps ~1-in-10 gameplay-only let's-plays. Prompt tightening before v1 ship; v1.1 golden eval catches regressions.
- Pre-flight grades were LLM-applied, not human. Aggregate score should be read with that bias; signal-strength classification is objective. Re-running with a wider set (incl. an industrial/enterprise idea) is a candidate before v1 ship.
