"""SQLite database manager and data access layer for LumiSense.
Thread-safe, uses WAL mode for concurrent reading & writing.
"""
import sqlite3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(settings.DATABASE_PATH), timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def init_db():
    """Initializes tables and indexes."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. sensor_readings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sensor_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        light_raw INTEGER NOT NULL,
        light_smoothed REAL NOT NULL,
        motion INTEGER NOT NULL,
        temperature REAL,
        humidity REAL,
        predicted_demand REAL,
        anomaly_score REAL,
        is_anomaly INTEGER DEFAULT 0,
        source TEXT DEFAULT 'real'
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON sensor_readings(timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_source ON sensor_readings(source);")
    
    # 2. anomalies table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS anomalies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        reading_id INTEGER,
        light_raw INTEGER NOT NULL,
        motion INTEGER NOT NULL,
        anomaly_score REAL NOT NULL,
        description TEXT NOT NULL,
        severity TEXT DEFAULT 'WARNING',
        FOREIGN KEY(reading_id) REFERENCES sensor_readings(id)
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_timestamp ON anomalies(timestamp);")
    
    # 3. recommendations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        rule_code TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        severity TEXT DEFAULT 'INFO',
        suggested_action TEXT,
        acknowledged INTEGER DEFAULT 0
    );
    """)
    
    # 4. ml_models metadata table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ml_models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_name TEXT NOT NULL,
        model_type TEXT NOT NULL,
        trained_at TEXT NOT NULL,
        num_samples INTEGER NOT NULL,
        mae REAL,
        rmse REAL,
        r2 REAL,
        is_active INTEGER DEFAULT 1,
        metadata_json TEXT
    );
    """)
    
    # 5. system_events table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        message TEXT NOT NULL,
        level TEXT DEFAULT 'INFO'
    );
    """)
    
    conn.commit()
    conn.close()

def insert_reading(
    light_raw: int,
    light_smoothed: float,
    motion: int,
    temperature: Optional[float] = None,
    humidity: Optional[float] = None,
    predicted_demand: Optional[float] = None,
    anomaly_score: Optional[float] = None,
    is_anomaly: bool = False,
    source: str = "real",
    timestamp_override: Optional[datetime] = None
) -> int:
    ts_str = (timestamp_override or datetime.now(timezone.utc)).isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sensor_readings 
        (timestamp, light_raw, light_smoothed, motion, temperature, humidity, predicted_demand, anomaly_score, is_anomaly, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ts_str, light_raw, light_smoothed, motion,
        temperature, humidity, predicted_demand, anomaly_score,
        1 if is_anomaly else 0, source
    ))
    reading_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reading_id

def get_latest_reading(source: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if source is None:
        cursor.execute("SELECT * FROM sensor_readings ORDER BY id DESC LIMIT 1")
    else:
        cursor.execute(
            "SELECT * FROM sensor_readings WHERE source = ? ORDER BY id DESC LIMIT 1",
            (source,)
        )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_readings_history(
    limit: int = 100,
    hours: Optional[float] = None,
    source: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    source_clause = " AND source = ?" if source is not None else ""
    source_params = (source,) if source is not None else ()
    if hours is not None:
        since_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        cursor.execute(
            f"SELECT * FROM sensor_readings WHERE timestamp >= ?{source_clause} "
            "ORDER BY timestamp ASC LIMIT ?",
            (since_time, *source_params, limit)
        )
    else:
        cursor.execute(
            f"SELECT * FROM (SELECT * FROM sensor_readings WHERE 1 = 1{source_clause} "
            "ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
            (*source_params, limit)
        )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_total_readings_count() -> Tuple[int, int, int]:
    """Returns (total, real_count, simulated_count)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sensor_readings")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM sensor_readings WHERE source = 'real'")
    real_cnt = cursor.fetchone()[0]
    conn.close()
    sim_cnt = total - real_cnt
    return total, real_cnt, sim_cnt

def insert_anomaly(reading_id: Optional[int], light_raw: int, motion: int, anomaly_score: float, description: str, severity: str = "WARNING"):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO anomalies (timestamp, reading_id, light_raw, motion, anomaly_score, description, severity)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (now_str, reading_id, light_raw, motion, anomaly_score, description, severity))
    conn.commit()
    conn.close()

def get_anomalies(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM anomalies ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def insert_recommendation(rule_code: str, title: str, message: str, suggested_action: str, severity: str = "INFO"):
    conn = get_connection()
    cursor = conn.cursor()
    # Check if identical recommendation added in last 5 minutes to prevent spam
    five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    cursor.execute("SELECT id FROM recommendations WHERE rule_code = ? AND timestamp >= ?", (rule_code, five_min_ago))
    if cursor.fetchone() is None:
        now_str = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO recommendations (timestamp, rule_code, title, message, severity, suggested_action)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (now_str, rule_code, title, message, severity, suggested_action))
        conn.commit()
    conn.close()

def get_recommendations(limit: int = 30) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recommendations ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def log_system_event(event_type: str, message: str, level: str = "INFO"):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("INSERT INTO system_events (timestamp, event_type, message, level) VALUES (?, ?, ?, ?)",
                   (now_str, event_type, message, level))
    conn.commit()
    conn.close()

def save_model_record(model_name: str, model_type: str, num_samples: int, mae: float, rmse: float, r2: float, metadata: dict):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO ml_models (model_name, model_type, trained_at, num_samples, mae, rmse, r2, is_active, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (model_name, model_type, now_str, num_samples, mae, rmse, r2, json.dumps(metadata)))
    conn.commit()
    conn.close()

def get_latest_model_record(model_type: str = "demand_regressor") -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ml_models WHERE model_type = ? ORDER BY id DESC LIMIT 1", (model_type,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        if d.get("metadata_json"):
            d["metadata"] = json.loads(d["metadata_json"])
        return d
    return None
