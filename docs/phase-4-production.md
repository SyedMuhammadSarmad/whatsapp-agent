# Phase 4 — Production Deployment

> **Status:** Deferred — do this when the app is stable and tested
> **Prerequisite:** Phase 1 (and optionally Phase 2/3) working in development

---

## What this covers

1. Permanent Meta access token (no more 24h expiry)
2. Registering your real business phone number with WhatsApp
3. Deploying the FastAPI server (Railway or Render)
4. Production Redis (Upstash)
5. Optionally consolidating to one number for WhatsApp + voice

---

## 1. Get a permanent Meta access token

The development token expires every 24 hours. For production:

1. Go to [business.facebook.com](https://business.facebook.com) → Settings → System Users
2. Create a **System User** with Admin role
3. Under the system user, click **Generate new token**
4. Select your app and grant:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
5. Copy the token → set as `META_ACCESS_TOKEN` in your production environment
6. This token does not expire

---

## 2. Register your real business phone number

> The Meta test number only works with registered test recipients.
> To reach real clients, register your own number.

**Requirements:**
- A phone number you own (mobile, landline, or VoIP)
- It must NOT already be registered with a WhatsApp personal or business account
  (you'll need to delete the existing account first)
- It must be able to receive SMS or a voice call for OTP verification

**Steps:**
1. WhatsApp Business → Phone Numbers → Add phone number
2. Enter your number
3. Choose verification: SMS or voice call
4. Enter the OTP code
5. Your number is now a WhatsApp Business number

**If you want one number for WhatsApp + voice (Twilio):**
- Buy a Twilio number → follow steps above to register it with WhatsApp
- Twilio handles voice; Meta handles WhatsApp messages on that same number

---

## 3. Deploy to Railway (recommended)

[railway.app](https://railway.app) — $5/month, very simple deployment.

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and init
railway login
cd ai-client-handler
railway init

# Add Redis service
railway add redis

# Set environment variables
railway variables set OPENAI_API_KEY=sk-...
railway variables set META_PHONE_NUMBER_ID=...
railway variables set META_ACCESS_TOKEN=...
railway variables set META_APP_SECRET=...
railway variables set META_VERIFY_TOKEN=...
railway variables set ASANA_ACCESS_TOKEN=...
railway variables set ASANA_WORKSPACE_ID=...
railway variables set REDIS_URL=$(railway variables get REDIS_URL)

# Deploy
railway up
```

Railway gives you a permanent URL like `https://your-app.up.railway.app`.

### `Procfile` (add to `ai-client-handler/`)

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## 4. Alternative: Deploy to Render

[render.com](https://render.com) — free tier available (spins down when idle, not ideal for production).

1. Connect your GitHub repo
2. Create a **Web Service** pointing to `ai-client-handler/`
3. Set Build Command: `pip install -r requirements.txt`
   (or use the uv build pack if available)
4. Set Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add all environment variables in the dashboard
6. Create a **Redis** service from Render's add-ons

---

## 5. Production Redis — Upstash

For serverless or low-traffic production, Upstash is simpler than managing a Redis server.

1. Sign up at [upstash.com](https://upstash.com) → Create Database → Global (lowest latency)
2. Copy the Redis URL: `rediss://:password@host:port`
3. Set `REDIS_URL=rediss://:password@host:port` in your production env vars

Free tier: 10,000 requests/day, sufficient for early production.

---

## 6. Update the webhook URL in Meta console

Once deployed, update Meta's webhook:

1. WhatsApp → Configuration → Edit webhook
2. Set Callback URL to your production URL: `https://your-app.up.railway.app/webhook/whatsapp`
3. Verify token: same `META_VERIFY_TOKEN` value
4. Click **Verify and save**

---

## 7. Go live checklist

- [ ] Permanent system user token set (not dev token)
- [ ] Real business phone number registered with WhatsApp
- [ ] Server deployed and health check returns 200: `GET /health`
- [ ] Webhook URL updated in Meta console and verified
- [ ] Production Redis connected (REDIS_URL set)
- [ ] Test a full message flow from a real WhatsApp number (not a test recipient)
- [ ] Monitor OpenAI costs in platform.openai.com dashboard
- [ ] Set up Meta conversation-based pricing alerts in Meta Business Manager

---

## Monitoring

Add basic logging to production to track message volume and errors:

```python
# At the top of routers/whatsapp.py
import logging
logger = logging.getLogger(__name__)

# Inside whatsapp_webhook(), after processing each message:
logger.info("Processed message from %s", msg.session_key)
```

Railway and Render both expose logs in their dashboards.
For more advanced monitoring, connect to a service like Sentry or Logtail.
