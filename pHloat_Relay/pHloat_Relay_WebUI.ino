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
  String apiKey = preferences.getString("apiKey", "");
  preferences.end();

  String html = phloat_load_template(TPL_CONFIG);
  phloat_tpl_replace(html, "{{WIFI_SSID}}", String(relayConfig.wifiSSID));
  phloat_tpl_replace(html, "{{NTP_SERVER}}", String(relayConfig.ntpServer));
  phloat_tpl_replace(html, "{{TIMEZONE_OFFSET}}", String(relayConfig.timezoneOffset));
  phloat_tpl_replace(html, "{{UPLOAD_URL}}", String(relayConfig.googleSheetURL));
  phloat_tpl_replace(html, "{{AP_PASSWORD}}", String(relayConfig.apPassword));
  phloat_tpl_replace(html, "{{PMK}}", String(relayConfig.pmk));
  phloat_tpl_replace(html, "{{API_KEY}}", apiKey);
  phloat_tpl_replace(html, "{{UPLOAD_SECRET}}", String(relayConfig.uploadSecret));
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
  strlcpy(relayConfig.pmk, doc["pmk"] | "", sizeof(relayConfig.pmk));

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
//  CALIBRATION PAGE (/calibration)
// ═══════════════════════════════════════════════════════════════

void handleCalibration() {
  // ── SPIFFS-safe sensor discovery: iterate root, filter /data/*.csv ──
  String sensorList = "[";
  File root = SPIFFS.open("/");
  bool first = true;

  while (true) {
    File f = root.openNextFile();
    if (!f) break;

    String name = String(f.name());
    f.close();

    // Only process CSV files in /data/
    if (!name.startsWith("/data/") || !name.endsWith(".csv")) continue;

    // Extract device name: "/data/Fermenter-1_20260429.csv" → "Fermenter-1"
    int slash    = name.lastIndexOf('/');
    int under    = name.indexOf('_', slash + 1);
    if (under <= slash) continue;

    String dev = name.substring(slash + 1, under);

    // Deduplicate
    if (sensorList.indexOf("\"" + dev + "\"") >= 0) continue;

    if (!first) sensorList += ",";
    sensorList += "\"" + dev + "\"";
    first = false;
  }
  root.close();
  sensorList += "]";

  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>pH Sensor Calibration</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 900px; margin: 20px auto;
           padding: 20px; background: #f5f5f5; }
    .container { background: white; padding: 30px; border-radius: 10px;
                 box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    h1 { color: #333; border-bottom: 3px solid #667eea; padding-bottom: 10px; }
    .calibration-steps { background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }
    .calibration-steps ol { margin-left: 20px; }
    .calibration-steps li { margin: 10px 0; line-height: 1.6; }
    label { display: block; margin-top: 15px; font-weight: bold; color: #555; }
    select, input { width: 100%; padding: 10px; margin-top: 5px;
                    border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
    .reading-group { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }
    .reading-box { background: #f9f9f9; padding: 15px; border-radius: 8px; border: 2px solid #ddd; }
    .reading-box label { margin-top: 0; color: #667eea; }
    button { width: 100%; padding: 12px; margin-top: 20px; background: #667eea;
             color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
    button:hover { background: #764ba2; }
    .back-link { display: inline-block; margin-bottom: 20px; color: #667eea; text-decoration: none; }
    .success { background: #4CAF50; color: white; padding: 15px; border-radius: 5px;
               margin: 20px 0; display: none; }
  </style>
</head>
<body>
  <a href="/" class="back-link">&larr; Back to Dashboard</a>

  <div class="container">
    <h1>🎯 pH Sensor Calibration</h1>

    <div class="calibration-steps">
      <strong>3-Point Calibration Procedure:</strong>
      <ol>
        <li>Select the sensor you want to calibrate</li>
        <li>Place sensor in pH 7.0 buffer, wait for stable reading, note the value</li>
        <li>Rinse, place in pH 4.0 buffer, wait for stable reading, note the value</li>
        <li>Rinse, place in pH 10.0 buffer, wait for stable reading, note the value</li>
        <li>Enter all three readings below and click "Save Calibration"</li>
      </ol>
    </div>

    <div class="success" id="successMsg">Calibration saved!</div>

    <form id="calibrationForm">
      <label for="sensorSelect">Select Sensor:</label>
      <select id="sensorSelect" name="sensor" required>
        <option value="">-- Choose a sensor --</option>
      </select>

      <div class="reading-group">
        <div class="reading-box">
          <label for="ph4">pH 4.0 Buffer Reading:</label>
          <input type="number" step="0.01" id="ph4" name="ph4"
                 placeholder="e.g., 4.02" min="0" max="13" required>
        </div>
        <div class="reading-box">
          <label for="ph7">pH 7.0 Buffer Reading:</label>
          <input type="number" step="0.01" id="ph7" name="ph7"
                 placeholder="e.g., 7.01" min="0" max="13" required>
        </div>
        <div class="reading-box">
          <label for="ph10">pH 10.0 Buffer Reading:</label>
          <input type="number" step="0.01" id="ph10" name="ph10"
                 placeholder="e.g., 10.03" min="0" max="13" required>
        </div>
      </div>

      <button type="submit">Save Calibration</button>
    </form>
  </div>

  <script>
    const sensors = )rawliteral" + sensorList + R"rawliteral(;
    const sel = document.getElementById('sensorSelect');
    sensors.forEach(s => {
      const o = document.createElement('option');
      o.value = s; o.textContent = s;
      sel.appendChild(o);
    });

    const apiKey = sessionStorage.getItem('apiKey') || '';

    document.getElementById('calibrationForm').addEventListener('submit', function(e) {
      e.preventDefault();
      const headers = {'Content-Type': 'application/json'};
      if (apiKey) headers['X-API-Key'] = apiKey;

      fetch('/saveCalibration', {
        method: 'POST', headers: headers,
        body: JSON.stringify({
          sensor: document.getElementById('sensorSelect').value,
          ph4:    parseFloat(document.getElementById('ph4').value),
          ph7:    parseFloat(document.getElementById('ph7').value),
          ph10:   parseFloat(document.getElementById('ph10').value)
        })
      })
      .then(r => r.json())
      .then(result => {
        if (result.success) {
          document.getElementById('successMsg').style.display = 'block';
          setTimeout(() => { document.getElementById('successMsg').style.display = 'none'; }, 3000);
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
//  DATA PAGE (/data)
// ═══════════════════════════════════════════════════════════════

void handleData() {
  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>pHloat Data Review</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 1000px; margin: 20px auto;
           padding: 20px; background: #f5f5f5; }
    .container { background: white; padding: 30px; border-radius: 10px;
                 box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    h1 { color: #333; border-bottom: 3px solid #667eea; padding-bottom: 10px; }
    .file-list { margin: 20px 0; }
    .file-item { background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 8px;
                 display: flex; justify-content: space-between; align-items: center;
                 border: 1px solid #ddd; }
    .file-info { flex-grow: 1; }
    .file-name { font-weight: bold; color: #333; font-size: 1.1em; }
    .file-size { color: #888; font-size: 0.9em; margin-top: 5px; }
    .file-actions { display: flex; gap: 10px; }
    .btn { padding: 8px 20px; border: none; border-radius: 5px; cursor: pointer;
           font-size: 14px; text-decoration: none; display: inline-block; }
    .btn-download { background: #4CAF50; color: white; }
    .btn-delete { background: #f44336; color: white; }
    .btn:hover { opacity: 0.8; }
    .back-link { display: inline-block; margin-bottom: 20px; color: #667eea; text-decoration: none; }
    .storage-warning { background: #fff3cd; border: 2px solid #ffc107;
                       padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    .storage-critical { background: #f8d7da; border: 2px solid #f44336; }
  </style>
</head>
<body>
  <a href="/" class="back-link">&larr; Back to Dashboard</a>

  <div class="container">
    <h1>📊 Data Review & Management</h1>

    <div id="storageWarning" style="display:none;">
      <p><strong>⚠️ Storage Alert:</strong> <span id="warningText"></span></p>
    </div>

    <div class="file-list" id="fileList"><p>Loading files...</p></div>
  </div>

  <script>
    const apiKey = sessionStorage.getItem('apiKey') || '';

    function loadFiles() {
      fetch('/storageInfo').then(r => r.json()).then(data => {
        const warn = document.getElementById('storageWarning');
        const warnText = document.getElementById('warningText');

        if (data.free < 524288) {
          warn.style.display = 'block';
          if (data.free < 102400) {
            warn.className = 'storage-critical';
            warnText.textContent = 'Critical! Only ' + (data.free / 1024).toFixed(1)
                                 + ' KB free. Delete old data immediately.';
          } else {
            warn.className = 'storage-warning';
            warnText.textContent = 'Low storage: ' + (data.free / 1024).toFixed(1)
                                 + ' KB free. Consider deleting old files.';
          }
        }

        if (data.files && data.files.length > 0) {
          let h = '';
          data.files.forEach(f => {
            h += '<div class="file-item"><div class="file-info">'
               + '<div class="file-name">' + f.name + '</div>'
               + '<div class="file-size">' + (f.size / 1024).toFixed(2) + ' KB</div>'
               + '</div><div class="file-actions">'
               + '<a href="/download?file=' + encodeURIComponent(f.path)
               + '" class="btn btn-download">Download</a>'
               + '<button onclick="del(\'' + f.path + '\')" class="btn btn-delete">Delete</button>'
               + '</div></div>';
          });
          document.getElementById('fileList').innerHTML = h;
        } else {
          document.getElementById('fileList').innerHTML = '<p>No data files found.</p>';
        }
      });
    }

    function del(path) {
      if (!confirm('Delete this file?')) return;

      const headers = {'Content-Type': 'application/json'};
      if (apiKey) headers['X-API-Key'] = apiKey;

      fetch('/deleteData', {
        method: 'POST', headers: headers,
        body: JSON.stringify({file: path})
      })
      .then(r => r.json())
      .then(result => {
        if (result.success) loadFiles(); else alert('Delete failed');
      });
    }

    loadFiles();
  </script>
</body>
</html>
)rawliteral";

  server.send(200, "text/html", html);
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
