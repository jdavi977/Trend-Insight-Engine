from fastapi import APIRouter, HTTPException, status

from app.preprocessing.validateUrl import validateAppStore
from app.schemas.api import AppStoreAnalyzeRequest
from app.services.appstore_service import app_store_manual

router = APIRouter()


@router.post("/analyze/appStore")
def analyze_appStore(request: AppStoreAnalyzeRequest):
    if not validateAppStore(request.appStoreURL):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid link")
    return app_store_manual(request.appStoreURL)
