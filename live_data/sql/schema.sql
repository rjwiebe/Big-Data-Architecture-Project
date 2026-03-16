CREATE TABLE IF NOT EXISTS feed_ingestions (
    id BIGSERIAL PRIMARY KEY,
    feed_type TEXT NOT NULL,
    source_url TEXT NOT NULL,
    feed_timestamp TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload BYTEA NOT NULL,
    entity_count INTEGER NOT NULL,
    status_code INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feed_ingestions_feed_type_fetched_at
    ON feed_ingestions (feed_type, fetched_at DESC);

CREATE TABLE IF NOT EXISTS vehicle_positions (
    id BIGSERIAL PRIMARY KEY,
    ingestion_id BIGINT NOT NULL REFERENCES feed_ingestions(id) ON DELETE CASCADE,
    feed_timestamp TIMESTAMPTZ,
    entity_id TEXT,
    trip_id TEXT,
    route_id TEXT,
    vehicle_id TEXT,
    vehicle_label TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    bearing REAL,
    speed_mps REAL,
    occupancy_status TEXT,
    current_status TEXT,
    current_stop_sequence INTEGER,
    stop_id TEXT,
    vehicle_timestamp TIMESTAMPTZ,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vehicle_positions_trip_time
    ON vehicle_positions (trip_id, vehicle_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vehicle_positions_route_time
    ON vehicle_positions (route_id, vehicle_timestamp DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_vehicle_positions_entity_feed_ts
    ON vehicle_positions (entity_id, feed_timestamp);

CREATE TABLE IF NOT EXISTS trip_updates (
    id BIGSERIAL PRIMARY KEY,
    ingestion_id BIGINT NOT NULL REFERENCES feed_ingestions(id) ON DELETE CASCADE,
    feed_timestamp TIMESTAMPTZ,
    entity_id TEXT,
    trip_id TEXT,
    route_id TEXT,
    direction_id INTEGER,
    start_date TEXT,
    schedule_relationship TEXT,
    vehicle_id TEXT,
    vehicle_label TEXT,
    delay_seconds INTEGER,
    timestamp TIMESTAMPTZ,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trip_updates_trip_time
    ON trip_updates (trip_id, timestamp DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_trip_updates_entity_feed_ts
    ON trip_updates (entity_id, feed_timestamp);

CREATE TABLE IF NOT EXISTS stop_time_updates (
    id BIGSERIAL PRIMARY KEY,
    trip_update_id BIGINT NOT NULL REFERENCES trip_updates(id) ON DELETE CASCADE,
    stop_sequence INTEGER,
    stop_id TEXT,
    arrival_delay_seconds INTEGER,
    arrival_time TIMESTAMPTZ,
    departure_delay_seconds INTEGER,
    departure_time TIMESTAMPTZ,
    schedule_relationship TEXT,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stop_time_updates_stop_time
    ON stop_time_updates (stop_id, arrival_time DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_stop_time_updates_trip_stop
    ON stop_time_updates (trip_update_id, stop_sequence, stop_id);

CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    ingestion_id BIGINT NOT NULL REFERENCES feed_ingestions(id) ON DELETE CASCADE,
    feed_timestamp TIMESTAMPTZ,
    entity_id TEXT,
    active_period_start TIMESTAMPTZ,
    active_period_end TIMESTAMPTZ,
    cause TEXT,
    effect TEXT,
    severity_level TEXT,
    header_text TEXT,
    description_text TEXT,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_active_period
    ON alerts (active_period_start DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_alerts_entity_feed_ts
    ON alerts (entity_id, feed_timestamp);
