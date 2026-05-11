import httpx
import time
import os
from redis_client import RedisClient

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_COSTS = {
    "openai/gpt-4o": {"in": 0.000005, "out": 0.000015},
    "anthropic/claude-haiku": {"in": 0.00000025, "out": 0.00000125},
    "openai/gpt-4o-mini": {"in": 0.00000015, "out": 0.0000006},
}

class LLMClient:
    def __init__(self, agent_id: str, project_id: str):
        self.agent_id = agent_id
        self.project_id = project_id
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.redis = RedisClient()

    async def call(self, messages: list, model: str = "openai/gpt-4o-mini") -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": model, "messages": messages}
            )
            data = response.json()

        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        rates = MODEL_COSTS.get(model, {"in": 0.000001, "out": 0.000002})
        cost = tokens_in * rates["in"] + tokens_out * rates["out"]

        await self.redis.stream_add("corp:costs", {
            "agent": self.agent_id,
            "project": self.project_id,
            "model": model,
            "tokens_in": str(tokens_in),
            "tokens_out": str(tokens_out),
            "cost_usd": str(round(cost, 8)),
            "ts": str(time.time())
        })

        return data
