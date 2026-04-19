import os
import unittest
from unittest.mock import patch

from rtd_collector.config import (
    DEFAULT_ALERTS_URL,
    DEFAULT_TRIP_UPDATES_URL,
    DEFAULT_VEHICLE_POSITIONS_URL,
    load_config,
)


class CollectorConfigTests(unittest.TestCase):
    def test_load_config_requires_postgres_dsn(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "POSTGRES_DSN is required"):
                load_config()

    def test_load_config_uses_defaults_when_optional_env_is_missing(self):
        with patch.dict(
            os.environ,
            {
                "POSTGRES_DSN": "postgresql://collector:secret@localhost:5432/rtd_live",
            },
            clear=True,
        ):
            config = load_config()

        self.assertEqual(config.postgres_dsn, "postgresql://collector:secret@localhost:5432/rtd_live")
        self.assertEqual(config.vehicle_positions_url, DEFAULT_VEHICLE_POSITIONS_URL)
        self.assertEqual(config.trip_updates_url, DEFAULT_TRIP_UPDATES_URL)
        self.assertEqual(config.alerts_url, DEFAULT_ALERTS_URL)
        self.assertEqual(config.run_mode, "daemon")
        self.assertIsNone(config.redis_url)
        self.assertEqual(config.poll_interval_seconds, 20)
        self.assertEqual(config.request_timeout_seconds, 20)

    def test_load_config_reads_overrides(self):
        with patch.dict(
            os.environ,
            {
                "POSTGRES_DSN": "postgresql://collector:secret@localhost:5432/rtd_live",
                "RUN_MODE": "cron",
                "REDIS_URL": "redis://localhost:6379/0",
                "REDIS_KEY_PREFIX": "rtd",
                "REDIS_TTL_SECONDS": "120",
                "REDIS_PUBLISH_CHANNEL": "rtd:updates",
                "POLL_INTERVAL_SECONDS": "45",
                "REQUEST_TIMEOUT_SECONDS": "12",
                "REQUEST_RETRY_TOTAL": "5",
                "REQUEST_RETRY_BACKOFF_SECONDS": "2.5",
            },
            clear=True,
        ):
            config = load_config()

        self.assertEqual(config.run_mode, "cron")
        self.assertEqual(config.redis_url, "redis://localhost:6379/0")
        self.assertEqual(config.redis_key_prefix, "rtd")
        self.assertEqual(config.redis_ttl_seconds, 120)
        self.assertEqual(config.redis_publish_channel, "rtd:updates")
        self.assertEqual(config.poll_interval_seconds, 45)
        self.assertEqual(config.request_timeout_seconds, 12)
        self.assertEqual(config.request_retry_total, 5)
        self.assertEqual(config.request_retry_backoff_seconds, 2.5)
