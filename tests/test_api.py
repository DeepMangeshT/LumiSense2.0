"""Integration tests for FastAPI endpoints.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, insert_reading, get_latest_reading, get_readings_history, get_total_readings_count
from app.config import settings
import app.api.routes_sensors as sensor_routes
from app.serial.collector import serial_collector
from app.services.simulation_worker import simulation_worker
from datetime import datetime, timezone, timedelta
import pytest

@pytest.fixture(autouse=True)
def isolate_database_for_api_tests(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "DATABASE_PATH", tmp_path / "lumisense-test.db")
    monkeypatch.setattr(serial_collector, "start", lambda: None)
    monkeypatch.setattr(serial_collector, "stop", lambda: None)
    monkeypatch.setattr(simulation_worker, "start", lambda: None)
    monkeypatch.setattr(simulation_worker, "stop", lambda: None)

def test_api_health_and_root():
    with TestClient(app) as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["service"] == "LumiSense"

        res_root = client.get("/")
        assert res_root.status_code == 200

    assert get_total_readings_count() == (0, 0, 0)

def test_api_system_status():
    with TestClient(app) as client:
        res = client.get("/api/status")
        assert res.status_code == 200
        data = res.json()
        assert "arduino_connected" in data
        assert "database_connected" in data
        assert data["database_connected"] is True
        assert "simulation_mode" in data

def test_api_sensors_latest_and_history():
    with TestClient(app) as client:
        res = client.get("/api/sensors/history?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        if len(data) > 0:
            item = data[0]
            assert "light_raw" in item
            assert "motion" in item
            assert "light_smoothed" in item

def test_api_efficiency_score():
    with TestClient(app) as client:
        res = client.get("/api/recommendations/score")
        assert res.status_code == 200
        data = res.json()
        assert 0 <= data["score"] <= 100
        assert "disclaimer" in data
        assert "certified" in data["disclaimer"] # Explains project-defined metric disclaimer

def test_api_ml_status():
    with TestClient(app) as client:
        res = client.get("/api/ml/status")
        assert res.status_code == 200
        data = res.json()
        assert "readiness_state" in data

def test_sensor_database_queries_can_filter_by_source(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "DATABASE_PATH", tmp_path / "sensor-test.db")
    init_db()
    insert_reading(100, 100.0, 0, source="simulated", timestamp_override=datetime.now(timezone.utc) - timedelta(seconds=2))
    insert_reading(250, 250.0, 1, source="real")

    assert get_latest_reading(source="real")["light_raw"] == 250
    assert [row["source"] for row in get_readings_history(limit=10, source="real")] == ["real"]

@pytest.mark.parametrize("connected", [True, False])
def test_sensor_endpoints_use_live_source_only(monkeypatch, connected):
    monkeypatch.setattr(sensor_routes.serial_collector, "is_connected", connected)
    monkeypatch.setattr(
        sensor_routes.serial_collector,
        "last_reading_time",
        datetime.now(timezone.utc) if connected else None
    )
    sources = []

    def capture_latest(source=None):
        sources.append(source)
        return None

    def capture_history(limit, hours=None, source=None):
        sources.append(source)
        return []

    monkeypatch.setattr(sensor_routes, "get_latest_reading", capture_latest)
    monkeypatch.setattr(sensor_routes, "get_readings_history", capture_history)

    assert sensor_routes.get_latest_sensor_reading() is None
    assert sensor_routes.get_sensor_history(limit=1) == []
    assert sources == ["real", "real"]

def test_latest_sensor_waits_for_first_frame_after_connect(monkeypatch):
    monkeypatch.setattr(sensor_routes.serial_collector, "is_connected", True)
    monkeypatch.setattr(sensor_routes.serial_collector, "last_reading_time", None)
    monkeypatch.setattr(
        sensor_routes,
        "get_latest_reading",
        lambda **kwargs: pytest.fail("A stale database reading must not be served")
    )

    assert sensor_routes.get_latest_sensor_reading() is None
