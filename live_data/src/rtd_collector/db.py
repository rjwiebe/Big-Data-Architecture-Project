from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


def to_utc_dt(timestamp: int | None) -> datetime | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


class PostgresStore:
    def __init__(self, dsn: str):
        self._dsn = dsn

    @contextmanager
    def connection(self) -> Iterator[psycopg2.extensions.connection]:
        conn = psycopg2.connect(self._dsn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self, schema_path: str = "sql/schema.sql") -> None:
        path = Path(schema_path)
        ddl = path.read_text(encoding="utf-8")
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
        logger.info("Schema initialized from %s", path)

    def insert_ingestion(
        self,
        conn: psycopg2.extensions.connection,
        *,
        feed_type: str,
        source_url: str,
        feed_timestamp: datetime | None,
        raw_payload: bytes,
        entity_count: int,
        status_code: int,
    ) -> int:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO feed_ingestions (
                    feed_type,
                    source_url,
                    feed_timestamp,
                    raw_payload,
                    entity_count,
                    status_code
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    feed_type,
                    source_url,
                    feed_timestamp,
                    psycopg2.Binary(raw_payload),
                    entity_count,
                    status_code,
                ),
            )
            return cur.fetchone()[0]

    def insert_vehicle_positions(
        self,
        conn: psycopg2.extensions.connection,
        rows: list[tuple],
    ) -> None:
        if not rows:
            return
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO vehicle_positions (
                    ingestion_id,
                    feed_timestamp,
                    entity_id,
                    trip_id,
                    route_id,
                    vehicle_id,
                    vehicle_label,
                    latitude,
                    longitude,
                    bearing,
                    speed_mps,
                    occupancy_status,
                    current_status,
                    current_stop_sequence,
                    stop_id,
                    vehicle_timestamp
                )
                VALUES %s
                ON CONFLICT (entity_id, feed_timestamp)
                DO UPDATE SET
                    ingestion_id = EXCLUDED.ingestion_id,
                    trip_id = EXCLUDED.trip_id,
                    route_id = EXCLUDED.route_id,
                    vehicle_id = EXCLUDED.vehicle_id,
                    vehicle_label = EXCLUDED.vehicle_label,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    bearing = EXCLUDED.bearing,
                    speed_mps = EXCLUDED.speed_mps,
                    occupancy_status = EXCLUDED.occupancy_status,
                    current_status = EXCLUDED.current_status,
                    current_stop_sequence = EXCLUDED.current_stop_sequence,
                    stop_id = EXCLUDED.stop_id,
                    vehicle_timestamp = EXCLUDED.vehicle_timestamp
                """,
                rows,
                page_size=500,
            )

    def insert_trip_updates(
        self,
        conn: psycopg2.extensions.connection,
        rows: list[tuple],
    ) -> list[int]:
        if not rows:
            return []
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO trip_updates (
                    ingestion_id,
                    feed_timestamp,
                    entity_id,
                    trip_id,
                    route_id,
                    direction_id,
                    start_date,
                    schedule_relationship,
                    vehicle_id,
                    vehicle_label,
                    delay_seconds,
                    timestamp
                )
                VALUES %s
                ON CONFLICT (entity_id, feed_timestamp)
                DO UPDATE SET
                    ingestion_id = EXCLUDED.ingestion_id,
                    trip_id = EXCLUDED.trip_id,
                    route_id = EXCLUDED.route_id,
                    direction_id = EXCLUDED.direction_id,
                    start_date = EXCLUDED.start_date,
                    schedule_relationship = EXCLUDED.schedule_relationship,
                    vehicle_id = EXCLUDED.vehicle_id,
                    vehicle_label = EXCLUDED.vehicle_label,
                    delay_seconds = EXCLUDED.delay_seconds,
                    timestamp = EXCLUDED.timestamp
                RETURNING id
                """,
                rows,
                page_size=200,
            )
            result = cur.fetchall()
        return [row[0] for row in result]

    def insert_stop_time_updates(
        self,
        conn: psycopg2.extensions.connection,
        rows: list[tuple],
    ) -> None:
        if not rows:
            return
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO stop_time_updates (
                    trip_update_id,
                    stop_sequence,
                    stop_id,
                    arrival_delay_seconds,
                    arrival_time,
                    departure_delay_seconds,
                    departure_time,
                    schedule_relationship
                )
                VALUES %s
                ON CONFLICT (trip_update_id, stop_sequence, stop_id)
                DO UPDATE SET
                    arrival_delay_seconds = EXCLUDED.arrival_delay_seconds,
                    arrival_time = EXCLUDED.arrival_time,
                    departure_delay_seconds = EXCLUDED.departure_delay_seconds,
                    departure_time = EXCLUDED.departure_time,
                    schedule_relationship = EXCLUDED.schedule_relationship
                """,
                rows,
                page_size=500,
            )

    def insert_alerts(
        self,
        conn: psycopg2.extensions.connection,
        rows: list[tuple],
    ) -> None:
        if not rows:
            return
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO alerts (
                    ingestion_id,
                    feed_timestamp,
                    entity_id,
                    active_period_start,
                    active_period_end,
                    cause,
                    effect,
                    severity_level,
                    header_text,
                    description_text
                )
                VALUES %s
                ON CONFLICT (entity_id, feed_timestamp)
                DO UPDATE SET
                    ingestion_id = EXCLUDED.ingestion_id,
                    active_period_start = EXCLUDED.active_period_start,
                    active_period_end = EXCLUDED.active_period_end,
                    cause = EXCLUDED.cause,
                    effect = EXCLUDED.effect,
                    severity_level = EXCLUDED.severity_level,
                    header_text = EXCLUDED.header_text,
                    description_text = EXCLUDED.description_text
                """,
                rows,
                page_size=200,
            )
