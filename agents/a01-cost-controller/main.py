import asyncio
import asyncpg
import redis.asyncio as aioredis
import os
import json
from dotenv import load_dotenv

load_dotenv("/Volumes/256/digital-corp/core/.env")

REDIS_URL = "redis://localhost:6379"
PG_DSN = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5432/{os.getenv('POSTGRES_DB')}"

async def main():
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    pg = await asyncpg.connect(PG_DSN)

    try:
        await r.xgroup_create("corp:costs", "a01-cost-controller", "$", mkstream=True)
    except Exception:
        pass

    print("A01 Cost Controller started")

    while True:
        msgs = await r.xreadgroup("a01-cost-controller", "worker-1", {"corp:costs": ">"}, count=10, block=2000)
        for stream, entries in (msgs or []):
            for msg_id, data in entries:
                try:
                    await pg.execute("""
                        INSERT INTO costs (agent_id, project_id, model, tokens_in, tokens_out, cost_usd)
                        VALUES ($1,$2,$3,$4,$5,$6)
                    """,
                        data.get("agent"), data.get("project"), data.get("model"),
                        int(data.get("tokens_in", 0)), int(data.get("tokens_out", 0)),
                        float(data.get("cost_usd", 0))
                    )
                    await r.xack("corp:costs", "a01-cost-controller", msg_id)
                except Exception as e:
                    print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
