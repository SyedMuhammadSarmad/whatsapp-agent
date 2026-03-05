Great question. Let me trace just this part in detail.

  ---
  The Reply Journey — 4 Stages

  Agent produces text
        ↓
  router gets the text
        ↓
  MetaProvider makes HTTP call to Facebook's servers
        ↓
  Facebook delivers message to client's WhatsApp

  ---
  Stage 1 — Agent Produces the Reply Text

  In app/client_agent.py:

  result = await Runner.run(client_agent, input=history)

  return result.final_output   # ← just a plain Python string
  # e.g. "Project Alpha has 3 open tasks: Fix login bug..."

  result.final_output is nothing special — it is just a regular Python string. The agent is done at this point. It doesn't  
  know anything about WhatsApp, Meta, or HTTP. It just returned text.

  ---
  Stage 2 — Router Receives the Text

  Back in routers/whatsapp.py:

  reply = await handle_message(msg.session_key, msg.text)
  #  reply = "Project Alpha has 3 open tasks: Fix login bug..."

  await provider.send(msg.sender_id, reply)
  #  sender_id = "15551234567"
  #  reply     = the string from the agent

  The router holds two things:
  - Who to send to → msg.sender_id (the client's phone number)
  - What to send → reply (the agent's text)

  It passes both to provider.send().

  ★ Insight ─────────────────────────────────────
  - provider is the MetaProvider() instance created at the bottom of meta_provider.py — it's created once when the server   
  starts and reused for every message. The router doesn't create a new one each time.
  - The router doesn't care how the message is sent. It just calls provider.send(). If you swapped MetaProvider for a       
  TwilioProvider, the router code would not change at all. This is the strategy pattern in action.
  ─────────────────────────────────────────────────

  ---
  Stage 3 — MetaProvider Makes the HTTP Call

  This is the most important part. Open services/messaging/meta_provider.py:

  async def send(self, to: str, text: str) -> None:
      recipient = to.lstrip("+")
      # "15551234567".lstrip("+") → "15551234567"  (no + sign, Meta requires this)

      async with httpx.AsyncClient() as client:
          response = await client.post(
              f"https://graph.facebook.com/v19.0/{settings.META_PHONE_NUMBER_ID}/messages",
              headers={
                  "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
              },
              json={
                  "messaging_product": "whatsapp",
                  "recipient_type": "individual",
                  "to": recipient,
                  "type": "text",
                  "text": {
                      "preview_url": False,
                      "body": text,        # ← the agent's reply string goes here
                  },
              },
          )
          response.raise_for_status()

  Let me break down every line:

  The URL

  https://graph.facebook.com/v19.0/993469833857037/messages
                                    ^^^^^^^^^^^^^^^^
                                    META_PHONE_NUMBER_ID from .env
                                    (your WhatsApp Business phone number's ID)
  This is Meta's Graph API endpoint. 993469833857037 is not a phone number — it's the internal ID Meta assigned to your     
  WhatsApp Business phone number. You got it from the Meta console.

  The Authorization Header

  "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}"
  This is like a password. Meta checks this token to confirm:
  1. You are who you say you are
  2. You have permission to send messages from this phone number

  This is exactly what was returning 401 Unauthorized — because the token was expired (dev tokens last 24 hours only).      

  The JSON Body

  {
      "messaging_product": "whatsapp",     # tells Meta this is a WhatsApp message
      "recipient_type": "individual",      # not a group, just one person
      "to": "15551234567",                 # the client's phone number
      "type": "text",                      # it's a text message (not image, doc, etc.)
      "text": {
          "preview_url": False,            # don't generate link previews
          "body": "Project Alpha has 3 open tasks..."   # THE ACTUAL MESSAGE
      }
  }

  This is the instruction you send to Meta saying: "Please deliver this text to this phone number via WhatsApp."

  response.raise_for_status()

  response.raise_for_status()
  After Meta processes your request, it responds with a status code:
  - 200 OK → message queued for delivery — raise_for_status() does nothing
  - 401 Unauthorized → bad/expired token → raises HTTPStatusError (what you saw)
  - 400 Bad Request → wrong JSON format → raises HTTPStatusError

  ---
  Stage 4 — Facebook Delivers to Client's WhatsApp

  After your server sends the HTTP POST to graph.facebook.com, Meta takes over:

  Your server ──POST──► graph.facebook.com
                               │
                               ▼
                      Meta's WhatsApp servers
                               │
                      find the client's phone
                               │
                               ▼
                      Client's WhatsApp app
                      receives the message

  You never communicate directly with the client's phone. You communicate with Meta's servers, and Meta delivers it. This is   exactly the same as how WhatsApp works for regular users — messages go through Meta's infrastructure.

  ---
  The Full Reply Path in One Picture

   client_agent.py          whatsapp.py            meta_provider.py        Facebook
        │                       │                        │                     │
        │  return               │                        │                     │
        │  "3 open tasks..."    │                        │                     │
        │──────────────────────►│                        │                     │
        │                       │  provider.send(        │                     │
        │                       │    "15551234567",      │                     │
        │                       │    "3 open tasks..."   │                     │
        │                       │  )                     │                     │
        │                       │───────────────────────►│                     │
        │                       │                        │  POST               │
        │                       │                        │  /v19.0/.../messages│
        │                       │                        │  Authorization: ... │
        │                       │                        │  body: "3 open..."  │
        │                       │                        │────────────────────►│
        │                       │                        │                     │ delivers to
        │                       │                        │                     │ client WhatsApp
        │                       │                        │◄────────────────────│
        │                       │                        │  200 OK             │
        │                       │◄───────────────────────│                     │

  ★ Insight ─────────────────────────────────────
  - Your server never holds a permanent connection to the client's phone. The flow is always: client → Meta → your server   
  (inbound), and your server → Meta → client (outbound). Meta's servers are the middleman in both directions.
  - async with httpx.AsyncClient() is crucial here. async means while Python is waiting for Facebook to respond (which takes   100-500ms over the network), your server is free to handle other incoming webhook requests. Without async, the entire    
  server would freeze waiting for Meta to reply.
  - The reason sender_id (raw "15551234567") is used for provider.send() and NOT session_key ("+15551234567") is that Meta's   API rejects phone numbers with a leading +. The lstrip("+") on line 21 of meta_provider.py is a safety net in case a +   
  slips through.