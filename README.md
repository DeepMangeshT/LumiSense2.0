# LumiSense — IoT-Based Smart Light & Energy Usage Monitoring System

> **Sub-title:** IoT-Based Smart Light and Energy Usage Monitoring System  
> **Course/Level:** B.Tech Information Technology — Final Year Capstone / Academic Mini-Project  
> **Target Platform:** Windows (Primary), Linux, macOS  

---

## 1. Project Overview

**LumiSense** is a low-cost, extensible IoT and Machine Learning environmental monitoring system designed to monitor contextual and environmental conditions related to lighting and room usage.

The system collects real-time sensor data from an **Arduino Uno R3** over USB serial communication, validates incoming readings, eliminates analog noise using configurable moving-average smoothing, stores historical logs in an indexed SQLite database, and trains machine learning models (**Random Forest Regressor** and **Isolation Forest**) to forecast lighting demand and detect unusual usage patterns.

A modern, responsive web dashboard built with **React** and **Vite** displays live dials, historical charts, model performance evaluations, anomaly logs, and energy-saving recommendations.

---

## 2. Important Academic & Technical Disclosures

> [!IMPORTANT]
> **Technical Limitation:** The current hardware uses environmental and occupancy sensors (LDR and PIR). **It does NOT directly measure electrical voltage, current, or electricity consumption in kilowatt-hours (kWh).**
>
> Therefore, this project adheres to strict technical honesty:
> * It models **Estimated Lighting Demand (%)**, reflecting the required artificial illumination based on ambient daylight and occupant presence.
> * It identifies **Potential Lighting/Usage Inefficiencies**, such as lights remaining active in an empty room, rather than claiming proven electrical kilowatt-hour waste.
> * Raw LDR values are presented as **Relative Light Level (ADC 0–1023)**, rather than uncalibrated lux.
> * The software architecture is designed so that a dedicated voltage/current sensor (e.g. ACS712) or smart power meter can be added in the future without refactoring.

---

## 3. Key Features

* **Real-Time Telemetry Stream:** Continuous LDR relative light level and PIR occupancy detection at 9600 baud.
* **Zero-Crash Resilience:** Background serial collector with auto-reconnect logic; unplugging or replugging the Arduino will not crash the backend.
* **Dual Operating Modes:**
  * **Real Hardware Mode:** Reads physical Arduino Uno sensor data.
  * **Simulation Mode:** Realistic diurnal daylight simulation with occupant activity patterns for demonstrations even when the hardware is not connected.
* **Signal Validation & Smoothing:** Rejects out-of-range ADC frames and smooths fluctuations using a configurable moving-average window ($N=5$).
* **Machine Learning Pipeline:**
  * **Random Forest Regressor:** Continuous prediction of Estimated Lighting Demand (0–100%).
  * **Isolation Forest:** Unsupervised detection of anomalous sensor configurations (e.g., high illumination during late-night vacant hours).
  * **Data Readiness Verification:** Explicitly guards against training on insufficient data ($<100$ records = Insufficient, $100-500$ = Early experimentation, $500+$ = Ready).
  * **Evaluation Metrics:** Displays real MAE, RMSE, and $R^2$ scores on test splits.
* **Live Anomaly Injection Sandbox:** Interactive demo buttons on the web interface allowing evaluators to inject simulated anomalies and watch real-time detection in action.
* **LumiSense Efficiency Score (0–100):** Custom analytical score quantifying occupancy-to-lighting harmony, complete with diagnostic factor breakdowns and disclaimers.
* **Extensible Schema:** Ready to accept future temperature and humidity sensors (e.g. DHT11) without schema migrations.
* **Cyber-Clean UI:** Dark/Light themes, glassmorphism cards, responsive Recharts telemetry graphs, and live SVG dials.

---

## 4. Hardware Architecture & Wiring

### Hardware Components
* **Microcontroller:** Arduino Uno R3
* **Light Sensor:** LDR Light Dependent Resistor Module (LM393 analog module)
* **Motion Sensor:** HC-SR501 PIR Motion Sensor
* **Connection Cable:** USB Type A-to-B Cable
* *(Future Extension):* DHT11 Temperature & Humidity Sensor

### Wiring Diagram

```
┌────────────────────────────────────────────────────────┐
│                      ARDUINO UNO                       │
│                                                        │
│  [5V]  ──────┬──────────┬───────────────────────────── │
│  [GND] ──────┼──────────┼───────────────────────────── │
│  [A0]  ──────┼──────────┼─────────────── (LDR AO)      │
│  [D2]  ──────┼──────────┴─────────────── (PIR OUT)     │
│  [D7]  ──────┴────────────────────────── (DHT11 DATA)  │
└────────────────────────────────────────────────────────┘
```

| Sensor Pin | Arduino Pin | Description |
| :--- | :--- | :--- |
| **LDR VCC** | **5V** | 5V DC Power |
| **LDR GND** | **GND** | Ground reference |
| **LDR AO** | **A0** | **Analog Input** (Continuous 0–1023 relative level) |
| **LDR DO** | *Unused* | Digital comparator threshold (unused) |
| **HC-SR501 VCC**| **5V** | 5V DC Power |
| **HC-SR501 GND**| **GND** | Ground reference |
| **HC-SR501 OUT**| **D2** | **Digital Input** (HIGH = Motion detected, LOW = Idle) |
| **DHT11** | **D7** | Digital single-bus data pin |

---

## 5. Software Requirements

Before getting started, make sure you have:
* **Python 3.10+** (Python 3.13 supported)
* **Node.js 18+** & **npm**
* **Arduino IDE** (if uploading to physical microcontroller)

---

## 6. Installation & Setup (Windows First)

### Step 1: Clone or Navigate to Project
Open **PowerShell** or **Command Prompt**:
```powershell
cd "c:\Users\DEEP M THAKUR\Downloads\LumiSense"
```

### Step 2: Set Up Python Backend
Create and activate a virtual environment (optional, or use global python):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(On macOS/Linux: `source venv/bin/activate`)*

Install required packages:
```powershell
pip install -r requirements.txt
```

### Step 3: Set Up React Frontend
Open a second terminal window in the `frontend` directory:
```powershell
cd frontend
npm install
```

---

## 7. Running LumiSense

### Starting the Backend Server
From the project root:
```powershell
python backend/run.py
```
* Backend API: **http://localhost:8000**
* Interactive OpenAPI Documentation: **http://localhost:8000/docs**
* On first startup, the system creates `data/lumisense.db` without inserting sample readings and does not start simulation. Sensor APIs and dashboard analytics use hardware readings only; previously stored demo records are not removed, but are excluded from the live sensor views.

### Starting the Frontend Dashboard
From the `frontend` directory:
```powershell
npm run dev
```
Open your browser and navigate to: **http://localhost:5173**

---

## 8. Arduino Setup & Uploading Firmware

1. Connect your Arduino Uno to your PC using the USB A-to-B cable.
2. Launch the **Arduino IDE**.
3. Install **DHT sensor library by Adafruit** and **Adafruit Unified Sensor** from Library Manager, and wire the DHT11 DATA pin to D7 (VCC to 5V, GND to GND).
4. Open `arduino/lumisense.ino`.
5. Go to **Tools > Board** and select **Arduino Uno**.
6. Go to **Tools > Port** and choose your Arduino COM port (e.g., `COM3`, `COM4`).
7. Click **Upload** (`Ctrl + U`).
8. **Important:** Close the Arduino IDE Serial Monitor before starting the LumiSense backend, as Windows allows only one application to hold an open serial connection.
9. In the LumiSense Web Dashboard, navigate to **Settings** and ensure your COM port is selected (or set to **AUTO**). The system will automatically detect the Arduino and use real hardware data.

---

## 9. Running Automated Tests

Run the full pytest suite:
```powershell
python -m pytest tests/ -v
```
The unit and integration tests verify:
* Multi-format serial parsing (Legacy text `"Light: 222 | Motion: YES"`, CSV `"222,1"`, JSON)
* Data boundary validation (ADC 0–1023, PIR 0/1, temperature, humidity)
* Moving average signal filtering
* ML feature extraction without data leakage and demand target logic
* FastAPI REST endpoints (`/api/health`, `/api/status`, `/api/sensors/history`, etc.)

---

## 10. LumiSense Efficiency Score Calculation

The **LumiSense Efficiency Score ($S$)** is an academic metric calculated as:

$$S = 100 - (\text{Unoccupied Overillumination Penalty}) - (\text{Recent Anomaly Penalty})$$

* **Unoccupied High Light:** If relative light $> 500$ when motion $= 0$, a deduction of 1.5 points per reading is applied; if light $> 300$, a 0.7 point deduction is applied.
* **Anomaly Penalty:** Active statistical anomalies within the observation window deduct 3.0 points each (capped at 20 points).
* **Score Interpretation:**
  * **85 – 100:** *Excellent* (High natural light usage, fixtures off when vacant)
  * **70 – 84:** *Good* (Normal baseline room operation)
  * **50 – 69:** *Fair* (Sporadic instances of unused lighting)
  * **$< 50$:** *Inefficient* (Frequent sustained lighting in unoccupied room)

*Disclaimer: This is a project-defined analytical metric and should not be interpreted as a certified energy-efficiency standard.*

---

## 11. Project Directory Structure

```text
LumiSense/
│
├── arduino/
│   ├── lumisense.ino          # Arduino Uno firmware (LDR + PIR + future DHT11)
│   └── README.md              # Wiring schematics and pinout table
│
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI modular route handlers
│   │   ├── ml/                # Feature engineering, Random Forest, Isolation Forest
│   │   ├── models/            # Pydantic validation schemas
│   │   ├── serial/            # Pyserial collector and multi-format parser
│   │   ├── services/          # Filtering, validation, simulation, recommendations
│   │   ├── config.py          # Settings and environment defaults
│   │   ├── database.py        # SQLite WAL manager and CRUD functions
│   │   └── main.py            # FastAPI application factory and lifespan manager
│   ├── run.py                 # Backend launcher script
│   └── requirements.txt       # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/        # Navbar, Sidebar, MetricCard, LiveGauge, AlertBanner
│   │   ├── pages/             # Dashboard, Analytics, Predictions, Anomalies, Recommendations, Settings
│   │   ├── services/          # Centralized API client (api.js)
│   │   ├── App.jsx            # State management and tab routing
│   │   └── index.css          # Design system (Dark/Light glassmorphism)
│   ├── package.json           # React, Vite, Recharts, Lucide-React
│   └── vite.config.js
│
├── data/
│   └── lumisense.db           # SQLite database (auto-initialized)
│
├── docs/
│   ├── architecture.md        # Architectural diagrams and design principles
│   ├── data-flow.md           # Step-by-step telemetry pipeline
│   ├── ml-methodology.md      # ML models, features, and readiness criteria
│   ├── api.md                 # REST API reference
│   └── hardware-integration.md# Physical sensor connections and calibration
│
├── tests/
│   ├── test_api.py            # FastAPI integration tests
│   ├── test_ml.py             # Feature engineering and readiness tests
│   ├── test_parser.py         # Serial parser tests
│   └── test_validator.py      # Validator and moving average filter tests
│
├── .env.example               # Example configuration variables
├── README.md                  # Complete project guide
└── requirements.txt           # Root requirements
```

---

## 12. Authors & Acknowledgments

* **Student Developer:** Final Year Information Technology Student
* **Institution:** Information Technology Engineering Department
* **Project Title:** LumiSense: IoT-Based Smart Light and Energy Usage Monitoring System
