"""Background worker for Simulation Mode.
Periodically feeds realistic simulated environmental data through the identical validation,
filtering, ML prediction, anomaly detection, and database pipeline.
"""
import time
import threading
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.services.simulation import sensor_simulator
from app.services.validator import SensorDataValidator
from app.services.filter import signal_filter
from app.database import (
    insert_reading, insert_anomaly,
    get_readings_history, log_system_event
)
from app.ml.pipeline import ml_pipeline
from app.services.recommendation import RecommendationEngine

logger = logging.getLogger(__name__)

class SimulationWorker:
    def __init__(self):
        self.is_running: bool = False
        self.thread: Optional[threading.Thread] = None
        self.interval: float = settings.SIMULATION_INTERVAL_SEC
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self.last_reading_time: Optional[datetime] = None

    def start(self):
        with self._lock:
            if self.is_running:
                return
            self.is_running = True
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logger.info("Simulation Worker started.")
            log_system_event("SIMULATION_STARTED", "Sensor simulation mode activated", "INFO")

    def stop(self):
        with self._lock:
            if not self.is_running:
                return
            self.is_running = False
            self._stop_event.set()
            if self.thread and self.thread is not threading.current_thread():
                self.thread.join()
            self.thread = None
        logger.info("Simulation Worker stopped.")
        log_system_event("SIMULATION_STOPPED", "Sensor simulation mode deactivated", "INFO")

    def _run(self):
        while self.is_running:
            try:
                # 1. Generate realistic synthetic reading
                raw_data = sensor_simulator.generate_reading()

                # 2. Same validation layer
                is_valid, validated, error_msg = SensorDataValidator.validate_reading(raw_data)
                if not is_valid:
                    logger.error(f"Simulator produced invalid reading: {error_msg}")
                    continue

                raw_light = validated["light_raw"]
                motion = validated["motion"]
                temp = validated.get("temperature")
                hum = validated.get("humidity")

                # 3. Same smoothing filter
                light_smoothed = signal_filter.smooth(raw_light)

                # 4. Contextual history
                recent_history = get_readings_history(limit=10)
                reading_dict = {
                    "light_raw": raw_light,
                    "light_smoothed": light_smoothed,
                    "motion": motion,
                    "temperature": temp,
                    "humidity": hum
                }

                # 5. ML predictions
                pred_demand = ml_pipeline.predict_demand(reading_dict, recent_history)
                is_anomaly, anomaly_score, anomaly_desc = ml_pipeline.detect_anomaly(reading_dict, recent_history)

                # 6. Database persistence
                reading_id = insert_reading(
                    light_raw=raw_light,
                    light_smoothed=light_smoothed,
                    motion=motion,
                    temperature=temp,
                    humidity=hum,
                    predicted_demand=pred_demand,
                    anomaly_score=anomaly_score,
                    is_anomaly=is_anomaly,
                    source="simulated"
                )

                if is_anomaly:
                    insert_anomaly(
                        reading_id=reading_id,
                        light_raw=raw_light,
                        motion=motion,
                        anomaly_score=anomaly_score,
                        description=anomaly_desc or "Simulated unusual pattern detected.",
                        severity="WARNING"
                    )

                # 7. Recommendations
                RecommendationEngine.evaluate_readings(reading_dict, recent_history)

                self.last_reading_time = datetime.now(timezone.utc)

            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")

            self._stop_event.wait(self.interval)

# Global simulation worker instance
simulation_worker = SimulationWorker()
