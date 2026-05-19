/*
 * pHloat pH Sensor - ESP32-S3
 * v3.2 — Real temperature sensing, encrypted ESP-NOW, configurable security
 *
 * Reads pH from Atlas Scientific pH OEM circuit via I2C.
 * Reads temperature from DS18B20 OneWire probe for pH compensation.
 * Transmits data to pHloat Relay via encrypted ESP-NOW.
 * Deep sleep between readings (1 minute intervals).
 * Web UI for initial configuration.
 *
 * Hardware:
 * - ESP32-S3
 * - Atlas Scientific pH OEM Circuit (I2C mode, addr 0x63)
 * - DS18B20 temperature probe (OneWire, default GPIO 4)
 * - Battery power supply
 *
 * I2C Pins: SDA=GPIO 8, SCL=GPIO 9
 */

#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <esp_now.h>
#include <esp_sleep.h>
#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>

// ── Hardware pins ─────────────────────────────────────────────
#define PH_SENSOR_ADDR   0x63
#define I2C_SDA          8
#define I2C_SCL          9
#define CONFIG_BUTTON     0
#define TEMP_PIN_DEFAULT  4   // OneWire data pin (changeable in config)

// ── Timing ────────────────────────────────────────────────────
#define SLEEP_DURATION    60  // seconds between readings

// ── Default AP password (change before flashing) ──────────────
#define DEFAULT_AP_PASSWORD  "phloat123"

// ── Device configuration ──────────────────────────────────────
struct Config {
  char deviceName[32];
  char relayMac[18];
  char apPassword[32];
  char pmk[32];           // ESP-NOW PMK (16 bytes hex = 32 chars)
  uint8_t tempPin;
  bool configured;
  uint32_t readingCount;
};

Config config;
Preferences preferences;
WebServer server(80);
OneWire* oneWire = nullptr;
DallasTemperature* tempSensor = nullptr;

// ── pH reading data structure for ESP-NOW ─────────────────────
struct SensorData {
  char deviceName[32];
  float pH;
  float temperature;
  uint32_t readingNumber;
  uint64_t timestamp;
};

// ── Forward declarations ──────────────────────────────────────
void enterConfigMode();
void setupWebServer();
void handleRoot();
void handleSave();
void handleStatus();
float readPH();
float readTemperature();
bool initTempSensor();
void sendDataViaESPNow(float ph, float temp);
void goToSleep();

// ═══════════════════════════════════════════════════════════════
//  SETUP
// ═══════════════════════════════════════════════════════════════

void setup() {
  Serial.begin(115200);

  preferences.begin("phloat", false);

  // Load configuration
  config.configured = preferences.getBool("configured", false);
  if (config.configured) {
    preferences.getString("deviceName", config.deviceName, sizeof(config.deviceName));
    preferences.getString("relayMac",    config.relayMac,    sizeof(config.relayMac));
    preferences.getString("apPassword",  config.apPassword,  sizeof(config.apPassword));
    preferences.getString("pmk",         config.pmk,         sizeof(config.pmk));
    config.tempPin      = preferences.getUChar("tempPin", TEMP_PIN_DEFAULT);
    config.readingCount = preferences.getULong("readCount", 0);
  }

  // Fill defaults for unset optional fields
  if (strlen(config.apPassword) == 0) {
    strlcpy(config.apPassword, DEFAULT_AP_PASSWORD, sizeof(config.apPassword));
  }
  if (config.tempPin == 0) {
    config.tempPin = TEMP_PIN_DEFAULT;
  }

  // Check if config button is pressed
  pinMode(CONFIG_BUTTON, INPUT_PULLUP);
  delay(100);

  if (digitalRead(CONFIG_BUTTON) == LOW || !config.configured) {
    Serial.println("Entering configuration mode...");
    enterConfigMode();
    return;
  }

  Serial.println("pHloat Sensor starting...");
  Serial.printf("Device: %s\n", config.deviceName);
  Serial.printf("Reading #%lu\n", config.readingCount + 1);

  // Initialize I2C
  Wire.begin(I2C_SDA, I2C_SCL);
  delay(100);

  // Initialize temperature sensor
  initTempSensor();

  // Read pH and temperature
  float ph = readPH();
  float temp = readTemperature();

  // Apply temperature compensation to pH if we have a real reading
  if (ph > 0 && ph < 14 && temp > -40 && temp < 125) {
    // Nernst-based temperature compensation: pH varies ~0.03 per °C from 25°C
    float calTemp = 25.0;
    ph = ph + (calTemp - temp) * 0.03;
  }

  Serial.printf("pH: %.2f, Temp: %.2f°C\n", ph, temp);

  // Send data via ESP-NOW
  if (ph > 0 && ph < 14) {
    sendDataViaESPNow(ph, temp);
    config.readingCount++;
    preferences.putULong("readCount", config.readingCount);
  } else {
    Serial.println("Invalid pH reading, not sending data");
  }

  goToSleep();
}

void loop() {
  // Normal operation never reaches here — deep sleep restarts from setup()
}

// ═══════════════════════════════════════════════════════════════
//  CONFIGURATION MODE (WiFi AP + Web Server)
// ═══════════════════════════════════════════════════════════════

void enterConfigMode() {
  WiFi.mode(WIFI_AP);
  String apName = "pHloat-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  WiFi.softAP(apName.c_str(), config.apPassword);

  Serial.println("Configuration AP started");
  Serial.printf("SSID: %s\n", apName.c_str());
  Serial.printf("IP: %s\n", WiFi.softAPIP().toString().c_str());

  setupWebServer();
  server.begin();

  while (true) {
    server.handleClient();
    delay(10);
  }
}

void setupWebServer() {
  server.on("/",        handleRoot);
  server.on("/save",    HTTP_POST, handleSave);
  server.on("/status",  handleStatus);
}

void handleRoot() {
  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>pHloat Sensor Configuration</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto;
           padding: 20px; background: #f5f5f5; }
    .container { background: white; padding: 30px; border-radius: 10px;
                 box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
    label { display: block; margin-top: 15px; font-weight: bold; color: #555; }
    input, select { width: 100%; padding: 10px; margin-top: 5px;
                    border: 1px solid #ddd; border-radius: 5px;
                    box-sizing: border-box; font-size: 16px; }
    button { width: 100%; padding: 12px; margin-top: 20px; background: #4CAF50;
             color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
    button:hover { background: #45a049; }
    .info { background: #e3f2fd; padding: 15px; border-radius: 5px; margin-top: 20px; }
    .success { background: #4CAF50; color: white; padding: 15px; border-radius: 5px;
               margin-top: 20px; display: none; }
    .help { font-size: 0.85em; color: #888; font-weight: normal; }
  </style>
</head>
<body>
  <div class="container">
    <h1>pHloat Sensor Setup</h1>

    <form id="configForm">
      <label for="deviceName">Device Name:</label>
      <input type="text" id="deviceName" name="deviceName" value=")rawliteral"
      + String(config.deviceName) + R"rawliteral(" placeholder="e.g., Fermenter-1" required>

      <label for="relayMac">Relay MAC Address:</label>
      <input type="text" id="relayMac" name="relayMac" value=")rawliteral"
      + String(config.relayMac) + R"rawliteral(" placeholder="AA:BB:CC:DD:EE:FF"
             pattern="[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}" required>

      <label for="apPassword">AP Password: <span class="help">(for config mode WiFi)</span></label>
      <input type="text" id="apPassword" name="apPassword" value=")rawliteral"
      + String(config.apPassword) + R"rawliteral(" minlength="8" required>

      <label for="pmk">ESP-NOW Encryption Key (PMK): <span class="help">(16 bytes hex = 32 hex chars)</span></label>
      <input type="text" id="pmk" name="pmk" value=")rawliteral"
      + String(config.pmk) + R"rawliteral(" placeholder="32 hex characters for over-the-air encryption"
             pattern="[0-9A-Fa-f]{32}" maxlength="32">

      <label for="tempPin">Temperature Sensor GPIO Pin:</label>
      <input type="number" id="tempPin" name="tempPin" value=")rawliteral"
      + String(config.tempPin) + R"rawliteral(" min="0" max="39">

      <button type="submit">Save Configuration</button>
    </form>

    <div class="success" id="successMsg">
      Configuration saved! Device will reboot and start taking readings.
    </div>

    <div class="info">
      <strong>Setup Instructions:</strong><br>
      1. Give your sensor a unique name<br>
      2. Enter your pHloat Relay's MAC address<br>
      3. Set an AP password (min 8 chars, for config WiFi)<br>
      4. Set the ESP-NOW PMK for encrypted data transmission<br>
      5. Specify the GPIO pin for your DS18B20 temp probe<br>
      6. Save and the device will reboot<br><br>
      <strong>Note:</strong> Calibration is performed through the Relay interface.
    </div>
  </div>

  <script>
    document.getElementById('configForm').addEventListener('submit', function(e) {
      e.preventDefault();
      const formData = new FormData(this);
      const data = {};
      formData.forEach((value, key) => data[key] = value);
      fetch('/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
      })
      .then(response => response.json())
      .then(result => {
        if (result.success) {
          document.getElementById('successMsg').style.display = 'block';
          setTimeout(() => { location.href = '/'; }, 3000);
        } else {
          alert('Error: ' + (result.error || 'Unknown'));
        }
      });
    });
  </script>
</body>
</html>
)rawliteral";
  server.send(200, "text/html", html);
}

void handleSave() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"success\":false,\"error\":\"No data\"}");
    return;
  }

  String body = server.arg("plain");

  // Use ArduinoJson for robust parsing
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, body);

  if (error) {
    Serial.printf("JSON parse error: %s\n", error.c_str());
    server.send(400, "application/json", "{\"success\":false,\"error\":\"Invalid JSON\"}");
    return;
  }

  const char* name = doc["deviceName"] | "";
  const char* mac  = doc["relayMac"]    | "";
  const char* pw   = doc["apPassword"]  | DEFAULT_AP_PASSWORD;
  const char* pmk  = doc["pmk"]         | "";
  uint8_t pin      = doc["tempPin"]     | TEMP_PIN_DEFAULT;

  // Validate
  if (strlen(name) == 0 || strlen(mac) == 0) {
    server.send(400, "application/json", "{\"success\":false,\"error\":\"Name and MAC required\"}");
    return;
  }
  if (strlen(pw) < 8) {
    server.send(400, "application/json", "{\"success\":false,\"error\":\"Password must be 8+ chars\"}");
    return;
  }
  if (strlen(pmk) > 0 && strlen(pmk) != 32) {
    server.send(400, "application/json", "{\"success\":false,\"error\":\"PMK must be exactly 32 hex chars if set\"}");
    return;
  }

  // Save to preferences
  preferences.putString("deviceName", name);
  preferences.putString("relayMac",    mac);
  preferences.putString("apPassword",  pw);
  preferences.putString("pmk",         pmk);
  preferences.putUChar("tempPin",     pin);
  preferences.putBool("configured", true);

  Serial.printf("Saved: Device=%s, Relay=%s, TempPin=%u\n", name, mac, pin);

  server.send(200, "application/json", "{\"success\":true}");

  delay(1000);
  ESP.restart();
}

void handleStatus() {
  StaticJsonDocument<256> doc;
  doc["deviceName"]   = config.deviceName;
  doc["relayMac"]     = config.relayMac;
  doc["configured"]   = config.configured;
  doc["readingCount"] = config.readingCount;
  doc["tempPin"]      = config.tempPin;

  String json;
  serializeJson(doc, json);
  server.send(200, "application/json", json);
}

// ═══════════════════════════════════════════════════════════════
//  SENSOR READING
// ═══════════════════════════════════════════════════════════════

float readPH() {
  Wire.beginTransmission(PH_SENSOR_ADDR);
  Wire.write('R');
  Wire.endTransmission();

  delay(900);  // Atlas pH OEM needs ~900ms to complete a reading

  Wire.requestFrom(PH_SENSOR_ADDR, 20);

  byte code = Wire.read();
  if (code != 1) {
    Serial.printf("pH read error: code %d\n", code);
    return -1.0;
  }

  char data[20];
  int i = 0;
  while (Wire.available() && i < 19) {
    data[i++] = Wire.read();
  }
  data[i] = '\0';

  return atof(data);
}

bool initTempSensor() {
  if (oneWire) {
    delete tempSensor;
    delete oneWire;
  }
  oneWire    = new OneWire(config.tempPin);
  tempSensor = new DallasTemperature(oneWire);
  tempSensor->begin();

  int count = tempSensor->getDeviceCount();
  if (count == 0) {
    Serial.println("No DS18B20 found on pin " + String(config.tempPin) + " — will return -127");
    return false;
  }
  Serial.printf("Found %d DS18B20 sensor(s) on pin %u\n", count, config.tempPin);
  return true;
}

float readTemperature() {
  if (!tempSensor || tempSensor->getDeviceCount() == 0) {
    return -127.0;  // Sentinel: no sensor
  }

  tempSensor->requestTemperatures();
  float temp = tempSensor->getTempCByIndex(0);

  // DallasTemperature returns DEVICE_DISCONNECTED_C (-127) on failure
  if (temp <= -127.0) {
    Serial.println("DS18B20 read failed");
  }

  return temp;
}

// ═══════════════════════════════════════════════════════════════
//  ESP-NOW TRANSMISSION (encrypted, streamlined)
// ═══════════════════════════════════════════════════════════════

void sendDataViaESPNow(float ph, float temp) {
  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }

  // Set PMK for encryption (applies to all peers)
  if (strlen(config.pmk) == 32) {
    // Convert hex PMK to 16 raw bytes
    uint8_t pmkBytes[16];
    for (int i = 0; i < 16; i++) {
      char hex[3] = { config.pmk[i*2], config.pmk[i*2+1], '\0' };
      pmkBytes[i] = (uint8_t)strtol(hex, nullptr, 16);
    }
    esp_now_set_pmk(pmkBytes);
  }

  // Parse relay MAC address
  uint8_t relayMacBytes[6];
  int parsed = sscanf(config.relayMac, "%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",
             &relayMacBytes[0], &relayMacBytes[1], &relayMacBytes[2],
             &relayMacBytes[3], &relayMacBytes[4], &relayMacBytes[5]);

  if (parsed != 6) {
    Serial.println("Invalid relay MAC address");
    return;
  }

  // Add peer with encryption enabled when PMK is set
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, relayMacBytes, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = (strlen(config.pmk) == 32);

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add ESP-NOW peer");
    return;
  }

  // Prepare and send data
  SensorData data;
  strlcpy(data.deviceName, config.deviceName, sizeof(data.deviceName));
  data.pH             = ph;
  data.temperature     = temp;
  data.readingNumber  = config.readingCount + 1;
  data.timestamp      = millis();

  esp_err_t result = esp_now_send(relayMacBytes, (uint8_t*)&data, sizeof(data));

  if (result == ESP_OK) {
    Serial.println("Data sent via encrypted ESP-NOW");
  } else {
    Serial.printf("ESP-NOW send error: %d\n", result);
  }

  // No deinit() or extra delay — deep sleep will clean up everything
}

// ═══════════════════════════════════════════════════════════════
//  DEEP SLEEP
// ═══════════════════════════════════════════════════════════════

void goToSleep() {
  Serial.printf("Sleeping for %d seconds...\n", SLEEP_DURATION);
  preferences.end();

  // Clean up heap allocations
  if (tempSensor) { delete tempSensor; tempSensor = nullptr; }
  if (oneWire)    { delete oneWire;    oneWire    = nullptr; }

  esp_sleep_enable_timer_wakeup(SLEEP_DURATION * 1000000ULL);
  esp_deep_sleep_start();
}
