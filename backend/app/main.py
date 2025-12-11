from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from scripts.run_youtube_pipeline import run_youtube_pipeline
from scripts.run_app_pipeline import run_app_pipeline
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
        return run_youtube_pipeline(request.youtubeURL)

@app.post("/analyze/appStore")
def analyze_appStore(request: AppStoreAnalyzeRequest):
    if not validateAppStore(request.appStoreURL):
        raise HTTPException(status_code=400, detail="Invalid link")
    else:
        return run_app_pipeline(request.appStoreURL)

@app.post("/data/send")
def save_data(request: DataSave):
    data_save(request.data)