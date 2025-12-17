from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from scripts.youtubePipeline import youtube_manual
from scripts.appStorePipeline import app_store_manual
from scripts.data_save import data_save
from preprocessing.validateUrl import validateYoutube, validateAppStore

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

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

@app.post("/data/send")
def save_data(request: DataSave):
    data_save(request.data)