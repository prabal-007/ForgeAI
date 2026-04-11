from fastapi import FastAPI

from app.api.routes_pipeline import router as pipeline_router
from app.api.routes_products import router as product_router
from app.db.session import init_db

app = FastAPI(title="ForgeAI")

app.include_router(product_router, prefix="/products")
app.include_router(pipeline_router, prefix="/pipeline")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def root() -> dict:
    return {"message": "ForgeAI running"}
