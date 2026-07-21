# Trend Insight Engine — Product Requirements Document

| | |
|---|---|
| **Version** | 2.2 |
| **Status** | Draft — slice 1 (end-to-end happy path) shipped 2026-06-01; slice 2 (lifecycle hardening) specced |
| **Last updated** | 2026-06-02 |
| **Owner** | John Lowen David |
| **Supersedes** | v2.1 — added §7.8 selection-bias mitigations, `coverage` field in §7.4, §15 cost-tradeoff table. v2.2 adds §7.9 evaluation harness, §10.1 model routing, promotes golden eval seed to v1 scope |
| **Pre-flight validation** | PASS — see [findings memo](../planning/prototypes/preflight/findings.md) |
| **Implementation** | 3-slice build plan, see [§15 status table](#15-v11-roadmap--known-limitations). This PRD remains the v1 *target*; built state is tracked there. |

---

## Background: Why this version exists

v1 was a **URL-in, problems-out analyzer**: paste a YouTube video or App Store app URL, get a ranked list of problems for that single source. A weekly cron extended the same one-shot extraction to top-N items per category, persisting to `automatic_table` / `automatic_apple_table` as a "weekly trending" feed. Successive iterations added RAG retrieval, recurrence tagging, cross-pass refinement, and the v3 canonical-ledger spec.

Two compounding problems drove the pivot:

1. **No anchored user.** v1 grew by feature accretion without a sharp answer to *"who is this for, and what decision are they making?"* Writing the first PRD draft surfaced that the implied user — *someone who wants insights about a specific video or app they've already chosen* — wasn't a real persona with a real workflow. The weekly trending feed had the same problem: popular-video summaries are content, not a decision-support tool.
2. **The output shape didn't match the natural workflow.** A solo founder or indie dev doesn't start with a competitor URL — they start with an *idea* and need a cross-competitor view of unaddressed pain (§2). v1 forced the user to (a) pick a competitor themselves, (b) run it through the analyzer one URL at a time, then (c) do the cross-source synthesis in their head. The two steps the tool *should* own — competitor discovery and cross-source synthesis — were the two steps the tool wasn't doing.

v2 inverts the entry point: **idea-in, cross-competitor gaps-out.** Pre-flight (§7.3) turns the idea into a candidate competitor list the user can edit; the pipeline fans out across the approved sources; quote-then-claim synthesis (§7.7) returns ranked gaps grounded in verbatim quotes. The weekly trending pipeline, the `/analyze/youtube` and `/analyze/appStore` single-URL endpoints, and the `automatic_table` / `automatic_apple_table` stores are **removed** (§7.2, §9) — they served a workflow that wasn't load-bearing.

**What carries over** from v1: per-source extraction logic, App Store / YouTube client wrappers, PII redaction, Pydantic validation at boundaries, and the layered `api/ → services/` architecture (§10). The pivot is in the *framing and entry point*, not a ground-up rewrite of pipeline internals — which is also why the v3 RAG / canonical-ledger work is deferred: it was solving for longitudinal trend detection in a product whose primary user journey is now single-run, idea-scoped.

The cost of the pivot is explicit: §4 leading indicators replace any v1 "weekly engagement" framing, longitudinal outcome tracking is deferred to v1.1 (§15), and the pre-flight stage was prototyped and graded on 15 ideas before committing to the v2 build ([findings memo](../planning/prototypes/preflight/findings.md)) to confirm the new entry point is actually viable before rebuilding around it.

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
| US-4 | user who started a run | keep the result page open and have it update itself as the run finishes | I don't babysit a multi-minute job |
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
- **Run Status / Result** — live progress while `running` (the page polls and updates itself in-session), full result when `done`. The backend `GET /runs/:id` endpoint sets `X-Robots-Tag: noindex, nofollow`. *Navigation is state-based (no shareable/deep-linkable client URL in v2 — see §15); the run is reached in-session by approving it or opening it from the feed.* When `done`:
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

These reduce one bias vector (idea-leakage) and make the rest *visible*, consistent with §1's "decision support, not verdict" framing. They do not *measure* selection bias — that requires the golden eval (§15). Higher-cost active mitigations are catalogued in §15.

### 7.9 Evaluation harness

v1 ships the evaluation harness and a seed set. v1.1 fills the full golden eval corpus (§15). The harness is the prerequisite for every cost-increasing quality improvement in §15 — without measurement, no mitigation can be justified.

**Harness (v1 scope):**

A runner script that takes an idea + hand-labelled expected gaps, executes the full pipeline, and scores the output against four metrics:

| Metric | What it measures | How |
|---|---|---|
| **Gap recall** | Did the expected gaps surface? | Fuzzy match each labelled gap against output gaps; report hit/miss per idea |
| **Hallucination rate** | Gaps with broken or missing grounding | Count gaps whose `evidence_quote_ids` reference IDs not in the quote pool, or with <2 citations |
| **Citation ratio** | What fraction of retrieved evidence was used | `coverage.citation_ratio` — already in §7.4. Logged per run for trend tracking |
| **Severity calibration** | Is the rubric applied consistently? | Flag runs where >80% of gaps are severity 4–5 (inflation) or >80% are 1–2 (deflation) |

The harness outputs a structured JSON report per idea. No CI gate in v1 — runs are manual and results reviewed by hand.

**Seed set (v1 scope):**

5 ideas drawn from the pre-flight validation set (§14.18), each hand-labelled with 3–5 expected gaps and expected severity ranges. Enough to confirm the harness works and establish a baseline, not enough to be statistically meaningful.

Selection criteria for seed ideas: one per category (consumer-app, mobile-game, creator-tool, productivity, low-signal), covering the range of signal strengths.

**Full set (v1.1):**

15–20 ideas with hand-labelled expected gaps. Automated: runs before every prompt or model change. Regression gate: if gap recall drops >15% or hallucination rate exceeds 5%, block the change. See §15 for sequencing with other mitigations.

**Per-run quality signals (v1 scope):**

In addition to `coverage` (§7.4), the output schema gains a `quality_signals` field logged on every production run — not just eval runs:

```
quality_signals: {
  quote_source_diversity: float,   // 0–1; 1 = citations spread evenly across sources
  severity_distribution: [int],    // count of gaps at each severity level [1..5]
  single_source_gap_count: int,    // gaps where spread == 1 (weaker evidence)
  extraction_yield: [{ source, comment_count, pain_item_count }]
}
```

`quote_source_diversity` flags when the synthesizer over-indexes on one source. `extraction_yield` flags sources where hundreds of comments produce very few pain items — a possible extraction failure.

These signals are logged, not surfaced in the UI in v1. They feed the golden eval analysis in v1.1 and inform whether cost-increasing mitigations (adversarial pass, cold-model critique) are justified.

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

### 10.1 Model routing

v1 uses a single model (gpt-4o) for all LLM stages. This section documents the per-stage requirements so that agent orchestration — routing different stages to different models — becomes a configuration change, not an architecture change.

| Stage | Calls / run | Token profile | Latency constraint | v1 model | Future routing candidates |
|---|---|---|---|---|---|
| **Pre-flight** | 1 | Light (idea text + search results) | ≤10s user-facing | gpt-4o | Cheaper/faster (gpt-4o-mini, Haiku-class). Classification + ranking is a simpler task; accuracy must be validated via §7.9 harness before downgrading. |
| **Per-source extraction** | 10 (parallel) | Heavy (hundreds of comments each) | Background; dominates total run time | gpt-4o | Same family. Token volume is the cost driver — stratified sampling (§15) reduces input before model routing helps. |
| **Synthesis** | 1 | Heavy (entire pooled quote set) | Background; single largest call | gpt-4o | Reasoning model (o3-class, Opus with extended thinking). One call per run, highest-stakes output — a stronger model here has the best cost/accuracy ratio. |
| **Idea-match** | 0–1 | Light (gap list + idea text) | Background | gpt-4o | Cheaper model viable; low-stakes relative to synthesis. |
| **Adversarial pass** (v1.1) | 0–1 | Synthesis-sized | Background | — | Different model family (Claude, Gemini). Same-family critique catches fewer blind spots. |
| **Cold-model critique** (v1.1) | 0–1 | Synthesis-sized | Background | — | Different family + low temperature. Independent audit of synthesis output. |

**Implementation rule:** each pipeline stage resolves its model config through a single routing function — `resolve(stage_name) → (model, temperature, max_tokens)` — *before* it calls the LLM. The resolver returns config only; the SDK call itself stays in the stage module (e.g. `app/llm/preflight.py`), not inside the router. The discipline being enforced is "no stage hardcodes a model," not "all SDK calls live in one file." v1 config maps every stage to gpt-4o. Swapping a model for one stage requires changing one config entry and validating against the §7.9 eval harness — no pipeline code changes.

**Cost-neutral orchestration path:** downgrading pre-flight and idea-match to a cheaper model frees ~10–15% of per-run token budget — enough to fund an adversarial pass (§15) at net-zero cost increase. This is the recommended first move when the eval harness shows the cheaper models maintain accuracy on those stages.

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
- **Run** — One end-to-end submission, identified by `run_id`. Addressable server-side at `GET /runs/:id`; the v2 frontend reaches it via in-session state-based navigation (shareable client URLs deferred — §15).
- **Severity** — 1–5 with anchored rubric (§7.4).
- **Frequency** — Raw count of supporting pain items.
- **Spread** — Count of distinct competitors surfacing a gap.
- **Model routing** — Config-driven mapping of pipeline stages to LLM models. v1 maps all stages to gpt-4o; enables agent orchestration without code changes (§10.1).
- **Eval harness** — Runner script that scores pipeline output against hand-labelled expected gaps. Measures gap recall, hallucination rate, citation ratio, severity calibration (§7.9).
- **Golden eval set** — Corpus of ideas with hand-labelled expected gaps used by the eval harness. 5-idea seed in v1; full 15–20 idea set in v1.1.
- **Quality signals** — Per-run metrics (quote diversity, severity distribution, extraction yield) logged for trend analysis. Not surfaced in v1 UI (§7.9).

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
20. **Evaluation harness + seed set (v1)** — Harness runner + 5 hand-labelled ideas ship with v1 (§7.9). Full 15–20 idea corpus and CI regression gate deferred to v1.1. Rationale: the harness is the prerequisite for justifying every cost-increasing mitigation in §15 — shipping the infrastructure early means v1.1 improvements are data-driven from day one.
21. **Model routing as config (v1)** — All LLM calls route through a single `(stage_name) → model` resolver (§10.1). v1 maps everything to gpt-4o. Swapping a model per stage requires one config change + eval harness validation — no pipeline code changes. Rationale: makes agent orchestration (multi-model, cold-model critique) a deployment decision, not an architecture change.

## 15. v1.1 Roadmap & Known Limitations

### Implementation status (3-slice v1 build)

v1 is built in three vertical slices against this PRD — each a tracer bullet through the §10 architecture, additive (not corrective) over the last. This PRD describes the v1 *target*; the table below is the source of truth for what is actually built.

| Slice | Scope | Status |
|---|---|---|
| **Slice 1 — end-to-end happy path** | Idea → pre-flight → approve → parallel per-source extraction → quote-then-claim synthesis → grounded gaps, persisted to Supabase and read in the browser. Endpoints `POST /runs`, `POST /runs/:id/approve`, `GET /runs/:id`, `GET /runs`; pages Home, New Run, Run Result; model-routing resolver (§10.1), idea-blinded extraction (§7.8), persist-time PII redaction (§8), coverage + citation counts (§7.4, §7.8). | **Shipped** 2026-06-01 — [spec](../planning/specs/v2-slice-1-end-to-end_spec.md) |
| **Slice 2 — lifecycle hardening** | Makes the system safe to expose to an untrusted user: §6 sad paths US-S1…S7 and §8 non-functional requirements — source retry + ≥70% partial-source threshold, server-restart → `failed`, per-IP rate limit, daily budget cap, concurrency guard; `POST /runs/:id/feedback` + `POST /runs/:id/report` (the §4 feedback loop); `react-router-dom` migration to shareable `/runs/:id` URLs (below); My Runs. | **Shipped** 2026-06-06 — [spec](../planning/specs/v2-slice-2-lifecycle-hardening_spec.md) |
| **Slice 3 — eval + v1 removal** | Eval harness + 5-idea seed set (§7.9), `quality_signals` field (§7.9), removal of the legacy `/analyze/*` endpoints, weekly jobs, `automatic_table*`, and the unlinked v1 frontend pages; retirement of the v1-only `create_response` LLM helper still reached by those endpoints; removal of the LLM-guessed `signal_strength` **gate** (see note below); pre-flight robustness deferred from the slice-2 review — Pydantic validation of the `generate_queries` output and optional parallelization of the `preflight_service.run` search fan-out (see slice-2 spec §3). | **Shipped** 2026-06-11 — [spec](../planning/specs/v2-slice-3-eval-and-v1-removal_spec.md) |

All three slices have shipped — **v1 is complete** as of 2026-06-11. The §6 sad paths, §8 abuse/cost guards, §4 feedback indicators, and `partial_sources` handling are wired (slice 2); the eval harness + 5-idea seed set, `quality_signals`, and count-based low-signal gate are in place and the legacy v1 surface is removed (slice 3). Remaining work is the v1.1 roadmap below.

**Note — `signal_strength` gate removal (slice 3).** Before slice 3, the low-signal gate (§7.2 approve `400`, §7.3 step (b), §7.6 acknowledgement) keyed off an *LLM-guessed* `signal_strength` produced by the `PREFLIGHT_GENERATE_QUERIES` call **before any search runs**. That guess is biased and redundant: it's generated in the same call that produces the queries (motivated to rate its own queries favourably), its rubric examples conflate searchability with consumer-vs-B2B category, and it predicts an outcome — *"will the App Store + YouTube return real competitors?"* — that materialises seconds later in the same function as the actual candidate count (`preflight_service.run` already logs `len(raw_apps)`, `len(raw_videos)`, `len(candidates)`). The guess can pass a 0-candidate run or block one with 8 real competitors. Slice 3 removed the LLM grade as a **gate** and keyed the acknowledgement on the observed candidate count instead. `signal_reasoning` is **retained** as displayed pre-flight copy (§7.6) — useful UX, just not load-bearing. (Note: US-S1 "zero competitors found" is already the count-based sad path; this folds the low-signal gate into the same evidence.)

### Deferred to v1.1

Deferred from v1, in rough priority (note: eval harness + seed set promoted to v1 scope in §7.9):

1. **Full golden evaluation set.** Expand the v1 seed set (5 ideas, §7.9) to 15–20 ideas with hand-labelled expected gaps. Automate runs before every prompt or model change with regression gates. The seed harness ships with v1; the full corpus and CI gate are v1.1.
2. **Queue UX with ETA.** Replaces `429 busy` with accept-and-queue showing position + estimated start.
3. **Longitudinal outcome tracking.** Optional email at submit; 14-day follow-up: *"did the gap prove real?"* Until this exists, §4 indicators can't distinguish "ran successfully" from "user built on it."
4. **User research on §2.** The four-step workflow is a hypothesis. Interview 5–10 indie devs pre-v1.1.
5. **Per-run engagement-filter tuning** if §7.5 defaults prove wrong.
6. **Reddit + HN sources.** Broadens signal for B2B/devtools/developer-tool categories where App Store + YouTube are thin.

**Note — shareable / deep-linkable run URLs are v1 (slice 2), not v1.1.** Slice-1 frontend shipped on in-session state-based navigation (`currentPage` + `activeRunId`, no client router), so a run currently can't be bookmarked, shared, or reopened across a reload — only revisited within the session via the feed or "My Runs." Real URLs (`/`, `/runs/new`, `/runs/:id`) require a router (`react-router-dom`) and converting the three run-lifecycle pages; this lands in **slice 2** (done before the slice-2 feedback/report UI so that UI isn't built twice), and delivers US-4 ("return via a saved URL") and US-5 sharing. Captured in ADR 2026-06-01 (frontend routing: state vs. router).

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
- Quote-then-claim defends against hallucination but not selection bias. v1 reduces one vector, surfaces the rest (§7.8), and ships the eval harness + seed set (§7.9) to establish a baseline. v1.1 scales the eval corpus and adds active defence (adversarial pass).
- Grounded competitor search depends on App Store + YouTube returning useful results. For niche/new categories, US-S1 (zero competitors) is the expected outcome.
- YouTube ranker keeps ~1-in-10 gameplay-only let's-plays. Prompt tightening before v1 ship; v1.1 golden eval catches regressions.
- Pre-flight grades were LLM-applied, not human. Aggregate score should be read with that bias; signal-strength classification is objective. Re-running with a wider set (incl. an industrial/enterprise idea) is a candidate before v1 ship.
