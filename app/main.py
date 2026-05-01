from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from starlette.exceptions import HTTPException as StarletteHTTPException

from app.scripts.youtubePipeline import youtube_manual
from app.scripts.appStorePipeline import app_store_manual
from app.scripts.data_save import data_save
from app.preprocessing.validateUrl import validateYoutube, validateAppStore
from app.config.settings import GAME_CATEGORY_ID, SCIENCE_TECH_ID, HOW_TO_STYLE_ID
from app.lib.db import get_weekly_ids
from app.schemas.api import AppStoreAnalyzeRequest, DataSave, YoutubeAnalyzeRequest

import logging
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("api")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.post("/analyze/youtube")
def analyze_youtube(request: YoutubeAnalyzeRequest):
    if not validateYoutube(request.youtubeURL):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid link")
    else:
        return youtube_manual(request.youtubeURL)

@app.post("/analyze/appStore")
def analyze_appStore(request: AppStoreAnalyzeRequest):
    if not validateAppStore(request.appStoreURL):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid link")
    else:
        return app_store_manual(request.appStoreURL)

@app.get("/", include_in_schema=False, name="home")
@app.get("/get/homePage")
def get_home_data():
    ids = []
    try:
        gameData = get_weekly_ids(GAME_CATEGORY_ID)
        ids.append(gameData)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to fetch game data from supabase")
    try:
        scitechData = get_weekly_ids(SCIENCE_TECH_ID)
        ids.append(scitechData)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to fetch scitech data from supabase")
    try:
        howstyleData = get_weekly_ids(HOW_TO_STYLE_ID)
        ids.append(howstyleData)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to fetch style data from supabase")
    return ids

@app.post("/data/send", include_in_schema=False)
def save_data(request: DataSave):
    data_save(request.data)

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):
    message = (
        exception.detail
        if exception.detail
        else "Validation error in request body."
    )
    return JSONResponse(
        status_code=exception.status_code,
        content={"detail": message},
    )

@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )
    return JSONResponse(
        status_code=exception.status_code,
        content={"detail": message},
    )
    