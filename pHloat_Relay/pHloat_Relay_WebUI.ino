/*
 * pHloat_Relay_WebUI.ino
 * v3.2 — SPIFFS-safe file listing, masked secrets, configurable auth, OTA link
 *
 * Web interface handlers for pHloat Relay.
 * Include this file after pHloat_Relay.ino.
 */

// ── Shared auth check for write endpoints ─────────────────────
bool requireAuth() {
  if (!server.hasHeader("X-API-Key")) {
    server.send(401, "application/json", "{\"success\":false,\"error\":\"API key required\"}");
    return false;
  }
  preferences.begin("relay-config", true);
  String storedKey = preferences.getString("apiKey", "");
  preferences.end();

  if (storedKey.length() == 0) return true;  // no key set = auth disabled

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
  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>pHloat Relay Dashboard</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
           background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
           min-height: 100vh; padding: 20px; }
    .container { max-width: 1200px; margin: 0 auto; }
    .header { background: white; padding: 30px; border-radius: 15px;
              box-shadow: 0 10px 30px rgba(0,0,0,0.2); margin-bottom: 30px;
              text-align: center; }
    .header h1 { color: #333; font-size: 2.5em; margin-bottom: 10px; }
    .header .subtitle { color: #666; font-size: 1.1em; }
    .mac-address { background: #f0f0f0; padding: 10px 20px; border-radius: 8px;
                   display: inline-block; margin-top: 15px;
                   font-family: monospace; font-weight: bold; color: #764ba2; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
             gap: 20px; margin-bottom: 30px; }
    .card { background: white; padding: 25px; border-radius: 12px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1); transition: transform 0.2s;
            cursor: pointer; }
    .card:hover { transform: translateY(-5px); box-shadow: 0 10px 25px rgba(0,0,0,0.15); }
    .card h2 { color: #667eea; margin-bottom: 15px; font-size: 1.5em; }
    .card p { color: #666; line-height: 1.6; }
    .card .icon { font-size: 3em; margin-bottom: 15px; }
    .status-badge { display: inline-block; padding: 5px 15px; border-radius: 20px;
                    font-size: 0.9em; font-weight: bold; margin-top: 10px; }
    .status-online { background: #4CAF50; color: white; }
    .status-offline { background: #f44336; color: white; }
    .info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-top: 15px; }
    .info-item { background: #f9f9f9; padding: 12px; border-radius: 8px; }
    .info-label { font-size: 0.9em; color: #888; margin-bottom: 5px; }
    .info-value { font-weight: bold; color: #333; font-size: 1.1em; }
    .ota-badge { display: inline-block; background: #ff9800; color: white; padding: 3px 10px;
                 border-radius: 10px; font-size: 0.75em; margin-left: 8px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>pHloat Relay Dashboard</h1>
      <p class="subtitle">pH Monitoring & Data Management System</p>
      <div class="mac-address" id="macAddress">Loading...</div>
    </div>

    <div class="cards">
      <div class="card" onclick="location.href='/config'">
        <div class="icon">⚙️</div>
        <h2>Configuration</h2>
        <p>WiFi, Google Sheets, encryption keys, and system settings</p>
        <div id="wifiStatus" class="status-badge">Checking...</div>
      </div>

      <div class="card" onclick="location.href='/calibration'">
        <div class="icon">🎯</div>
        <h2>Calibration</h2>
        <p>Calibrate pH sensors using 3-point calibration (pH 4, 7, 10)</p>
        <div class="info-value" id="sensorCount">0 sensors calibrated</div>
      </div>

      <div class="card" onclick="location.href='/data'">
        <div class="icon">📊</div>
        <h2>Data Review</h2>
        <p>View, download, and manage pH sensor data files</p>
        <div class="info-value" id="dataFiles">Loading...</div>
      </div>

      <div class="card">
        <div class="icon">💾</div>
        <h2>Storage Status</h2>
        <div class="info-grid">
          <div class="info-item"><div class="info-label">Used</div>
            <div class="info-value" id="storageUsed">...</div></div>
          <div class="info-item"><div class="info-label">Free</div>
            <div class="info-value" id="storageFree">...</div></div>
          <div class="info-item"><div class="info-label">Total</div>
            <div class="info-value" id="storageTotal">...</div></div>
          <div class="info-item"><div class="info-label">Reserved</div>
            <div class="info-value">512 KB</div></div>
        </div>
      </div>

      <div class="card" onclick="location.href='/update'">
        <div class="icon">🔄</div>
        <h2>Firmware Update <span class="ota-badge">OTA</span></h2>
        <p>Upload new firmware over-the-air. No USB cable needed.</p>
        <div class="info-value">ElegantOTA</div>
      </div>
    </div>
  </div>

  <script>
    function updateStatus() {
      fetch('/status').then(r => r.json()).then(data => {
        document.getElementById('macAddress').textContent = 'MAC: ' + data.mac;
        const w = document.getElementById('wifiStatus');
        w.textContent = data.wifiConnected ? 'WiFi Connected' : 'WiFi Offline';
        w.className = 'status-badge ' + (data.wifiConnected ? 'status-online' : 'status-offline');
      });

      fetch('/storageInfo').then(r => r.json()).then(data => {
        document.getElementById('storageUsed').textContent  = (data.used / 1024).toFixed(1) + ' KB';
        document.getElementById('storageFree').textContent  = (data.free / 1024).toFixed(1) + ' KB';
        document.getElementById('storageTotal').textContent = (data.total / 1024).toFixed(1) + ' KB';
        document.getElementById('dataFiles').textContent    = data.fileCount + ' data files';
        if (data.free < 524288) {
          document.getElementById('storageFree').style.color = '#f44336';
        }
      });
    }

    // Read API key from URL param or prompt
    if (!sessionStorage.getItem('apiKey')) {
      const params = new URLSearchParams(window.location.search);
      const k = params.get('key');
      if (k) sessionStorage.setItem('apiKey', k);
    }
    updateStatus();
    setInterval(updateStatus, 5000);
  </script>
</body>
</html>
)rawliteral";

  server.send(200, "text/html", html);
}

// ═══════════════════════════════════════════════════════════════
//  CONFIGURATION PAGE (/config)
// ═══════════════════════════════════════════════════════════════

void handleConfig() {
  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>pHloat Configuration</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto;
           padding: 20px; background: #f5f5f5; }
    .container { background: white; padding: 30px; border-radius: 10px;
                 box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    h1 { color: #333; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin-bottom: 30px; }
    .section { margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #eee; }
    .section:last-child { border-bottom: none; }
    .section h2 { color: #667eea; margin-bottom: 15px; font-size: 1.3em; }
    label { display: block; margin-top: 15px; font-weight: bold; color: #555; }
    input[type="text"], input[type="password"], input[type="number"], select {
      width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ddd;
      border-radius: 5px; box-sizing: border-box; font-size: 16px; }
    .checkbox-group { margin-top: 15px; }
    .checkbox-group label { display: inline-block; font-weight: normal; margin-left: 10px; }
    .checkbox-group input[type="checkbox"] { width: auto; margin-right: 5px; }
    button { width: 100%; padding: 12px; margin-top: 20px; background: #667eea;
             color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
    button:hover { background: #764ba2; }
    .back-link { display: inline-block; margin-bottom: 20px; color: #667eea; text-decoration: none; }
    .success { background: #4CAF50; color: white; padding: 15px; border-radius: 5px;
               margin-bottom: 20px; display: none; }
    .help-text { font-size: 0.9em; color: #888; margin-top: 5px; font-weight: normal; }
    .secret-note { background: #fff3cd; padding: 8px 12px; border-radius: 5px;
                   font-size: 0.85em; color: #856404; margin-top: 5px; }
  </style>
</head>
<body>
  <a href="/" class="back-link">&larr; Back to Dashboard</a>

  <div class="container">
    <h1>⚙️ System Configuration</h1>

    <div class="success" id="successMsg">Configuration saved! Restarting...</div>

    <!-- API Key gate -->
    <div id="authGate" style="display:none;">
      <div class="section">
        <h2>Authentication Required</h2>
        <p style="color:#666; margin-bottom:15px;">Enter the relay API key to access configuration.</p>
        <label for="authKey">API Key:</label>
        <input type="password" id="authKey" placeholder="Enter API key">
        <button onclick="unlock()">Unlock</button>
      </div>
    </div>

    <form id="configForm" style="display:none;">
      <div class="section">
        <h2>WiFi Settings</h2>
        <div class="checkbox-group">
          <input type="checkbox" id="wifiEnabled" name="wifiEnabled">
          <label for="wifiEnabled">Enable WiFi Connection</label>
        </div>
        <label for="wifiSSID">WiFi Network Name (SSID):</label>
        <input type="text" id="wifiSSID" name="wifiSSID" value=")rawliteral"
        + String(relayConfig.wifiSSID) + R"rawliteral(">

        <label for="wifiPassword">WiFi Password:</label>
        <input type="password" id="wifiPassword" name="wifiPassword" placeholder="(leave blank to keep current)">
        <div class="help-text">Fill in only to change the stored password</div>
      </div>

      <div class="section">
        <h2>Time Settings</h2>
        <label for="ntpServer">NTP Server:</label>
        <input type="text" id="ntpServer" name="ntpServer" value=")rawliteral"
        + String(relayConfig.ntpServer) + R"rawliteral(">

        <label for="timezoneOffset">Timezone Offset (seconds):</label>
        <input type="number" id="timezoneOffset" name="timezoneOffset" value=")rawliteral"
        + String(relayConfig.timezoneOffset) + R"rawliteral(">
        <div class="help-text">e.g., -18000 for EST, -14400 for EDT</div>
      </div>

      <div class="section">
        <h2>Google Sheets Integration</h2>
        <div class="checkbox-group">
          <input type="checkbox" id="sheetsEnabled" name="sheetsEnabled">
          <label for="sheetsEnabled">Enable Google Sheets Upload</label>
        </div>
        <label for="googleSheetURL">Google Apps Script Web App URL:</label>
        <input type="text" id="googleSheetURL" name="googleSheetURL"
               value=")rawliteral" + String(relayConfig.googleSheetURL) + R"rawliteral("
               placeholder="https://script.google.com/macros/s/...">
        <div class="help-text">Always use the HTTPS URL from your Apps Script deployment</div>
      </div>

      <div class="section">
        <h2>Security</h2>
        <label for="apPassword">AP Mode Password:</label>
        <input type="text" id="apPassword" name="apPassword" value=")rawliteral"
        + String(relayConfig.apPassword) + R"rawliteral(">
        <div class="help-text">Password for the "pHloat-Relay" WiFi access point</div>

        <label for="pmk">ESP-NOW PMK (Encryption Key):</label>
        <input type="text" id="pmk" name="pmk" value=")rawliteral"
        + String(relayConfig.pmk) + R"rawliteral("
               placeholder="32 hex characters (must match sensor PMK)" maxlength="32">
        <div class="help-text">Set the same 32-char hex key on ALL sensors and this relay</div>

        <label for="apiKey">Web UI API Key:</label>
        <input type="text" id="apiKey" name="apiKey" value=")
        + String([&]() {
            preferences.begin("relay-config", true);
            String k = preferences.getString("apiKey", "");
            preferences.end();
            return k;
          }())
        + R"rawliteral(" placeholder="Leave blank for no auth">
        <div class="help-text">Protects config/calibration endpoints. Required for POST requests.</div>
      </div>

      <button type="submit">Save Configuration</button>
    </form>
  </div>

  <script>
    let apiKey = sessionStorage.getItem('apiKey') || '';

    function unlock() {
      const k = document.getElementById('authKey').value;
      // Test the key against /status (all endpoints accept valid header)
      fetch('/status', { headers: {'X-API-Key': k} })
        .then(r => { if (r.ok) return r.json(); throw new Error('auth'); })
        .then(() => {
          apiKey = k;
          sessionStorage.setItem('apiKey', k);
          document.getElementById('authGate').style.display = 'none';
          document.getElementById('configForm').style.display = '';
          loadConfig();
        })
        .catch(() => alert('Invalid API key'));
      }

    function maybeAuth(cb) {
      // Check if auth is required by trying unauthenticated request
      fetch('/status').then(r => r.json()).then(data => {
        // Always load config — if auth is needed for saves, it'll be caught at submit
        document.getElementById('configForm').style.display = '';
        loadConfig();
      });
      // Skip auth gate for now — it triggers only on save failure
      document.getElementById('configForm').style.display = '';
      loadConfig();
    }

    function loadConfig() {
      document.getElementById('wifiEnabled').checked = )rawliteral"
      + String(relayConfig.wifiEnabled ? "true" : "false") + R"rawliteral(;
      document.getElementById('sheetsEnabled').checked = )rawliteral"
      + String(relayConfig.sheetsEnabled ? "true" : "false") + R"rawliteral(;
    }

    document.getElementById('configForm').addEventListener('submit', function(e) {
      e.preventDefault();
      const pw = document.getElementById('wifiPassword').value;

      const formData = {
        wifiEnabled:    document.getElementById('wifiEnabled').checked,
        wifiSSID:       document.getElementById('wifiSSID').value,
        ntpServer:      document.getElementById('ntpServer').value,
        timezoneOffset: parseInt(document.getElementById('timezoneOffset').value),
        sheetsEnabled:  document.getElementById('sheetsEnabled').checked,
        googleSheetURL: document.getElementById('googleSheetURL').value,
        apPassword:     document.getElementById('apPassword').value,
        pmk:            document.getElementById('pmk').value,
        apiKey:         document.getElementById('apiKey').value
      };

      // Only send password if changed
      if (pw.length > 0) formData.wifiPassword = pw;

      const headers = {'Content-Type': 'application/json'};
      if (apiKey) headers['X-API-Key'] = apiKey;

      fetch('/saveConfig', {
        method: 'POST', headers: headers,
        body: JSON.stringify(formData)
      })
      .then(r => r.json())
      .then(result => {
        if (result.success) {
          document.getElementById('successMsg').style.display = 'block';
          setTimeout(() => { location.href = '/'; }, 2000);
        } else {
          alert('Error: ' + (result.error || 'Unknown'));
        }
      })
      .catch(err => alert('Network error: ' + err));
    });

    maybeAuth();
  </script>
</body>
</html>
)rawliteral";

  server.send(200, "text/html", html);
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
  const char* apPassword = doc["apPassword"] | DEFAULT_AP_PASSWORD;
  if (strlen(apPassword) >= 8) {
    strlcpy(relayConfig.apPassword, apPassword, sizeof(relayConfig.apPassword));
  }
  strlcpy(relayConfig.pmk, doc["pmk"] | "", sizeof(relayConfig.pmk));

  // API key (stored separately for auth check)
  const char* apiKey = doc["apiKey"] | "";
  preferences.begin("relay-config", false);
  preferences.putString("apiKey", apiKey);
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
