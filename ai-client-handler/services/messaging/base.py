from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Literal, Optional


# Channel type — extended when voice is added in Phase 3
Channel = Literal["whatsapp", "voice"]


def _normalize_phone(raw: str) -> str:
    """Normalize any provider's phone format to E.164 (e.g. '+15551234567').

    This ensures Redis history is keyed consistently regardless of which
    provider or channel a message arrives on:

      Meta Cloud API:      '15551234567'          → '+15551234567'
      Twilio WhatsApp:     'whatsapp:+15551234567' → '+15551234567'
      Twilio Voice (Ph.3): '+15551234567'          → '+15551234567' (no-op)
    """
    s = raw.strip()
    if s.startswith("whatsapp:"):
        s = s[len("whatsapp:"):]
    if not s.startswith("+"):
        s = "+" + s
    return s


@dataclass
class IncomingMessage:
    """Platform-agnostic representation of an inbound message.

    This is the normalization boundary — the agent layer never sees anything
    Meta- or Twilio-specific.

    Fields
    ------
    sender_id   Raw value from provider (passed back to provider.send() as-is).
    text        Message body.
    channel     'whatsapp' or 'voice' — lets future routing logic know the origin.
    media_url   Phase 2: URL of an audio/media attachment (voice notes).
    session_key Normalized E.164 phone — used as the Redis history key.
                Computed automatically from sender_id in __post_init__.
    """
    sender_id: str
    text: str
    channel: Channel = "whatsapp"
    media_url: Optional[str] = None
    session_key: str = field(init=False)

    def __post_init__(self):
        self.session_key = _normalize_phone(self.sender_id)


class MessagingProvider(ABC):
    """Abstract messaging provider — implement once per platform."""

    @abstractmethod
    async def send(self, to: str, text: str) -> None:
        """Send a text reply to the given recipient identifier."""
        ...
