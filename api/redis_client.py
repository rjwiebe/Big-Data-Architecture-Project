import json
import logging
import redis.asyncio as redis

class RedisClient:
    def __init__(self, redis_url: str | None, ttl: int = 900):
        self.redis_url = redis_url
        self.redis_pool = None
        self.ttl = ttl
        self.logger = logging.getLogger(__name__)

    async def connect(self):
        if self.redis_pool or not self.redis_url:
            return
        self.redis_pool = redis.from_url(self.redis_url, decode_responses=True)

    async def disconnect(self):
        if self.redis_pool:
            await self.redis_pool.aclose()
            self.redis_pool = None

    async def publish_entity(self, key: str, channel: str, entity_dict: dict):
        if not self.redis_pool:
            await self.connect()
        
        if not self.redis_pool:
            return

        try:
            entity_json = json.dumps(entity_dict)
            
            async with self.redis_pool.pipeline(transaction=True) as pipe:
                pipe.setex(key, self.ttl, entity_json)
                pipe.publish(channel, entity_json)
                await pipe.execute()
                
        except Exception as exc:
            self.logger.error("Failed to publish entity to %s: %s", key, exc)

    async def get_realtime_updates(self, stop_id: str):
        if not self.redis_pool:
            await self.connect()

        if not self.redis_pool:
            return []

        # Redis schema is not finalized yet, so realtime enrichment remains best-effort.
        # Missing or unreadable keys should never break the public API contract.
        try:
            await self.redis_pool.ping()
        except Exception as exc:
            self.logger.warning("Realtime Redis unavailable for %s: %s", stop_id, exc)
            return []

        return []
