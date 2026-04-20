import unittest

from fastapi.testclient import TestClient

from api.config import Settings
from api.main import create_app
from api.redis_client import RedisClient


# ---------------------------------------------------------------------------
# Fake dependencies — no real DB or Redis needed
# ---------------------------------------------------------------------------

class FakeDB:
    """
    Intercepts db.fetch() calls and returns canned GTFS-like rows.
    Route-search queries are identified by the presence of 'boarding_stop_id'
    (a column alias unique to that query). Everything else falls through to
    the nearest-stations path used by the existing contract tests.
    """

    async def fetch(self, query: str, *args):
        if "boarding_stop_id" in query:
            # Route search query — args: orig_lat, orig_lon, dest_lat, dest_lon, limit
            limit = args[4]
            rows = [
                {
                    "route_id": "route-A",
                    "route_short_name": "A",
                    "route_long_name": "A Line - University of Colorado A Line",
                    "route_type": 2,
                    "boarding_stop_id": "stop-union",
                    "boarding_stop_name": "Union Station",
                    "origin_distance_meters": 95.0,
                    "alighting_stop_id": "stop-airport",
                    "alighting_stop_name": "Denver Airport Station",
                    "dest_distance_meters": 210.0,
                },
                {
                    "route_id": "route-15",
                    "route_short_name": "15",
                    "route_long_name": "East Colfax",
                    "route_type": 3,
                    "boarding_stop_id": "stop-colfax-w",
                    "boarding_stop_name": "Colfax & Broadway",
                    "origin_distance_meters": 340.0,
                    "alighting_stop_id": "stop-colfax-e",
                    "alighting_stop_name": "Colfax & Yosemite",
                    "dest_distance_meters": 180.0,
                },
            ]
            return rows[:limit]

        if "FROM stops" in query:
            # Nearest-stations query — keep compatible with existing FakeDB
            limit = args[2]
            return [
                {
                    "stop_id": "stop-union",
                    "stop_name": "Union Station",
                    "latitude": 39.7527,
                    "longitude": -105.0001,
                    "distance_meters": 95.0,
                },
            ][:limit]

        return []

    async def fetchrow(self, query: str, *args):
        return None


class FakeRedis:
    async def get_realtime_updates(self, entity_id: str):
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_client():
    app = create_app(
        settings=Settings(
            postgres_dsn="postgresql://user:password@localhost:5432/test",
            redis_url=None,
            allowed_origins=[],
            port=8080,
            redis_ttl=900,
        ),
        connect_external_services=False,
    )
    app.state.db = FakeDB()
    app.state.redis = FakeRedis()
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class RouteSearchContractTests(unittest.TestCase):

    def test_returns_200_with_valid_coordinates(self):
        """Endpoint accepts four coordinates and returns HTTP 200."""
        with make_client() as client:
            response = client.get(
                "/api/route-search"
                "?orig_lat=39.7527&orig_lon=-105.0001"
                "&dest_lat=39.8561&dest_lon=-104.6737"
            )
        self.assertEqual(response.status_code, 200)

    def test_response_is_a_list(self):
        """Response body is a JSON array."""
        with make_client() as client:
            response = client.get(
                "/api/route-search"
                "?orig_lat=39.7527&orig_lon=-105.0001"
                "&dest_lat=39.8561&dest_lon=-104.6737"
            )
        self.assertIsInstance(response.json(), list)

    def test_result_contains_required_fields(self):
        """Each result has the fields the frontend depends on."""
        required_fields = {
            "route_id",
            "route_short_name",
            "route_long_name",
            "route_type",
            "boarding_stop_id",
            "boarding_stop_name",
            "origin_distance_meters",
            "alighting_stop_id",
            "alighting_stop_name",
            "dest_distance_meters",
        }
        with make_client() as client:
            response = client.get(
                "/api/route-search"
                "?orig_lat=39.7527&orig_lon=-105.0001"
                "&dest_lat=39.8561&dest_lon=-104.6737"
            )
        payload = response.json()
        self.assertTrue(len(payload) > 0, "Expected at least one result from fake DB")
        for field in required_fields:
            self.assertIn(field, payload[0], f"Missing field: {field}")

    def test_limit_parameter_is_respected(self):
        """The limit query param caps the number of results returned."""
        with make_client() as client:
            response = client.get(
                "/api/route-search"
                "?orig_lat=39.7527&orig_lon=-105.0001"
                "&dest_lat=39.8561&dest_lon=-104.6737"
                "&limit=1"
            )
        self.assertEqual(len(response.json()), 1)

    def test_distance_fields_are_numeric(self):
        """Walk distance values are floats, not strings."""
        with make_client() as client:
            response = client.get(
                "/api/route-search"
                "?orig_lat=39.7527&orig_lon=-105.0001"
                "&dest_lat=39.8561&dest_lon=-104.6737"
            )
        for result in response.json():
            self.assertIsInstance(result["origin_distance_meters"], float)
            self.assertIsInstance(result["dest_distance_meters"], float)

    def test_missing_origin_lat_returns_422(self):
        """FastAPI returns 422 Unprocessable Entity when a required param is missing."""
        with make_client() as client:
            response = client.get(
                "/api/route-search"
                "?orig_lon=-105.0001"
                "&dest_lat=39.8561&dest_lon=-104.6737"
            )
        self.assertEqual(response.status_code, 422)

    def test_missing_dest_coords_returns_422(self):
        """Both dest_lat and dest_lon are required."""
        with make_client() as client:
            response = client.get(
                "/api/route-search"
                "?orig_lat=39.7527&orig_lon=-105.0001"
                "&dest_lat=39.8561"
                # dest_lon omitted
            )
        self.assertEqual(response.status_code, 422)

    def test_first_result_matches_fake_data(self):
        """Spot-check that the fake DB rows round-trip correctly through the API."""
        with make_client() as client:
            response = client.get(
                "/api/route-search"
                "?orig_lat=39.7527&orig_lon=-105.0001"
                "&dest_lat=39.8561&dest_lon=-104.6737"
            )
        first = response.json()[0]
        self.assertEqual(first["route_id"], "route-A")
        self.assertEqual(first["route_short_name"], "A")
        self.assertEqual(first["boarding_stop_name"], "Union Station")
        self.assertEqual(first["alighting_stop_name"], "Denver Airport Station")
