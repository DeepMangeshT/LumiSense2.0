# LumiSense Hardware Integration Guide

This guide covers physical wiring, calibration steps, and serial integration for the Arduino Uno and sensors.

---

## 1. Physical Hardware Components

1. **Microcontroller:** Arduino Uno R3 (ATmega328P, 16 MHz, 10-bit ADC).
2. **Light Sensor:** LDR Light Dependent Resistor module (LM393-based with Analog Output AO pin).
3. **Motion Sensor:** HC-SR501 Pyroelectric Infrared (PIR) Sensor.
4. **Connection:** Standard USB Type A-to-B cable to host Windows PC.
5. **Temperature and humidity:** DHT11 sensor (firmware configured for DHT11).

---

## 2. Pin Connections Table

| Sensor Pin | Arduino Pin | Function | Notes |
| :--- | :--- | :--- | :--- |
| **LDR VCC** | 5V | Power | Powers LM393 chip |
| **LDR GND** | GND | Ground | Common system ground |
| **LDR AO** | **A0** | Analog In | Continuous voltage reading (0–1023) |
| **LDR DO** | *Unused* | Digital Out | Fixed threshold (not used) |
| **HC-SR501 VCC** | 5V | Power | Requires 4.5V–12V DC |
| **HC-SR501 GND** | GND | Ground | Common system ground |
| **HC-SR501 OUT** | **D2** | Digital In | HIGH = Motion, LOW = Idle |
| **DHT11 DATA** | **D7** | Digital I/O | Requires the Adafruit DHT library |

---

## 3. Sensor Nuances & Calibration

### 3.1. LDR Analog Light Level
* **Relative ADC Value:** Arduino's 10-bit Analog-to-Digital Converter reads voltages from 0 to 5V as integers from `0` to `1023`.
* **Important:** This reading represents **Relative Light Level**, not calibrated physical lux. Do not label raw readings as lux without a calibrated lux meter reference curve.
* **Fluctuation:** Low-cost LDRs experience slight thermal noise ($\pm 5-15$ units). The backend's moving average filter (`SignalFilter` with $N=5$) smooths these fluctuations while retaining the raw value.

### 3.2. HC-SR501 PIR Calibration
* **Warm-up Time:** HC-SR501 requires approximately 15 to 30 seconds upon power-up to adjust to ambient infrared radiation.
* **Sensitivity Potentiometer:** Set midway (~4 to 5 meters).
* **Time Delay Potentiometer:** Set fully counterclockwise (~3 seconds duration) so the system receives fast updates.
* **Jumper (H vs L):** Set to **H (Repeatable trigger)** mode.

### 3.3. DHT11 Temperature and Humidity
* Connect DATA to D7, VCC to 5V, and GND to GND.
* Install **DHT sensor library by Adafruit** and **Adafruit Unified Sensor** in Arduino IDE Library Manager.
* The firmware sends temperature and humidity as JSON fields. A failed or missing DHT reading is transmitted as `null`; the dashboard does not substitute simulated values.

---

## 4. Troubleshooting Serial Connection on Windows

1. **Port Locked / "Permission Denied" Error:**
   * In Windows, only one application can access a COM port at a time.
   * If you have the Arduino IDE **Serial Monitor** open, close it before starting the Python backend.
2. **Arduino Reset on Connect:**
   * When serial communication is initiated, the Arduino Uno DTR line toggles and resets the board.
   * The Python `SerialCollector` waits 1.5 seconds and flushes the buffer before reading frames.
3. **Driver Issues:**
   * Official Arduino Uno uses the standard Windows USB-CDC driver.
   * Clone boards using the CH340 or CP2102 chip require the CH340/CP2102 driver installed on Windows.
