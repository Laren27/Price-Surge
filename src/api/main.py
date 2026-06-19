# src/api/main.py

from fastapi import FastAPI
from src.api.routers import analysis, restaurants

app = FastAPI(
    title="Food Delivery Surge Pricing API",
    description="Weather-aware dynamic pricing analysis of 19 restaurants in Bhubaneswar.",
    version="1.0.0"
)

# Health check — always build this first.
# Lets you confirm the server is running before testing real endpoints.
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "message": "API is running"}

# Attach routers
app.include_router(restaurants.router)
app.include_router(analysis.router)