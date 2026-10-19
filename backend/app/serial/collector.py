"""Background Serial Port Collector for Arduino Uno USB communication.
Features:
- Auto-discovery of Arduino COM ports on Windows / Linux / macOS
- Auto-reconnect loop with graceful error handling
- Zero-crash architecture: if Arduino unplugged, continues retrying seamlessly
- Thread-safe state tracking
"""
import time
import serial
import serial.tools.list_ports
import threading
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from app.config import settings
from app.serial.parser import SerialDataParser
from app.services.validator import SensorDataValidator
from app.services.filter import signal_filter
from app.database import (
    insert_reading, insert_anomaly,
    log_system_event, get_readings_history
)
from app.ml.pipeline import ml_pipeline
from app.services.recommendation import RecommendationEngine

logger = logging.getLogger(__name__)

class SerialCollector:
    def __init__(self):
        self.port: Optional[str] = settings.SERIAL_PORT
        self.active_port: Optional[str] = None
        self.baud_rate: int = settings.SERIAL_BAUD_RATE
        self.is_connected: bool = False
        self.is_running: bool = False
        self.serial_instance: Optional[serial.Serial] = None
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.last_reading_time: Optional[datetime] = None
        self.last_raw_payload: Optional[str] = None
        self.status_message: str = "Initialized"

    def list_available_ports(self) -> List[Dict[str, Any]]:
        """Returns detected serial ports with Arduino candidate heuristics."""
        ports = serial.tools.list_ports.comports()
        result = []
        for p in ports:
            desc = p.description or ""
            hwid = p.hwid or ""
            is_arduino = any(k in (desc + hwid).lower() for k in ["arduino", "ch340", "cp210", "ftdi", "usb serial"])
            result.append({
                "device": p.device,
                "description": desc,
                "hwid": hwid,
                "is_arduino_candidate": is_arduino
            })
        return result

    def auto_detect_arduino_port(self) -> Optional[str]:
        """Tries to find Arduino among available COM ports."""
        ports = self.list_available_ports()
        for p in ports:
            if p["is_arduino_candidate"]:
                return p["device"]
        if ports:
            return ports[0]["device"] # Fallback to first available port
        return None

    def start(self):
        with self._lock:
            if self.is_running:
                return
            self.is_running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            logger.info("Serial Collector thread started.")

    def stop(self):
        with self._lock:
            self.is_running = False
            if self.serial_instance and self.serial_instance.is_open:
                try:
                    self.serial_instance.close()
                except Exception:
                    pass
            self.is_connected = False
            self.active_port = None
            self.status_message = "Stopped"

    def configure(self, port: Optional[str] = None, baud_rate: Optional[int] = None):
        """Reconfigures port or baud rate on the fly."""
        with self._lock:
            if port is not None:
                self.port = port
            if baud_rate is not None:
                self.baud_rate = baud_rate
            # Close existing connection to trigger reconnect with new settings
            if self.serial_instance and self.serial_instance.is_open:
                try:
                    self.serial_instance.close()
                except Exception:
                    pass
                self.serial_instance = None
                self.is_connected = False
                self.active_port = None

    def _run_loop(self):
        """Worker loop that attempts connections and reads frames."""
        while self.is_running:
            target_port = self.port or self.auto_detect_arduino_port()
            if not target_port:
                self.is_connected = False
                self.status_message = "No serial/COM ports detected. Waiting..."
                time.sleep(settings.SERIAL_RETRY_INTERVAL)
                continue

            try:
                self.status_message = f"Connecting to {target_port} at {self.baud_rate} baud..."
                logger.info(self.status_message)
                ser = serial.Serial(target_port, self.baud_rate, timeout=settings.SERIAL_TIMEOUT)
                self.serial_instance = ser
                self.is_connected = True
                self.active_port = target_port
                self.last_reading_time = None
                self.status_message = f"Connected to {target_port} ({self.baud_rate} baud)"
                log_system_event("ARDUINO_CONNECTED", f"Serial connection established on {target_port}", "INFO")

                from app.services.simulation_worker import simulation_worker
                simulation_worker.stop()

                # Flush bootloader garbage
                time.sleep(1.5)
                ser.reset_input_buffer()

                while self.is_running and ser.is_open:
                    if ser.in_waiting > 0:
                        raw_bytes = ser.readline()
                        try:
                            line = raw_bytes.decode("utf-8", errors="replace").strip()
                        except Exception:
                            continue

                        if not line:
                            continue

                        self.last_raw_payload = line
                        self._process_incoming_line(line)
                    else:
                        time.sleep(0.05)

            except (serial.SerialException, OSError) as e:
                self.is_connected = False
                self.active_port = None
                self.status_message = f"Disconnected: {e}. Retrying in {settings.SERIAL_RETRY_INTERVAL}s..."
                logger.warning(self.status_message)
                log_system_event("ARDUINO_DISCONNECTED", f"Serial disconnected on {target_port}: {e}", "WARNING")
                if self.serial_instance:
                    try:
                        self.serial_instance.close()
                    except Exception:
                        pass
                    self.serial_instance = None
                time.sleep(settings.SERIAL_RETRY_INTERVAL)
            except Exception as e:
                self.is_connected = False
                self.active_port = None
                self.status_message = f"Serial collector error: {e}"
                logger.error(f"Unexpected serial loop error: {e}")
                time.sleep(settings.SERIAL_RETRY_INTERVAL)

    def _process_incoming_line(self, line: str):
        """Parses, validates, filters, evaluates ML, and persists incoming sensor line."""
        parsed = SerialDataParser.parse_line(line)
        if not parsed:
            return

        is_valid, validated, error_msg = SensorDataValidator.validate_reading(parsed)
        if not is_valid:
            logger.warning(f"Invalid sensor frame rejected: {error_msg}")
            log_system_event("DATA_VALIDATION_ERROR", f"Rejected frame '{line}': {error_msg}", "WARNING")
            return

        raw_light = validated["light_raw"]
        motion = validated["motion"]
        temp = validated.get("temperature")
        hum = validated.get("humidity")

        # Smooth signal
        light_smoothed = signal_filter.smooth(raw_light)

        # Context for ML
        recent_history = get_readings_history(limit=10)
        reading_dict = {
            "light_raw": raw_light,
            "light_smoothed": light_smoothed,
            "motion": motion,
            "temperature": temp,
            "humidity": hum
        }

        # ML inference
        pred_demand = ml_pipeline.predict_demand(reading_dict, recent_history)
        is_anomaly, anomaly_score, anomaly_desc = ml_pipeline.detect_anomaly(reading_dict, recent_history)

        # Insert reading
        reading_id = insert_reading(
            light_raw=raw_light,
            light_smoothed=light_smoothed,
            motion=motion,
            temperature=temp,
            humidity=hum,
            predicted_demand=pred_demand,
            anomaly_score=anomaly_score,
            is_anomaly=is_anomaly,
            source="real"
        )

        if is_anomaly:
            insert_anomaly(
                reading_id=reading_id,
                light_raw=raw_light,
                motion=motion,
                anomaly_score=anomaly_score,
                description=anomaly_desc or "Unusual usage pattern detected.",
                severity="WARNING"
            )

        # Heuristic recommendations
        RecommendationEngine.evaluate_readings(reading_dict, recent_history)

        self.last_reading_time = datetime.now(timezone.utc)

# Global serial collector instance
serial_collector = SerialCollector()
