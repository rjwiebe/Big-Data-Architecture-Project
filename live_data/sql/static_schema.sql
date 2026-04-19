CREATE TABLE IF NOT EXISTS routes (
    route_id TEXT PRIMARY KEY,
    feed_source TEXT NOT NULL,
    route_short_name TEXT,
    route_long_name TEXT,
    route_type INTEGER,
    route_color TEXT,
    route_text_color TEXT
);

CREATE TABLE IF NOT EXISTS stops (
    stop_id TEXT PRIMARY KEY,
    feed_source TEXT NOT NULL,
    stop_name TEXT NOT NULL,
    stop_lat DOUBLE PRECISION NOT NULL,
    stop_lon DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS trips (
    trip_id TEXT PRIMARY KEY,
    feed_source TEXT NOT NULL,
    route_id TEXT NOT NULL REFERENCES routes(route_id) ON DELETE CASCADE,
    service_id TEXT,
    trip_headsign TEXT,
    direction_id INTEGER,
    shape_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_trips_route_id
    ON trips (route_id);

CREATE INDEX IF NOT EXISTS idx_trips_shape_id
    ON trips (shape_id);

CREATE TABLE IF NOT EXISTS stop_times (
    trip_id TEXT NOT NULL REFERENCES trips(trip_id) ON DELETE CASCADE,
    feed_source TEXT NOT NULL,
    arrival_time TEXT,
    departure_time TEXT,
    arrival_seconds INTEGER,
    departure_seconds INTEGER,
    stop_id TEXT NOT NULL REFERENCES stops(stop_id) ON DELETE CASCADE,
    stop_sequence INTEGER NOT NULL,
    PRIMARY KEY (trip_id, stop_sequence)
);

CREATE INDEX IF NOT EXISTS idx_stop_times_stop_id_arrival
    ON stop_times (stop_id, arrival_seconds);

CREATE INDEX IF NOT EXISTS idx_stop_times_trip_id
    ON stop_times (trip_id);

CREATE TABLE IF NOT EXISTS shapes (
    shape_id TEXT NOT NULL,
    feed_source TEXT NOT NULL,
    shape_pt_lat DOUBLE PRECISION NOT NULL,
    shape_pt_lon DOUBLE PRECISION NOT NULL,
    shape_pt_sequence INTEGER NOT NULL,
    PRIMARY KEY (shape_id, shape_pt_sequence)
);

CREATE INDEX IF NOT EXISTS idx_shapes_shape_id
    ON shapes (shape_id);
