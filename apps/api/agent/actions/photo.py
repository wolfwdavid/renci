"""Multimodal photo analysis tools using Gemini vision."""

import httpx
from config import settings


async def download_twilio_media(url: str) -> bytes:
    """Download an MMS media file from Twilio (requires auth)."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.content


def extract_menu_from_photo(photo_description: str) -> dict:
    """Extract menu items and prices from a photo of a menu or price list.

    Use this when the owner sends a photo of their menu and wants to
    add items to their website. The photo_description comes from Gemini's
    vision analysis of the image.

    Args:
        photo_description: A text description of the menu items seen in the photo.
    """
    return {
        "status": "success",
        "message": (
            "I can see the menu items in your photo. "
            "I'll add them to your website. "
            "Text me to confirm or edit any items."
        ),
        "description": photo_description,
    }
