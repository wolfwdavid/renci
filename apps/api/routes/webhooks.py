from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sms.twilio_handler import parse_incoming_sms, IncomingSMS
from sms.router import route_message

router = APIRouter()


@router.post("/webhooks/sms")
async def sms_webhook(request: Request):
    """Twilio SMS webhook — receives all incoming messages."""
    form_data = await request.form()
    message = parse_incoming_sms(dict(form_data))

    response_text = await route_message(message)

    # Return TwiML response
    twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{response_text}</Message></Response>'
    return Response(content=twiml, media_type="application/xml")


class EmailMessage(BaseModel):
    from_address: str
    body: str
    subject: str = "Renci"


@router.post("/webhooks/email")
async def email_webhook(msg: EmailMessage):
    """Direct email webhook — for testing or external email forwarding services."""
    sms_msg = IncomingSMS(
        from_number=msg.from_address,
        body=msg.body,
        media_urls=[],
        num_media=0,
    )
    response_text = await route_message(sms_msg)
    return {"response": response_text, "from": msg.from_address}


@router.post("/webhooks/email/poll")
async def email_poll():
    """Manually trigger an email poll cycle."""
    from email_channel.poller import poll_emails_once
    count = await poll_emails_once()
    return {"processed": count}


@router.get("/agent/status")
async def agent_status():
    """Get the live agent poller status."""
    from email_channel.poller import _running
    return {"active": _running}


@router.post("/agent/toggle")
async def agent_toggle():
    """Toggle the live agent email poller on/off."""
    import asyncio
    from email_channel.poller import _running, start_email_poller, stop_email_poller

    if _running:
        stop_email_poller()
        return {"active": False, "message": "Live agent stopped"}
    else:
        asyncio.create_task(start_email_poller(interval_seconds=15))
        return {"active": True, "message": "Live agent started"}
