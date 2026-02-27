# AI Client Handler — Architecture & Implementation Guide

## Overview

A Python-based AI agent system that handles client communication via WhatsApp,
integrates with Asana for project management, and is designed to scale from
text-based automation to full voice conversations across messaging platforms.

**Project manager:** [uv](https://docs.astral.sh/uv/) — replaces pip + venv + pip-tools.

---

## Vision

```
Client (WhatsApp / Phone Call)
        ↓
    Twilio (communication layer)
        ↓
    FastAPI Server (your backend)
        ↓
    OpenAI Agents SDK (intelligence layer)
        ↓
    Tools: Asana | Memory (Redis)
        ↓
    Response back to Client
```

---

## Technology Stack

### Core

| Technology | Role | Why |
|---|---|---|
| **Python 3.11+** | Language | Full async support, rich ecosystem |
| **uv** | Project manager | Replaces pip + venv + pip-tools in one binary |
| **FastAPI** | Backend server | Fast, async, perfect for webhooks |
| **OpenAI Agents SDK** | Agent logic | Tool calling, multi-agent, history management |
| **gpt-4o-mini** | Language model | Cost-optimised (~$0.002/1K tokens) |

### Communication

| Technology | Role | Why |
|---|---|---|
| **Twilio WhatsApp Sandbox** | WhatsApp messaging | Free for testing, no approval needed |
| **Twilio REST API** | Send replies | Async reply via REST (not TwiML) |

### Integrations

| Technology | Role | Why |
|---|---|---|
| **Asana Python SDK v5** | Project management tools | Agent can query/create tasks |
| **Redis (asyncio)** | Conversation history / session state | Fast, ephemeral, 24h TTL |

### Infrastructure

| Technology | Role |
|---|---|
| **Docker** | Local Redis container |
| **ngrok** | Expose localhost to Twilio during development |
| **Railway / Render** | Production hosting (future) |

---

## Architecture

### Platform Migration Design

The system is designed so switching WhatsApp providers (Twilio → Meta Cloud API)
requires changing **only 2 files**, not the agent or business logic.

| Layer | File | Platform-specific? |
|---|---|---|
| Agent logic | `agents/client_agent.py` | **No** — never changes |
| Session memory | `services/session_manager.py` | **No** — never changes |
| Asana tools | `agents/tools/asana_tool.py` | **No** — never changes |
| Messaging contract | `services/messaging/base.py` | **No** — never changes |
| Twilio implementation | `services/messaging/twilio_provider.py` | **Yes** → swap with `meta_provider.py` |
| Webhook parser | `routers/whatsapp.py` | **Yes** → update to parse Meta JSON format |

### Normalization boundary

```python
# services/messaging/base.py — the contract that never changes
@dataclass
class IncomingMessage:
    sender_id: str       # E.164 phone number
    text: str
    media_url: Optional[str] = None  # Phase 2: voice notes

class MessagingProvider(ABC):
    @abstractmethod
    async def send(self, to: str, text: str) -> None: ...
```

The webhook normalises the raw Twilio form POST into `IncomingMessage` immediately.
Everything below that point is platform-agnostic.

### Conversation history flow

```
Redis.get(client_id)          ← load prior turns
    ↓
append {"role": "user", ...}  ← add new message
    ↓
Runner.run(agent, input=history)
    ↓
result.to_input_list()        ← full turn incl. tool calls
    ↓
Redis.setex(client_id, 86400) ← persist with 24h TTL
    ↓
return result.final_output
```

`result.to_input_list()` is the key — it serialises the complete turn
(user message + tool calls + tool results + assistant reply) in the format
the SDK expects on the next `Runner.run()` call.

---

## Project Structure

```
ai-client-handler/
├── pyproject.toml             # uv project manifest (replaces requirements.txt)
├── uv.lock                    # auto-generated lockfile (commit this)
├── requirements.txt           # generated via: uv export --format requirements-txt
├── main.py                    # FastAPI app entry point
├── config.py                  # pydantic-settings env vars
├── .env.example               # template — copy to .env
│
├── agents/
│   ├── client_agent.py        # Agent + history management (platform-agnostic)
│   └── tools/
│       └── asana_tool.py      # get_project_status, create_client_task
│
├── routers/
│   └── whatsapp.py            # Twilio webhook — only platform-specific file
│
└── services/
    ├── messaging/
    │   ├── base.py            # IncomingMessage + abstract MessagingProvider
    │   └── twilio_provider.py # Twilio implementation (swap to migrate)
    └── session_manager.py     # Redis get/save/clear history
```

> Voice files (`voice.py`, `transcription.py`) are deferred to Phase 2+.

---

## Implementation Phases

### Phase 1 — WhatsApp Text (MVP) ✅

**What it does:**
- Receives WhatsApp messages via Twilio webhook
- Validates Twilio signature (security)
- Passes message + Redis conversation history to OpenAI agent
- Agent queries Asana for project data
- Sends reply back via Twilio REST API

**Running locally:**
```bash
# Prerequisites: uv installed, Docker running

cd ai-client-handler

uv sync                              # install deps, create .venv/
cp .env.example .env                 # fill in API keys

docker run -d -p 6379:6379 redis     # start Redis

uv run uvicorn main:app --reload     # start FastAPI on :8000
ngrok http 8000                      # expose to internet

# Set https://<ngrok-id>.ngrok-free.app/webhook/whatsapp
# in Twilio sandbox console → "When a message comes in"
```

**Verification checklist:**
- [ ] `curl http://localhost:8000/health` returns `{"status":"ok"}`
- [ ] Send WhatsApp → agent replies within 3–5 seconds
- [ ] Send second message → agent remembers previous context (Redis working)

---

### Phase 2 — Audio Message Support (Deferred)

**What it adds:**
- Client sends voice note on WhatsApp
- System downloads from Twilio, transcribes via Whisper
- Transcribed text enters normal agent flow

**Files to add:**
```
services/transcription.py     # Whisper transcription
```

**Cost:** ~$0.006/min of audio (Whisper API)

**Key change in `routers/whatsapp.py`:**
```python
# Already supported via IncomingMessage.media_url
msg = IncomingMessage(sender_id=From, text=Body, media_url=MediaUrl0)
if msg.media_url:
    msg.text = await transcribe_audio(msg.media_url)
```

---

### Phase 3 — Voice Call Support (Deferred)

**What it adds:**
- Client calls Twilio number
- Call audio streams to FastAPI via WebSocket
- OpenAI Realtime API handles real-time voice conversation
- Agent can query Asana mid-call and speak results

**Files to add:**
```
routers/voice.py     # TwiML webhook + WebSocket bridge
```

**Cost:** Twilio Voice (~$0.013/min) + OpenAI Realtime (~$0.06/min audio)

---

### Phase 4 — Meta Cloud API Migration (Deferred)

**What changes:**
1. Write `services/messaging/meta_provider.py` implementing `MessagingProvider`
2. Update `routers/whatsapp.py` to parse Meta's JSON webhook (not Twilio form data)
3. Set `MESSAGING_PROVIDER=meta` in `.env`

**What stays the same:** everything else — agent, tools, Redis, Asana.

---

## Environment Variables

```env
# OpenAI
OPENAI_API_KEY=sk-...

# Twilio (WhatsApp Sandbox)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Asana
ASANA_ACCESS_TOKEN=...
ASANA_WORKSPACE_ID=...

# Redis
REDIS_URL=redis://localhost:6379
```

---

## Key Design Decisions & Bug Fixes

| Decision | Rationale |
|---|---|
| `result.to_input_list()` for history | Preserves full turn (tool calls + results), not just text |
| `@function_tool` decorator | Correct OpenAI Agents SDK decorator (not `@tool`) |
| Twilio `RequestValidator` in webhook | Prevents forged requests — returns 403 on failure |
| `redis.asyncio` (non-blocking) | All handlers are async — blocking Redis would freeze the event loop |
| `IncomingMessage` dataclass boundary | Decouples agent from platform — enables migration with 2 file changes |
| Asana SDK v5 (`TasksApi`, `ProjectsApi`) | Old flat `asana.Client` API is deprecated |
| `gpt-4o-mini` as default model | ~15× cheaper than gpt-4o, sufficient for text task management |
| `package = false` in pyproject.toml | Marks this as an app, not a library — uv won't try to build/install it |

---

## Cost Estimates (MVP text-only)

| Service | Free | Paid |
|---|---|---|
| OpenAI gpt-4o-mini | Pay per use | ~$0.002/1K tokens |
| Twilio WhatsApp Sandbox | Free for testing | ~$0.005/message in production |
| Asana | Free (≤15 users) | — |
| Redis (Upstash) | 10K req/day free | $0.2/100K req |
| Hosting (Railway) | — | ~$5/month |

**Estimated cost per WhatsApp conversation (10 turns):** < $0.05

---

## Resources

- [uv Documentation](https://docs.astral.sh/uv/)
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [Twilio WhatsApp Sandbox](https://www.twilio.com/docs/whatsapp/sandbox)
- [Asana Python SDK v5](https://github.com/Asana/python-asana)
- [Redis asyncio](https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html)
- [FastAPI](https://fastapi.tiangolo.com/)
