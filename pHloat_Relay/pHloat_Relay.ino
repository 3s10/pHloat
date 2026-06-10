/*
 * pHloat Relay - ESP32
 * v3.2 — Encrypted ESP-NOW, piecewise calibration, OTA updates, HTTPS uploads
 *
 * Receives pH data from multiple pHloat Sensors via encrypted ESP-NOW.
 * Matches pH readings with Tilt Hydrometer data by timestamp.
 * Uploads combined data to Google Sheets over HTTPS.
 * Provides web UI for configuration, calibration, and data review.
 * Local data storage with management.
 * Over-the-air firmware updates via ElegantOTA.
 *
 * Hardware:
 * - ESP32 (any variant)
 * - SD card or SPIFFS for data storage
 */

#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <esp_now.h>
#include <SPIFFS.h>
#include <time.h>
#include <ArduinoJson.h>
#include <ElegantOTA.h>
#include "phloat_common.h"

// ── Defaults ──────────────────────────────────────────────────
#define DEFAULT_AP_PASSWORD  ""  // generated on first boot if unset
#define DEFAULT_PMK          ""  // 32 hex chars for ESP-NOW encryption

// ── Web server ─────────────────────────────────────────────────
WebServer server(80);
Preferences preferences;

// ── Configuration structure ────────────────────────────────────
struct RelayConfig {
  char wifiSSID[64];
  char wifiPassword[64];
  char googleSheetURL[256];
  char apPassword[32];
  char pmk[32];           // ESP-NOW PMK (16 bytes → 32 hex chars)
  char uploadSecret[33];  // shared with Google Apps Script / Tilt Pi
  bool wifiEnabled;
  bool sheetsEnabled;
  char ntpServer[64];
  int timezoneOffset;
};

RelayConfig relayConfig;

// ── Calibration data ───────────────────────────────────────────
struct CalibrationData {
  float ph4_reading;
  float ph7_reading;
  float ph10_reading;
  bool calibrated;
  unsigned long calibrationTime;
};

#define MAX_SENSORS 10
struct SensorCalibration {
  char deviceName[32];
  CalibrationData cal;
};

SensorCalibration sensorCalibrations[MAX_SENSORS];
int numCalibratedSensors = 0;

// ── File paths ─────────────────────────────────────────────────
#define DATA_DIR         "/data"
#define CALIBRATION_FILE "/calibrations.json"

// ── Time sync ──────────────────────────────────────────────────
bool     timeInitialized    = false;
unsigned long lastTimeSync  = 0;
time_t   timeOffset         = 0;

// ── Forward declarations ──────────────────────────────────────
void initWiFi();
void initESPNow();
void onDataReceived(const uint8_t *mac_addr, const uint8_t *data, int data_len);
void setupWebServer();
void saveDataToFile(const SensorData &data);
void uploadReadingRemote(const SensorData &data);
void handleRoot();
void handleConfig();
void handleSaveConfig();
void handleCalibration();
void handleSaveCalibration();
void handleData();
void handleDownload();
void handleDeleteData();
void handleStatus();
void handleStorageInfo();
void loadConfig();
void saveConfig();
void loadCalibrations();
void saveCalibrations();
void initTime();
time_t getCurrentTime();
String getFormattedTime(time_t t);
float calibratePH(const char* deviceName, float rawPH);
void ensureSecurityDefaults();

// ═══════════════════════════════════════════════════════════════
//  SETUP
// ═══════════════════════════════════════════════════════════════

void setup() {
  Serial.begin(115200);
  Serial.println("\n\npHloat Relay Starting...");

  if (!SPIFFS.begin(true)) {
    Serial.println("SPIFFS Mount Failed");
    return;
  }
  Serial.println("SPIFFS initialized");

  loadConfig();
  ensureSecurityDefaults();
  loadCalibrations();

  // Print MAC for sensor pairing
  WiFi.mode(WIFI_STA);
  Serial.print("Relay MAC Address: ");
  Serial.println(WiFi.macAddress());

  if (relayConfig.wifiEnabled) {
    initWiFi();
    initTime();
  }

  initESPNow();
  setupWebServer();

  // OTA updates require the same AP password used for config mode
  ElegantOTA.begin(&server, "phloat", relayConfig.apPassword);

  server.begin();
  Serial.println("Web server started on port 80");

  if (relayConfig.wifiEnabled) {
    Serial.print("Access web UI at: http://");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi disabled - starting AP mode for configuration");
    WiFi.mode(WIFI_AP);
    WiFi.softAP("pHloat-Relay", relayConfig.apPassword);
    Serial.print("AP IP: ");
    Serial.println(WiFi.softAPIP());
  }

  Serial.println("pHloat Relay ready!");
}

void loop() {
  server.handleClient();
  ElegantOTA.loop();

  if (relayConfig.wifiEnabled && timeInitialized) {
    if (millis() - lastTimeSync > 3600000) {
      initTime();
    }
  }

  delay(10);
}

// ═══════════════════════════════════════════════════════════════
//  WIFI & TIME
// ═══════════════════════════════════════════════════════════════

void initWiFi() {
  Serial.printf("Connecting to WiFi: %s\n", relayConfig.wifiSSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(relayConfig.wifiSSID, relayConfig.wifiPassword);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi connection failed!");
    relayConfig.wifiEnabled = false;
  }
}

void initTime() {
  configTime(relayConfig.timezoneOffset, 0, relayConfig.ntpServer);

  struct tm timeinfo;
  if (getLocalTime(&timeinfo)) {
    timeInitialized = true;
    lastTimeSync    = millis();
    Serial.println("Time synchronized with NTP");
    Serial.println(&timeinfo, "%A, %B %d %Y %H:%M:%S");
  } else {
    Serial.println("Failed to obtain time");
    timeInitialized = false;
  }
}

time_t getCurrentTime() {
  if (!timeInitialized) return 0;
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) return 0;
  return mktime(&timeinfo);
}

String getFormattedTime(time_t t) {
  struct tm *timeinfo = localtime(&t);
  char buffer[64];
  strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", timeinfo);
  return String(buffer);
}

// ═══════════════════════════════════════════════════════════════
//  ESP-NOW (encrypted)
// ═══════════════════════════════════════════════════════════════

void initESPNow() {
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  if (strlen(relayConfig.pmk) == 32) {
    if (phloat_apply_pmk(relayConfig.pmk)) {
      Serial.println("ESP-NOW PMK set (encryption enabled)");
    } else {
      Serial.println("ESP-NOW PMK invalid — running without encryption");
    }
  } else {
    Serial.println("ESP-NOW running without encryption (PMK not set)");
  }

  esp_now_register_recv_cb(onDataReceived);
  Serial.println("ESP-NOW initialized");
}

void onDataReceived(const uint8_t *mac_addr, const uint8_t *data, int data_len) {
  if (!phloat_valid_sensor_packet(data, data_len)) {
    Serial.printf("Invalid ESP-NOW packet (size=%d, expected %d)\n", data_len, (int)sizeof(SensorData));
    return;
  }

  if (!phloat_mac_allowed(preferences, mac_addr, true)) {
    return;
  }

  SensorData receivedData;
  memcpy(&receivedData, data, sizeof(SensorData));
  phloat_sanitize_device_name(receivedData.deviceName, receivedData.deviceName, sizeof(receivedData.deviceName));

  time_t relayTime = getCurrentTime();
  if (relayTime > 0) {
    receivedData.timestamp = (uint64_t)relayTime;
  }

  Serial.printf("\n--- Data Received from %s ---\n", receivedData.deviceName);
  Serial.printf("Raw pH: %.2f, Temp: %.2f°C, Reading #%lu\n",
                receivedData.pH, receivedData.temperature, receivedData.readingNumber);

  float calibratedPH = calibratePH(receivedData.deviceName, receivedData.pH);
  receivedData.pH = calibratedPH;
  Serial.printf("Calibrated pH: %.2f\n", calibratedPH);

  saveDataToFile(receivedData);

  if (relayConfig.wifiEnabled && relayConfig.sheetsEnabled) {
    uploadReadingRemote(receivedData);
  }

  Serial.println("---------------------------\n");
}

// ═══════════════════════════════════════════════════════════════
//  CALIBRATION — piecewise linear 3-point
// ═══════════════════════════════════════════════════════════════

float calibratePH(const char* deviceName, float rawPH) {
  for (int i = 0; i < numCalibratedSensors; i++) {
    if (strcmp(sensorCalibrations[i].deviceName, deviceName) == 0) {
      CalibrationData &cal = sensorCalibrations[i].cal;
      if (!cal.calibrated) return rawPH;

      float slopeLow  = cal.ph7_reading - cal.ph4_reading;
      float slopeHigh = cal.ph10_reading - cal.ph7_reading;

      if (rawPH <= cal.ph7_reading) {
        if (fabs(slopeLow) < 0.01) return rawPH;  // guard div-by-zero
        return 4.0f + (rawPH - cal.ph4_reading) * 3.0f / slopeLow;
      } else {
        if (fabs(slopeHigh) < 0.01) return rawPH;
        return 7.0f + (rawPH - cal.ph7_reading) * 3.0f / slopeHigh;
      }
    }
  }
  return rawPH;
}

// ═══════════════════════════════════════════════════════════════
//  DATA STORAGE
// ═══════════════════════════════════════════════════════════════

void saveDataToFile(const SensorData &data) {
  char safeName[32];
  phloat_sanitize_device_name(data.deviceName, safeName, sizeof(safeName));
  String filename = String(DATA_DIR) + "/" + safeName + "_";

  if (timeInitialized) {
    struct tm *timeinfo = localtime((time_t*)&data.timestamp);
    char dateStr[32];
    strftime(dateStr, sizeof(dateStr), "%Y%m%d", timeinfo);
    filename += dateStr;
  } else {
    filename += "pending";
  }
  filename += ".csv";

  bool fileExists = SPIFFS.exists(filename);

  File file = SPIFFS.open(filename, FILE_APPEND);
  if (!file) {
    Serial.println("Failed to open file for writing");
    return;
  }

  if (!fileExists) {
    file.println("Timestamp,Device,pH,Temperature,ReadingNumber");
  }

  String line;
  if (timeInitialized) {
    line += getFormattedTime(data.timestamp);
  } else {
    line += String(data.timestamp);
  }
  line += "," + String(safeName) + ","
       + String(data.pH, 2) + "," + String(data.temperature, 1) + ","
       + String(data.readingNumber);

  file.println(line);
  file.close();

  Serial.printf("Data saved to %s\n", filename.c_str());
}

// ═══════════════════════════════════════════════════════════════
//  REMOTE UPLOAD (Google Apps Script or Tilt Pi /api/ph)
// ═══════════════════════════════════════════════════════════════

String buildUploadPayload(const SensorData &data) {
  StaticJsonDocument<512> doc;
  doc["device"]        = data.deviceName;
  doc["pH"]            = String(data.pH, 2);
  doc["temperature"]   = String(data.temperature, 1);
  doc["timestamp"]     = timeInitialized ? getFormattedTime(data.timestamp) : String(data.timestamp);
  doc["readingNumber"] = data.readingNumber;

  String jsonData;
  serializeJson(doc, jsonData);
  return jsonData;
}

void uploadReadingRemote(const SensorData &data) {
  if (!relayConfig.sheetsEnabled || strlen(relayConfig.googleSheetURL) == 0) return;

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, skipping upload");
    return;
  }

  String url = relayConfig.googleSheetURL;
  phloat_normalize_upload_url(url);

  HTTPClient http;
  http.begin(url);

  String jsonData = buildUploadPayload(data);

  if (phloat_is_tiltpi_upload_url(url.c_str())) {
    Serial.println("Uploading to Tilt Pi /api/ph...");
  } else if (phloat_is_gas_upload_url(url.c_str())) {
    Serial.println("Uploading to Google Apps Script...");
  } else {
    Serial.println("Uploading to remote endpoint...");
  }

  http.addHeader("Content-Type", "application/json");
  if (strlen(relayConfig.uploadSecret) > 0) {
    http.addHeader(PHLOAT_UPLOAD_HEADER, relayConfig.uploadSecret);
  }

  int code = http.POST(jsonData);

  if (code > 0) {
    Serial.printf("Upload OK: %d — %s\n", code, http.getString().c_str());
  } else {
    Serial.printf("Upload failed: %s\n", http.errorToString(code).c_str());
  }

  http.end();
}

// ═══════════════════════════════════════════════════════════════
//  CONFIG PERSISTENCE
// ═══════════════════════════════════════════════════════════════

void loadConfig() {
  preferences.begin("relay-config", true);

  preferences.getString("wifiSSID",   relayConfig.wifiSSID,      sizeof(relayConfig.wifiSSID));
  preferences.getString("wifiPass",   relayConfig.wifiPassword,  sizeof(relayConfig.wifiPassword));
  preferences.getString("sheetURL",   relayConfig.googleSheetURL, sizeof(relayConfig.googleSheetURL));
  preferences.getString("apPassword", relayConfig.apPassword,    sizeof(relayConfig.apPassword));
  preferences.getString("pmk",        relayConfig.pmk,           sizeof(relayConfig.pmk));
  preferences.getString("uploadSecret", relayConfig.uploadSecret, sizeof(relayConfig.uploadSecret));

  relayConfig.wifiEnabled   = preferences.getBool("wifiEnabled",   false);
  relayConfig.sheetsEnabled = preferences.getBool("sheetsEnabled", false);

  preferences.getString("ntpServer", relayConfig.ntpServer, sizeof(relayConfig.ntpServer));
  if (strlen(relayConfig.ntpServer) == 0) {
    strlcpy(relayConfig.ntpServer, "pool.ntp.org", sizeof(relayConfig.ntpServer));
  }
  relayConfig.timezoneOffset = preferences.getInt("tzOffset", -18000);  // EST default

  preferences.end();

  Serial.println("Configuration loaded");
}

void ensureSecurityDefaults() {
  preferences.begin("relay-config", false);

  String apiKey = preferences.getString("apiKey", "");
  if (apiKey.length() == 0) {
    char key[33];
    phloat_generate_hex_token(key, sizeof(key));
    apiKey = key;
    preferences.putString("apiKey", apiKey);
    Serial.println("*** SECURITY: Generated API key (save this): " + apiKey);
  }

  String uploadSecret = preferences.getString("uploadSecret", "");
  if (uploadSecret.length() == 0) {
    uploadSecret = apiKey;
    preferences.putString("uploadSecret", uploadSecret);
  }
  strlcpy(relayConfig.uploadSecret, uploadSecret.c_str(), sizeof(relayConfig.uploadSecret));

  if (strlen(relayConfig.apPassword) == 0 || phloat_is_weak_password(relayConfig.apPassword)) {
    char pass[17];
    phloat_generate_hex_token(pass, sizeof(pass));
    pass[16] = '\0';
    preferences.putString("apPassword", pass);
    strlcpy(relayConfig.apPassword, pass, sizeof(relayConfig.apPassword));
    Serial.println("*** SECURITY: Generated AP password (save this): " + String(pass));
  }

  preferences.end();
}

void saveConfig() {
  preferences.begin("relay-config", false);

  preferences.putString("wifiSSID",   relayConfig.wifiSSID);
  preferences.putString("wifiPass",   relayConfig.wifiPassword);
  preferences.putString("sheetURL",   relayConfig.googleSheetURL);
  preferences.putString("apPassword", relayConfig.apPassword);
  preferences.putString("pmk",        relayConfig.pmk);
  preferences.putString("uploadSecret", relayConfig.uploadSecret);
  preferences.putBool("wifiEnabled",   relayConfig.wifiEnabled);
  preferences.putBool("sheetsEnabled", relayConfig.sheetsEnabled);
  preferences.putString("ntpServer",  relayConfig.ntpServer);
  preferences.putInt("tzOffset",      relayConfig.timezoneOffset);

  preferences.end();

  Serial.println("Configuration saved");
}

void loadCalibrations() {
  File file = SPIFFS.open(CALIBRATION_FILE, FILE_READ);
  if (!file) {
    Serial.println("No calibration file found");
    numCalibratedSensors = 0;
    return;
  }

  StaticJsonDocument<2048> doc;
  DeserializationError error = deserializeJson(doc, file);
  file.close();

  if (error) {
    Serial.println("Failed to parse calibration file");
    numCalibratedSensors = 0;
    return;
  }

  JsonArray sensors = doc["sensors"];
  numCalibratedSensors = 0;

  for (JsonObject sensor : sensors) {
    if (numCalibratedSensors >= MAX_SENSORS) break;
    strlcpy(sensorCalibrations[numCalibratedSensors].deviceName,
            sensor["device"], sizeof(sensorCalibrations[0].deviceName));
    sensorCalibrations[numCalibratedSensors].cal.ph4_reading     = sensor["ph4"];
    sensorCalibrations[numCalibratedSensors].cal.ph7_reading     = sensor["ph7"];
    sensorCalibrations[numCalibratedSensors].cal.ph10_reading    = sensor["ph10"];
    sensorCalibrations[numCalibratedSensors].cal.calibrated      = sensor["calibrated"];
    sensorCalibrations[numCalibratedSensors].cal.calibrationTime = sensor["time"];
    numCalibratedSensors++;
  }

  Serial.printf("Loaded %d sensor calibrations\n", numCalibratedSensors);
}

void saveCalibrations() {
  StaticJsonDocument<2048> doc;
  JsonArray sensors = doc.createNestedArray("sensors");

  for (int i = 0; i < numCalibratedSensors; i++) {
    JsonObject s = sensors.createNestedObject();
    s["device"]     = sensorCalibrations[i].deviceName;
    s["ph4"]        = sensorCalibrations[i].cal.ph4_reading;
    s["ph7"]        = sensorCalibrations[i].cal.ph7_reading;
    s["ph10"]       = sensorCalibrations[i].cal.ph10_reading;
    s["calibrated"] = sensorCalibrations[i].cal.calibrated;
    s["time"]       = sensorCalibrations[i].cal.calibrationTime;
  }

  File file = SPIFFS.open(CALIBRATION_FILE, FILE_WRITE);
  if (!file) {
    Serial.println("Failed to save calibrations");
    return;
  }

  serializeJson(doc, file);
  file.close();

  Serial.println("Calibrations saved");
}

// ═══════════════════════════════════════════════════════════════
//  WEB SERVER ROUTES
// ═══════════════════════════════════════════════════════════════

void setupWebServer() {
  server.on("/",               handleRoot);
  server.on("/config",         handleConfig);
  server.on("/saveConfig",     HTTP_POST, handleSaveConfig);
  server.on("/calibration",    handleCalibration);
  server.on("/saveCalibration", HTTP_POST, handleSaveCalibration);
  server.on("/data",           handleData);
  server.on("/download",       handleDownload);
  server.on("/deleteData",     HTTP_POST, handleDeleteData);
  server.on("/status",         handleStatus);
  server.on("/storageInfo",    handleStorageInfo);
}

// ── Web UI handlers are in pHloat_Relay_WebUI.ino ──────────────
