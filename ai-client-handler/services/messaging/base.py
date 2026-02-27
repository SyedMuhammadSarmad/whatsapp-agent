from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional


@dataclass
class IncomingMessage:
    """Platform-agnostic representation of an inbound message.

    This dataclass is the normalization boundary — the agent layer
    never sees anything Twilio- or Meta-specific.
    """
    sender_id: str       # E.164 phone number, e.g. whatsapp:+12125551234
    text: str
    media_url: Optional[str] = None  # reserved for Phase 2 audio support


class MessagingProvider(ABC):
    """Abstract messaging provider — implement once per platform."""

    @abstractmethod
    async def send(self, to: str, text: str) -> None:
        """Send a text message to the given recipient."""
        ...
