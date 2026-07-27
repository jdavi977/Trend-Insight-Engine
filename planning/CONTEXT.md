# Planning Context — Trend Insight Engine

> Authority: [docs/PRD.md](../docs/PRD.md) (v2.2) — Background, §1–§3, §7.1,
> §7.3, §7.5, §7.7–§7.9, §8, §10.1, §15. This file summarises those sections;
> the PRD governs. Read the named sections, not the whole file.

## What This App Does (v2)
Takes a builder's **idea** (vague or specific) and returns a ranked list of
**evidence-backed candidate gaps** drawn from real complaints across relevant
competitors. Every gap is grounded in verbatim, PII-redacted quotes — synthesis
cannot claim a gap that isn't cited to retrieved evidence.

Framing: **decision support, not a verdict.** Best-fit categories are consumer
apps, mobile games, creator tools, productivity. B2B/devtools/enterprise are
warned as low-signal but allowed with explicit acknowledgement.

## Core-Loop Foundation (the scope-down reference)
The foundation this project scales back to is **one loop**: an **idea** goes in →
**pre-flight** classifies it and proposes competitors → **ingest** pulls YouTube
comments and App Store reviews per competitor → **clean** normalises and filters
them → **redact** strips PII → **idea-blinded per-source extraction** turns each
source into pain items without seeing the idea → **quote-then-claim synthesis**
ranks those into candidate gaps → **persisted, quote-grounded gaps** come out.
Everything not serving that loop is **opt-in-later**: cut cleanly and recoverable
from git, never left half-maintained. This paragraph is the reference every
scope-down cut is judged against
([scope-down-core-pipeline_spec.md](specs/scope-down-core-pipeline_spec.md) G1).

**Opt-in-later surfaces** — verdicts and reasons in that spec §5, logged on
[#76](https://github.com/jdavi977/Trend-Insight-Engine/issues/76):

- *Removed (slice 1):* the empty v1-teardown shells `app/rag/`, `app/lib/`,
  `tests/rag/`, `tests/jobs/`; the dead v1 modules
  `preprocessing/validateUrl.py` (+ its test) and `utilities/textCleaning.py`.
- *Removed (slice 2, [#87](https://github.com/jdavi977/Trend-Insight-Engine/issues/87)):*
  the eval harness (`app/eval/` + `tests/eval/`) and the `quality_signals`
  surface it was the only real consumer of — the schema, the pipeline
  computation, and the `quality_signals_json` write. The **column itself still
  exists**; the physical drop is slice 5 (spec R5 — code stops writing first).
- *Still live, scheduled for removal:* the `target_gap` field + `idea_match`
  stage (folded into `idea`); `POST /runs/:id/feedback`, `POST /runs/:id/report`,
  `feedback_events`, and the `reported` state; the dead `preflight_raw_json`
  column. Each leaves in its own slice — this file is updated by the slice that
  removes it, never ahead of it (spec D4).

**Cross-spec consequence of the harness cut** (spec D3, recorded here because
this is where the reliability work will look): the deleted
`pipeline-reliability-hardening` spec's **exit-criterion 5** — *"eval harness
green post-retune, all 5 seed categories, recall not worse"* — is void, as is its
planned `quality_signals` extension (`quotes_dropped_for_budget`). The eventual
engagement-filter retune **must bring its own validation** and must not be filed
citing exit-criterion 5.

**Kept, explicitly** (so a later sweep doesn't re-flag them): `partial_sources_json`
(written + read), `preprocessing/redact.py`, `preprocessing/reviewPipeline.py`,
`jobs/preflight_smoke.py`.

## The v1→v2 Pivot (why this version exists)
v1 was **URL-in, problems-out** for a single source, plus a weekly trending
cron. Two problems drove the pivot (PRD Background):
1. No anchored user — "insights about a URL I already picked" wasn't a real
   workflow.
2. Output shape didn't match the natural workflow — builders start with an
   *idea*, not a competitor URL.

v2 inverts the entry point: **idea-in, cross-competitor gaps-out.**
**Removed:** weekly trending pipeline, `/analyze/youtube` + `/analyze/appStore`
single-URL endpoints, `automatic_table` / `automatic_apple_table` stores.
**Carried over:** per-source extraction logic, App Store / YouTube client
wrappers, PII redaction, Pydantic boundary validation, `api/ → services/` layering.
**Deferred to v1.1:** RAG / canonical-ledger (v3 work), longitudinal tracking.

## Pipeline Flow (v2)
```
Idea text
 → Pre-flight (1 LLM call + grounded search): classify category,
   signal_strength (high|medium|low), propose 5 apps + 5 videos
 → User reviews: acknowledge low-signal if flagged; edit competitor list
 → POST /runs/:id/approve
 → Background job: sources fan out concurrently (≤10), sequential within source:
   ingestion → preprocessing → PII strip → idea-blinded LLM extract → pain list
   (retry once per source; ≥70% must succeed or run fails)
 → Quote-then-claim synthesis (1 LLM call): ranked gaps, each citing ≥2 quote IDs
 → Optional idea-match (if target_gap supplied)
 → Persist to Supabase → done (or done + partial_sources banner)
```

## Run Lifecycle
`pending → preflight_ready → running → done | failed` (plus `reported`,
admin-hidden). `failed` terminal with structured `failure_reason`.

## Architectural Principles
- Layer rule: `api/ → services/` only. Pipeline modules don't import each other.
- Every gap must cite ≥2 retrieved `quote_id`s; uncited/hallucinated-ID gaps
  rejected post-synthesis (PRD §7.7).
- **Idea-blinded extraction:** per-source prompts exclude `idea`/`target_gap`;
  only synthesis + idea-match see them (confirmation-bias mitigation, §7.8).
- Pydantic validates all boundaries; synthesis output additionally validated for
  quote-ID grounding.
- PII redacted at persist time (regex + NER); raw text never persisted (§8).
- **Model routing as config:** every LLM call resolves `(stage) → (model, temp,
  max_tokens)` via one resolver; v1 maps all stages to gpt-4o (§10.1).
- Coverage + quality signals logged per run (citation ratio, severity spread,
  quote-source diversity, extraction yield) — §7.8 / §7.9.

## Current Priorities
- **v1 is complete** (2026-06-11): all three v2.2 slices shipped — the PRD §15
  status table is the source of truth.
  - Slice 1 — end-to-end happy path (shipped 2026-06-01).
  - Slice 2 — lifecycle hardening: sad paths, rate limit + budget cap,
    feedback/report, `react-router-dom` shareable URLs, My Runs
    (shipped 2026-06-06).
  - Slice 3 — eval harness + 5-idea seed set, `quality_signals`, count-based
    low-signal gate, pre-flight robustness, v1 legacy teardown
    (shipped 2026-06-11).
  - The three slice specs were retired with the v2 build; PRD §15 is the
    surviving record.
- The legacy v1 surface is gone: `/analyze/*` endpoints, weekly jobs,
  `automatic_table*`, RAG surface, and the unlinked v1 frontend pages are
  deleted; `create_app` mounts only the v2 routers.
- **Next: v1.1 roadmap (PRD §15)** — full golden eval corpus (15–20 ideas) +
  CI regression gate, queue UX with ETA, longitudinal outcome tracking, user
  research on the §2 workflow, Reddit/HN sources.

## Known Constraints
- Pre-flight ≤10s (user waits); full run ≤5 min p50; cap 5 concurrent OpenAI calls.
- Rate limits: per-IP 3 runs/hr, 10/day; daily OpenAI budget cap → 429.
- v1: in-process background tasks, single active run/instance; 2nd submit → 429 busy.
- Server restart while `running` → `failed` (failure_reason: server_restart).
- Engagement filters per-category (PRD §7.5), applied server-side, not UI-tunable.
- Grounded search depends on App Store + YouTube returning useful results;
  zero-competitor (US-S1) is expected for niche/new categories.
