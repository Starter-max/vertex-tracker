import redis.asyncio as redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class RedisClient:
    def __init__(self):
        self.r = redis.from_url(REDIS_URL, decode_responses=True)

    async def stream_add(self, stream: str, data: dict):
        await self.r.xadd(stream, data)

    async def stream_read(self, stream: str, group: str, consumer: str, count: int = 10):
        try:
            return await self.r.xreadgroup(group, consumer, {stream: ">"}, count=count)
        except Exception:
            return []

    async def ping(self) -> bool:
        try:
            return await self.r.ping()
        except Exception:
            return False
