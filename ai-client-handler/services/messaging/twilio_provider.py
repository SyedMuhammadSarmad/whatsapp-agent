from twilio.rest import Client
from .base import MessagingProvider
from config import settings


class TwilioProvider(MessagingProvider):
    """Twilio WhatsApp implementation of MessagingProvider.

    To migrate to Meta Cloud API, replace this file with meta_provider.py
    that implements the same interface — nothing else changes.
    """

    def __init__(self):
        self._client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    async def send(self, to: str, text: str) -> None:
        # Twilio's Python client is synchronous; for MVP this is fine.
        # For high-throughput, wrap in asyncio.to_thread().
        self._client.messages.create(
            body=text,
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=to,
        )


# Module-level singleton — imported directly by the webhook router
provider = TwilioProvider()
