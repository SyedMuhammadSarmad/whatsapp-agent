# Setup Guide — WhatsApp AI Agent (uv)

> **Prerequisite accounts:** Twilio (free sandbox), OpenAI API, Asana (free), Redis (local Docker or Upstash free tier)

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

> uv replaces pip, venv, and pip-tools in one binary. No other Python tooling needed.

---

## 2. Clone / enter the project

```bash
cd ai-client-handler
```

---

## 3. Create the virtual environment and install dependencies

```bash
# Reads pyproject.toml, resolves deps, creates .venv/, writes uv.lock
uv sync
```

To also install dev dependencies (pytest, ruff):

```bash
uv sync --group dev
```

uv automatically creates `.venv/` inside `ai-client-handler/`. You never need to
manually activate it — `uv run` handles that for you.

---

## 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your real credentials:

| Variable | Where to get it |
|---|---|
| `OPENAI_API_KEY` | platform.openai.com → API keys |
| `TWILIO_ACCOUNT_SID` | twilio.com → Console dashboard |
| `TWILIO_AUTH_TOKEN` | twilio.com → Console dashboard |
| `TWILIO_WHATSAPP_NUMBER` | `whatsapp:+14155238886` (sandbox default) |
| `ASANA_ACCESS_TOKEN` | app.asana.com → Profile → My Profile Settings → Apps |
| `ASANA_WORKSPACE_ID` | Asana URL: `app.asana.com/0/<workspace_id>/...` |
| `REDIS_URL` | `redis://localhost:6379` (local) or Upstash URL |

---

## 5. Start Redis

### Option A — Local Docker (recommended for dev)

```bash
docker run -d --name redis-agent -p 6379:6379 redis:7-alpine
```

### Option B — Upstash (free cloud, no Docker needed)

1. Sign up at upstash.com → Create a Redis database
2. Copy the `UPSTASH_REDIS_REST_URL` → use as `REDIS_URL` in `.env`
   Format: `rediss://:password@host:port`

---

## 6. Run the development server

```bash
# From inside ai-client-handler/
uv run uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

Verify with: `curl http://localhost:8000/health` → `{"status":"ok"}`

---

## 7. Expose to the internet (Twilio needs a public URL)

```bash
ngrok http 8000
```

ngrok gives you a URL like `https://abc123.ngrok-free.app`.

---

## 8. Configure Twilio WhatsApp Sandbox

1. Go to [twilio.com/console](https://twilio.com/console)
2. Navigate to **Messaging → Try it out → Send a WhatsApp message**
3. Follow the sandbox join instructions (send a WhatsApp message to the sandbox number)
4. Under **Sandbox settings**, set:
   - **When a message comes in:** `https://abc123.ngrok-free.app/webhook/whatsapp`
   - Method: `HTTP POST`
5. Save

---

## 9. Test end-to-end

Send a WhatsApp message to the Twilio sandbox number from your phone.

Expected flow:
1. Twilio → POST to your `/webhook/whatsapp`
2. FastAPI validates the Twilio signature
3. `handle_message()` runs the agent with conversation history
4. Agent optionally calls Asana tools
5. Reply sent back to your WhatsApp within 3–5 seconds

---

## Common uv commands

| Task | Command |
|---|---|
| Install / sync dependencies | `uv sync` |
| Add a new package | `uv add <package>` |
| Add a dev-only package | `uv add --group dev <package>` |
| Remove a package | `uv remove <package>` |
| Run a command in venv | `uv run <command>` |
| Run tests | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Export to requirements.txt | `uv export --format requirements-txt -o requirements.txt` |
| Update all packages | `uv lock --upgrade` then `uv sync` |
| Show installed packages | `uv pip list` |

---

## Troubleshooting

**`ModuleNotFoundError`** — run `uv sync` to ensure the venv is up to date.

**`403 Invalid Twilio signature`** — your ngrok URL changed. Update it in the Twilio console.
Also ensure `request.url` in the webhook matches the URL Twilio is posting to exactly
(watch for `http` vs `https`).

**`redis.exceptions.ConnectionError`** — Redis is not running. Start Docker container or check Upstash URL.

**`openai_agents` not found** — the package is `openai-agents` on PyPI. Run `uv add openai-agents`.
