"""Profile update actions — hours, contact, description."""

from db.firestore import update_business


async def update_hours(business_id: str, hours: dict) -> None:
    await update_business(business_id, {"hours": hours})


async def update_contact(business_id: str, updates: dict) -> None:
    clean = {}
    if "phone" in updates and updates["phone"]:
        clean["phone"] = updates["phone"]
    if "email" in updates and updates["email"]:
        clean["email"] = updates["email"]
    if clean:
        await update_business(business_id, clean)


async def update_description(business_id: str, updates: dict) -> None:
    clean = {}
    if "description_en" in updates and updates["description_en"]:
        clean["description_en"] = updates["description_en"]
    if "description_zh" in updates and updates["description_zh"]:
        clean["description_zh"] = updates["description_zh"]
    if clean:
        await update_business(business_id, clean)
