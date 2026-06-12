"""Root health/version route (issue #72, OQ5).

`GET /` previously belonged to the v1 home page router. With the v1 surface
removed, the root serves a tiny static liveness payload for deploy checks —
no service calls, no Supabase round-trip.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health() -> dict:
    return {"service": "trend-insight-engine", "status": "ok"}
