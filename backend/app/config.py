import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ML_MODELS_DIR = BASE_DIR / "ml" / "models"
ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)

class Settings:
    PROJECT_NAME: str = "LumiSense"
    PROJECT_SUBTITLE: str = "IoT-Based Smart Light and Energy Usage Monitoring System"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Database
    DATABASE_PATH: Path = DATA_DIR / "lumisense.db"
    DATABASE_URL: str = f"sqlite:///{DATABASE_PATH}"
    
    # Serial Port Settings
    _serial_port = os.getenv("LUMISENSE_SERIAL_PORT")
    SERIAL_PORT: Optional[str] = (
        None if not _serial_port or _serial_port.strip().upper() == "AUTO" else _serial_port.strip()
    )
    SERIAL_BAUD_RATE: int = int(os.getenv("LUMISENSE_BAUD_RATE", 9600))
    SERIAL_TIMEOUT: float = 1.0
    SERIAL_RETRY_INTERVAL: float = 3.0
    
    # Sensor Calibration & Validation
    LDR_MIN_RAW: int = 0
    LDR_MAX_RAW: int = 1023
    SMOOTHING_WINDOW_SIZE: int = int(os.getenv("LUMISENSE_SMOOTHING_WINDOW", 5))
    
    # Simulation Mode
    SIMULATION_INTERVAL_SEC: float = 1.5
    
    # ML Thresholds
    MIN_RECORDS_FOR_EXPERIMENTATION: int = 100
    MIN_RECORDS_FOR_TRAINING: int = 500
    DEMAND_MODEL_PATH: Path = ML_MODELS_DIR / "random_forest_demand.joblib"
    ANOMALY_MODEL_PATH: Path = ML_MODELS_DIR / "isolation_forest.joblib"

settings = Settings()
