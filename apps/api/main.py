import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.webhooks import router as webhooks_router
from routes.health import router as health_router
from routes.api import router as api_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Renci API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(api_router)
