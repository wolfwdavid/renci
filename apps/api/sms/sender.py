from twilio.rest import Client
from config import settings


def get_twilio_client() -> Client:
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


async def send_sms(to: str, body: str) -> None:
    """Send an SMS via Twilio."""
    client = get_twilio_client()
    client.messages.create(
        body=body,
        from_=settings.twilio_phone_number,
        to=to,
    )
