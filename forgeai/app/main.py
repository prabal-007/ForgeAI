from fastapi import FastAPI
from app.api.routes_products import router as product_router

app = FastAPI(title="ForgeAI")

app.include_router(product_router, prefix="/products")

@app.get("/")
def root():
    return {"message": "ForgeAI running"}
