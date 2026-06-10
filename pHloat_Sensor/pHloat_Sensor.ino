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
#include "phloat_common.h"
#include "web_ui_templates.h"
#include "phloat_web.h"

// ── Hardware pins ─────────────────────────────────────────────
#define PH_SENSOR_ADDR   0x63
#define I2C_SDA          8
#define I2C_SCL          9
#define CONFIG_BUTTON     0
#define TEMP_PIN_DEFAULT  4   // OneWire data pin (changeable in config)

// ── Timing ────────────────────────────────────────────────────
#define SLEEP_DURATION    60  // seconds between readings

// ── Default AP password (generated on first boot if unset) ────
#define DEFAULT_AP_PASSWORD  ""

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

volatile bool espNowAck = false;
volatile bool espNowOk = false;

void onEspNowSent(const uint8_t *mac, esp_now_send_status_t status) {
  espNowAck = true;
  espNowOk = (status == ESP_NOW_SEND_SUCCESS);
}

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
void ensureSensorSecurityDefaults();

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
  ensureSensorSecurityDefaults();
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

  // Atlas pH OEM applies temperature compensation internally when temp is sent via I2C.
  // Do not apply a second manual correction here.

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
  String html = phloat_load_template(TPL_CONFIG);
  phloat_tpl_replace(html, "{{DEVICE_NAME}}", String(config.deviceName));
  phloat_tpl_replace(html, "{{RELAY_MAC}}", String(config.relayMac));
  phloat_tpl_replace(html, "{{AP_PASSWORD}}", String(config.apPassword));
  phloat_tpl_replace(html, "{{PMK}}", String(config.pmk));
  phloat_tpl_replace(html, "{{TEMP_PIN}}", String(config.tempPin));
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
  if (strlen(pw) < PHLOAT_MIN_AP_PASSWORD_LEN || phloat_is_weak_password(pw)) {
    server.send(400, "application/json", "{\"success\":false,\"error\":\"Password must be 12+ chars and not the default\"}");
    return;
  }
  if (strlen(pmk) > 0 && strlen(pmk) != 32) {
    server.send(400, "application/json", "{\"success\":false,\"error\":\"PMK must be exactly 32 hex chars if set\"}");
    return;
  }

  char safeName[32];
  phloat_sanitize_device_name(name, safeName, sizeof(safeName));

  // Save to preferences
  preferences.putString("deviceName", safeName);
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

  esp_now_register_send_cb(onEspNowSent);

  if (strlen(config.pmk) == 32 && !phloat_apply_pmk(config.pmk)) {
    Serial.println("Invalid ESP-NOW PMK");
  }

  uint8_t relayMacBytes[6];
  if (!phloat_parse_mac(config.relayMac, relayMacBytes)) {
    Serial.println("Invalid relay MAC address");
    return;
  }

  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, relayMacBytes, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = (strlen(config.pmk) == 32);

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add ESP-NOW peer");
    return;
  }

  SensorData data;
  phloat_init_sensor_data(data);
  phloat_sanitize_device_name(config.deviceName, data.deviceName, sizeof(data.deviceName));
  data.pH = ph;
  data.temperature = temp;
  data.readingNumber = config.readingCount + 1;
  data.timestamp = 0;
  WiFi.macAddress(data.senderMac);

  bool sent = false;
  for (int attempt = 0; attempt < 3; attempt++) {
    espNowAck = false;
    espNowOk = false;
    esp_err_t result = esp_now_send(relayMacBytes, (uint8_t*)&data, sizeof(data));
    if (result != ESP_OK) {
      Serial.printf("ESP-NOW send error: %d\n", result);
      continue;
    }

    unsigned long start = millis();
    while (!espNowAck && millis() - start < 500) {
      delay(10);
    }
    if (espNowOk) {
      sent = true;
      Serial.println("Data sent via ESP-NOW");
      break;
    }
    Serial.printf("ESP-NOW send attempt %d failed, retrying...\n", attempt + 1);
    delay(50);
  }

  if (!sent) {
    Serial.println("ESP-NOW send failed after retries");
  }
}

void ensureSensorSecurityDefaults() {
  if (strlen(config.apPassword) == 0 || phloat_is_weak_password(config.apPassword)) {
    char pass[17];
    phloat_generate_hex_token(pass, sizeof(pass));
    pass[16] = '\0';
    strlcpy(config.apPassword, pass, sizeof(config.apPassword));
    preferences.putString("apPassword", pass);
    Serial.println("*** SECURITY: Generated AP password (save this): " + String(pass));
  }
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
