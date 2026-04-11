from fastapi import APIRouter

router = APIRouter(tags=["products"])


@router.get("/")
def list_products() -> dict:
    # Placeholder until DB integration.
    return {"items": []}
