from app.clients.supabase import supabase_client


def upsert_embedding(
    id: str,
    embedding: list[float],
    problem: str,
    type: str,
    severity: int,
    frequency: int,
    source: str,
    source_url: str,
    title: str | None,
    extracted_at: str,
) -> None:
    supabase_client.table("insights").upsert(
        {
            "id": id,
            "embedding": embedding,
            "problem": problem,
            "type": type,
            "severity": severity,
            "frequency": frequency,
            "source": source,
            "source_url": source_url,
            "title": title,
            "extracted_at": extracted_at,
        }
    ).execute()


def query_similar(
    embedding: list[float],
    threshold: float,
    k: int,
) -> list[dict]:
    result = supabase_client.rpc(
        "match_insights",
        {
            "query_embedding": embedding,
            "match_threshold": threshold,
            "match_count": k,
        },
    ).execute()
    return result.data or []
