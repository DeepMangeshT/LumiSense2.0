"""Sensors and Analytics API endpoints.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import numpy as np

from app.models.schemas import SensorReadingResponse
from app.database import get_latest_reading, get_readings_history, get_connection
from app.serial.collector import serial_collector

router = APIRouter()

def _active_source() -> str:
    return "real"

@router.get("/latest", response_model=Optional[SensorReadingResponse])
def get_latest_sensor_reading():
    if serial_collector.is_connected and serial_collector.last_reading_time is None:
        return None
    reading = get_latest_reading(source=_active_source())
    if not reading:
        return None
    return SensorReadingResponse(**reading)

@router.get("/history", response_model=List[SensorReadingResponse])
def get_sensor_history(
    limit: int = Query(60, ge=1, le=1000, description="Max readings to return"),
    hours: Optional[float] = Query(None, ge=0.1, le=168.0, description="History window in hours")
):
    rows = get_readings_history(limit=limit, hours=hours, source=_active_source())
    return [SensorReadingResponse(**r) for r in rows]

@router.get("/analytics")
def get_sensor_analytics(
    timeframe: str = Query("24h", description="'1h', '24h', '7d', 'all'")
):
    """Calculates statistics, diurnal aggregations, and trends."""
    hours_map = {"1h": 1.0, "24h": 24.0, "7d": 168.0, "all": None}
    hours = hours_map.get(timeframe, 24.0)

    rows = get_readings_history(limit=1000, hours=hours, source=_active_source())
    if not rows:
        return {
            "timeframe": timeframe,
            "count": 0,
            "light_stats": {"avg": 0, "min": 0, "max": 0},
            "motion_stats": {"active_percentage": 0, "active_count": 0},
            "temperature_stats": {"avg": None, "sensor_connected": False},
            "hourly_trend": []
        }

    lights = [r["light_smoothed"] for r in rows]
    motions = [r["motion"] for r in rows]
    temps = [r["temperature"] for r in rows if r.get("temperature") is not None]

    # Hourly grouping for trend graphs
    hourly_buckets: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        ts = r["timestamp"]
        try:
            dt = datetime.fromisoformat(ts)
            key = dt.strftime("%Y-%m-%d %H:00")
            if key not in hourly_buckets:
                hourly_buckets[key] = {"lights": [], "motions": [], "demands": []}
            hourly_buckets[key]["lights"].append(r["light_smoothed"])
            hourly_buckets[key]["motions"].append(r["motion"])
            if r.get("predicted_demand") is not None:
                hourly_buckets[key]["demands"].append(r["predicted_demand"])
        except Exception:
            continue

    hourly_trend = []
    for hour_str, data in sorted(hourly_buckets.items()):
        hourly_trend.append({
            "hour": hour_str.split(" ")[-1],
            "datetime": hour_str,
            "avg_light": round(float(np.mean(data["lights"])), 1) if data["lights"] else 0,
            "motion_rate": round(float(np.mean(data["motions"])) * 100, 1) if data["motions"] else 0,
            "avg_demand": round(float(np.mean(data["demands"])), 1) if data["demands"] else None
        })

    return {
        "timeframe": timeframe,
        "count": len(rows),
        "light_stats": {
            "avg": round(float(np.mean(lights)), 1),
            "min": int(np.min(lights)),
            "max": int(np.max(lights)),
            "std": round(float(np.std(lights)), 1)
        },
        "motion_stats": {
            "active_percentage": round(float(np.mean(motions)) * 100, 1),
            "active_count": int(sum(motions)),
            "inactive_count": len(motions) - int(sum(motions))
        },
        "temperature_stats": {
            "avg": round(float(np.mean(temps)), 1) if temps else None,
            "sensor_connected": len(temps) > 0
        },
        "hourly_trend": hourly_trend
    }
