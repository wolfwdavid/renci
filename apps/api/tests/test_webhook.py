"""Tests for the FastAPI webhook endpoint and health check."""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Health endpoint returns healthy status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "renci-api"


@pytest.mark.asyncio
async def test_sms_webhook_new_user():
    """SMS webhook handles a new user registration start."""
    with patch("routes.webhooks.route_message", new_callable=AsyncMock, return_value="Welcome to Renci!"):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/webhooks/sms",
                data={
                    "From": "+12125551234",
                    "Body": "Hi",
                    "NumMedia": "0",
                },
            )
    assert resp.status_code == 200
    assert "Welcome to Renci!" in resp.text
    assert "<?xml" in resp.text
    assert "<Message>" in resp.text


@pytest.mark.asyncio
async def test_sms_webhook_returns_twiml():
    """SMS webhook returns valid TwiML XML."""
    with patch("routes.webhooks.route_message", new_callable=AsyncMock, return_value="Hours updated!"):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/webhooks/sms",
                data={
                    "From": "+12125551234",
                    "Body": "Update hours Mon-Fri 9-5",
                    "NumMedia": "0",
                },
            )
    assert resp.headers["content-type"] == "application/xml"
    assert "<Response>" in resp.text
    assert "Hours updated!" in resp.text
