from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from app.scripts.youtubePipeline import youtube_manual
from app.scripts.appStorePipeline import app_store_manual
from app.scripts.data_save import data_save
from app.preprocessing.validateUrl import validateYoutube, validateAppStore
from app.config.settings import GAME_CATEGORY_ID, SCIENCE_TECH_ID, HOW_TO_STYLE_ID
from app.lib.db import get_weekly_ids
from typing import Any, Optional
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

class ErrorResponse(BaseModel):
    error: str
    message: str
    request_id: Optional[str] = None
    details: Optional[Any] = None

class YoutubeAnalyzeRequest(BaseModel):
    youtubeURL: str

class AppStoreAnalyzeRequest(BaseModel):
    appStoreURL: str

class DataSave(BaseModel):
    data: dict

@app.post("/analyze/youtube")
def analyze_youtube(request: YoutubeAnalyzeRequest):
    if not validateYoutube(request.youtubeURL):
        raise HTTPException(status_code=400, detail="Invalid link")
    else:
        return youtube_manual(request.youtubeURL)

@app.post("/analyze/appStore")
def analyze_appStore(request: AppStoreAnalyzeRequest):
    if not validateAppStore(request.appStoreURL):
        raise HTTPException(status_code=400, detail="Invalid link")
    else:
        return app_store_manual(request.appStoreURL)

@app.get("/get/homePage")
def get_home_data():
    ids = []
    gameData = get_weekly_ids(GAME_CATEGORY_ID)
    scitechData = get_weekly_ids(SCIENCE_TECH_ID)
    howstyleData = get_weekly_ids(HOW_TO_STYLE_ID)
    ids.append(gameData)
    ids.append(scitechData)
    ids.append(howstyleData)
    return ids

@app.post("/data/send")
def save_data(request: DataSave):
    data_save(request.data)