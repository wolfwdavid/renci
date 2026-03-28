"""Tests for the multi-step SMS registration flow."""

import pytest
from unittest.mock import AsyncMock, patch
from sms.twilio_handler import IncomingSMS
from agent.actions.registration import handle_registration


def _make_sms(body: str, from_number: str = "+12125551234") -> IncomingSMS:
    return IncomingSMS(
        from_number=from_number,
        body=body,
        media_urls=[],
        num_media=0,
    )


@pytest.mark.asyncio
async def test_new_user_gets_welcome():
    """First message from unknown number starts registration."""
    with patch("agent.actions.registration.get_owner_by_phone", new_callable=AsyncMock, return_value=None), \
         patch("agent.actions.registration.create_owner", new_callable=AsyncMock, return_value={"id": "o1", "phone": "+12125551234", "registration_step": "name", "registration_data": {}}):
        result = await handle_registration(_make_sms("Hi"))
    assert "Welcome" in result or "welcome" in result.lower()
    assert "你的店叫什么名字" in result


@pytest.mark.asyncio
async def test_name_step_asks_for_type():
    """After providing name, registration asks for business type."""
    owner = {
        "id": "o1",
        "phone": "+12125551234",
        "registration_step": "name",
        "registration_data": {},
    }
    with patch("agent.actions.registration.get_owner_by_phone", new_callable=AsyncMock, return_value=owner), \
         patch("agent.actions.registration.update_owner", new_callable=AsyncMock):
        result = await handle_registration(_make_sms("Wong's Bakery"))
    assert "Wong's Bakery" in result
    assert "1=Restaurant" in result or "Restaurant" in result


@pytest.mark.asyncio
async def test_type_step_invalid_input():
    """Invalid type selection gets re-prompted."""
    owner = {
        "id": "o1",
        "phone": "+12125551234",
        "registration_step": "type",
        "registration_data": {"name": "Wong's Bakery"},
    }
    with patch("agent.actions.registration.get_owner_by_phone", new_callable=AsyncMock, return_value=owner):
        result = await handle_registration(_make_sms("banana"))
    assert "1-7" in result


@pytest.mark.asyncio
async def test_type_step_valid_input():
    """Valid type selection moves to address step."""
    owner = {
        "id": "o1",
        "phone": "+12125551234",
        "registration_step": "type",
        "registration_data": {"name": "Wong's Bakery"},
    }
    with patch("agent.actions.registration.get_owner_by_phone", new_callable=AsyncMock, return_value=owner), \
         patch("agent.actions.registration.update_owner", new_callable=AsyncMock):
        result = await handle_registration(_make_sms("2"))
    assert "address" in result.lower() or "地址" in result


@pytest.mark.asyncio
async def test_address_appends_nyc():
    """Address without NYC gets NYC appended."""
    owner = {
        "id": "o1",
        "phone": "+12125551234",
        "registration_step": "address",
        "registration_data": {"name": "Wong's Bakery", "business_type": "bakery"},
    }
    with patch("agent.actions.registration.get_owner_by_phone", new_callable=AsyncMock, return_value=owner), \
         patch("agent.actions.registration.update_owner", new_callable=AsyncMock):
        result = await handle_registration(_make_sms("65 Mott St"))
    assert "New York" in result
    assert "Y/N" in result


@pytest.mark.asyncio
async def test_address_confirm_yes():
    """Confirming address moves to email step."""
    owner = {
        "id": "o1",
        "phone": "+12125551234",
        "registration_step": "address_confirm",
        "registration_data": {"name": "Wong's Bakery", "business_type": "bakery", "address": "65 Mott St, New York, NY"},
    }
    with patch("agent.actions.registration.get_owner_by_phone", new_callable=AsyncMock, return_value=owner), \
         patch("agent.actions.registration.update_owner", new_callable=AsyncMock):
        result = await handle_registration(_make_sms("Y"))
    assert "email" in result.lower() or "电邮" in result


@pytest.mark.asyncio
async def test_address_confirm_no():
    """Declining address goes back to address step."""
    owner = {
        "id": "o1",
        "phone": "+12125551234",
        "registration_step": "address_confirm",
        "registration_data": {"name": "Wong's Bakery", "business_type": "bakery", "address": "65 Mott St, New York, NY"},
    }
    with patch("agent.actions.registration.get_owner_by_phone", new_callable=AsyncMock, return_value=owner), \
         patch("agent.actions.registration.update_owner", new_callable=AsyncMock):
        result = await handle_registration(_make_sms("N"))
    assert "correct address" in result.lower() or "正确的地址" in result


@pytest.mark.asyncio
async def test_email_invalid():
    """Invalid email gets re-prompted."""
    owner = {
        "id": "o1",
        "phone": "+12125551234",
        "registration_step": "email",
        "registration_data": {"name": "Wong's Bakery", "business_type": "bakery", "address": "65 Mott St, New York, NY"},
    }
    with patch("agent.actions.registration.get_owner_by_phone", new_callable=AsyncMock, return_value=owner):
        result = await handle_registration(_make_sms("notanemail"))
    assert "valid email" in result.lower() or "有效的电邮" in result


@pytest.mark.asyncio
async def test_email_completes_registration():
    """Valid email creates business and completes registration."""
    owner = {
        "id": "o1",
        "phone": "+12125551234",
        "registration_step": "email",
        "registration_data": {"name": "Wong's Bakery", "business_type": "bakery", "address": "65 Mott St, New York, NY"},
    }
    with patch("agent.actions.registration.get_owner_by_phone", new_callable=AsyncMock, return_value=owner), \
         patch("agent.actions.registration.create_business", new_callable=AsyncMock, return_value="biz123"), \
         patch("agent.actions.registration.update_owner", new_callable=AsyncMock):
        result = await handle_registration(_make_sms("wong@gmail.com"))
    assert "renci.app/" in result
    assert "wongs-bakery" in result
    assert "Update hours" in result or "更新营业时间" in result
