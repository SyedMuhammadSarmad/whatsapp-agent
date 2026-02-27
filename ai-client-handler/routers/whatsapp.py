from fastapi import APIRouter, Form, Request, HTTPException
from twilio.request_validator import RequestValidator

from services.messaging.base import IncomingMessage
from services.messaging.twilio_provider import provider
from agents.client_agent import handle_message
from config import settings

router = APIRouter()
_validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),   # noqa: N803 — Twilio sends "From" (capitalised)
    Body: str = Form(...),
):
    """Receive an inbound WhatsApp message from Twilio, process it, and reply.

    Security: validates the X-Twilio-Signature header so only genuine Twilio
    requests are accepted. Returns 403 for any unsigned or tampered requests.
    """
    # --- Signature validation ---
    form_data = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")

    if not _validator.validate(str(request.url), dict(form_data), signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    # --- Normalise to platform-agnostic message ---
    msg = IncomingMessage(sender_id=From, text=Body)

    # --- Agent processing ---
    reply = await handle_message(msg.sender_id, msg.text)

    # --- Send reply back via Twilio REST ---
    await provider.send(msg.sender_id, reply)

    return {"status": "ok"}
