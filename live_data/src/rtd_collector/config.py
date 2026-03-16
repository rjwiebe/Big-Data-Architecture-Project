from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class CollectorConfig:
    postgres_dsn: str
    vehicle_positions_url: str
    trip_updates_url: str
    alerts_url: str
    run_mode: str
    redis_url: str | None
    redis_key_prefix: str
    redis_ttl_seconds: int
    redis_publish_channel: str
    poll_interval_seconds: int
    request_timeout_seconds: int
    request_retry_total: int
    request_retry_backoff_seconds: float


DEFAULT_VEHICLE_POSITIONS_URL = "https://open-data.rtd-denver.com/files/gtfs-rt/rtd/VehiclePosition.pb"
DEFAULT_TRIP_UPDATES_URL = "https://open-data.rtd-denver.com/files/gtfs-rt/rtd/TripUpdate.pb"
DEFAULT_ALERTS_URL = "https://open-data.rtd-denver.com/files/gtfs-rt/rtd/Alerts.pb"


def load_config() -> CollectorConfig:
    load_dotenv()

    postgres_dsn = os.getenv("POSTGRES_DSN")
    if not postgres_dsn:
        raise ValueError("POSTGRES_DSN is required")

    return CollectorConfig(
        postgres_dsn=postgres_dsn,
        vehicle_positions_url=os.getenv("VEHICLE_POSITIONS_URL", DEFAULT_VEHICLE_POSITIONS_URL),
        trip_updates_url=os.getenv("TRIP_UPDATES_URL", DEFAULT_TRIP_UPDATES_URL),
        alerts_url=os.getenv("ALERTS_URL", DEFAULT_ALERTS_URL),
        run_mode=os.getenv("RUN_MODE", "daemon"),
        redis_url=os.getenv("REDIS_URL") or None,
        redis_key_prefix=os.getenv("REDIS_KEY_PREFIX", ""),
        redis_ttl_seconds=int(os.getenv("REDIS_TTL_SECONDS", "900")),
        redis_publish_channel=os.getenv("REDIS_PUBLISH_CHANNEL", "rtd:live_updates"),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "20")),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")),
        request_retry_total=int(os.getenv("REQUEST_RETRY_TOTAL", "3")),
        request_retry_backoff_seconds=float(os.getenv("REQUEST_RETRY_BACKOFF_SECONDS", "1.0")),
    )
