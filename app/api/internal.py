from fastapi import APIRouter

from app.schemas.api import DataSave
from app.services.persistence_service import data_save

router = APIRouter()


@router.post("/data/send", include_in_schema=False)
def save_data(request: DataSave):
    data_save(request.data)
