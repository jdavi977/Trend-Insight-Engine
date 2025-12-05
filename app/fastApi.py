from fastapi import FastAPI
from pydantic import BaseModel
from scripts.run_youtube_pipeline import run_pipeline

app = FastAPI()

class AnalyzeRequest(BaseModel):
    youtubeURL: str

@app.post("/analyze")
def analyze_video(request: AnalyzeRequest):
    result = run_pipeline(request.youtubeURL)
    return result
