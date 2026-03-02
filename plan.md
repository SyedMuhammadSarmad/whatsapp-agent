# AI Client Handler — Architecture & Implementation Guide

## Overview

A Python-based AI agent that handles client communication via WhatsApp,
integrates with Asana for project management, and scales from text-based
automation to full voice conversations.

**Current phase:** Phase 1 (text-only, Meta Cloud API)
**Project manager:** [uv](https://docs.astral.sh/uv/)

---

## System Architecture

```
Client (WhatsApp)
        │
        ▼
Meta Cloud API
        │  POST JSON
        ▼
FastAPI  /webhook/whatsapp
        │
        ├─ GET  → webhook ownership verification (one-time)
        └─ POST → validate X-Hub-Signature-256
                  filter type="text" messages
                  normalize → IncomingMessage
                        │
                        ▼
              agents/client_agent.py
                        │
                  ┌─────┴─────┐
                  │           │
            Redis history   OpenAI gpt-4o-mini
                  │           │
                  │      ┌────┴────┐
                  │    Asana     Asana
                  │  get_status  create_task
                  │
                  └─ save updated history
                        │
                        ▼
              meta_provider.send(reply)
                        │
                        ▼
              Graph API → client's WhatsApp
```

---

## Platform Design

Two providers, two channels, zero overlap:

```
WhatsApp text  → Meta Cloud API  → /webhook/whatsapp  →  meta_provider.py
Voice calls    → Twilio Voice    → /webhook/voice      →  twilio_voice.py (Phase 3)
                                         │
                              Both share the same:
                              • client_agent.py
                              • session_manager.py (Redis)
                              • asana_tool.py
```

Same client, unified history: phone number normalization in `IncomingMessage.session_key`
means WhatsApp texts and voice calls use the same Redis key (`+15551234567`),
so the agent always has full context regardless of channel.

---

## Phone Number Strategy

| Phase | Provider | Number |
|---|---|---|
| Dev (now) | Meta free test number | provided by Meta |
| Phase 3 dev | Twilio test number | ~$1/month |
| Production | One real business number | registered on Meta + Twilio |

To use one number for both: buy a Twilio number → register it with WhatsApp Business.
Alternatively use your own business number for Meta and a separate Twilio number for voice.

---

## File Map

```
ai-client-handler/
├── main.py                           FastAPI app entry point
├── config.py                         pydantic-settings env vars
├── pyproject.toml                    uv project manifest
├── .env.example                      credential template
│
├── agents/
│   ├── client_agent.py               Agent + Redis history (platform-agnostic)
│   └── tools/
│       └── asana_tool.py             get_project_status, create_client_task
│
├── routers/
│   └── whatsapp.py                   Meta webhook (GET verify + POST handler)
│                                     ← Phase 3 adds: voice.py
│
└── services/
    ├── messaging/
    │   ├── base.py                   IncomingMessage + phone normalization + abstract provider
    │   ├── meta_provider.py          Meta Graph API (current, text)
    │   └── twilio_provider.py        Twilio WhatsApp (kept for reference / Phase 3 voice)
    │                                 ← Phase 3 adds: twilio_voice_provider.py
    └── session_manager.py            Redis get/save/clear history
```

---

## Platform Migration Reference

| Layer | File | Platform-specific? |
|---|---|---|
| Agent logic | `agents/client_agent.py` | No — never changes |
| Asana tools | `agents/tools/asana_tool.py` | No — never changes |
| Session memory | `services/session_manager.py` | No — never changes |
| Contract | `services/messaging/base.py` | No — never changes |
| Text provider | `services/messaging/meta_provider.py` | Yes — swap per provider |
| Webhook parser | `routers/whatsapp.py` | Yes — one per platform format |

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| `result.to_input_list()` for Redis history | Preserves full turn (tool calls + results), not just text |
| `@function_tool` decorator | Correct OpenAI Agents SDK decorator (not `@tool`) |
| `IncomingMessage.session_key` normalization | E.164 key ensures cross-channel Redis history sharing |
| HMAC-SHA256 with `hmac.compare_digest` | Prevents timing attacks on signature validation |
| Return 200 for status update events | Meta retries and disables webhook on any non-200 response |
| `httpx.AsyncClient` in MetaProvider | Non-blocking; compatible with FastAPI's async event loop |
| `gpt-4o-mini` model | ~15× cheaper than gpt-4o, sufficient for text task management |
| `package = false` in pyproject.toml | Marks this as an application, not an installable library |

---

## Environment Variables

```env
# Core
OPENAI_API_KEY=sk-...
ASANA_ACCESS_TOKEN=...
ASANA_WORKSPACE_ID=...
REDIS_URL=redis://localhost:6379

# Meta Cloud API (Phase 1 — required)
META_PHONE_NUMBER_ID=...
META_ACCESS_TOKEN=...
META_APP_SECRET=...
META_VERIFY_TOKEN=...

# Twilio Voice (Phase 3 — leave empty until then)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
```

---

## Phases

### Phase 1 — WhatsApp Text (current) ✅
Meta Cloud API. See `SETUP.md` for full instructions.

### Phase 2 — Audio Messages (voice notes)
See `docs/phase-2-audio.md`

### Phase 3 — Voice Calls
See `docs/phase-3-voice-calls.md`

### Phase 4 — Production
See `docs/phase-4-production.md`

---

## Running Locally

```bash
cd ai-client-handler
uv sync
cp .env.example .env        # fill in META_* and other keys
docker run -d -p 6379:6379 redis
uv run uvicorn main:app --reload --port 8000
ngrok http 8000
# Paste ngrok URL into Meta console → WhatsApp → Configuration
```

---

## Cost Estimates (Phase 1, text-only)

| Service | Free tier | Paid |
|---|---|---|
| Meta WhatsApp | 1,000 conversations/month free | $0.005–0.09 per conversation |
| OpenAI gpt-4o-mini | Pay per use | ~$0.002/1K tokens |
| Asana | Free (≤15 users) | — |
| Redis (Upstash) | 10K req/day free | $0.2/100K req |

**Estimated cost per 10-turn conversation:** < $0.05
