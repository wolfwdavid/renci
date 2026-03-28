"""Session memory stub — future conversation state management.

Will store conversation history per owner in Firestore
to enable multi-turn dialogue in assistant mode.
"""


async def get_session(owner_id: str) -> dict:
    """Get conversation session for an owner. Stub."""
    return {"owner_id": owner_id, "messages": []}


async def save_message(owner_id: str, role: str, content: str) -> None:
    """Save a message to session history. Stub."""
    pass
