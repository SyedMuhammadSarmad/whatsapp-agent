from dotenv import load_dotenv
load_dotenv()  # load .env into os.environ before any SDK reads environment variables

from fastapi import FastAPI
from routers.whatsapp import router as whatsapp_router

app = FastAPI(title="WhatsApp AI Agent", version="1.0.0")

app.include_router(whatsapp_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
