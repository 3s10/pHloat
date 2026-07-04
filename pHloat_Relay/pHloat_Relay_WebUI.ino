/*
 * pHloat_Relay_WebUI.ino
 * v3.3 — HTML templates in web/relay/*.html (see scripts/embed_web_ui.py)
 *
 * Web interface handlers for pHloat Relay.
 * Include this file after pHloat_Relay.ino.
 */

#include "web_ui_templates.h"
#include "phloat_web.h"

// ── Shared auth check for write endpoints ─────────────────────
bool requireAuth() {
  if (!server.hasHeader("X-API-Key")) {
    server.send(401, "application/json", "{\"success\":false,\"error\":\"API key required\"}");
    return false;
  }
  preferences.begin("relay-config", true);
  String storedKey = preferences.getString("apiKey", "");
  preferences.end();

  if (storedKey.length() == 0) {
    server.send(503, "application/json", "{\"success\":false,\"error\":\"API key not initialized\"}");
    return false;
  }

  String supplied = server.header("X-API-Key");
  if (supplied != storedKey) {
    server.send(403, "application/json", "{\"success\":false,\"error\":\"Invalid API key\"}");
    return false;
  }
  return true;
}

// ═══════════════════════════════════════════════════════════════
//  DASHBOARD (/)
// ═══════════════════════════════════════════════════════════════

void handleRoot() {
  server.send(200, "text/html", phloat_load_template(TPL_DASHBOARD));
}

// ═══════════════════════════════════════════════════════════════
//  CONFIGURATION PAGE (/config)
// ═══════════════════════════════════════════════════════════════

void handleConfig() {
  preferences.begin("relay-config", true);
  bool haveApiKey = preferences.getString("apiKey", "").length() > 0;
  preferences.end();

  String html = phloat_load_template(TPL_CONFIG);
  phloat_tpl_replace(html, "{{WIFI_SSID}}", String(relayConfig.wifiSSID));
  phloat_tpl_replace(html, "{{NTP_SERVER}}", String(relayConfig.ntpServer));
  phloat_tpl_replace(html, "{{TIMEZONE_OFFSET}}", String(relayConfig.timezoneOffset));
  phloat_tpl_replace(html, "{{UPLOAD_URL}}", String(relayConfig.googleSheetURL));
  // Secrets are NEVER sent to the browser. The fields render blank; a blank
  // field on save means "keep the stored value" (see handleSaveConfig). A
  // status hint tells the operator whether each secret is already set.
  const char *keepHint = "configured — leave blank to keep";
  phloat_tpl_replace(html, "{{AP_PASSWORD}}", "");
  phloat_tpl_replace(html, "{{PMK}}", "");
  phloat_tpl_replace(html, "{{API_KEY}}", "");
  phloat_tpl_replace(html, "{{UPLOAD_SECRET}}", "");
  phloat_tpl_replace(html, "{{AP_PASSWORD_SET}}", strlen(relayConfig.apPassword) ? keepHint : "not set");
  phloat_tpl_replace(html, "{{PMK_SET}}", strlen(relayConfig.pmk) ? keepHint : "not set");
  phloat_tpl_replace(html, "{{API_KEY_SET}}", haveApiKey ? keepHint : "not set");
  phloat_tpl_replace(html, "{{UPLOAD_SECRET_SET}}", strlen(relayConfig.uploadSecret) ? keepHint : "not set");
  phloat_tpl_replace(html, "{{WIFI_ENABLED}}", relayConfig.wifiEnabled ? "true" : "false");
  phloat_tpl_replace(html, "{{SHEETS_ENABLED}}", relayConfig.sheetsEnabled ? "true" : "false");
  server.send(200, "text/html", html);
}

// ═══════════════════════════════════════════════════════════════
//  CALIBRATION PAGE (/calibration)
// ═══════════════════════════════════════════════════════════════

void handleCalibration() {
  String sensorList = "[";
  File root = SPIFFS.open("/");
  bool first = true;

  while (true) {
    File f = root.openNextFile();
    if (!f) break;

    String name = String(f.name());
    f.close();

    if (!name.startsWith("/data/") || !name.endsWith(".csv")) continue;

    int slash = name.lastIndexOf('/');
    int under = name.indexOf('_', slash + 1);
    if (under <= slash) continue;

    String dev = name.substring(slash + 1, under);
    if (sensorList.indexOf("\"" + dev + "\"") >= 0) continue;

    if (!first) sensorList += ",";
    sensorList += "\"" + dev + "\"";
    first = false;
  }
  root.close();
  sensorList += "]";

  String html = phloat_load_template(TPL_CALIBRATION);
  phloat_tpl_replace(html, "{{SENSOR_LIST_JSON}}", sensorList);
  server.send(200, "text/html", html);
}

// ═══════════════════════════════════════════════════════════════
//  DATA PAGE (/data)
// ═══════════════════════════════════════════════════════════════

void handleData() {
  server.send(200, "text/html", phloat_load_template(TPL_DATA));
}

// ═══════════════════════════════════════════════════════════════
//  SAVE CONFIG (/saveConfig — JSON POST)
// ═══════════════════════════════════════════════════════════════

void handleSaveConfig() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"success\":false,\"error\":\"No data\"}");
    return;
  }

  String body = server.arg("plain");

  StaticJsonDocument<1024> doc;
  DeserializationError error = deserializeJson(doc, body);
  if (error) {
    server.send(400, "application/json", "{\"success\":false}");
    return;
  }

  // ── Auth check ──
  if (!requireAuth()) return;

  // ── WiFi ──
  relayConfig.wifiEnabled   = doc["wifiEnabled"];
  strlcpy(relayConfig.wifiSSID, doc["wifiSSID"] | "", sizeof(relayConfig.wifiSSID));
  const char* newPass = doc["wifiPassword"] | "";
  if (strlen(newPass) > 0) {
    strlcpy(relayConfig.wifiPassword, newPass, sizeof(relayConfig.wifiPassword));
  }

  // ── Time ──
  strlcpy(relayConfig.ntpServer, doc["ntpServer"] | "pool.ntp.org", sizeof(relayConfig.ntpServer));
  relayConfig.timezoneOffset = doc["timezoneOffset"] | -18000;

  // ── Sheets ──
  relayConfig.sheetsEnabled = doc["sheetsEnabled"];
  strlcpy(relayConfig.googleSheetURL, doc["googleSheetURL"] | "", sizeof(relayConfig.googleSheetURL));

  // ── Security ──
  const char* apPassword = doc["apPassword"] | "";
  if (strlen(apPassword) >= PHLOAT_MIN_AP_PASSWORD_LEN && !phloat_is_weak_password(apPassword)) {
    strlcpy(relayConfig.apPassword, apPassword, sizeof(relayConfig.apPassword));
  }
  // Blank secret fields mean "keep current" — do not wipe the stored PMK.
  const char* newPmk = doc["pmk"] | "";
  if (strlen(newPmk) > 0) {
    strlcpy(relayConfig.pmk, newPmk, sizeof(relayConfig.pmk));
  }

  const char* apiKey = doc["apiKey"] | "";
  const char* uploadSecret = doc["uploadSecret"] | "";
  preferences.begin("relay-config", false);
  if (strlen(apiKey) > 0) {
    preferences.putString("apiKey", apiKey);
  }
  if (strlen(uploadSecret) > 0) {
    strlcpy(relayConfig.uploadSecret, uploadSecret, sizeof(relayConfig.uploadSecret));
    preferences.putString("uploadSecret", uploadSecret);
  } else if (strlen(apiKey) > 0) {
    strlcpy(relayConfig.uploadSecret, apiKey, sizeof(relayConfig.uploadSecret));
    preferences.putString("uploadSecret", apiKey);
  }
  preferences.end();

  saveConfig();
  server.send(200, "application/json", "{\"success\":true}");

  delay(1000);
  ESP.restart();
}

// ═══════════════════════════════════════════════════════════════
//  SAVE CALIBRATION (/saveCalibration — JSON POST)
// ═══════════════════════════════════════════════════════════════

void handleSaveCalibration() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"success\":false}");
    return;
  }

  if (!requireAuth()) return;

  String body = server.arg("plain");

  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, body);
  if (error) {
    server.send(400, "application/json", "{\"success\":false}");
    return;
  }

  const char* sensorName = doc["sensor"];
  float ph4  = doc["ph4"];
  float ph7  = doc["ph7"];
  float ph10 = doc["ph10"];

  // Validate: readings must be in ascending order (ph4 < ph7 < ph10)
  if (!(ph4 < ph7 && ph7 < ph10)) {
    server.send(400, "application/json",
      "{\"success\":false,\"error\":\"Readings must be in ascending order (pH4 < pH7 < pH10)\"}");
    return;
  }

  // Find or create calibration entry
  int idx = -1;
  for (int i = 0; i < numCalibratedSensors; i++) {
    if (strcmp(sensorCalibrations[i].deviceName, sensorName) == 0) {
      idx = i; break;
    }
  }

  if (idx == -1 && numCalibratedSensors < MAX_SENSORS) {
    idx = numCalibratedSensors++;
    strlcpy(sensorCalibrations[idx].deviceName, sensorName,
            sizeof(sensorCalibrations[idx].deviceName));
  }

  if (idx >= 0) {
    sensorCalibrations[idx].cal.ph4_reading     = ph4;
    sensorCalibrations[idx].cal.ph7_reading     = ph7;
    sensorCalibrations[idx].cal.ph10_reading    = ph10;
    sensorCalibrations[idx].cal.calibrated      = true;
    sensorCalibrations[idx].cal.calibrationTime = getCurrentTime();

    saveCalibrations();

    Serial.printf("Calibration saved for %s: pH4=%.2f, pH7=%.2f, pH10=%.2f\n",
                  sensorName, ph4, ph7, ph10);

    server.send(200, "application/json", "{\"success\":true}");
  } else {
    server.send(500, "application/json",
      "{\"success\":false,\"error\":\"Max sensors reached\"}");
  }
}

// ═══════════════════════════════════════════════════════════════
//  FILE DOWNLOAD (/download?file=...)
// ═══════════════════════════════════════════════════════════════

void handleDownload() {
  if (!server.hasArg("file")) {
    server.send(400, "text/plain", "No file specified");
    return;
  }

  String filepath = server.arg("file");

  // Prevent directory traversal
  if (filepath.indexOf("..") >= 0 || !filepath.startsWith("/")) {
    server.send(403, "text/plain", "Forbidden");
    return;
  }

  if (!SPIFFS.exists(filepath)) {
    server.send(404, "text/plain", "File not found");
    return;
  }

  File file = SPIFFS.open(filepath, FILE_READ);
  if (!file) {
    server.send(500, "text/plain", "Failed to open file");
    return;
  }

  server.streamFile(file, "text/csv");
  file.close();
}

// ═══════════════════════════════════════════════════════════════
//  DELETE FILE (/deleteData — JSON POST)
// ═══════════════════════════════════════════════════════════════

void handleDeleteData() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"success\":false}");
    return;
  }

  if (!requireAuth()) return;

  String body = server.arg("plain");

  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, body);
  if (error) {
    server.send(400, "application/json", "{\"success\":false}");
    return;
  }

  const char* filepath = doc["file"];
  if (!filepath || String(filepath).indexOf("..") >= 0) {
    server.send(403, "application/json", "{\"success\":false,\"error\":\"Forbidden\"}");
    return;
  }

  if (SPIFFS.remove(filepath)) {
    Serial.printf("Deleted: %s\n", filepath);
    server.send(200, "application/json", "{\"success\":true}");
  } else {
    server.send(500, "application/json", "{\"success\":false}");
  }
}

// ═══════════════════════════════════════════════════════════════
//  STATUS & STORAGE ENDPOINTS
// ═══════════════════════════════════════════════════════════════

void handleStatus() {
  StaticJsonDocument<512> doc;

  doc["mac"]           = WiFi.macAddress();
  doc["wifiConnected"] = (WiFi.status() == WL_CONNECTED);
  doc["wifiSSID"]      = relayConfig.wifiSSID;
  doc["sheetsEnabled"] = relayConfig.sheetsEnabled;
  doc["timeSync"]      = timeInitialized;

  if (WiFi.status() == WL_CONNECTED) {
    doc["ip"] = WiFi.localIP().toString();
  }

  String json;
  serializeJson(doc, json);
  server.send(200, "application/json", json);
}

void handleStorageInfo() {
  size_t total = SPIFFS.totalBytes();
  size_t used  = SPIFFS.usedBytes();
  size_t free  = total - used;

  StaticJsonDocument<2048> doc;
  doc["total"] = total;
  doc["used"]  = used;
  doc["free"]  = free;

  // ── SPIFFS-safe: iterate root, filter /data/ files ──
  JsonArray files = doc.createNestedArray("files");
  File root = SPIFFS.open("/");
  int fileCount = 0;

  while (true) {
    File f = root.openNextFile();
    if (!f) break;

    String path = String(f.name());

    // Only report data files, skip directories and non-data files
    if (path.startsWith("/data/") && !path.endsWith("/")) {
      JsonObject fo = files.createNestedObject();
      fo["name"] = path.substring(path.lastIndexOf('/') + 1);
      fo["path"] = path;
      fo["size"] = f.size();
      fileCount++;
    }
    f.close();
  }
  root.close();

  doc["fileCount"] = fileCount;

  String json;
  serializeJson(doc, json);
  server.send(200, "application/json", json);
}
