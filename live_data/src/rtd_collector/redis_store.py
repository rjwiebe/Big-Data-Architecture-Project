from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import redis

logger = logging.getLogger(__name__)


def _isoformat(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_isoformat(item) for item in value]
    if isinstance(value, dict):
        return {key: _isoformat(item) for key, item in value.items()}
    return value


class RedisStore:
    def __init__(
        self,
        redis_url: str,
        *,
        key_prefix: str,
        ttl_seconds: int,
        publish_channel: str,
    ):
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds
        self._publish_channel = publish_channel

    def _entity_key(self, entity_id: str) -> str:
        if self._key_prefix:
            return f"{self._key_prefix}:{entity_id}"
        return entity_id

    def publish_entity(
        self,
        *,
        entity_id: str,
        feed_type: str,
        payload: dict[str, Any],
        feed_timestamp: datetime | None,
    ) -> None:
        key = self._entity_key(entity_id)
        current_raw = self._client.get(key)
        if current_raw:
            document = json.loads(current_raw)
        else:
            document = {
                "entity_id": entity_id,
                "feeds": {},
            }

        document["entity_id"] = entity_id
        document["updated_at"] = _isoformat(feed_timestamp)
        document["feeds"][feed_type] = _isoformat(payload)

        encoded = json.dumps(document, separators=(",", ":"), sort_keys=True)
        pipe = self._client.pipeline()
        pipe.set(key, encoded, ex=self._ttl_seconds)
        pipe.publish(
            self._publish_channel,
            json.dumps(
                {
                    "entity_id": entity_id,
                    "feed_type": feed_type,
                    "redis_key": key,
                    "feed_timestamp": _isoformat(feed_timestamp),
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
        pipe.execute()

    def ping(self) -> bool:
        return bool(self._client.ping())
