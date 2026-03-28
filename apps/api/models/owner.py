from pydantic import BaseModel
from datetime import datetime


class Owner(BaseModel):
    id: str = ""
    phone: str = ""
    email: str = ""
    business_id: str = ""
    language: str = "en"
    registration_step: str | None = None
    registration_data: dict = {}
    created_at: datetime | None = None
