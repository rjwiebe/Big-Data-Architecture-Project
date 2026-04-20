from __future__ import annotations

import argparse
import csv
import logging
import os
from dataclasses import dataclass
from io import BytesIO, TextIOWrapper
from pathlib import Path
from zipfile import ZipFile

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

DEFAULT_STATIC_GTFS_URLS = (
    "https://www.rtd-denver.com/files/gtfs/google_transit.zip",
    "https://www.rtd-denver.com/files/gtfs/google_transit_flex.zip",
    "https://www.rtd-denver.com/files/gtfs/bustang-co-us.zip",
)
DEFAULT_TIMEOUT_SECONDS = 120
REQUIRED_GTFS_FILES = (
    "routes.txt",
    "stops.txt",
    "trips.txt",
    "stop_times.txt",
    "shapes.txt",
)


@dataclass(frozen=True)
class StaticSyncConfig:
    postgres_dsn: str
    static_gtfs_urls: tuple[str, ...]
    timeout_seconds: int


@dataclass(frozen=True)
class StaticSyncResult:
    routes: int
    stops: int
    trips: int
    stop_times: int
    shapes: int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RTD Denver static GTFS sync")
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize static GTFS PostgreSQL schema and exit",
    )
    parser.add_argument(
        "--download-url",
        action="append",
        help="Override STATIC_GTFS_URLS for this run; pass multiple times for multiple archives",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def load_static_sync_config(download_urls: list[str] | None = None) -> StaticSyncConfig:
    load_dotenv()

    postgres_dsn = os.getenv("POSTGRES_DSN")
    if not postgres_dsn:
        raise ValueError("POSTGRES_DSN is required")

    configured_urls = download_urls
    if not configured_urls:
        env_urls = os.getenv("STATIC_GTFS_URLS")
        if env_urls:
            delimiter = "|" if "|" in env_urls else ","
            configured_urls = [url.strip() for url in env_urls.split(delimiter) if url.strip()]
        else:
            configured_urls = list(DEFAULT_STATIC_GTFS_URLS)

    return StaticSyncConfig(
        postgres_dsn=postgres_dsn,
        static_gtfs_urls=tuple(configured_urls),
        timeout_seconds=int(os.getenv("STATIC_GTFS_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))),
    )


def parse_gtfs_time(value: str | None) -> tuple[str | None, int | None]:
    if value is None:
        return None, None

    normalized = value.strip()
    if not normalized:
        return None, None

    parts = normalized.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid GTFS time value: {value}")

    hours, minutes, seconds = (int(part) for part in parts)
    return normalized, (hours * 3600) + (minutes * 60) + seconds


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _to_int(value: str | None) -> int | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    return int(cleaned)


def _to_float(value: str | None) -> float | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    return float(cleaned)


def download_gtfs_zip(url: str, timeout_seconds: int) -> bytes:
    response = requests.get(
        url,
        timeout=timeout_seconds,
        headers={"User-Agent": "rtd-denver-static-gtfs-sync/0.1.0"},
    )
    response.raise_for_status()
    return response.content


def infer_feed_source(url: str) -> str:
    filename = url.rstrip("/").rsplit("/", 1)[-1]
    stem = filename.removesuffix(".zip")
    return stem.replace("_", "-").replace(".", "-") or "static-gtfs"


def qualify_id(feed_source: str, raw_id: str | None) -> str | None:
    cleaned = _clean_text(raw_id)
    if cleaned is None:
        return None
    return f"{feed_source}:{cleaned}"


class StaticGTFSStore:
    def __init__(self, dsn: str):
        self._dsn = dsn

    def init_schema(self, schema_path: str = "sql/static_schema.sql") -> None:
        path = Path(schema_path)
        ddl = path.read_text(encoding="utf-8")
        with psycopg2.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
        logger.info("Static schema initialized from %s", path)

    def sync_archives(self, archives: list[tuple[str, bytes]]) -> StaticSyncResult:
        with psycopg2.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                self._truncate_existing_tables(cur)
                routes = 0
                stops = 0
                trips = 0
                stop_times = 0
                shapes = 0

                for url, payload in archives:
                    feed_source = infer_feed_source(url)
                    with ZipFile(BytesIO(payload)) as archive:
                        self._validate_required_files(archive)
                        routes += self._load_routes(cur, archive, feed_source)
                        stops += self._load_stops(cur, archive, feed_source)
                        trips += self._load_trips(cur, archive, feed_source)
                        stop_times += self._load_stop_times(cur, archive, feed_source)
                        shapes += self._load_shapes(cur, archive, feed_source)

        return StaticSyncResult(
            routes=routes,
            stops=stops,
            trips=trips,
            stop_times=stop_times,
            shapes=shapes,
        )

    def _validate_required_files(self, archive: ZipFile) -> None:
        archive_names = set(archive.namelist())
        missing = [name for name in REQUIRED_GTFS_FILES if name not in archive_names]
        if missing:
            raise FileNotFoundError(f"GTFS archive missing required files: {', '.join(missing)}")

    def _truncate_existing_tables(self, cur: psycopg2.extensions.cursor) -> None:
        cur.execute(
            """
            TRUNCATE TABLE
                stop_times,
                trips,
                shapes,
                routes,
                stops
            CASCADE
            """
        )

    def _reader(self, archive: ZipFile, filename: str) -> csv.DictReader:
        handle = archive.open(filename, "r")
        wrapper = TextIOWrapper(handle, encoding="utf-8-sig", newline="")
        return csv.DictReader(wrapper)

    def _load_routes(self, cur: psycopg2.extensions.cursor, archive: ZipFile, feed_source: str) -> int:
        query = """
            INSERT INTO routes (
                route_id,
                feed_source,
                route_short_name,
                route_long_name,
                route_type,
                route_color,
                route_text_color
            )
            VALUES %s
        """
        return self._bulk_insert(
            cur,
            query,
            (
                (
                    qualify_id(feed_source, row["route_id"]),
                    feed_source,
                    _clean_text(row.get("route_short_name")),
                    _clean_text(row.get("route_long_name")),
                    _to_int(row.get("route_type")),
                    _clean_text(row.get("route_color")),
                    _clean_text(row.get("route_text_color")),
                )
                for row in self._reader(archive, "routes.txt")
            ),
        )

    def _load_stops(self, cur: psycopg2.extensions.cursor, archive: ZipFile, feed_source: str) -> int:
        query = """
            INSERT INTO stops (
                stop_id,
                feed_source,
                stop_name,
                stop_lat,
                stop_lon
            )
            VALUES %s
        """
        return self._bulk_insert(
            cur,
            query,
            (
                (
                    qualify_id(feed_source, row["stop_id"]),
                    feed_source,
                    _clean_text(row.get("stop_name")) or "",
                    _to_float(row.get("stop_lat")),
                    _to_float(row.get("stop_lon")),
                )
                for row in self._reader(archive, "stops.txt")
            ),
        )

    def _load_trips(self, cur: psycopg2.extensions.cursor, archive: ZipFile, feed_source: str) -> int:
        query = """
            INSERT INTO trips (
                trip_id,
                feed_source,
                route_id,
                service_id,
                trip_headsign,
                direction_id,
                shape_id
            )
            VALUES %s
        """
        return self._bulk_insert(
            cur,
            query,
            (
                (
                    qualify_id(feed_source, row["trip_id"]),
                    feed_source,
                    qualify_id(feed_source, row["route_id"]),
                    _clean_text(row.get("service_id")),
                    _clean_text(row.get("trip_headsign")),
                    _to_int(row.get("direction_id")),
                    qualify_id(feed_source, row.get("shape_id")),
                )
                for row in self._reader(archive, "trips.txt")
            ),
        )

    def _load_stop_times(self, cur: psycopg2.extensions.cursor, archive: ZipFile, feed_source: str) -> int:
        query = """
            INSERT INTO stop_times (
                trip_id,
                feed_source,
                arrival_time,
                departure_time,
                arrival_seconds,
                departure_seconds,
                stop_id,
                stop_sequence
            )
            VALUES %s
        """

        def rows() -> list[tuple[str | int | None, ...]]:
            for row in self._reader(archive, "stop_times.txt"):
                arrival_time, arrival_seconds = parse_gtfs_time(row.get("arrival_time"))
                departure_time, departure_seconds = parse_gtfs_time(row.get("departure_time"))
                yield (
                    qualify_id(feed_source, row["trip_id"]),
                    feed_source,
                    arrival_time,
                    departure_time,
                    arrival_seconds,
                    departure_seconds,
                    qualify_id(feed_source, row["stop_id"]),
                    _to_int(row.get("stop_sequence")),
                )

        return self._bulk_insert(cur, query, rows())

    def _load_shapes(self, cur: psycopg2.extensions.cursor, archive: ZipFile, feed_source: str) -> int:
        query = """
            INSERT INTO shapes (
                shape_id,
                feed_source,
                shape_pt_lat,
                shape_pt_lon,
                shape_pt_sequence
            )
            VALUES %s
        """
        return self._bulk_insert(
            cur,
            query,
            (
                (
                    qualify_id(feed_source, row["shape_id"]),
                    feed_source,
                    _to_float(row.get("shape_pt_lat")),
                    _to_float(row.get("shape_pt_lon")),
                    _to_int(row.get("shape_pt_sequence")),
                )
                for row in self._reader(archive, "shapes.txt")
            ),
        )

    def _bulk_insert(
        self,
        cur: psycopg2.extensions.cursor,
        query: str,
        rows: object,
        *,
        batch_size: int = 1000,
    ) -> int:
        count = 0
        batch: list[tuple[object, ...]] = []
        for row in rows:
            batch.append(row)
            if len(batch) >= batch_size:
                psycopg2.extras.execute_values(cur, query, batch, page_size=batch_size)
                count += len(batch)
                batch.clear()

        if batch:
            psycopg2.extras.execute_values(cur, query, batch, page_size=batch_size)
            count += len(batch)

        return count


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = load_static_sync_config(args.download_url)
    store = StaticGTFSStore(config.postgres_dsn)

    if args.init_db:
        store.init_schema()
        return

    store.init_schema()
    archives = [(url, download_gtfs_zip(url, config.timeout_seconds)) for url in config.static_gtfs_urls]
    result = store.sync_archives(archives)
    logger.info(
        "Static GTFS sync complete from %s source archive(s): %s routes, %s stops, %s trips, %s stop_times, %s shapes",
        len(config.static_gtfs_urls),
        result.routes,
        result.stops,
        result.trips,
        result.stop_times,
        result.shapes,
    )


if __name__ == "__main__":
    main()
