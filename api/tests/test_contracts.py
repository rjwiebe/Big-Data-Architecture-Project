import unittest

from fastapi.testclient import TestClient

from api.config import Settings
from api.main import create_app
from api.redis_client import RedisClient


class FakeDB:
    async def fetch(self, query: str, *args):
        if "FROM stops" in query:
            limit = args[2]
            rows = [
                {
                    "stop_id": "stop-1",
                    "stop_name": "Union Station",
                    "latitude": 39.7527,
                    "longitude": -105.0001,
                    "distance_meters": 120.5,
                },
                {
                    "stop_id": "stop-2",
                    "stop_name": "Civic Center Station",
                    "latitude": 39.7395,
                    "longitude": -104.9849,
                    "distance_meters": 260.2,
                },
            ]
            return rows[:limit]
        return []

    async def fetchrow(self, query: str, *args):
        return None


class FakeRedis:
    async def get_realtime_updates(self, entity_id: str):
        if entity_id == "stop-1":
            return [
                {
                    "route_short_name": "A",
                    "headsign": "Denver Airport Station",
                    "minutes_until_arrival": 4,
                }
            ]
        return []


class ApiContractTests(unittest.TestCase):
    def make_client(self, redis_client):
        app = create_app(
            settings=Settings(
                postgres_dsn="postgresql://user:password@localhost:5432/test",
                redis_url=None,
                allowed_origins=[],
                port=8080,
            ),
            connect_external_services=False,
        )
        app.state.db = FakeDB()
        app.state.redis = redis_client
        return TestClient(app)

    def test_health_check_returns_ok(self):
        with self.make_client(RedisClient(None)) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_nearest_stations_contract_includes_expected_fields(self):
        with self.make_client(FakeRedis()) as client:
            response = client.get("/api/nearest-stations?lat=39.7392&lon=-104.9903&limit=2")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["stop_id"], "stop-1")
        self.assertEqual(payload[0]["next_arrivals"][0]["route_short_name"], "A")
        self.assertIn("distance_meters", payload[0])

    def test_nearest_stations_still_returns_valid_json_without_redis_url(self):
        with self.make_client(RedisClient(None)) as client:
            response = client.get("/api/nearest-stations?lat=39.7392&lon=-104.9903&limit=1")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["next_arrivals"], [])
