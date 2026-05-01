from fastapi import APIRouter, HTTPException, status

from app.preprocessing.validateUrl import validateYoutube
from app.schemas.api import YoutubeAnalyzeRequest
from app.services.youtube_service import youtube_manual

router = APIRouter()


@router.post("/analyze/youtube")
def analyze_youtube(request: YoutubeAnalyzeRequest):
    if not validateYoutube(request.youtubeURL):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid link")
    return youtube_manual(request.youtubeURL)
