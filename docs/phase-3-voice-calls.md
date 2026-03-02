# Phase 3 — Voice Call Support (Twilio + OpenAI Realtime API)

> **Status:** Deferred — requires Twilio account + OpenAI credits budgeted
> **Prerequisite:** Phase 1 working. Phase 2 is optional (independent).

---

## What this adds

Clients can phone call your Twilio number and speak directly to the AI agent
in real time. The agent can query Asana mid-call and speak the results.
Conversation history from prior WhatsApp texts is visible to the voice agent
(shared Redis key via phone number normalization).

```
Client dials +15551234567 (Twilio number)
        ↓
Twilio → POST /webhook/voice  (TwiML webhook)
        ↓
routers/voice.py: return TwiML instructing Twilio to open a media stream
        ↓
Twilio streams audio to wss://yourdomain.com/ws/voice
        ↓
routers/voice.py WebSocket handler: bridge Twilio ↔ OpenAI Realtime API
        ↓
OpenAI Realtime responds with audio
        ↓
Audio piped back to Twilio → client hears response
```

---

## Cost

| Service | Cost |
|---|---|
| Twilio Voice | ~$0.013 / minute |
| Twilio phone number | ~$1 / month |
| OpenAI Realtime API | ~$0.06 / minute (audio in + out) |
| **Total per minute of conversation** | **~$0.073** |

A 5-minute call costs about $0.37.

---

## Files to add

| File | Purpose |
|---|---|
| `routers/voice.py` | TwiML webhook + WebSocket bridge |

**Nothing else changes.** `client_agent.py`, `session_manager.py`, `asana_tool.py`,
and `meta_provider.py` are all untouched.

---

## Environment variables to fill in

In your `.env`, set the Twilio vars that were left empty in Phase 1:

```env
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+15551234567   # the number you buy from Twilio
```

---

## Implementation

### `routers/voice.py` (new file)

```python
import asyncio
import json
import websockets
from fastapi import APIRouter, WebSocket
from fastapi.responses import Response
from config import settings

router = APIRouter()

# TwiML that instructs Twilio to open an audio media stream to our WebSocket
_TWIML = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{host}/ws/voice"/>
    </Connect>
</Response>"""


@router.post("/webhook/voice")
async def voice_webhook(request):
    """Twilio calls this when a client dials your number.
    Returns TwiML telling Twilio to stream the call audio to /ws/voice.
    """
    host = request.headers.get("host", "yourdomain.com")
    return Response(content=_TWIML.format(host=host), media_type="application/xml")


@router.websocket("/ws/voice")
async def voice_stream(websocket: WebSocket):
    """WebSocket bridge: Twilio audio ↔ OpenAI Realtime API.

    Twilio sends raw mulaw audio in base64-encoded JSON packets.
    OpenAI Realtime API responds with audio deltas.
    We bridge the two streams concurrently with asyncio.gather.
    """
    await websocket.accept()

    openai_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}

    async with websockets.connect(openai_url, extra_headers=headers) as openai_ws:
        # Configure the realtime session
        await openai_ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "instructions": (
                    "You are an AI assistant for a software agency. "
                    "Help clients with project updates and task creation. "
                    "Be concise — the client is on a phone call."
                ),
                "voice": "alloy",
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "turn_detection": {"type": "server_vad"},
            }
        }))

        async def receive_from_twilio():
            """Forward Twilio audio to OpenAI."""
            async for raw in websocket.iter_text():
                data = json.loads(raw)
                if data.get("event") == "media":
                    await openai_ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": data["media"]["payload"],
                    }))
                elif data.get("event") == "stop":
                    break

        async def send_to_twilio():
            """Forward OpenAI audio back to Twilio."""
            async for raw in openai_ws:
                data = json.loads(raw)
                if data.get("type") == "response.audio.delta":
                    await websocket.send_text(json.dumps({
                        "event": "media",
                        "streamSid": "",  # Twilio fills this in
                        "media": {"payload": data["delta"]},
                    }))

        await asyncio.gather(receive_from_twilio(), send_to_twilio())
```

### Register the router in `main.py`

```python
from routers.voice import router as voice_router
app.include_router(voice_router)
```

---

## Twilio setup

1. Sign up at [twilio.com](https://twilio.com)
2. Buy a phone number: Console → Phone Numbers → Buy a number
3. Under the number's configuration, set:
   - **Voice webhook:** `https://<your-domain>/webhook/voice` (HTTP POST)
4. If you want this same number for WhatsApp too:
   - Register it with Meta WhatsApp Business (see SETUP.md)
   - Twilio handles voice; Meta handles WhatsApp text

---

## Shared conversation history with WhatsApp

Because `session_key` normalizes all phone formats to E.164:
- WhatsApp text from `15551234567` → Redis key `+15551234567`
- Voice call from `+15551234567` → Redis key `+15551234567`

To load prior WhatsApp context at the start of a voice call, call
`get_history(normalized_phone)` before connecting to the Realtime API
and send it as the initial session context.

---

## Testing

1. Call your Twilio number from your phone
2. Agent should greet you and answer questions
3. Ask about a project → agent queries Asana and speaks the result
4. Hang up, then send a WhatsApp message → agent remembers the call
