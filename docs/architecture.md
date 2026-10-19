# LumiSense System Architecture

This document details the high-level architecture, module decomposition, and design rationale of **LumiSense — IoT-Based Smart Light and Energy Usage Monitoring System**.

---

## 1. Architectural Philosophy

LumiSense is engineered as an extensible, layered IoT & Machine Learning application designed for environmental and room usage monitoring. 

Key design principles:
* **Separation of Concerns:** Hardware serial collection, signal processing, machine learning, persistence, and presentation are strictly decoupled.
* **Resilience:** The software is zero-crash; disconnects, malformed frames, and missing hardware fail gracefully without terminating the server.
* **Hardware Extensibility:** Currently built for an Arduino Uno with an LDR (A0) and PIR (D2), the schema and ingestion pipeline natively accommodate future temperature and humidity sensors (e.g. DHT11) or future smart energy sensors without refactoring.
* **Technically Honest:** Distinguishes environmental context from actual electrical measurements. Predictions are labeled as *Estimated Lighting Demand (%)* and *Potential Usage Inefficiencies*.

---

## 2. High-Level Architecture Diagram

```
┌────────────────────────────────────────────────────────┐
│                   PHYSICAL SENSORS                     │
│   • LDR Light Sensor (AO)    • HC-SR501 PIR (D2)       │
│   • DHT11 Temp/Humidity Sensor (D7)                    │
└──────────────────────────┬─────────────────────────────┘
                           │ 10-bit ADC / Digital High-Low
                           ▼
┌────────────────────────────────────────────────────────┐
│                  ARDUINO UNO R3                        │
│   • 9600 Baud Serial Stream                            │
│   • Formats: "Light: 222 | Motion: YES" or CSV/JSON    │
└──────────────────────────┬─────────────────────────────┘
                           │ USB A-to-B Cable
                           ▼
┌────────────────────────────────────────────────────────┐
│               PYTHON SERIAL COLLECTOR                  │
│   • Auto-discovery of COM ports                        │
│   • Non-blocking background worker with auto-reconnect │
│   • Seamless fallback to Simulation Mode               │
└──────────────────────────┬─────────────────────────────┘
                           │ Raw Line String
                           ▼
┌────────────────────────────────────────────────────────┐
│             VALIDATION & FILTERING PIPELINE            │
│   • Multi-Format Serial Parser (Text, CSV, JSON)       │
│   • Boundary Validation (LDR: 0-1023, PIR: 0/1)        │
│   • Moving Average Smoothing (Configurable Window N)   │
└──────────────────────────┬─────────────────────────────┘
                           │ Normalized Telemetry Vector
                           ▼
┌────────────────────────────────────────────────────────┐
│               DATABASE ACCESS LAYER (WAL)              │
│   • SQLite Database (lumisense.db)                     │
│   • Historical telemetry, anomalies, models, audit logs│
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────────┐ ┌───────────────────────┐
│     ML & ANALYTICS ENGINE    │ │    RULE RECOMMENDATION │
│ • Random Forest Regressor    │ │ • Heuristic rules     │
│   (Lighting Demand %)        │ │ • Project-defined     │
│ • Isolation Forest Anomaly   │ │   LumiSense Efficiency│
│ • Feature Engineering        │ │   Score (0-100)       │
└──────────────┬───────────────┘ └───────────┬───────────┘
               │                             │
               ▼                             ▼
┌────────────────────────────────────────────────────────┐
│                   FASTAPI BACKEND                      │
│   • REST API Endpoints with Pydantic validation        │
│   • OpenAPI Interactive Documentation (/docs)          │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP / JSON Polling
                           ▼
┌────────────────────────────────────────────────────────┐
│              REACT + VITE WEB DASHBOARD                │
│   • Modern Glassmorphism & Cyber-Clean Dark/Light Mode │
│   • Real-Time Recharts Telemetry Streams               │
│   • Live Anomaly Demo Injection Sandbox                │
│   • Serial & System Settings Console                   │
└────────────────────────────────────────────────────────┘
```

---

## 3. Subsystem Breakdown

### 3.1. Telemetry Ingestion Layer (`backend/app/serial/`)
* **`collector.py`**: Manages USB serial connectivity via `pyserial`. Runs in an isolated daemon thread so that communication delays or port drops never block API requests.
* **`parser.py`**: Accepts legacy strings (`"Light: 222 | Motion: YES"`), compact CSV (`"222,1"`), and structured JSON (`{"light": 222, "motion": 1}`).

### 3.2. Data Validation & Signal Smoothing (`backend/app/services/`)
* **`validator.py`**: Enforces strict hardware limits. Rejects corrupted ADC frames (< 0 or > 1023) and validates binary motion logic.
* **`filter.py`**: A thread-safe moving average buffer of length `N` (default 5). Provides both raw and filtered signals for dashboard rendering.
* **`simulation.py`**: Generates diurnal daylight curves and Markovian occupant activity when running in demo/offline mode.

### 3.3. Persistence Layer (`backend/app/database.py`)
* Leverages SQLite in Write-Ahead Logging (`PRAGMA journal_mode = WAL`) mode for concurrent readers and writers without database locking errors.
* Indexed on `timestamp` and `source` for rapid historical queries.

### 3.4. Machine Learning Subsystem (`backend/app/ml/`)
* **Feature Engineering**: Derives cyclical temporal components (hour, minute, day of week, weekend indicator), rolling statistical moments (rolling light mean, motion activity rate), and 1-lag steps without data leakage.
* **Random Forest Regressor**: Estimates expected artificial lighting demand based on available daylight and occupant presence.
* **Isolation Forest**: Learns normal multidimensional sensor distributions to flag anomalous usage patterns.
