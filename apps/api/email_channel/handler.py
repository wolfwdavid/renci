"""Email channel handler — bridges email to the same agent pipeline as SMS."""

from email_channel.receiver import IncomingEmail
from sms.twilio_handler import IncomingSMS
from sms.router import route_message
from email_channel.sender import send_email_reply


async def handle_email(email_msg: IncomingEmail) -> str:
    """Process an incoming email through the agent pipeline.

    Converts the email into an IncomingSMS-compatible format so we can
    reuse the exact same routing/agent logic. The email address acts
    as the phone number for identity lookup.
    """
    # Convert email to SMS-compatible format
    sms_msg = IncomingSMS(
        from_number=email_msg.from_address,  # email as identity
        body=email_msg.body or email_msg.subject,
        media_urls=[],
        num_media=0,
    )

    # Route through the same pipeline
    response = await route_message(sms_msg)

    # Send reply
    subject = email_msg.subject or "Renci"
    send_email_reply(email_msg.from_address, subject, response)

    return response
