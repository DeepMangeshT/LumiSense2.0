/*
  =============================================================================
  LumiSense — IoT-Based Smart Light and Energy Usage Monitoring System
  Arduino Uno Firmware (v1.0)
  =============================================================================
  
  Hardware Pin Configuration:
  ---------------------------
  1. LDR Module (LM393 analog module):
     - VCC  -> Arduino 5V
     - GND  -> Arduino GND
     - AO   -> Arduino Analog Pin A0  (Continuous 10-bit analog reading: 0-1023)
     - DO   -> Not connected
     
  2. PIR Motion Sensor (HC-SR501):
     - VCC  -> Arduino 5V
     - GND  -> Arduino GND
     - OUT  -> Arduino Digital Pin D2 (Binary occupancy signal: HIGH / LOW)

  3. DHT11 Temperature & Humidity:
     - VCC  -> Arduino 5V
     - GND  -> Arduino GND
     - DATA -> Arduino Digital Pin D7
     (DHT library and sensor are required for live temperature and humidity)
     
  Serial Communication:
  ---------------------
  - Baud Rate: 9600 bps
  - USB Type A-to-B cable to Host PC
  - Formats Supported:
      FORMAT_JSON: "{\"light\":222,\"motion\":1,\"temperature\":25.0,\"humidity\":50.0}"
  =============================================================================
*/

// Configuration
#define LDR_PIN       A0       // LDR Analog input
#define PIR_PIN       2        // PIR Digital input
#define STATUS_LED    13       // Onboard LED for transmission heartbeat
#define BAUD_RATE     9600     // Standard serial baud rate
#define SAMPLE_DELAY  1000     // Telemetry interval in milliseconds (1 Hz)

// Format Selector:
// 1 = Legacy Text Format ("Light: 222 | Motion: YES")
// 2 = Structured CSV ("222,1")
// 3 = Structured JSON ("{\"light\":222,\"motion\":1}")
#define OUTPUT_FORMAT 3

// Enable when a DHT11 is connected to D7 and the Adafruit DHT library is installed.
#define ENABLE_DHT    1

#if ENABLE_DHT
  #include <DHT.h>
  #define DHTPIN 7
  #define DHTTYPE DHT11
  DHT dht(DHTPIN, DHTTYPE);
#endif

void setup() {
  // Initialize serial communication
  Serial.begin(BAUD_RATE);
  while (!Serial) {
    ; // Wait for serial port to connect (needed for native USB)
  }

  // Configure pin modes
  pinMode(LDR_PIN, INPUT);
  pinMode(PIR_PIN, INPUT);
  pinMode(STATUS_LED, OUTPUT);

  #if ENABLE_DHT
    dht.begin();
  #endif

  // Brief warm-up indication for PIR sensor (HC-SR501 stabilizes in ~10-15s)
  for (int i = 0; i < 3; i++) {
    digitalWrite(STATUS_LED, HIGH);
    delay(100);
    digitalWrite(STATUS_LED, LOW);
    delay(100);
  }
}

void loop() {
  // 1. Read LDR Light Level (0 to 1023)
  // Higher value typically correlates with higher relative illumination
  int lightRaw = analogRead(LDR_PIN);

  // 2. Read PIR Motion State (HIGH / LOW)
  int pirState = digitalRead(PIR_PIN);
  int motionDetected = (pirState == HIGH) ? 1 : 0;

  // 3. Read DHT11 temperature and humidity
  float temperature = NAN;
  float humidity = NAN;
  #if ENABLE_DHT
    temperature = dht.readTemperature();
    humidity = dht.readHumidity();
  #endif

  // 4. Visual Heartbeat Blink
  digitalWrite(STATUS_LED, HIGH);

  // 5. Output Telemetry via USB Serial
  #if (OUTPUT_FORMAT == 1)
    // Legacy Human-Readable Text Format: "Light: 222 | Motion: YES"
    Serial.print("Light: ");
    Serial.print(lightRaw);
    Serial.print(" | Motion: ");
    Serial.println(motionDetected ? "YES" : "NO");

  #elif (OUTPUT_FORMAT == 2)
    // Compact CSV Format: "light,motion" or "light,motion,temp,humidity"
    Serial.print(lightRaw);
    Serial.print(",");
    Serial.print(motionDetected);
    #if ENABLE_DHT
      Serial.print(",");
      Serial.print(temperature, 1);
      Serial.print(",");
      Serial.print(humidity, 1);
    #endif
    Serial.println();

  #elif (OUTPUT_FORMAT == 3)
    // Structured JSON Format
    Serial.print("{\"light\":");
    Serial.print(lightRaw);
    Serial.print(",\"motion\":");
    Serial.print(motionDetected);
      Serial.print(",\"temperature\":");
      if (isnan(temperature)) {
        Serial.print("null");
      } else {
        Serial.print(temperature, 1);
      }
      Serial.print(",\"humidity\":");
      if (isnan(humidity)) {
        Serial.print("null");
      } else {
        Serial.print(humidity, 1);
      }
    Serial.println("}");
  #endif

  digitalWrite(STATUS_LED, LOW);

  // Wait before next reading
  delay(SAMPLE_DELAY);
}
