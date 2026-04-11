from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.orchestrator import _to_response
from app.db.models import Product
from app.dependencies import get_db

router = APIRouter(tags=["products"])


@router.get("/{product_id}")
def get_product_route(product_id: UUID, db: Session = Depends(get_db)) -> dict:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _to_response(product).model_dump()
