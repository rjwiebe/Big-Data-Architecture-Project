from __future__ import annotations

import argparse
import logging
import signal
import sys
from threading import Event

from .collector import FeedPull, GTFSRTCollector
from .config import load_config
from .db import PostgresStore
from .redis_store import RedisStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RTD Denver GTFS-RT collector")
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize PostgreSQL schema and exit",
    )
    parser.add_argument(
        "--once",
        choices=["vehicle_positions", "trip_updates", "alerts"],
        help="Collect only one feed once and exit",
    )
    parser.add_argument(
        "--run-mode",
        choices=["daemon", "cron"],
        help="Override RUN_MODE env var; use cron for one full pass then exit",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = load_config()
    store = PostgresStore(config.postgres_dsn)
    redis_store = None
    if config.redis_url:
        redis_store = RedisStore(
            config.redis_url,
            key_prefix=config.redis_key_prefix,
            ttl_seconds=config.redis_ttl_seconds,
            publish_channel=config.redis_publish_channel,
        )
        if redis_store.ping():
            logging.getLogger(__name__).info("Redis sink enabled")

    if args.init_db:
        store.init_schema()
        return

    collector = GTFSRTCollector(config=config, store=store, redis_store=redis_store)
    run_mode = args.run_mode or config.run_mode

    if args.once:
        url_map = {
            "vehicle_positions": config.vehicle_positions_url,
            "trip_updates": config.trip_updates_url,
            "alerts": config.alerts_url,
        }
        collector.collect_once(FeedPull(feed_type=args.once, url=url_map[args.once]))
        return

    if run_mode == "cron":
        failures = collector.collect_all_once()
        if failures:
            logging.getLogger(__name__).error("Cron run finished with %s failed feed(s)", failures)
            sys.exit(1)
        logging.getLogger(__name__).info("Cron run finished successfully")
        return

    stop_event = Event()

    def _request_stop(_: int, __: object) -> None:
        logging.getLogger(__name__).info("Shutdown signal received, stopping collector")
        stop_event.set()

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    collector.run_forever(stop_event=stop_event)


if __name__ == "__main__":
    main()
