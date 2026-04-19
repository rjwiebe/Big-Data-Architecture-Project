import os
import unittest
from unittest.mock import patch

from rtd_collector.static_sync import (
    DEFAULT_STATIC_GTFS_URLS,
    infer_feed_source,
    load_static_sync_config,
    parse_gtfs_time,
    qualify_id,
)


class StaticSyncTests(unittest.TestCase):
    def test_parse_gtfs_time_keeps_gtfs_values_over_24_hours(self):
        value, seconds = parse_gtfs_time("25:10:05")

        self.assertEqual(value, "25:10:05")
        self.assertEqual(seconds, 90605)

    def test_parse_gtfs_time_handles_empty_values(self):
        value, seconds = parse_gtfs_time("")

        self.assertIsNone(value)
        self.assertIsNone(seconds)

    def test_load_static_sync_config_uses_defaults(self):
        with patch.dict(
            os.environ,
            {
                "POSTGRES_DSN": "postgresql://collector:secret@localhost:5432/rtd_static",
            },
            clear=True,
        ):
            config = load_static_sync_config()

        self.assertEqual(config.postgres_dsn, "postgresql://collector:secret@localhost:5432/rtd_static")
        self.assertEqual(config.static_gtfs_urls, DEFAULT_STATIC_GTFS_URLS)
        self.assertEqual(config.timeout_seconds, 120)

    def test_load_static_sync_config_requires_postgres_dsn(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "POSTGRES_DSN is required"):
                load_static_sync_config()

    def test_infer_feed_source_uses_zip_filename(self):
        self.assertEqual(
            infer_feed_source("https://www.rtd-denver.com/files/gtfs/google_transit_flex.zip"),
            "google-transit-flex",
        )

    def test_qualify_id_prefixes_feed_source(self):
        self.assertEqual(qualify_id("google-transit", "route-10"), "google-transit:route-10")
