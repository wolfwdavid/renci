from fastapi import APIRouter, Request, Response
from sms.twilio_handler import parse_incoming_sms
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
