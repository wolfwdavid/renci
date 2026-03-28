from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/businesses/{slug}")
async def get_business(slug: str):
    """Get business by slug — used by SvelteKit frontend."""
    from db.firestore import get_business_by_slug

    business = await get_business_by_slug(slug)
    if not business:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Business not found")
    return business
