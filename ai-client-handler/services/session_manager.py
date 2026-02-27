import json
import redis.asyncio as aioredis
from config import settings

# Single connection pool shared across all requests
_redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

_HISTORY_TTL = 86400  # 24 hours — conversation resets after a day of inactivity


async def get_history(client_id: str) -> list:
    """Return the stored conversation history for a client, or [] if none."""
    data = await _redis.get(f"history:{client_id}")
    return json.loads(data) if data else []


async def save_history(client_id: str, history: list) -> None:
    """Persist conversation history with a 24-hour TTL."""
    await _redis.setex(f"history:{client_id}", _HISTORY_TTL, json.dumps(history))


async def clear_history(client_id: str) -> None:
    """Explicitly reset a client's conversation (e.g. on demand or after resolution)."""
    await _redis.delete(f"history:{client_id}")
