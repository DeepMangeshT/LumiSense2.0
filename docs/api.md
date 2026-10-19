# LumiSense REST API Documentation

LumiSense provides a RESTful API built on **FastAPI**. Interactive Swagger UI documentation is available at `http://localhost:8000/docs`.

---

## Base URL

```text
http://localhost:8000/api
```

---

## 1. System & Health Endpoints

### `GET /api/health`
Returns service availability status.
* **Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "LumiSense",
  "timestamp": "2026-10-01T09:30:00Z"
}
```

### `GET /api/status`
Returns unified hardware connectivity, database counts, and background daemon statuses.
* `database_records_count` is the count of real hardware readings. Sample/demo readings are not inserted on application startup.
* **Response (200 OK):**
```json
{
  "arduino_connected": true,
  "serial_port": "COM3",
  "baud_rate": 9600,
  "last_reading_time": "2026-10-01T09:30:00Z",
  "seconds_since_last_reading": 0.8,
  "database_connected": true,
  "database_records_count": 684,
  "simulation_mode": false,
  "ml_model_ready": true,
  "active_model_name": "Random Forest Regressor (Demand)",
  "smoothing_window": 5,
  "uptime_seconds": 124.5
}
```

### `GET /api/serial/ports`
Lists all detected serial/COM ports on the host system with Arduino flags.

### `POST /api/settings`
Updates runtime parameters (COM port, baud rate, smoothing window, simulation toggle).

---

## 2. Telemetry & Sensor Endpoints

### `GET /api/sensors/latest`
Returns the most recent validated sensor frame.
* When the Arduino is connected, this endpoint returns only real sensor readings (or `null` until its first valid frame arrives); seeded and simulated rows are excluded.

### `GET /api/sensors/history?limit=60&hours=1`
Returns chronological sensor readings for graphing.
* When the Arduino is connected, only readings collected from hardware are returned.
* **Query Parameters:**
  * `limit` (int, default: 60, max: 1000): Maximum records returned.
  * `hours` (float, optional): Time window in hours.

### `GET /api/sensors/analytics?timeframe=24h`
Returns aggregated diurnal light curves, motion activity rates, and min/max/average statistics.
* **Supported timeframes:** `'1h'`, `'24h'`, `'7d'`, `'all'`.
* While the Arduino is connected, the aggregates are calculated from real hardware readings only.

---

## 3. Machine Learning Endpoints

### `GET /api/ml/status`
Returns current data readiness state (`INSUFFICIENT_DATA`, `EARLY_EXPERIMENTATION`, `READY`), dataset breakdown, and model evaluation metrics.

### `POST /api/ml/train`
Triggers model retraining on stored sensor readings.
* **Body:**
```json
{
  "include_simulated_data": true,
  "test_size": 0.2,
  "n_estimators": 80
}
```
* **Response (200 OK):**
```json
{
  "success": true,
  "message": "Models successfully trained and saved.",
  "num_samples_used": 600,
  "data_source_mix": "0 real / 600 simulated",
  "mae": 3.82,
  "rmse": 5.41,
  "r2": 0.884,
  "trained_at": "2026-10-01T09:31:00Z",
  "feature_names": ["hour", "minute", "day_of_week", "is_weekend", "light_smoothed", "motion", "..."]
}
```

### `GET /api/ml/prediction`
Returns real-time predicted lighting demand percentage for the active sensor state.

### `GET /api/ml/anomalies?limit=30`
Returns log of detected behavioral anomalies.

### `POST /api/ml/anomalies/trigger?anomaly_type=high_light_unoccupied`
Live demo endpoint to inject simulated anomalies for presentation testing.

---

## 4. Recommendations & Efficiency Endpoints

### `GET /api/recommendations`
Returns heuristic energy-saving and comfort suggestions.

### `GET /api/recommendations/score`
Returns the project-defined LumiSense Efficiency Score (0-100) with diagnostic breakdown and disclaimer.
