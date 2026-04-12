from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.orchestrator import approve_stage, create_pipeline_product, regenerate_stage, reject_stage, run_stage
from app.dependencies import get_db
from app.models.product import ProductCreateRequest, ProductTransitionRequest, StageActionResponse
from app.services.db_service import StateTransitionError

router = APIRouter(tags=["pipeline"])


def _handle_transition_error(exc: StateTransitionError) -> None:
    raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/products", response_model=StageActionResponse)
def create_product_route(request: ProductCreateRequest, db: Session = Depends(get_db)) -> StageActionResponse:
    try:
        return create_pipeline_product(db, request.brief)
    except StateTransitionError as exc:
        _handle_transition_error(exc)


@router.post("/{product_id}/run", response_model=StageActionResponse)
def run_stage_route(product_id: UUID, db: Session = Depends(get_db)) -> StageActionResponse:
    try:
        return run_stage(db, product_id)
    except StateTransitionError as exc:
        _handle_transition_error(exc)


@router.post("/{product_id}/approve", response_model=StageActionResponse)
def approve_stage_route(product_id: UUID, db: Session = Depends(get_db)) -> StageActionResponse:
    try:
        return approve_stage(db, product_id)
    except StateTransitionError as exc:
        _handle_transition_error(exc)


@router.post("/{product_id}/reject", response_model=StageActionResponse)
def reject_stage_route(
    product_id: UUID,
    request: ProductTransitionRequest,
    db: Session = Depends(get_db),
) -> StageActionResponse:
    try:
        return reject_stage(db, product_id, request.reason)
    except StateTransitionError as exc:
        _handle_transition_error(exc)


@router.post("/{product_id}/regenerate", response_model=StageActionResponse)
def regenerate_stage_route(product_id: UUID, db: Session = Depends(get_db)) -> StageActionResponse:
    try:
        return regenerate_stage(db, product_id)
    except StateTransitionError as exc:
        _handle_transition_error(exc)
