import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from routes.webhooks import router as webhooks_router
from routes.health import router as health_router
from routes.api import router as api_router
from config import settings

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start email poller if credentials are configured
    task = None
    if settings.renci_email and settings.renci_email_app_password:
        try:
            from email_channel.poller import start_email_poller, stop_email_poller
            task = asyncio.create_task(start_email_poller(interval_seconds=15))
        except Exception as e:
            logging.warning(f"Email poller failed to start: {e}")
    yield
    if task:
        try:
            stop_email_poller()
            task.cancel()
        except Exception:
            pass


app = FastAPI(title="Renci API", version="0.1.0", lifespan=lifespan)

app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(api_router)
