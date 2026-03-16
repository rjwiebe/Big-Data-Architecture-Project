from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from threading import Event
from typing import Any

import requests
from google.transit import gtfs_realtime_pb2
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import CollectorConfig
from .db import PostgresStore, to_utc_dt
from .redis_store import RedisStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedPull:
    feed_type: str
    url: str


def _safe_enum_name(enum_cls: Any, value: int | None) -> str | None:
    if value is None:
        return None
    try:
        return enum_cls.Name(value)
    except ValueError:
        return str(value)


class GTFSRTCollector:
    def __init__(self, config: CollectorConfig, store: PostgresStore, redis_store: RedisStore | None = None):
        self.config = config
        self.store = store
        self.redis_store = redis_store
        self.session = requests.Session()
        retry = Retry(
            total=self.config.request_retry_total,
            connect=self.config.request_retry_total,
            read=self.config.request_retry_total,
            backoff_factor=self.config.request_retry_backoff_seconds,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({"User-Agent": "rtd-denver-live-data-collector/0.1.0"})

    def build_pulls(self) -> list[FeedPull]:
        return [
            FeedPull("vehicle_positions", self.config.vehicle_positions_url),
            FeedPull("trip_updates", self.config.trip_updates_url),
            FeedPull("alerts", self.config.alerts_url),
        ]

    def collect_all_once(self, *, raise_on_error: bool = False) -> int:
        failures = 0
        for pull in self.build_pulls():
            try:
                self.collect_once(pull)
            except Exception:
                failures += 1
                logger.exception("Failed to collect %s", pull.feed_type)
                if raise_on_error:
                    raise
        return failures

    def run_forever(self, stop_event: Event | None = None) -> None:
        stop_event = stop_event or Event()
        pulls = self.build_pulls()

        logger.info("Starting collector loop with %ss poll interval", self.config.poll_interval_seconds)
        while not stop_event.is_set():
            started = time.monotonic()
            for pull in pulls:
                if stop_event.is_set():
                    break
                try:
                    self.collect_once(pull)
                except Exception:
                    logger.exception("Failed to collect %s", pull.feed_type)

            elapsed = time.monotonic() - started
            sleep_seconds = max(0, self.config.poll_interval_seconds - elapsed)
            if sleep_seconds:
                stop_event.wait(sleep_seconds)
        logger.info("Collector loop stopped")

    def collect_once(self, pull: FeedPull) -> None:
        response = self.session.get(pull.url, timeout=self.config.request_timeout_seconds)
        response.raise_for_status()

        message = gtfs_realtime_pb2.FeedMessage()
        message.ParseFromString(response.content)

        feed_timestamp = to_utc_dt(message.header.timestamp if message.header.timestamp else None)

        with self.store.connection() as conn:
            ingestion_id = self.store.insert_ingestion(
                conn,
                feed_type=pull.feed_type,
                source_url=pull.url,
                feed_timestamp=feed_timestamp,
                raw_payload=response.content,
                entity_count=len(message.entity),
                status_code=response.status_code,
            )

            if pull.feed_type == "vehicle_positions":
                rows = self._vehicle_rows(ingestion_id, feed_timestamp, message)
                self.store.insert_vehicle_positions(conn, rows)
                self._publish_redis_entities("vehicle_positions", feed_timestamp, message)
                logger.info("Inserted %s vehicle position rows", len(rows))
            elif pull.feed_type == "trip_updates":
                trip_rows, stop_rows_by_trip_idx = self._trip_rows(ingestion_id, feed_timestamp, message)
                ids = self.store.insert_trip_updates(conn, trip_rows)
                stop_rows: list[tuple[Any, ...]] = []
                for idx, trip_update_id in enumerate(ids):
                    for row in stop_rows_by_trip_idx.get(idx, []):
                        stop_rows.append((trip_update_id, *row))
                self.store.insert_stop_time_updates(conn, stop_rows)
                self._publish_redis_entities("trip_updates", feed_timestamp, message)
                logger.info("Inserted %s trip update rows and %s stop time rows", len(ids), len(stop_rows))
            elif pull.feed_type == "alerts":
                rows = self._alert_rows(ingestion_id, feed_timestamp, message)
                self.store.insert_alerts(conn, rows)
                self._publish_redis_entities("alerts", feed_timestamp, message)
                logger.info("Inserted %s alert rows", len(rows))

    def _publish_redis_entities(
        self,
        feed_type: str,
        feed_timestamp: datetime | None,
        message: gtfs_realtime_pb2.FeedMessage,
    ) -> None:
        if not self.redis_store:
            return

        try:
            if feed_type == "vehicle_positions":
                self._publish_vehicle_entities(feed_timestamp, message)
            elif feed_type == "trip_updates":
                self._publish_trip_entities(feed_timestamp, message)
            elif feed_type == "alerts":
                self._publish_alert_entities(feed_timestamp, message)
        except Exception:
            logger.exception("Failed to publish %s entities to Redis", feed_type)

    def _vehicle_rows(
        self,
        ingestion_id: int,
        feed_timestamp: datetime | None,
        message: gtfs_realtime_pb2.FeedMessage,
    ) -> list[tuple[Any, ...]]:
        rows: list[tuple[Any, ...]] = []
        for entity in message.entity:
            if not entity.HasField("vehicle"):
                continue

            vehicle = entity.vehicle
            trip = vehicle.trip
            position = vehicle.position
            descriptor = vehicle.vehicle

            rows.append(
                (
                    ingestion_id,
                    feed_timestamp,
                    entity.id or None,
                    trip.trip_id or None,
                    trip.route_id or None,
                    descriptor.id or None,
                    descriptor.label or None,
                    position.latitude if vehicle.HasField("position") else None,
                    position.longitude if vehicle.HasField("position") else None,
                    position.bearing if position.HasField("bearing") else None,
                    position.speed if position.HasField("speed") else None,
                    _safe_enum_name(
                        gtfs_realtime_pb2.VehiclePosition.OccupancyStatus,
                        vehicle.occupancy_status if vehicle.HasField("occupancy_status") else None,
                    ),
                    _safe_enum_name(
                        gtfs_realtime_pb2.VehiclePosition.VehicleStopStatus,
                        vehicle.current_status if vehicle.HasField("current_status") else None,
                    ),
                    vehicle.current_stop_sequence if vehicle.HasField("current_stop_sequence") else None,
                    vehicle.stop_id or None,
                    to_utc_dt(vehicle.timestamp if vehicle.HasField("timestamp") else None),
                )
            )

        return rows

    def _publish_vehicle_entities(
        self,
        feed_timestamp: datetime | None,
        message: gtfs_realtime_pb2.FeedMessage,
    ) -> None:
        if not self.redis_store:
            return

        published = 0
        for entity in message.entity:
            if not entity.HasField("vehicle") or not entity.id:
                continue

            vehicle = entity.vehicle
            trip = vehicle.trip
            position = vehicle.position
            descriptor = vehicle.vehicle

            payload = {
                "entity_id": entity.id,
                "trip_id": trip.trip_id or None,
                "route_id": trip.route_id or None,
                "vehicle_id": descriptor.id or None,
                "vehicle_label": descriptor.label or None,
                "latitude": position.latitude if vehicle.HasField("position") else None,
                "longitude": position.longitude if vehicle.HasField("position") else None,
                "bearing": position.bearing if position.HasField("bearing") else None,
                "speed_mps": position.speed if position.HasField("speed") else None,
                "occupancy_status": _safe_enum_name(
                    gtfs_realtime_pb2.VehiclePosition.OccupancyStatus,
                    vehicle.occupancy_status if vehicle.HasField("occupancy_status") else None,
                ),
                "current_status": _safe_enum_name(
                    gtfs_realtime_pb2.VehiclePosition.VehicleStopStatus,
                    vehicle.current_status if vehicle.HasField("current_status") else None,
                ),
                "current_stop_sequence": vehicle.current_stop_sequence if vehicle.HasField("current_stop_sequence") else None,
                "stop_id": vehicle.stop_id or None,
                "vehicle_timestamp": to_utc_dt(vehicle.timestamp if vehicle.HasField("timestamp") else None),
            }
            self.redis_store.publish_entity(
                entity_id=entity.id,
                feed_type="vehicle_positions",
                payload=payload,
                feed_timestamp=feed_timestamp,
            )
            published += 1

        logger.info("Published %s vehicle entities to Redis", published)

    def _trip_rows(
        self,
        ingestion_id: int,
        feed_timestamp: datetime | None,
        message: gtfs_realtime_pb2.FeedMessage,
    ) -> tuple[list[tuple[Any, ...]], dict[int, list[tuple[Any, ...]]]]:
        trip_rows: list[tuple[Any, ...]] = []
        stop_rows_by_trip_idx: dict[int, list[tuple[Any, ...]]] = {}

        for entity in message.entity:
            if not entity.HasField("trip_update"):
                continue

            trip_update = entity.trip_update
            trip = trip_update.trip
            vehicle = trip_update.vehicle
            trip_idx = len(trip_rows)

            trip_rows.append(
                (
                    ingestion_id,
                    feed_timestamp,
                    entity.id or None,
                    trip.trip_id or None,
                    trip.route_id or None,
                    trip.direction_id if trip.HasField("direction_id") else None,
                    trip.start_date or None,
                    _safe_enum_name(
                        gtfs_realtime_pb2.TripDescriptor.ScheduleRelationship,
                        trip.schedule_relationship if trip.HasField("schedule_relationship") else None,
                    ),
                    vehicle.id or None,
                    vehicle.label or None,
                    trip_update.delay if trip_update.HasField("delay") else None,
                    to_utc_dt(trip_update.timestamp if trip_update.HasField("timestamp") else None),
                )
            )

            stop_rows: list[tuple[Any, ...]] = []
            for stu in trip_update.stop_time_update:
                stop_rows.append(
                    (
                        stu.stop_sequence if stu.HasField("stop_sequence") else None,
                        stu.stop_id or None,
                        stu.arrival.delay if stu.HasField("arrival") and stu.arrival.HasField("delay") else None,
                        to_utc_dt(
                            stu.arrival.time
                            if stu.HasField("arrival") and stu.arrival.HasField("time")
                            else None
                        ),
                        stu.departure.delay
                        if stu.HasField("departure") and stu.departure.HasField("delay")
                        else None,
                        to_utc_dt(
                            stu.departure.time
                            if stu.HasField("departure") and stu.departure.HasField("time")
                            else None
                        ),
                        _safe_enum_name(
                            gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.ScheduleRelationship,
                            stu.schedule_relationship if stu.HasField("schedule_relationship") else None,
                        ),
                    )
                )

            stop_rows_by_trip_idx[trip_idx] = stop_rows

        return trip_rows, stop_rows_by_trip_idx

    def _publish_trip_entities(
        self,
        feed_timestamp: datetime | None,
        message: gtfs_realtime_pb2.FeedMessage,
    ) -> None:
        if not self.redis_store:
            return

        published = 0
        for entity in message.entity:
            if not entity.HasField("trip_update") or not entity.id:
                continue

            trip_update = entity.trip_update
            trip = trip_update.trip
            vehicle = trip_update.vehicle
            stop_updates: list[dict[str, Any]] = []
            for stu in trip_update.stop_time_update:
                stop_updates.append(
                    {
                        "stop_sequence": stu.stop_sequence if stu.HasField("stop_sequence") else None,
                        "stop_id": stu.stop_id or None,
                        "arrival_delay_seconds": stu.arrival.delay
                        if stu.HasField("arrival") and stu.arrival.HasField("delay")
                        else None,
                        "arrival_time": to_utc_dt(
                            stu.arrival.time if stu.HasField("arrival") and stu.arrival.HasField("time") else None
                        ),
                        "departure_delay_seconds": stu.departure.delay
                        if stu.HasField("departure") and stu.departure.HasField("delay")
                        else None,
                        "departure_time": to_utc_dt(
                            stu.departure.time
                            if stu.HasField("departure") and stu.departure.HasField("time")
                            else None
                        ),
                        "schedule_relationship": _safe_enum_name(
                            gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.ScheduleRelationship,
                            stu.schedule_relationship if stu.HasField("schedule_relationship") else None,
                        ),
                    }
                )

            payload = {
                "entity_id": entity.id,
                "trip_id": trip.trip_id or None,
                "route_id": trip.route_id or None,
                "direction_id": trip.direction_id if trip.HasField("direction_id") else None,
                "start_date": trip.start_date or None,
                "schedule_relationship": _safe_enum_name(
                    gtfs_realtime_pb2.TripDescriptor.ScheduleRelationship,
                    trip.schedule_relationship if trip.HasField("schedule_relationship") else None,
                ),
                "vehicle_id": vehicle.id or None,
                "vehicle_label": vehicle.label or None,
                "delay_seconds": trip_update.delay if trip_update.HasField("delay") else None,
                "timestamp": to_utc_dt(trip_update.timestamp if trip_update.HasField("timestamp") else None),
                "stop_time_updates": stop_updates,
            }
            self.redis_store.publish_entity(
                entity_id=entity.id,
                feed_type="trip_updates",
                payload=payload,
                feed_timestamp=feed_timestamp,
            )
            published += 1

        logger.info("Published %s trip update entities to Redis", published)

    def _alert_rows(
        self,
        ingestion_id: int,
        feed_timestamp: datetime | None,
        message: gtfs_realtime_pb2.FeedMessage,
    ) -> list[tuple[Any, ...]]:
        rows: list[tuple[Any, ...]] = []

        for entity in message.entity:
            if not entity.HasField("alert"):
                continue

            alert = entity.alert
            active_start = None
            active_end = None
            if alert.active_period:
                period = alert.active_period[0]
                active_start = to_utc_dt(period.start if period.HasField("start") else None)
                active_end = to_utc_dt(period.end if period.HasField("end") else None)

            rows.append(
                (
                    ingestion_id,
                    feed_timestamp,
                    entity.id or None,
                    active_start,
                    active_end,
                    _safe_enum_name(gtfs_realtime_pb2.Alert.Cause, alert.cause if alert.HasField("cause") else None),
                    _safe_enum_name(
                        gtfs_realtime_pb2.Alert.Effect,
                        alert.effect if alert.HasField("effect") else None,
                    ),
                    _safe_enum_name(
                        gtfs_realtime_pb2.Alert.SeverityLevel,
                        alert.severity_level if alert.HasField("severity_level") else None,
                    ),
                    alert.header_text.translation[0].text
                    if alert.header_text.translation
                    else None,
                    alert.description_text.translation[0].text
                    if alert.description_text.translation
                    else None,
                )
            )

        return rows

    def _publish_alert_entities(
        self,
        feed_timestamp: datetime | None,
        message: gtfs_realtime_pb2.FeedMessage,
    ) -> None:
        if not self.redis_store:
            return

        published = 0
        for entity in message.entity:
            if not entity.HasField("alert") or not entity.id:
                continue

            alert = entity.alert
            active_periods: list[dict[str, Any]] = []
            for period in alert.active_period:
                active_periods.append(
                    {
                        "start": to_utc_dt(period.start if period.HasField("start") else None),
                        "end": to_utc_dt(period.end if period.HasField("end") else None),
                    }
                )

            payload = {
                "entity_id": entity.id,
                "cause": _safe_enum_name(
                    gtfs_realtime_pb2.Alert.Cause,
                    alert.cause if alert.HasField("cause") else None,
                ),
                "effect": _safe_enum_name(
                    gtfs_realtime_pb2.Alert.Effect,
                    alert.effect if alert.HasField("effect") else None,
                ),
                "severity_level": _safe_enum_name(
                    gtfs_realtime_pb2.Alert.SeverityLevel,
                    alert.severity_level if alert.HasField("severity_level") else None,
                ),
                "header_text": alert.header_text.translation[0].text if alert.header_text.translation else None,
                "description_text": (
                    alert.description_text.translation[0].text if alert.description_text.translation else None
                ),
                "active_periods": active_periods,
            }
            self.redis_store.publish_entity(
                entity_id=entity.id,
                feed_type="alerts",
                payload=payload,
                feed_timestamp=feed_timestamp,
            )
            published += 1

        logger.info("Published %s alert entities to Redis", published)
