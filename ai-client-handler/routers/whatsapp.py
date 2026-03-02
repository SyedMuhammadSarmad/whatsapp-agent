import hashlib
import hmac

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse

from services.messaging.base import IncomingMessage
from services.messaging.meta_provider import provider
from app.client_agent import handle_message
from config import settings

router = APIRouter()


def _verify_signature(body: bytes, signature_header: str) -> bool:
    """Validate X-Hub-Signature-256 sent by Meta on every POST.

    Meta computes:  sha256=HMAC-SHA256(app_secret, raw_request_body)
    We recompute the same HMAC and compare using a constant-time
    comparison (hmac.compare_digest) to prevent timing attacks.
    """
    expected = "sha256=" + hmac.new(
        settings.META_APP_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@router.get("/webhook/whatsapp")
async def verify_webhook(request: Request):
    """One-time webhook verification endpoint.

    Meta calls this GET when you first register (or re-register) the
    webhook URL in the developer console.  It sends three query params:
      hub.mode         → always 'subscribe'
      hub.verify_token → the value you set in META_VERIFY_TOKEN
      hub.challenge    → a random string Meta wants echoed back

    Return the challenge as plain text to confirm ownership of the URL.
    """
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == settings.META_VERIFY_TOKEN
    ):
        return PlainTextResponse(params.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Receive inbound WhatsApp events from Meta Cloud API.

    Meta sends TWO kinds of POST to this endpoint:
      1. Actual messages  — processed by the agent
      2. Status updates   — delivered/read receipts, ignored here

    Both must return HTTP 200.  Returning 4xx on status updates causes
    Meta to retry and eventually disable the webhook subscription.
    """
    # --- Signature validation ---
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not _verify_signature(body, sig):
        raise HTTPException(status_code=403, detail="Invalid signature")

    data = await request.json()

    # --- Extract messages from Meta's nested envelope ---
    try:
        value = data["entry"][0]["changes"][0]["value"]
        messages = value.get("messages")
    except (KeyError, IndexError):
        # Not a message event (e.g. account update) — acknowledge and ignore
        return {"status": "ok"}

    if not messages:
        # Status update only (delivered/read receipt) — acknowledge and ignore
        return {"status": "ok"}

    # --- Process each text message ---
    for message in messages:
        if message.get("type") != "text":
            # Non-text message (image, audio, etc.) — Phase 2 will handle audio
            continue

        msg = IncomingMessage(
            sender_id=message["from"],        # e.g. "15551234567" (no +)
            text=message["text"]["body"],
            channel="whatsapp",
        )

        # session_key is the normalized E.164 phone used as the Redis key
        # sender_id (raw) is passed to provider.send() so Meta gets digits-only
        reply = await handle_message(msg.session_key, msg.text)
        await provider.send(msg.sender_id, reply)

    return {"status": "ok"}
