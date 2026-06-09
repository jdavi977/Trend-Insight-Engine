-- Slice 3 (issue #67): per-run quality signals (PRD §7.9 / spec §8).
--
-- Additive + idempotent per the slice-1 migration note: this runs against a
-- Supabase DB that already carries the slice-1/2 idea_runs schema, not an empty
-- one, so it only ADD COLUMN IF NOT EXISTS — never recreates the table.
--
-- quality_signals_json holds the observability bundle computed post-synthesis:
--   { quote_source_diversity, severity_distribution, single_source_gap_count,
--     extraction_yield }
-- It is logged, not rendered (PRD §7.9). NULLABLE on purpose: a computation
-- error persists NULL rather than failing an otherwise-successful run, so the
-- field is never load-bearing for completion.
ALTER TABLE idea_runs
    ADD COLUMN IF NOT EXISTS quality_signals_json JSONB;
