import logging
from fastapi import FastAPI
from routes.webhooks import router as webhooks_router
from routes.health import router as health_router
from routes.api import router as api_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Renci API", version="0.1.0")

app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(api_router)
