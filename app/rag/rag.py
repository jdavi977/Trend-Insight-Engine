"""RAG layer: embed-and-store (write path) and retrieve-similar (read path)."""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone

from app.clients.openai import create_embedding
from app.clients.pgvector import query_similar, upsert_embedding
from app.config.constants import RAG_DEDUP_SIMILARITY, RAG_MIN_SIMILARITY, RAG_TOP_K
from app.schemas.llm import LLMExtraction
from app.schemas.rag import RetrievedInsight

logger = logging.getLogger(__name__)


def _make_id(source_url: str, problem_text: str) -> str:
    digest = hashlib.sha256(f"{source_url}{problem_text}".encode()).digest()
    return str(uuid.UUID(bytes=digest[:16]))


def embed_and_store(extraction: LLMExtraction, source_url: str) -> None:
    """Embed each problem in extraction and upsert into pgvector.

    Errors are swallowed and logged — never fails the caller.
    """
    try:
        extracted_at = datetime.now(timezone.utc).isoformat()
        for problem in extraction.problems:
            text = f"{problem.problem}\n(type: {problem.type})"
            embedding = create_embedding(text)
            # Default: treat this as a new row; ID is derived from URL + problem text.
            row_id = _make_id(source_url, problem.problem)
            # Search for semantically similar rows above the dedup threshold.
            dedup_rows = query_similar(embedding, RAG_DEDUP_SIMILARITY, k=RAG_TOP_K)
            # A match from the same source URL and title means we've seen this problem
            # before — reuse its ID so the upsert overwrites (UPDATE) instead of inserting.
            same_source = next(
                (r for r in dedup_rows if r["source_url"] == source_url and r.get("title") == extraction.title),
                None,
            )
            if same_source:
                # Existing record found: upsert will UPDATE the row in place.
                row_id = same_source["id"]
                print("RAG update: existing problem matched for %r (id=%s)", problem.problem, row_id)
            else:
                # No match: upsert will INSERT a new row.
                print("RAG insert: new problem stored for %r (id=%s)", problem.problem, row_id)
            upsert_embedding(
                id=row_id,
                embedding=embedding,
                problem=problem.problem,
                type=problem.type,
                severity=problem.severity,
                frequency=problem.frequency,
                source=extraction.source,
                source_url=source_url,
                title=extraction.title,
                extracted_at=extracted_at,
            )
    except Exception:
        logger.exception("embed_and_store failed; skipping RAG write")


def enrich_problems(extraction: LLMExtraction) -> LLMExtraction:
    """Attach similar past insights and recurrence tag to each problem in-place."""
    for problem in extraction.problems:
        try:
            matches = retrieve_similar(problem.problem)
            problem.similar_insights = matches
            problem.recurrence = "known" if matches else "new"
        except Exception:
            logger.exception("enrich_problems failed for problem %r; skipping", problem.problem)
            problem.similar_insights = []
            problem.recurrence = "new"
    return extraction


def retrieve_similar(query: str, k: int = RAG_TOP_K) -> list[RetrievedInsight]:
    """Return up to k past insights with similarity >= RAG_MIN_SIMILARITY."""
    embedding = create_embedding(query)
    rows = query_similar(embedding, RAG_MIN_SIMILARITY, k)
    return [
        RetrievedInsight(
            problem=r["problem"],
            type=r["type"],
            severity=r["severity"],
            frequency=r["frequency"],
            source=r["source"],
            source_url=r["source_url"],
            title=r.get("title"),
            extracted_at=r["extracted_at"],
            similarity=r["similarity"],
        )
        for r in rows
    ]
