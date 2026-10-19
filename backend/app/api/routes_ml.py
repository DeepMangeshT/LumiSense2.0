"""Machine Learning and Anomaly Detection API endpoints.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone

from app.models.schemas import (
    MLStatusResponse, MLTrainingRequest, MLTrainingResponse,
    AnomalyRecord
)
from app.ml.pipeline import ml_pipeline
from app.database import get_anomalies, get_latest_reading
from app.services.simulation import sensor_simulator
from app.serial.collector import serial_collector

router = APIRouter()

@router.get("/status", response_model=MLStatusResponse)
def get_ml_status():
    """Returns data readiness status and trained model statistics."""
    info = ml_pipeline.check_readiness()
    return MLStatusResponse(**info)

@router.post("/train", response_model=MLTrainingResponse)
def train_ml_models(payload: MLTrainingRequest):
    """Triggers ML model training using stored sensor readings."""
    result = ml_pipeline.train_models(include_simulated=payload.include_simulated_data)
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("message", "Model training failed"))
    return MLTrainingResponse(**result)

@router.get("/prediction")
def get_current_prediction():
    """Returns real-time predicted lighting demand for the current sensor state."""
    if serial_collector.is_connected and serial_collector.last_reading_time is None:
        return {"predicted_demand": 0.0, "status": "Waiting for the first live sensor reading"}
    latest = get_latest_reading(source="real")
    if not latest:
        return {"predicted_demand": 0.0, "status": "No sensor readings available"}
    
    pred = ml_pipeline.predict_demand(latest)
    return {
        "timestamp": latest["timestamp"],
        "light_raw": latest["light_raw"],
        "light_smoothed": latest["light_smoothed"],
        "motion": latest["motion"],
        "predicted_demand": pred,
        "demand_unit": "Estimated Lighting Demand (%)",
        "model_trained": ml_pipeline.demand_model is not None
    }

@router.get("/anomalies", response_model=List[AnomalyRecord])
def get_detected_anomalies(limit: int = Query(30, ge=1, le=100)):
    """Returns list of detected unusual patterns (unoccupied high light, spikes, etc.)."""
    records = get_anomalies(limit=limit)
    return [AnomalyRecord(**r) for r in records]

@router.post("/anomalies/trigger")
def trigger_demo_anomaly(anomaly_type: str = Query("high_light_unoccupied", description="'high_light_unoccupied' or 'light_spike'")):
    """Injects a temporary anomaly in simulation mode for evaluation and testing."""
    sensor_simulator.trigger_anomaly(anomaly_type=anomaly_type, duration_steps=12)
    return {
        "success": True,
        "message": f"Injected simulated anomaly '{anomaly_type}' for 12 cycles. Watch Dashboard and Anomalies tabs!"
    }
