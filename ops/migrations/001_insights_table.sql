-- Enable pgvector extension (requires Supabase pgvector add-on or pg_vector extension)
CREATE EXTENSION IF NOT EXISTS vector;

-- Insights table: one row per ProblemItem, with 1536-dim embedding from text-embedding-3-small
CREATE TABLE IF NOT EXISTS insights (
    id          UUID        PRIMARY KEY,
    problem     TEXT        NOT NULL,
    type        TEXT        NOT NULL,
    severity    INTEGER     NOT NULL,
    frequency   INTEGER     NOT NULL,
    source      TEXT        NOT NULL,   -- 'youtube' | 'app_store'
    source_url  TEXT        NOT NULL,
    title       TEXT,
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    embedding   vector(1536) NOT NULL
);

-- HNSW index for cosine similarity (handles incremental inserts without rebuild)
CREATE INDEX IF NOT EXISTS insights_embedding_idx
    ON insights USING hnsw (embedding vector_cosine_ops);

-- RPC function used by pgvector client for similarity search
CREATE OR REPLACE FUNCTION match_insights(
    query_embedding vector(1536),
    match_threshold FLOAT,
    match_count     INT
)
RETURNS TABLE (
    id           UUID,
    problem      TEXT,
    type         TEXT,
    severity     INTEGER,
    frequency    INTEGER,
    source       TEXT,
    source_url   TEXT,
    title        TEXT,
    extracted_at TIMESTAMPTZ,
    similarity   FLOAT
)
LANGUAGE SQL STABLE
AS $$
    SELECT
        id,
        problem,
        type,
        severity,
        frequency,
        source,
        source_url,
        title,
        extracted_at,
        1 - (embedding <=> query_embedding) AS similarity
    FROM insights
    WHERE 1 - (embedding <=> query_embedding) >= match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
$$;
