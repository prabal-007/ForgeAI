from fastapi import APIRouter
from app.core.orchestrator import run_pipeline

router = APIRouter()

@router.post("/run")
def run():
    return run_pipeline()
