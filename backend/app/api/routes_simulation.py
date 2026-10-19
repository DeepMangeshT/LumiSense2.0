"""Simulation Mode API endpoints.
"""
from fastapi import APIRouter, HTTPException
from app.services.simulation_worker import simulation_worker
from app.serial.collector import serial_collector

router = APIRouter()

@router.post("/start")
def start_simulation():
    if serial_collector.is_connected:
        raise HTTPException(
            status_code=409,
            detail="Simulation cannot start while the Arduino is connected; live sensor data has priority."
        )
    simulation_worker.start()
    return {
        "success": True,
        "is_running": simulation_worker.is_running,
        "message": "Sensor simulation started"
    }

@router.post("/stop")
def stop_simulation():
    simulation_worker.stop()
    return {
        "success": True,
        "is_running": simulation_worker.is_running,
        "message": "Sensor simulation stopped"
    }

@router.get("/status")
def get_simulation_status():
    return {
        "is_running": simulation_worker.is_running,
        "interval_seconds": simulation_worker.interval,
        "last_reading_time": simulation_worker.last_reading_time
    }
