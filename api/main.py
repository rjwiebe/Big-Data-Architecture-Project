import logging
from contextlib import asynccontextmanager
from datetime import time
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import Settings, get_settings, load_settings
from .db import get_db, DBConnection
from .redis_client import RedisClient
from .services import (
    get_nearest_stations_with_realtime,
    get_nearest_lines,
    get_stop_schedule_with_realtime,
    get_route_details,
    get_route_vehicles_realtime
)


logger = logging.getLogger(__name__)
router = APIRouter()


class ScheduleEntryResponse(BaseModel):
    route_id: str
    route_short_name: str | None = None
    route_long_name: str | None = None
    trip_id: str
    headsign: str | None = None
    scheduled_arrival: time | None = None
    delay_seconds: int = 0
    realtime_status: str


class RouteStopResponse(BaseModel):
    stop_id: str
    stop_name: str
    latitude: float
    longitude: float
    stop_sequence: int


class ShapePointResponse(BaseModel):
    latitude: float
    longitude: float


class RouteInfoResponse(BaseModel):
    route_id: str
    route_short_name: str | None = None
    route_long_name: str | None = None
    route_type: int | None = None
    route_color: str | None = None
    route_text_color: str | None = None


class RouteDetailsResponse(BaseModel):
    route_info: RouteInfoResponse
    stops: list[RouteStopResponse]
    shape_points: list[ShapePointResponse]


class StationResponse(BaseModel):
    stop_id: str
    stop_name: str
    latitude: float
    longitude: float
    distance_meters: float
    next_arrivals: list[dict[str, Any]] = Field(default_factory=list)


async def get_redis(request: Request) -> RedisClient:
    return request.app.state.redis

@router.get("/api/nearest-stations", response_model=list[StationResponse])
async def nearest_stations(
    lat: float = Query(..., description="Latitude of the user location"),
    lon: float = Query(..., description="Longitude of the user location"),
    limit: int = Query(10, description="Number of stations to return"),
    db: DBConnection = Depends(get_db),
    redis_client: RedisClient = Depends(get_redis),
):
    try:
        stations = await get_nearest_stations_with_realtime(db, redis_client, lat, lon, limit)
        return stations
    except Exception as e:
        logger.exception("Failed to load nearest stations")
        raise HTTPException(status_code=500, detail=str(e))

class LineResponse(BaseModel):
    route_id: str
    route_short_name: str
    route_long_name: str
    route_type: int
    nearest_stop_id: str
    nearest_stop_name: str
    distance_meters: float

@router.get("/api/nearest-lines", response_model=list[LineResponse])
async def nearest_lines(
    lat: float = Query(..., description="Latitude of the user location"),
    lon: float = Query(..., description="Longitude of the user location"),
    limit: int = Query(10, description="Number of lines to return"),
    db: DBConnection = Depends(get_db),
):
    try:
        lines = await get_nearest_lines(db, lat, lon, limit)
        return lines
    except Exception as e:
        logger.exception("Failed to load nearest lines")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/stops/{stop_id}/schedule", response_model=list[ScheduleEntryResponse])
async def stop_schedule(
    stop_id: str,
    db: DBConnection = Depends(get_db),
    redis_client: RedisClient = Depends(get_redis),
):
    try:
        # Returns static schedule combined with realtime
        schedule = await get_stop_schedule_with_realtime(db, redis_client, stop_id)
        return schedule
    except Exception as e:
        logger.exception("Failed to load schedule for stop %s", stop_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/routes/{route_id}", response_model=RouteDetailsResponse)
async def route_details(route_id: str, db: DBConnection = Depends(get_db)):
    try:
        details = await get_route_details(db, route_id)
        if not details:
            raise HTTPException(status_code=404, detail="Route not found")
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to load route details for %s", route_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/routes/{route_id}/vehicles")
async def route_vehicles(
    route_id: str,
    redis_client: RedisClient = Depends(get_redis),
):
    try:
        vehicles = await get_route_vehicles_realtime(redis_client, route_id)
        return vehicles
    except Exception as e:
        logger.exception("Failed to load route vehicles for %s", route_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "ok"}


def create_lifespan(
    settings: Settings | None = None,
    *,
    connect_external_services: bool = True,
):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved_settings = settings or get_settings()
        app.state.settings = resolved_settings

        if not hasattr(app.state, "db"):
            app.state.db = DBConnection(resolved_settings.postgres_dsn)
        if not hasattr(app.state, "redis"):
            app.state.redis = RedisClient(resolved_settings.redis_url)

        if connect_external_services:
            await app.state.db.connect()
            await app.state.redis.connect()

        try:
            yield
        finally:
            if connect_external_services:
                await app.state.redis.disconnect()
                await app.state.db.disconnect()

    return lifespan


def configure_cors(app: FastAPI, allowed_origins: list[str]) -> None:
    if not allowed_origins:
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )


def create_app(
    settings: Settings | None = None,
    *,
    connect_external_services: bool = True,
) -> FastAPI:
    startup_settings = settings or load_settings(require_postgres=False)

    app = FastAPI(
        title="RTD Denver Transit API",
        description="API for finding nearest transit stations and real-time updates.",
        version="1.0.0",
        lifespan=create_lifespan(settings, connect_external_services=connect_external_services),
    )
    configure_cors(app, startup_settings.allowed_origins)
    app.include_router(router)
    return app


app = create_app()
