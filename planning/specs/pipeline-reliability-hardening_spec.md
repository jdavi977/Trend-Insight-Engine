# Pipeline Reliability Hardening — Gap Persistence, Synthesis Budget, Noise Filtering

| | |
|---|---|
| **Status** | Draft |
| **Created** | 2026-07-11 |
| **Owner** | John Lowen David |
| **Parent** | [PRD v2.2](../../docs/PRD.md) |
| **Goal** | Fix two production failures surfaced by real post-v1 runs (`gaps` table PK collision, synthesis-stage OpenAI rate-limit crash) and close the noise-filtering gap that causes the second failure — without the full stratified-sampling redesign PRD §15 defers to v1.1. |

---

## 1. Background — What Broke

v1 shipped 2026-06-11 (PRD §15, all three slices). The first real multi-source
runs against it, captured in
[logs/run_pipeline_debug.log](../../logs/run_pipeline_debug.log) on
2026-07-11, surfaced three problems none of the slice-1/2/3 exit criteria
exercised (no shipped test ran a second run after the first, or a run with a
large multi-source quote pool):

1. **`gaps` insert fails from the second run onward.**
   `run_id=39caf702-...` failed at persist with
   `duplicate key value violates unique constraint "gaps_pkey" ... Key
   (gap_id)=(gap_001) already exists`
   ([run_pipeline_debug.log:13](../../logs/run_pipeline_debug.log#L13)).

2. **Synthesis 429s on multi-source runs.**
   Two subsequent runs (`run_id=7ed6156a-...`, `run_id=1a1d8709-...`) each
   failed with `openai.RateLimitError: 429 ... tokens per min (TPM): Limit
   30000, Requested 31617` / `31843` at the single synthesis call
   ([run_pipeline_debug.log:12](../../logs/run_pipeline_debug.log#L12),
   [:71](../../logs/run_pipeline_debug.log#L71)).

3. **The engagement filter is miscalibrated in both directions.** Working
   notes (`NOTES.md`, 2026-07-10) independently recorded: YouTube comments
   frequently filter down to `[]` (over-filtered), while App Store sources
   routinely hit the 500-review fetch cap with most of it surviving the
   filter (under-filtered) — the latter is what feeds issue 2. Both trace to
   one cause: `ENGAGEMENT_FILTERS` (PRD §7.5) is a flat per-category
   like/vote threshold with no tie to a token or count budget, tuned once in
   slice 1 and never revisited against real fetched volumes.

The PRD already named this exact risk before v1 shipped. §10.1 calls
synthesis "the single largest call (sees the entire pooled quote set)" and
names stratified sampling as the fix, but defers it: "reduces input before
model routing helps... promote to v1 if refactor is small" (§15). It wasn't
promoted. This spec is the minimum that stops runs from crashing — not the
full stratified-sampling redesign.

## 2. What Ships in This Spec

- **`gaps` table composite primary key** — `(run_id, gap_id)` instead of
  `gap_id` alone, applied by hand in the Supabase SQL editor (no checked-in
  migration for this table — [[slice1-tables-no-checked-in-migration]]).
- **A hard token budget on the synthesis call** — cap the serialized
  quote+pain-item payload before it's sent, with deterministic, observable
  trimming. Never a silent drop, never a second surprise 429.
- **Engagement-filter recalibration**, keyed off the asymmetry already
  observed: replace the flat YouTube threshold with a per-category value
  (App Store already has one) and raise the App Store floor enough that a
  500-review fetch doesn't routinely dump 400+ quotes into the pool.
- **Cross-source dedup** on quote text (today only same-source, by content
  hash —
  [per_source_extraction_service.py:117-142](../../app/services/per_source_extraction_service.py#L117-L142))
  so identical boilerplate reviews across apps don't each burn budget.

## 3. Out of Scope

- **Full stratified sampling** (length/likes/recency strata, PRD §15) — a
  bigger refactor, explicitly deferred there pending the eval harness proving
  it's worth it. This spec's budget cap is a backstop, not a replacement.
- **"What's missing" adversarial pass, cold-model critique, multi-framing
  extraction** (PRD §15) — unrelated quality levers, not needed to stop the
  crash.
- **Spam / non-English / bot-comment detection.** No signal in the current
  logs that this is happening; not chasing it speculatively.
- **Per-run configurable engagement thresholds or token budget** — server-side
  constants only, same pattern as `ENGAGEMENT_FILTERS` today (PRD §7.5 note:
  "not UI-tunable").
- **Migrating `gaps` / `idea_runs` / `feedback_events` to checked-in
  migrations in general.** Tracked as its own long-standing gap, not solved
  here.
- **Model upgrade for synthesis** (bigger-context / higher-TPM model). A real
  alternative fix (§10.1 "Future routing candidates"), but it's a cost/quality
  tradeoff via `MODEL_ROUTING` config, not a code change — noted in Open
  Questions (§9), not committed here.

## 4. Issue 1 — `gaps` Primary Key Collision (already fixed)

**Root cause.** [synthesis.py:133](../../app/llm/synthesis.py#L133) mints
`gap_id` as `f"gap_{ordinal:03d}"` — restarting at `gap_001` on every run by
design; it's a **stable ID for thumbs-up tracking within a run**
([docs/PRD.md:204](../../docs/PRD.md#L204)).
[run_pipeline_service.py `_gap_rows`](../../app/services/run_pipeline_service.py#L350-L365)
writes both `gap_id` and `run_id` per row, so the intended unique key is the
pair. The Supabase table (created via dashboard, no migration —
[[slice1-tables-no-checked-in-migration]]) has `gaps_pkey` on `gap_id` alone,
so any run's `gap_001` collides with every other run's.

**Fix.** Composite primary key, applied directly in the Supabase SQL editor:

```sql
-- Pre-check: confirm no existing (run_id, gap_id) duplicates before narrowing the key.
SELECT run_id, gap_id, count(*)
FROM gaps
GROUP BY run_id, gap_id
HAVING count(*) > 1;

-- Then:
ALTER TABLE gaps DROP CONSTRAINT gaps_pkey;
ALTER TABLE gaps ADD CONSTRAINT gaps_pkey PRIMARY KEY (run_id, gap_id);
```

**Blast radius check.** Nothing else treats `gap_id` as globally unique:
`list_gaps_for_run`
([supabase.py:179-188](../../app/clients/supabase.py#L179-L188)) already
scopes by `run_id`; `RunFeedback.new_to_me_gap_ids` validation
([idea_run_service.py:137-139](../../app/services/idea_run_service.py#L137-L139))
checks membership against `list_gaps_for_run(run_id)` — already run-scoped.
No surrogate `id` column is referenced anywhere. Safe, additive schema
change.

## 5. Issue 2 — Synthesis Token Budget Overflow

**Root cause.**
[synthesis.py `_build_user_message`](../../app/llm/synthesis.py#L49-L71)
serializes every `Quote` and every `PainItem` it's handed with no truncation,
count limit, or token estimate.
[run_pipeline_service.py:485-489](../../app/services/run_pipeline_service.py#L485-L489)
feeds it the union of every surviving source's **full** `quote_pool` (not
just cited quotes — grounding requires the whole pool be visible so the model
can cite any of it) across up to 10 sources, uncapped.
`MODEL_ROUTING["synthesis"]`
([constants.py:42](../../app/config/constants.py#L42)) is always `gpt-4o`
regardless of input size. Nothing between ingestion and the OpenAI call ever
estimates or bounds the token count.

This is worse than when slice 1 shipped: `_ingest` now sorts App Store
reviews by `"mostHelpful"` instead of `"mostRecent"`
([run_pipeline_service.py:203-212](../../app/services/run_pipeline_service.py#L203-L212),
currently uncommitted), which front-loads already-voted-up reviews — more of
the 500-cap fetch now clears the engagement threshold than before.

**Fix — token-budget-aware trim before the synthesis call.**

1. Add `SYNTHESIS_TOKEN_BUDGET` to `app/config/constants.py` (proposed
   starting value in Open Questions §9) sized comfortably under the org's
   30k TPM ceiling, leaving headroom for the system prompt +
   `max_tokens=6000` output.
2. In `run_pipeline_service.py`, before calling
   `synthesis_stage.synthesize`, rank the pooled quotes by `like_count`
   descending (existing signal, no new dependency) and take a prefix that
   fits the budget, estimated with `tiktoken` rather than a char-count
   heuristic.
3. **Always keep every quote cited by a surviving `PainItem` first**, before
   filling the rest of the budget by engagement rank — trimming must not
   silently break grounding for pain items that already passed per-source
   extraction.
4. Drop `PainItem`s whose citations got trimmed out (same rule
   `_validate_pain_items` already applies per-source —
   [per_source_extraction_service.py:196-224](../../app/services/per_source_extraction_service.py#L196-L224)).
5. Log the trim (`quotes_dropped_for_budget=<n>`) at the same point
   `quality_signals` is computed, and extend `QualitySignals`
   ([schemas/runs.py:183-196](../../app/schemas/runs.py#L183-L196)) with a
   `quotes_dropped_for_budget: int` field so a trimmed run is observable
   without grepping logs. Nullable-safe like the rest of `quality_signals` —
   never load-bearing for completion.

**Why not just switch models?** A higher-TPM or bigger-context model
(§10.1 "Future routing candidates") sidesteps this specific crash but not the
underlying selection-bias problem PRD §15 already flags, costs more per run,
and is a one-line `MODEL_ROUTING` change independent of this spec if the
budget cap alone proves insufficient. Noted as a fallback in §9, not the
primary fix.

## 6. Issue 3 — Noise Filtering Recalibration

**Root cause.**
`ENGAGEMENT_FILTERS` ([constants.py:88-97](../../app/config/constants.py#L88-L97))
sets YouTube at a flat `10` likes across every category, while App Store
thresholds vary 2–6 by category. Two symptoms follow directly, both already
observed (`NOTES.md`, 2026-07-10):

- **YouTube over-filtered.** Most comments on a given video never reach 10
  likes, so `_filter_by_engagement`
  ([per_source_extraction_service.py:110-114](../../app/services/per_source_extraction_service.py#L110-L114))
  frequently returns `[]`, and `extract_per_source` short-circuits to
  `([], [])`
  ([per_source_extraction_service.py:253-254](../../app/services/per_source_extraction_service.py#L253-L254))
  — a source silently contributes nothing, with no failure signal (it's not
  a `_SourceFailure`, just an empty yield).
- **App Store under-filtered relative to fetch volume.** Thresholds of 2–6
  votes barely trim a 500-review, `mostHelpful`-sorted fetch — this is the
  primary contributor to §5's overflow.

**Fix.**

1. Re-tune `ENGAGEMENT_FILTERS`: replace the flat YouTube `10` with
   per-category values (mirroring the App Store column's existing shape),
   and raise the App Store floor enough that a 500-review fetch trims
   materially. Exact values are a calibration exercise (§9), not guessable
   from the table alone.
2. **Cross-source dedup.** `_build_quote_pool`
   ([per_source_extraction_service.py:117-142](../../app/services/per_source_extraction_service.py#L117-L142))
   dedupes only within one source's comments (hash keyed on
   `source_id|text`). Identical boilerplate ("Great app!", copy-pasted
   review text) across multiple App Store apps currently counts once per
   app. Move dedup to a normalized-text key (lowercased, whitespace-
   collapsed) applied when `all_quotes` is assembled across sources in
   `run_pipeline_service.py`, so a near-identical quote seen on 3 apps costs
   budget once, not 3 times. Keep the highest-engagement instance.
3. **Re-run the slice-3 eval harness seed set**
   ([app/eval/harness.py](../../app/eval/harness.py), 5 categories —
   [app/eval/seed/](../../app/eval/seed/)) before/after threshold changes to
   confirm gap recall doesn't regress — the measurement layer to check this
   didn't exist when the original thresholds were picked in slice 1.

## 7. Data Model Changes

Two changes; the `gaps` one is a manual dashboard operation (no checked-in
migration — [[slice1-tables-no-checked-in-migration]]), the
`quality_signals_json` one is additive/idempotent per the same note.

```
gaps  (existing, manual dashboard change — §4)
  DROP CONSTRAINT gaps_pkey (on gap_id)
  ADD CONSTRAINT gaps_pkey PRIMARY KEY (run_id, gap_id)

idea_runs  (existing, additive)
  quality_signals_json gains quotes_dropped_for_budget (int) inside the
  existing JSONB blob — no column-level migration needed, it's a new key in
  an already-nullable JSONB field.
```

## 8. Schema / Config Additions

- `app/config/constants.py`: `SYNTHESIS_TOKEN_BUDGET` (int); re-tuned
  `ENGAGEMENT_FILTERS` values.
- `app/schemas/runs.py`: `QualitySignals.quotes_dropped_for_budget: int =
  Field(ge=0, default=0)`.
- New pure function (proposed `app/llm/token_budget.py`, or inline in
  `synthesis.py` — Open Question §9) that ranks + trims `(quotes,
  pain_items, budget) → (quotes, pain_items, dropped_count)` using
  `tiktoken`. Unit-testable in isolation, same pattern as
  `app/eval/metrics.py`'s pure scorers.

## 9. Open Questions

1. **`SYNTHESIS_TOKEN_BUDGET` value.** Needs headroom under 30k TPM for the
   system prompt + `max_tokens=6000` output + per-request overhead. Proposed
   starting point ~20k input tokens (leaves ~10k headroom); validate against
   the eval harness seed set's largest-pool idea before committing.
2. **Token counting: `tiktoken` exact count vs. a cheap heuristic
   (chars/4)?** `tiktoken` is exact but adds per-run CPU cost on every
   synthesis call; a heuristic is free but is arguably how this went
   uncaught in the first place. Lean `tiktoken` — the pipeline already pays
   LLM latency measured in seconds, a tokenizer pass is noise.
3. **Re-tuned engagement threshold values.** Proposed direction (YouTube
   per-category instead of flat 10, App Store floor raised) is directional,
   not numeric — needs a pass against real fetched-volume data (the kind
   `NOTES.md` was already collecting) and a green eval-harness run before
   landing, not a guess.
4. **Does a trimmed run need a UI-visible signal**, or is
   `quotes_dropped_for_budget` in `quality_signals` (logged only, same as
   every other quality signal, PRD §7.9) enough for v1? Leaning logged-only,
   consistent with the rest of `quality_signals` — promote to a Result-page
   banner only if trimming turns out to be common in practice.
5. **Fallback model swap for synthesis** (§5 "why not just switch models") —
   worth an experiment against the eval harness independent of this spec, or
   defer until the budget cap alone proves insufficient in production?
6. **YouTube empty-pool sources** — should a source that fetches N comments
   but filters to `[]` count differently for the §8 70%-partial-source
   threshold than an actual fetch failure? Today it's silently "succeeded
   with 0 yield," which historically undercounts how thin a run's real
   evidence base is. Related to, but not required by, this spec's threshold
   retuning — flagging for a decision, not committing a fix here.

## 10. Exit Criteria

1. **No PK collision.** Two consecutive runs each producing a first-ranked
   `gap_001` both persist successfully; `gaps` insert never raises a
   `gaps_pkey` duplicate-key error.
2. **No synthesis 429 from payload size.** A run pooling more than
   `SYNTHESIS_TOKEN_BUDGET` tokens' worth of quotes completes; the trim is
   deterministic (same input → same kept set) and logged.
3. **Grounding contract holds post-trim.** No `PainItem` in a trimmed run
   cites a `quote_id` outside the trimmed pool.
4. **`quotes_dropped_for_budget` observable.** Present (possibly `0`) in
   `quality_signals_json` on every completed run.
5. **Eval harness green post-retune.** All 5 seed-set categories
   (`app/eval/harness.py`) show gap recall not worse than the pre-retune
   baseline after `ENGAGEMENT_FILTERS` changes.
6. **Cross-source dedup verified.** A fixture with the same normalized quote
   text injected across two sources' comment lists contributes exactly one
   `Quote` to `all_quotes`.
7. **No regression to slice 1–3 invariants** — grounding (≥2 citations),
   idea-blinding, model-routing-via-resolver, retry/partial-source,
   `quality_signals` never load-bearing for completion.

## 11. Sub-Milestones (each PR independently mergeable)

1. **`gaps` composite PK** — dashboard SQL change (§4) + a boundary test
   confirming two same-ordinal gaps from different runs persist. No app code
   change.
2. **Token-budget trim function** — pure, unit-tested `(quotes, pain_items,
   budget) → (quotes, pain_items, dropped_count)` helper (§8). No wiring
   yet.
3. **Wire the trim into `run_pipeline_service`** — call the §5/§8 helper
   before `synthesis_stage.synthesize`; extend `QualitySignals` +
   `quotes_dropped_for_budget` logging (§5, §8). Tests: a fixture pool
   exceeding budget trims deterministically and preserves cited quotes.
4. **Cross-source dedup** — normalized-text dedup when assembling
   `all_quotes` (§6.2). Tests: duplicate text across two sources collapses
   to one `Quote`.
5. **Engagement-filter retune** — new `ENGAGEMENT_FILTERS` values (§6.1) +
   eval-harness re-run (§6.3, §9.3) attached to the PR as evidence.

## 12. Risks

- **Trimming introduces a new selection bias** (by-engagement-rank prefix) on
  top of the one PRD §15 already flags for per-source extraction — this spec
  adds the same bias at the synthesis layer as a deliberate tradeoff to stop
  the crash. Mitigation: it's a documented stopgap (§3 names stratified
  sampling as the real fix), and `quotes_dropped_for_budget` makes its
  frequency measurable so it can be prioritized honestly against other v1.1
  work.
- **Threshold retuning shifts which runs are "thin."** Raising the YouTube
  engagement floor could push more sources toward the empty-pool case
  (§9.6). Mitigation: eval-harness recall check (exit criterion 5) before
  landing.
- **`tiktoken`'s tokenizer can drift from the API's actual count** for newer
  models, making the budget estimate slightly off. Acceptable — the budget
  already has headroom (§9.1); it's a backstop against gross overflow, not a
  precise limit.
- **Manual Supabase dashboard change is easy to forget or apply
  inconsistently** across environments (no migration file, per
  [[slice1-tables-no-checked-in-migration]]). Mitigation: exit criterion 1
  is a runtime check, not just a one-time dashboard click — a regression
  here fails loudly (duplicate-key error), it doesn't silently corrupt
  data.

## 13. References

- [PRD v2.2](../../docs/PRD.md) — §7.5 (engagement filters), §7.9 (quality
  signals, eval harness), §10.1 (model routing, synthesis token-volume
  note), §15 (stratified sampling, deferred selection-bias mitigations).
- [logs/run_pipeline_debug.log](../../logs/run_pipeline_debug.log) — the
  three failing runs this spec addresses.
- [NOTES.md](../../NOTES.md) (2026-07-10 entry) — independent observation of
  the YouTube/App Store filtering asymmetry.
- [app/llm/synthesis.py](../../app/llm/synthesis.py) — unbounded prompt
  build (§5).
- [app/services/run_pipeline_service.py](../../app/services/run_pipeline_service.py) —
  quote/pain accumulation, trim call site (§5), `_ingest` sort-order change
  noted in §5.
- [app/services/per_source_extraction_service.py](../../app/services/per_source_extraction_service.py) —
  engagement filter, same-source dedup (§6).
- [app/config/constants.py](../../app/config/constants.py) —
  `ENGAGEMENT_FILTERS`, `MODEL_ROUTING`, new `SYNTHESIS_TOKEN_BUDGET` (§8).
- [app/eval/](../../app/eval/) — harness + seed set used to validate the §6
  retune (§9.3, exit criterion 5).
- [v2 Slice 1 spec](v2-slice-1-end-to-end_spec.md),
  [v2 Slice 3 spec](v2-slice-3-eval-and-v1-removal_spec.md) — prior art for
  the grounding contract and `quality_signals` this spec extends rather than
  replaces.
- [memory: slice1-tables-no-checked-in-migration](../../../.claude/projects/-home-john-Dev-Projects-Trend-Insight-Engine/memory/slice1-tables-no-checked-in-migration.md)
  — why §4/§7's `gaps` change is manual, not a migration file.
