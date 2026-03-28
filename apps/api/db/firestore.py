from google.cloud.firestore_v1 import AsyncClient
from config import settings
from datetime import datetime, timezone
import re

_client: AsyncClient | None = None


def get_db() -> AsyncClient:
    global _client
    if _client is None:
        _client = AsyncClient(
            project=settings.gcp_project_id,
            database=settings.firestore_database,
        )
    return _client


def slugify(name: str) -> str:
    """Convert a business name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


# --- Owner operations ---


async def get_owner_by_phone(phone: str) -> dict | None:
    db = get_db()
    query = db.collection("owners").where("phone", "==", phone).limit(1)
    docs = [doc async for doc in query.stream()]
    if not docs:
        return None
    data = docs[0].to_dict()
    data["id"] = docs[0].id
    return data


async def create_owner(phone: str) -> dict:
    db = get_db()
    data = {
        "phone": phone,
        "email": "",
        "business_id": "",
        "language": "en",
        "registration_step": "name",
        "registration_data": {},
        "created_at": datetime.now(timezone.utc),
    }
    doc_ref = db.collection("owners").document()
    await doc_ref.set(data)
    data["id"] = doc_ref.id
    return data


async def update_owner(owner_id: str, updates: dict) -> None:
    db = get_db()
    await db.collection("owners").document(owner_id).update(updates)


# --- Business operations ---


async def create_business(data: dict) -> str:
    db = get_db()
    now = datetime.now(timezone.utc)
    data["created_at"] = now
    data["updated_at"] = now
    data["tier"] = "free"
    data["photos"] = []
    data["social"] = {}
    data["menu_items"] = []
    data["theme"] = {"template": "default", "primary_color": "#D4382C"}

    doc_ref = db.collection("businesses").document()
    await doc_ref.set(data)
    return doc_ref.id


async def get_business(business_id: str) -> dict | None:
    db = get_db()
    doc = await db.collection("businesses").document(business_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


async def get_business_by_slug(slug: str) -> dict | None:
    db = get_db()
    query = db.collection("businesses").where("slug", "==", slug).limit(1)
    docs = [doc async for doc in query.stream()]
    if not docs:
        return None
    data = docs[0].to_dict()
    data["id"] = docs[0].id
    return data


async def update_business(business_id: str, updates: dict) -> None:
    db = get_db()
    updates["updated_at"] = datetime.now(timezone.utc)
    await db.collection("businesses").document(business_id).update(updates)
