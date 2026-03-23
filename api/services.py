from .db import DBConnection
from .redis_client import RedisClient

async def get_nearest_stations_with_realtime(
    db: DBConnection,
    redis_client: RedisClient,
    lat: float,
    lon: float,
    limit: int = 10,
) -> list[dict]:
    # Standard Haversine formula SQL query to find the nearest GTFS stops.
    # Assumes a standard 'stops' table exists in the PostgreSQL database.
    query = """
    SELECT 
        stop_id, 
        stop_name, 
        stop_lat AS latitude, 
        stop_lon AS longitude,
        ( 6371000 * acos( 
            cos( radians($1) ) * cos( radians( stop_lat ) ) * 
            cos( radians( stop_lon ) - radians($2) ) + 
            sin( radians($1) ) * sin( radians( stop_lat ) ) 
        ) ) AS distance_meters
    FROM stops
    ORDER BY distance_meters ASC
    LIMIT $3;
    """
    
    rows = await db.fetch(query, lat, lon, limit)

    stations = []
    for row in rows:
        stop_id = row['stop_id']
        # Fetch real-time arrivals from Redis (placeholder integration)
        realtime_data = await redis_client.get_realtime_updates(stop_id)
        
        stations.append({
            "stop_id": stop_id,
            "stop_name": row['stop_name'],
            "latitude": row['latitude'],
            "longitude": row['longitude'],
            "distance_meters": round(row['distance_meters'], 2),
            "next_arrivals": realtime_data
        })
        
    return stations

async def get_nearest_lines(db: DBConnection, lat: float, lon: float, limit: int = 10) -> list[dict]:
    # Joins stops -> stop_times -> trips -> routes to find distinct lines near the user
    query = """
    WITH nearest_stops AS (
        SELECT stop_id, stop_name,
            ( 6371000 * acos( 
                cos( radians($1) ) * cos( radians( stop_lat ) ) * 
                cos( radians( stop_lon ) - radians($2) ) + 
                sin( radians($1) ) * sin( radians( stop_lat ) ) 
            ) ) AS distance_meters
        FROM stops
        ORDER BY distance_meters ASC
        LIMIT 50
    )
    SELECT DISTINCT ON (r.route_id)
        r.route_id, r.route_short_name, r.route_long_name, r.route_type,
        ns.stop_id AS nearest_stop_id, ns.stop_name AS nearest_stop_name, ns.distance_meters
    FROM nearest_stops ns
    JOIN stop_times st ON ns.stop_id = st.stop_id
    JOIN trips t ON st.trip_id = t.trip_id
    JOIN routes r ON t.route_id = r.route_id
    ORDER BY r.route_id, ns.distance_meters ASC
    LIMIT $3;
    """
    rows = await db.fetch(query, lat, lon, limit)
    
    # Re-sort the final result by distance
    lines = [dict(r) for r in rows]
    lines.sort(key=lambda x: x['distance_meters'])
    
    return [{
        "route_id": row['route_id'],
        "route_short_name": row['route_short_name'],
        "route_long_name": row['route_long_name'],
        "route_type": row['route_type'],
        "nearest_stop_id": row['nearest_stop_id'],
        "nearest_stop_name": row['nearest_stop_name'],
        "distance_meters": round(row['distance_meters'], 2)
    } for row in lines]

async def get_stop_schedule_with_realtime(
    db: DBConnection,
    redis_client: RedisClient,
    stop_id: str,
) -> list[dict]:
    # Standard query to fetch upcoming scheduled trips for a specific stop
    # In a full production scenario, this must filter by current service_id/date and current time.
    # For now, limiting to the next available scheduled trips for brevity.
    query = """
    SELECT 
        st.trip_id, st.arrival_time, st.departure_time, st.stop_sequence,
        t.route_id, t.trip_headsign,
        r.route_short_name, r.route_long_name, r.route_type
    FROM stop_times st
    JOIN trips t ON st.trip_id = t.trip_id
    JOIN routes r ON t.route_id = r.route_id
    WHERE st.stop_id = $1
    ORDER BY st.arrival_time
    LIMIT 20;
    """
    rows = await db.fetch(query, stop_id)

    # Fetch real-time delay info for trips related to this stop
    # rtd_collector may store trip_updates by trip_id or stop_id
    # We pass trip_id to a stubbed fetch method to calculate updated_arrival
    
    schedule = []
    for row in rows:
        trip_id = row['trip_id']
        rt_updates = await redis_client.get_realtime_updates(trip_id)
        
        delay_seconds = 0
        if rt_updates and "delay_seconds" in rt_updates:
            delay_seconds = rt_updates["delay_seconds"]
            
        schedule.append({
            "route_id": row['route_id'],
            "route_short_name": row['route_short_name'],
            "route_long_name": row['route_long_name'],
            "trip_id": trip_id,
            "headsign": row['trip_headsign'],
            "scheduled_arrival": row['arrival_time'],
            "delay_seconds": delay_seconds,
            "realtime_status": "delayed" if delay_seconds > 60 else "on-time"
        })
    return schedule

async def get_route_details(db: DBConnection, route_id: str) -> dict | None:
    # Get basic route info
    route_query = """
    SELECT route_id, route_short_name, route_long_name, route_type, route_color, route_text_color
    FROM routes
    WHERE route_id = $1;
    """
    route_row = await db.fetchrow(route_query, route_id)
    if not route_row:
        return None
        
    # Get arbitrary trip and its stops as a representative sequence
    stops_query = """
    WITH sample_trip AS (
        SELECT trip_id, shape_id FROM trips WHERE route_id = $1 LIMIT 1
    )
    SELECT s.stop_id, s.stop_name, s.stop_lat AS latitude, s.stop_lon AS longitude, st.stop_sequence
    FROM stop_times st
    JOIN stops s ON st.stop_id = s.stop_id
    JOIN sample_trip samp ON samp.trip_id = st.trip_id
    ORDER BY st.stop_sequence;
    """
    stops_rows = await db.fetch(stops_query, route_id)
    
    # Also fetch the shape path for mapping
    shapes_query = """
    SELECT shape_pt_lat AS latitude, shape_pt_lon AS longitude, shape_pt_sequence
    FROM shapes
    WHERE shape_id = (SELECT shape_id FROM trips WHERE route_id = $1 LIMIT 1)
    ORDER BY shape_pt_sequence;
    """
    shape_rows = await db.fetch(shapes_query, route_id)
    
    return {
        "route_info": dict(route_row),
        "stops": [dict(s) for s in stops_rows],
        "shape_points": [{"latitude": shp['latitude'], "longitude": shp['longitude']} for shp in shape_rows]
    }

async def get_route_vehicles_realtime(redis_client: RedisClient, route_id: str) -> list[dict]:
    # Stub: query Redis for ALL `vehicle_positions` currently active for a specific `route_id`.
    # rtd_collector parses the PB payload into DB & Redis.
    # From previous exploration, it creates Redis messages under "key_prefix:entity_id".
    
    # In a full deployment, if Redis is geo-indexed or hashes are tracked by route_id,
    # we would execute `SMEMBERS routes:<route_id>:vehicles` and get the hashes.
    vehicles = await redis_client.get_realtime_updates(route_id)
    
    return vehicles
