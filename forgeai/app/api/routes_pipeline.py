from fastapi import APIRouter

from app.core.orchestrator import run_pipeline
from app.models.product import PipelineRunRequest, PipelineRunResponse

router = APIRouter(tags=["pipeline"])


@router.post("/run", response_model=PipelineRunResponse)
def run_pipeline_route(request: PipelineRunRequest) -> PipelineRunResponse:
    return run_pipeline(request)
