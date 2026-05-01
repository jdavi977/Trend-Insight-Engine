from pydantic import BaseModel


class YoutubeAnalyzeRequest(BaseModel):
    youtubeURL: str


class AppStoreAnalyzeRequest(BaseModel):
    appStoreURL: str


class DataSave(BaseModel):
    data: dict
