from fastapi import APIRouter, HTTPException, status

from app.config.settings import GAME_CATEGORY_ID, HOW_TO_STYLE_ID, SCIENCE_TECH_ID
from app.lib.db import get_weekly_ids

router = APIRouter()


@router.get("/", include_in_schema=False, name="home")
@router.get("/get/homePage")
def get_home_data():
    ids = []
    try:
        ids.append(get_weekly_ids(GAME_CATEGORY_ID))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch game data from supabase",
        )
    try:
        ids.append(get_weekly_ids(SCIENCE_TECH_ID))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch scitech data from supabase",
        )
    try:
        ids.append(get_weekly_ids(HOW_TO_STYLE_ID))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch style data from supabase",
        )
    return ids
