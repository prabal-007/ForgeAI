from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.orchestrator import _to_response, regenerate_cover
from app.db.models import Product
from app.dependencies import get_db
from app.services.db_service import StateTransitionError
from app.services.export_service import export_product

router = APIRouter(tags=["products"])


@router.get("/{product_id}")
def get_product_route(product_id: UUID, db: Session = Depends(get_db)) -> dict:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _to_response(product).model_dump()


@router.post("/{product_id}/regenerate-cover")
def regenerate_cover_route(product_id: UUID, db: Session = Depends(get_db)) -> dict:
    """
    Generate or re-generate cover for any product that has brand + idea data.
    Does NOT change pipeline stage or status. Safe to call at any stage.
    Use when design was approved without running, or to refresh the cover art.
    """
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        result = regenerate_cover(db, product_id)
    except StateTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.model_dump()


@router.post("/{product_id}/export")
def export_product_route(product_id: UUID, db: Session = Depends(get_db)) -> dict:
    try:
        export_record = export_product(db, product_id)
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"product": _to_response(product).model_dump(), "export": export_record}
