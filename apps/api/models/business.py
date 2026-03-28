from pydantic import BaseModel
from datetime import datetime


class MenuItem(BaseModel):
    name: str
    name_zh: str = ""
    price: float = 0.0
    description: str = ""
    category: str = ""


class BusinessProfile(BaseModel):
    id: str = ""
    slug: str = ""
    name: str = ""
    name_zh: str = ""
    business_type: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    description_en: str = ""
    description_zh: str = ""
    hours: dict[str, str] = {}
    menu_items: list[MenuItem] = []
    photos: list[str] = []
    social: dict[str, str] = {}
    theme: dict[str, str] = {"template": "default", "primary_color": "#D4382C"}
    tier: str = "free"
    created_at: datetime | None = None
    updated_at: datetime | None = None


BUSINESS_TYPES = {
    "1": "restaurant",
    "2": "bakery",
    "3": "grocery",
    "4": "salon",
    "5": "laundry",
    "6": "retail",
    "7": "other",
}
