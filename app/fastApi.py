from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from scripts.run_youtube_pipeline import run_pipeline
from preprocessing.ValidateUrl import validateURL

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class AnalyzeRequest(BaseModel):
    youtubeURL: str

@app.post("/analyze")
def analyze_video(request: AnalyzeRequest):
    if not validateURL(request.youtubeURL):
        raise HTTPException(status_code=400, detail="Invalid link")
    else:
        result = run_pipeline(request.youtubeURL)
        return result
