from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Core ---
    OPENAI_API_KEY: str
    ASANA_ACCESS_TOKEN: str
    ASANA_WORKSPACE_ID: str
    REDIS_URL: str = "redis://localhost:6379"

    # --- Meta Cloud API — WhatsApp text messaging (Phase 1) ---
    META_PHONE_NUMBER_ID: str   # WhatsApp Business → Phone Numbers → Phone Number ID
    META_ACCESS_TOKEN: str      # System user token (permanent) or temp dev token
    META_APP_SECRET: str        # App → Settings → Basic → App Secret (for HMAC validation)
    META_VERIFY_TOKEN: str      # Any string you choose; enter same value in Meta console

    # --- Twilio — voice calling (Phase 3, optional until then) ---
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""   # E.164 number Twilio assigns for voice calls

    class Config:
        env_file = ".env"


settings = Settings()
