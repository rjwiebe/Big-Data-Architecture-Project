BEGIN;

-- Keep newest row per (entity_id, feed_timestamp)
DELETE FROM vehicle_positions vp
USING (
    SELECT id
    FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY entity_id, feed_timestamp
                   ORDER BY id DESC
               ) AS rn
        FROM vehicle_positions
        WHERE entity_id IS NOT NULL AND feed_timestamp IS NOT NULL
    ) ranked
    WHERE rn > 1
) dup
WHERE vp.id = dup.id;

DELETE FROM trip_updates tu
USING (
    SELECT id
    FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY entity_id, feed_timestamp
                   ORDER BY id DESC
               ) AS rn
        FROM trip_updates
        WHERE entity_id IS NOT NULL AND feed_timestamp IS NOT NULL
    ) ranked
    WHERE rn > 1
) dup
WHERE tu.id = dup.id;

DELETE FROM alerts a
USING (
    SELECT id
    FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY entity_id, feed_timestamp
                   ORDER BY id DESC
               ) AS rn
        FROM alerts
        WHERE entity_id IS NOT NULL AND feed_timestamp IS NOT NULL
    ) ranked
    WHERE rn > 1
) dup
WHERE a.id = dup.id;

DELETE FROM stop_time_updates stu
USING (
    SELECT id
    FROM (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY trip_update_id, stop_sequence, stop_id
                   ORDER BY id DESC
               ) AS rn
        FROM stop_time_updates
        WHERE stop_sequence IS NOT NULL AND stop_id IS NOT NULL
    ) ranked
    WHERE rn > 1
) dup
WHERE stu.id = dup.id;

CREATE UNIQUE INDEX IF NOT EXISTS uq_vehicle_positions_entity_feed_ts
    ON vehicle_positions (entity_id, feed_timestamp);

CREATE UNIQUE INDEX IF NOT EXISTS uq_trip_updates_entity_feed_ts
    ON trip_updates (entity_id, feed_timestamp);

CREATE UNIQUE INDEX IF NOT EXISTS uq_alerts_entity_feed_ts
    ON alerts (entity_id, feed_timestamp);

CREATE UNIQUE INDEX IF NOT EXISTS uq_stop_time_updates_trip_stop
    ON stop_time_updates (trip_update_id, stop_sequence, stop_id);

COMMIT;
