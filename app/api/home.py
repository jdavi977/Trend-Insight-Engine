from fastapi import APIRouter, HTTPException, status

from app.config.constants import APPLE_GAMES_GENRE_ID, APPLE_SOCIAL_GENRE_ID, APPLE_UTILITIES_GENRE_ID, GAME_CATEGORY_ID, HOW_TO_STYLE_ID, SCIENCE_TECH_ID
from app.clients.supabase import get_weekly_apple_ids, get_weekly_ids, get_all_ids, get_all_apple_ids, get_insights_count

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

@router.get("/get/homePageAppStore")
def get_home_appstore_data():
    ids = []
    try:
        ids.append(get_weekly_apple_ids(APPLE_GAMES_GENRE_ID))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch game data from supabase",
        )
    try:
        ids.append(get_weekly_apple_ids(APPLE_SOCIAL_GENRE_ID))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch scitech data from supabase",
        )
    try:
        ids.append(get_weekly_apple_ids(APPLE_UTILITIES_GENRE_ID))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch style data from supabase",
        )
    return ids


@router.get("/get/homePageStats")
def get_home_page_stats():
    yt_rows = []
    try:
        yt_rows.extend(get_all_ids(GAME_CATEGORY_ID))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch YouTube game data from supabase",
        )
    try:
        yt_rows.extend(get_all_ids(SCIENCE_TECH_ID))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch YouTube science & tech data from supabase",
        )
    try:
        yt_rows.extend(get_all_ids(HOW_TO_STYLE_ID))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch YouTube how-to & style data from supabase",
        )

    app_rows = []
    try:
        app_rows.extend(get_all_apple_ids(APPLE_GAMES_GENRE_ID))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch App Store games data from supabase",
        )
    try:
        app_rows.extend(get_all_apple_ids(APPLE_SOCIAL_GENRE_ID))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch App Store social data from supabase",
        )
    try:
        app_rows.extend(get_all_apple_ids(APPLE_UTILITIES_GENRE_ID))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch App Store utilities data from supabase",
        )

    yt_count = len({row["key"] for row in yt_rows})
    app_count = len({row["app_id"] for row in app_rows})

    try:
        insights_count = get_insights_count()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch insights count from supabase",
        )

    return {
        "items_analyzed": {
            "youtube": yt_count,
            "appstore": app_count,
            "total": yt_count + app_count,
        },
        "problems_extracted": len(yt_rows) + len(app_rows),
        "insights_indexed": insights_count,
    }