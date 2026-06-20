# Setup Guide — WhatsApp AI Agent

> **Current phase:** Phase 1 — WhatsApp text messaging via Meta Cloud API
> For future phases see `docs/phase-2-audio.md`, `docs/phase-3-voice-calls.md`, `docs/phase-4-production.md`

---

## Prerequisites

| Account | Free tier | Sign up |
|---|---|---|
| Meta for Developers | Free sandbox, 1000 convos/month | developers.facebook.com |
| OpenAI API | Pay per use (~$0.002/1K tokens) | platform.openai.com |
| Asana | Free (≤15 users) | app.asana.com |
| Redis | Local Docker or Upstash free (10K req/day) | upstash.com |

You do **not** need a Twilio account for Phase 1.

---

## 1. Install uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify
uv --version
```

---

## 2. Install project dependencies

```bash
cd ai-client-handler
uv sync
```

uv reads `pyproject.toml`, resolves everything, and creates `.venv/` automatically.
You never need to manually activate the venv — `uv run` handles that.

---

## 3. Get Meta Cloud API credentials

### Step-by-step

1. Go to [developers.facebook.com](https://developers.facebook.com) and log in with your Facebook / Meta account
2. Click **My Apps → Create App**
3. Select **Business** as the app type → give it a name → Create
4. On the app dashboard, find **WhatsApp** and click **Set up**
5. Under **WhatsApp → Getting Started** you will see:
   - **Temporary access token** — copy this as `META_ACCESS_TOKEN`
   - **Phone Number ID** — copy this as `META_PHONE_NUMBER_ID`
   - **Test phone number** — this is what clients will message during dev
6. Go to **App Settings → Basic** → copy **App Secret** as `META_APP_SECRET`
7. Under **WhatsApp → Configuration** you will configure the webhook URL later (Step 7)
8. Add your personal WhatsApp number as a **test recipient**:
   - Under **WhatsApp → Getting Started → To** field, add your number
   - Meta allows up to 5 test recipients for free

> **Permanent token for production:** The temporary token expires in 24 hours.
> To get a permanent one: Business Settings → System Users → Create → assign WhatsApp permissions → Generate token.

---

## 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable | Where to find it |
|---|---|
| `OPENAI_API_KEY` | platform.openai.com → API keys |
| `META_PHONE_NUMBER_ID` | WhatsApp → Getting Started → Phone Number ID |
| `META_ACCESS_TOKEN` | WhatsApp → Getting Started → Temporary access token |
| `META_APP_SECRET` | App Settings → Basic → App Secret |
| `META_VERIFY_TOKEN` | **You choose this** — any string (e.g. `my-secret-42`). You'll paste the same value in the Meta console in Step 7. |
| `ASANA_ACCESS_TOKEN` | app.asana.com → Profile → Apps → Personal access token |
| `ASANA_WORKSPACE_ID` | From your Asana URL: `app.asana.com/0/<workspace_id>/...` |
| `REDIS_URL` | `redis://localhost:6379` (local) or Upstash URL |

Leave `TWILIO_*` variables empty — they're only needed in Phase 3.

---

## 5. Start Redis

### Option A — Local Docker (recommended for dev)

```bash
docker run -d --name redis-agent -p 6379:6379 redis:7-alpine
```

### Option B — Upstash (no Docker, free cloud tier)

1. Sign up at [upstash.com](https://upstash.com) → Create a Redis database → copy the URL
2. Set `REDIS_URL=rediss://:password@host:port` in `.env`

---

## 6. Run the development server

```bash
cd ai-client-handler
uv run uvicorn main:app --reload --port 8000
```

Verify it started:
```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

---

## 7. Expose your server to the internet

Meta needs to reach your local machine to deliver webhook events.

```bash
ngrok http 8000
```

ngrok gives you a URL like `https://abc123.ngrok-free.app`. Keep this terminal open.

---

## 8. Register the webhook in Meta console

1. Go to your app → **WhatsApp → Configuration**
2. Click **Edit** next to Webhook
3. Set:
   - **Callback URL:** `https://abc123.ngrok-free.app/webhook/whatsapp`
   - **Verify token:** the value you set as `META_VERIFY_TOKEN` in `.env`
4. Click **Verify and save** — Meta will call `GET /webhook/whatsapp` to verify ownership
5. Under **Webhook fields**, click **Manage** and subscribe to: `messages`

You should see **"Webhook verified"** in the console.

---

## 9. Test end-to-end

Send a WhatsApp message to your Meta test phone number from one of your registered test recipient numbers.

Expected flow:
1. Meta → POST to your `/webhook/whatsapp`
2. FastAPI validates `X-Hub-Signature-256`
3. Agent runs with your conversation history from Redis
4. Agent optionally queries Asana
5. Reply arrives on your WhatsApp within 3–5 seconds

Send a second message — the agent should remember your first message (Redis history working).

---

## Verification checklist

```bash
# 1. Webhook verification (simulates Meta's one-time check)
curl "http://localhost:8000/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=my-secret-42&hub.challenge=testtoken"
# → testtoken

# 2. Check Meta console shows "Webhook verified"

# 3. Send WhatsApp message from your phone to the test number
#    → agent replies within 3–5 seconds

# 4. Send a follow-up message
#    → agent references the first message (conversation memory working)

# 5. Send a non-text message (e.g. a photo)
#    → agent does NOT reply (gracefully ignored until Phase 2)
```

---

## Common uv commands

| Task | Command |
|---|---|
| Install / sync dependencies | `uv sync` |
| Run dev server | `uv run uvicorn main:app --reload --port 8000` |
| Add a new package | `uv add <package>` |
| Add a dev-only package | `uv add --group dev <package>` |
| Run tests | `uv run pytest` |
| Update all packages | `uv lock --upgrade && uv sync` |

---

## Troubleshooting

**Webhook verification fails (403)**
→ `META_VERIFY_TOKEN` in `.env` doesn't match what you typed in Meta console. They must be identical.

**Signature validation fails (403) on incoming messages**
→ `META_APP_SECRET` is wrong. Get it from App Settings → Basic → App Secret (not the access token).

**Agent doesn't reply**
→ Check your `META_ACCESS_TOKEN` is valid (dev token expires in 24h). Check `OPENAI_API_KEY`. Check Redis is running.

**`redis.exceptions.ConnectionError`**
→ Redis is not running. Start the Docker container or check your Upstash URL.

**`ValidationError` on startup**
→ A required env var is missing in `.env`. pydantic-settings will tell you which one.

**ngrok URL changed**
→ Update the Callback URL in Meta console → WhatsApp → Configuration.
