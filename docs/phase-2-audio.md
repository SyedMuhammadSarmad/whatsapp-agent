# Phase 2 — Audio Message Support (Voice Notes)

> **Status:** Deferred — implement when you have OpenAI credits budgeted
> **Prerequisite:** Phase 1 (Meta Cloud API text) must be working

---

## What this adds

Clients can send WhatsApp voice notes. The system downloads the audio,
transcribes it with OpenAI Whisper, and feeds the text into the normal agent flow.
The client experience is identical to text — they just speak instead of type.

```
Client sends voice note
        ↓
Meta → POST /webhook/whatsapp  (type="audio", media_id="...")
        ↓
routers/whatsapp.py: detect type="audio"
        ↓
services/transcription.py: download + transcribe via Whisper
        ↓
handle_message(session_key, transcribed_text)  [unchanged]
        ↓
meta_provider.send(reply)                       [unchanged]
```

---

## Cost

| Service | Cost |
|---|---|
| Whisper API | ~$0.006 / minute of audio |
| Typical voice note (15s) | ~$0.0015 per message |

Very cheap. A hundred voice notes costs about $0.15.

---

## Files to add / modify

| File | Change |
|---|---|
| `services/transcription.py` | **New** — download audio + Whisper transcription |
| `routers/whatsapp.py` | **Modify** — handle `type="audio"` messages |

Everything else (agent, Redis, Asana, Meta provider) is untouched.

---

## Implementation

### `services/transcription.py` (new file)

```python
import httpx
import openai
from config import settings

_openai = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def download_media(media_id: str) -> bytes:
    """Download audio bytes from Meta using the media ID."""
    # Step 1: Resolve media_id to a download URL
    async with httpx.AsyncClient() as client:
        url_resp = await client.get(
            f"https://graph.facebook.com/v19.0/{media_id}",
            headers={"Authorization": f"Bearer {settings.META_ACCESS_TOKEN}"},
        )
        url_resp.raise_for_status()
        download_url = url_resp.json()["url"]

        # Step 2: Download the audio bytes
        audio_resp = await client.get(
            download_url,
            headers={"Authorization": f"Bearer {settings.META_ACCESS_TOKEN}"},
        )
        audio_resp.raise_for_status()
        return audio_resp.content


async def transcribe_audio(media_id: str, mime_type: str = "audio/ogg") -> str:
    """Download a WhatsApp voice note and transcribe it with Whisper."""
    audio_bytes = await download_media(media_id)

    # Whisper needs a (filename, bytes, mime_type) tuple
    transcript = await _openai.audio.transcriptions.create(
        model="whisper-1",
        file=(f"audio.ogg", audio_bytes, mime_type),
        response_format="text",
    )
    return transcript
```

### Update `routers/whatsapp.py`

Add an `elif message.get("type") == "audio":` branch inside the message loop:

```python
# Inside the for message in messages loop:

if message.get("type") == "text":
    text = message["text"]["body"]

elif message.get("type") == "audio":
    from services.transcription import transcribe_audio
    media_id = message["audio"]["id"]
    mime_type = message["audio"].get("mime_type", "audio/ogg")
    text = await transcribe_audio(media_id, mime_type)

else:
    continue  # unsupported type, skip

msg = IncomingMessage(sender_id=message["from"], text=text, channel="whatsapp")
reply = await handle_message(msg.session_key, msg.text)
await provider.send(msg.sender_id, reply)
```

---

## Environment variables needed

No new env vars — uses the existing `META_ACCESS_TOKEN` and `OPENAI_API_KEY`.

---

## Testing

1. Send a voice note to your Meta test number from a registered test recipient
2. Verify the transcription is logged (add `print(text)` temporarily)
3. Verify the agent replies based on the spoken content
4. Verify conversation history is maintained (Redis key unchanged)
