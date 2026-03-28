"""Email channel handler — bridges email to the same agent pipeline as SMS."""

import re
from email_channel.receiver import IncomingEmail
from sms.twilio_handler import IncomingSMS
from sms.router import route_message
from email_channel.sender import send_email_reply

# Carrier SMS-to-email gateway domains
CARRIER_GATEWAYS = {
    "txt.att.net",
    "tmomail.net",
    "vtext.com",
    "messaging.sprintpcs.com",
    "mymetropcs.com",
    "sms.cricketwireless.net",
    "sms.myboostmobile.com",
    "pm.sprint.com",
    "mms.att.net",
    "mms.cricketwireless.net",
}

# Pattern: digits@carrier-gateway
SMS_EMAIL_PATTERN = re.compile(r"^\d{10,11}@(.+)$")


def is_sms_gateway_email(address: str) -> bool:
    """Check if an email address is from a phone carrier SMS gateway."""
    match = SMS_EMAIL_PATTERN.match(address)
    if not match:
        return False
    domain = match.group(1).lower()
    return domain in CARRIER_GATEWAYS


def extract_phone_from_gateway(address: str) -> str:
    """Extract the phone number from a carrier gateway email."""
    match = SMS_EMAIL_PATTERN.match(address)
    if match:
        digits = address.split("@")[0]
        if len(digits) == 10:
            return f"+1{digits}"
        return f"+{digits}"
    return address


async def handle_email(email_msg: IncomingEmail) -> str | None:
    """Process an incoming email through the agent pipeline.

    Only responds to emails from carrier SMS gateways (phone numbers).
    Regular email addresses are ignored.
    """
    if not is_sms_gateway_email(email_msg.from_address):
        return None  # Ignore non-SMS emails

    phone = extract_phone_from_gateway(email_msg.from_address)

    sms_msg = IncomingSMS(
        from_number=phone,
        body=email_msg.body or email_msg.subject,
        media_urls=[],
        num_media=0,
    )

    response = await route_message(sms_msg)

    subject = email_msg.subject or "Renci"
    send_email_reply(email_msg.from_address, subject, response)

    return response
