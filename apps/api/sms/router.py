from sms.twilio_handler import IncomingSMS
from db.firestore import get_owner_by_phone
from agent.core import dispatch
from agent.actions.registration import handle_registration


async def route_message(message: IncomingSMS) -> str:
    """Route an incoming SMS to registration or the agent."""
    owner = await get_owner_by_phone(message.from_number)

    if owner is None:
        # New user — start or continue registration
        return await handle_registration(message)

    if owner.get("registration_step"):
        # Registration in progress
        return await handle_registration(message)

    # Registered owner — send to agent
    business_id = owner.get("business_id")
    return await dispatch(message, owner, business_id)
