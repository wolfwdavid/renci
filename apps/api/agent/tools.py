"""Tool definitions for the Renci agent (Google ADK format).

ADK auto-generates JSON schemas from function signatures and docstrings.
Each tool is a plain Python function that performs its side-effects directly.
"""

from agent.actions.profile import update_hours, update_contact, update_description
from agent.prompts.templates import (
    hours_updated_response,
    contact_updated_response,
    status_response,
    help_response,
)
from db.firestore import get_business


async def update_business_hours(
    hours_monday: str = "",
    hours_tuesday: str = "",
    hours_wednesday: str = "",
    hours_thursday: str = "",
    hours_friday: str = "",
    hours_saturday: str = "",
    hours_sunday: str = "",
    business_id: str = "",
    language: str = "en",
) -> dict:
    """Update the business operating hours. Use when the owner mentions hours, schedule, open or close times.

    Args:
        hours_monday: Monday hours, e.g. "9:00-17:00" or "closed".
        hours_tuesday: Tuesday hours.
        hours_wednesday: Wednesday hours.
        hours_thursday: Thursday hours.
        hours_friday: Friday hours.
        hours_saturday: Saturday hours.
        hours_sunday: Sunday hours.
        business_id: The business ID (injected by system).
        language: Response language (injected by system).
    """
    hours = {}
    for day, val in [
        ("monday", hours_monday), ("tuesday", hours_tuesday),
        ("wednesday", hours_wednesday), ("thursday", hours_thursday),
        ("friday", hours_friday), ("saturday", hours_saturday),
        ("sunday", hours_sunday),
    ]:
        if val:
            hours[day] = val

    if not hours:
        return {"status": "error", "message": "No hours provided."}

    await update_hours(business_id, hours)
    return {"status": "success", "message": hours_updated_response(hours, language)}


async def update_contact_info(
    phone: str = "",
    email: str = "",
    business_id: str = "",
    language: str = "en",
) -> dict:
    """Update business contact information like phone number or email.

    Args:
        phone: New phone number for the business.
        email: New email address for the business.
        business_id: The business ID (injected by system).
        language: Response language (injected by system).
    """
    updates = {}
    if phone:
        updates["phone"] = phone
    if email:
        updates["email"] = email

    if not updates:
        return {"status": "error", "message": "No contact info provided."}

    await update_contact(business_id, updates)
    return {"status": "success", "message": contact_updated_response(updates, language)}


async def update_business_description(
    description_en: str = "",
    description_zh: str = "",
    business_id: str = "",
    language: str = "en",
) -> dict:
    """Update the business description or about text.

    Args:
        description_en: Business description in English.
        description_zh: Business description in Chinese.
        business_id: The business ID (injected by system).
        language: Response language (injected by system).
    """
    updates = {}
    if description_en:
        updates["description_en"] = description_en
    if description_zh:
        updates["description_zh"] = description_zh

    if not updates:
        return {"status": "error", "message": "No description provided."}

    await update_description(business_id, updates)
    msg = "Description updated!" if language == "en" else "商店描述已更新！"
    return {"status": "success", "message": msg}


async def show_status(business_id: str = "", language: str = "en") -> dict:
    """Show the business profile status including website URL, hours, and contact info.

    Use when the owner asks about their profile, status, or current settings.

    Args:
        business_id: The business ID (injected by system).
        language: Response language (injected by system).
    """
    business = await get_business(business_id)
    if not business:
        return {"status": "error", "message": "Business not found."}
    return {"status": "success", "message": status_response(business, language)}


def show_help(language: str = "en") -> dict:
    """Show available commands and what the owner can do via SMS.

    Use when the owner seems confused, asks for help, or sends an unclear message.

    Args:
        language: Response language (injected by system).
    """
    return {"status": "success", "message": help_response(language)}
