import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    postgres_dsn: str
    redis_url: str | None
    allowed_origins: list[str]
    port: int
    redis_ttl: int


def _parse_allowed_origins(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


def load_settings(*, require_postgres: bool = True) -> Settings:
    load_dotenv()

    postgres_dsn = os.getenv("POSTGRES_DSN") or ""
    if require_postgres and not postgres_dsn:
        raise ValueError("POSTGRES_DSN environment variable is required")

    return Settings(
        postgres_dsn=postgres_dsn,
        redis_url=os.getenv("REDIS_URL") or None,
        allowed_origins=_parse_allowed_origins(os.getenv("ALLOWED_ORIGINS")),
        port=int(os.getenv("PORT", "8080")),
        redis_ttl=int(os.getenv("REDIS_TTL", "900"))
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
