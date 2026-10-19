"""System and Hardware status API endpoints.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import time

from app.models.schemas import SystemStatusResponse, SettingsUpdateRequest, PortOption
from app.config import settings
from app.serial.collector import serial_collector
from app.services.simulation_worker import simulation_worker
from app.database import get_total_readings_count, get_latest_reading
from app.services.filter import signal_filter
from app.ml.pipeline import ml_pipeline

router = APIRouter()
START_TIME = time.time()

@router.get("/health")
def get_health():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/status", response_model=SystemStatusResponse)
def get_system_status():
    latest = get_latest_reading(source="real")
    last_time = serial_collector.last_reading_time if serial_collector.is_connected else None
    seconds_ago = None
    if not serial_collector.is_connected and latest and latest.get("timestamp"):
        try:
            last_time = datetime.fromisoformat(latest["timestamp"])
        except Exception:
            last_time = None
    if last_time:
        now_utc = datetime.now(timezone.utc)
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
        seconds_ago = round((now_utc - last_time).total_seconds(), 1)

    _, real_cnt, _ = get_total_readings_count()
    active_model = "Random Forest Regressor (Demand)" if ml_pipeline.demand_model else None

    return SystemStatusResponse(
        arduino_connected=serial_collector.is_connected,
        serial_port=serial_collector.active_port or serial_collector.port or "Auto-detecting",
        baud_rate=serial_collector.baud_rate,
        last_reading_time=last_time,
        seconds_since_last_reading=seconds_ago,
        database_connected=True,
        database_records_count=real_cnt,
        simulation_mode=simulation_worker.is_running,
        ml_model_ready=ml_pipeline.demand_model is not None,
        active_model_name=active_model,
        smoothing_window=signal_filter.window_size,
        uptime_seconds=round(time.time() - START_TIME, 1)
    )

@router.get("/serial/ports")
def get_available_serial_ports():
    """Lists detected host serial / COM ports with Arduino candidates flagged."""
    return {
        "ports": serial_collector.list_available_ports(),
        "current_configured_port": serial_collector.port,
        "active_port": serial_collector.active_port,
        "is_connected": serial_collector.is_connected,
        "status_message": serial_collector.status_message
    }

@router.post("/settings")
def update_settings(payload: SettingsUpdateRequest):
    """Updates runtime configuration: COM port, baud rate, smoothing window, simulation."""
    if payload.serial_port is not None:
        serial_collector.configure(port=payload.serial_port if payload.serial_port != "AUTO" else None)
    if payload.baud_rate is not None:
        serial_collector.configure(baud_rate=payload.baud_rate)
    if payload.smoothing_window is not None:
        signal_filter.set_window_size(payload.smoothing_window)
    if payload.simulation_mode is not None:
        if payload.simulation_mode:
            if serial_collector.is_connected:
                raise HTTPException(
                    status_code=409,
                    detail="Simulation cannot start while the Arduino is connected; live sensor data has priority."
                )
            simulation_worker.start()
        else:
            simulation_worker.stop()

    return {
        "success": True,
        "message": "Settings updated successfully",
        "current": {
            "serial_port": serial_collector.port,
            "baud_rate": serial_collector.baud_rate,
            "smoothing_window": signal_filter.window_size,
            "simulation_mode": simulation_worker.is_running
        }
    }
