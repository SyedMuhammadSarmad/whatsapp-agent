import httpx
from .base import MessagingProvider
from config import settings

_GRAPH_URL = "https://graph.facebook.com/v19.0"


class MetaProvider(MessagingProvider):
    """Meta Cloud API (WhatsApp Business Platform) implementation.

    Uses the Graph API to send outbound WhatsApp messages.
    httpx.AsyncClient is used so the send() call is non-blocking
    and compatible with FastAPI's async event loop.

    To migrate to a different provider, replace this file with a new
    implementation of MessagingProvider — nothing else changes.
    """

    async def send(self, to: str, text: str) -> None:
        # Meta Graph API expects the recipient as digits only (no leading +)
        recipient = to.lstrip("+")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{_GRAPH_URL}/{settings.META_PHONE_NUMBER_ID}/messages",
                headers={
                    "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": recipient,
                    "type": "text",
                    "text": {
                        "preview_url": False,
                        "body": text,
                    },
                },
            )
            response.raise_for_status()


# Module-level singleton — imported directly by the webhook router
provider = MetaProvider()
