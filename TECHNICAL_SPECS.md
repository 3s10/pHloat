# pHloat — Technical Specifications

| Property | Value |
|---|---|
| **Project** | pHloat pH Monitoring System |
| **Version** | v3.2 (Sensor), v3.2 (Relay) |
| **Classification** | Embedded IoT + Cloud-Integrated Brewery Fermentation Monitor |
| **License** | MIT |
| **Target** | Homebrew / nano-brewery fermentation pH tracking, with Tilt Hydrometer integration |

---

## Table of Contents

1. [Purpose & Overview](#1-purpose--overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [File Inventory](#3-file-inventory)
4. [Runtime Data Model](#4-runtime-data-model)
5. [Configuration System](#5-configuration-system)
6. [Core Algorithm / Business Logic](#6-core-algorithm--business-logic)
7. [Data Ingestion / Input Layer](#7-data-ingestion--input-layer)
8. [Field / Schema Mapping](#8-field--schema-mapping)
9. [Web Dashboard / API Surface](#9-web-dashboard--api-surface)
10. [Report / Output Generation](#10-report--output-generation)
11. [Security Model](#11-security-model)
12. [Conventions & Invariants](#12-conventions--invariants)
13. [Startup Sequence](#13-startup-sequence)
14. [How to Add a Feature](#14-how-to-add-a-feature)
15. [Glossary](#15-glossary)

---

## 1. Purpose & Overview

pHloat is a distributed, battery-powered pH monitoring system for brewery fermentation. It pairs battery-operated ESP32-S3 pH sensors (one per fermenter) with a central ESP32 relay hub. Sensors take readings every 60 seconds, transmit via encrypted ESP-NOW, then deep-sleep. The relay receives data, applies per-sensor calibration, stores it locally, and forwards it to Google Sheets (via HTTPS to a Google Apps Script Web App) or to a local Raspberry Pi running Tilt Pi.

The system optionally correlates pH readings with Tilt Hydrometer specific-gravity data via timestamp matching (±60 s window).

**Hardware stack:**
- Sensor node: ESP32-S3 + Atlas Scientific pH OEM circuit (I2C, addr 0x63) + DS18B20 temp probe + LiPo battery
- Relay node: Any ESP32 variant, wall-powered via USB, SPIFFS flash storage
- Optional central hub: Raspberry Pi (Tilt Pi) running a Python/Flask server

**Software stack:**
- Arduino C++ (ESP32 core) for embedded firmware
- Google Apps Script (JavaScript) for cloud ingestion
- Python 3 + Flask + SQLite for local Tilt Pi server

---

## 2. High-Level Architecture

### Data Flow Diagram

```
┌─────────────┐   I2C (addr 0x63)   ┌──────────────────┐
│  Atlas pH   │◄───────────────────►│   ESP32-S3       │
│  OEM + Probe│                     │  pHloat Sensor   │
└─────────────┘                     │                  │
┌─────────────┐   OneWire GPIO N    │  • read pH       │
│  DS18B20    │◄───────────────────►│  • read temp     │
│  Temp Probe │                     │  • temp comp     │
└─────────────┘                     │  • ESP-NOW tx    │
                                    └────────┬─────────┘
                                             │ ESP-NOW
                                    ┌────────▼─────────┐
                                    │   ESP32          │
                                    │  pHloat Relay    │
                                    │                  │
                                    │  • receive       │
                                    │  • calibrate     │
                                    │  • store (SPIFFS)│
                                    │  • upload (HTTPS)│
                                    └────────┬─────────┘
                                             │
                              ┌──────────────┼──────────────┐
                              │              │              │
                              ▼              ▼              ▼
                       ┌──────────┐  ┌──────────┐  ┌──────────────┐
                       │  Google  │  │  Local   │  │  Raspberry   │
                       │  Sheets  │  │  CSV     │  │  Pi / Tilt   │
                       │ (GAS)    │  │  (SPIFFS)│  │  Pi Server   │
                       └──────────┘  └──────────┘  └──────────────┘
```

### Communication Paths

| Path | Protocol | Payload | Encryption |
|---|---|---|---|
| Sensor → Atlas pH OEM | I2C (Wire lib) | `R` command + response | None (local bus) |
| Sensor → DS18B20 | OneWire | Scratchpad read | None (local bus) |
| Sensor → Relay | ESP-NOW (802.11 vendor action) | `SensorData` struct (32 B) | PMK (16 bytes) if configured |
| Relay → Google Sheets | HTTPS POST | JSON (~512 B) | TLS 1.2+ |
| Relay → Tilt Pi | HTTP POST | JSON | None (local LAN) |
| Relay ↔ Browser | HTTP (port 80) | HTML / JSON | None (local LAN) |
| Tilt Pi ↔ Browser | HTTP (port 5000) | HTML / JSON | None (local LAN) |

---

## 3. File Inventory

### Source Files

| File | Lines | Language | Role |
|---|---|---|---|
| `pHloat_Sensor/pHloat_Sensor.ino` | 496 | Arduino C++ | Sensor firmware: I2C pH read, OneWire temp, Nernst temp compensation, ESP-NOW TX, config-mode AP web server, deep-sleep orchestration |
| `pHloat_Relay/pHloat_Relay.ino` | 531 | Arduino C++ | Relay firmware: ESP-NOW RX, piecewise calibration engine, SPIFFS CSV persistence, HTTPS upload to Google Sheets, NTP time sync, config persistence via Preferences |
| `pHloat_Relay/pHloat_Relay_WebUI.ino` | 902 | Arduino C++ (embedded HTML/JS/CSS) | Web UI handlers served by `WebServer` on port 80: dashboard, config form, calibration wizard, data review/download, storage status, delete operations |
| `GoogleAppsScript.js` | 232 | Google Apps Script (JavaScript) | Cloud receiver: `doPost()` validates JSON, creates per-device sheets, searches Tilt sheets by timestamp (±60 s), appends matched rows with formatting |
| `install-phloat-tiltpi.sh` | 862 | Bash (embedded Python) | Raspberry Pi installer: creates Python venv, writes `phloat_server.py` (Flask + SQLite + gspread), installs systemd service, generates config JSON |

### Documentation Files (preserve only — do not overwrite)

| File | Role |
|---|---|
| `README.md` | Primary user documentation |
| `START_HERE.md` | Navigation guide / onboarding |
| `PROJECT_OVERVIEW.md` | Executive summary with decision tree |
| `QUICK_START.md` | 15-minute deployment checklist |
| `ASSEMBLY.md` | Physical build instructions |
| `WIRING.md` | Connection diagrams and color codes |
| `PARTS_LIST.md` | BOM with cost estimates |
| `TILT_PI_INTEGRATION.md` | Raspberry Pi / Tilt Pi setup guide |
| `INTEGRATION_COMPARISON.md` | Standalone relay vs. Tilt Pi comparison |
| `18650_BATTERY_GUIDE.md` | Battery upgrade reference |
| `DISSOLVED_OXYGEN_GUIDE.md` | DO sensor expansion reference |
| `PHLOAT_PRO_*.md` | Product variant guides (Design, Temperature, Ultra DO) |

---

## 4. Runtime Data Model

### On-Device (Relay — SPIFFS)

SPIFFS is mounted at boot with `SPIFFS.begin(true)` (auto-format on failure).

```
/
├── /data/
│   ├── {DeviceName}_YYYYMMDD.csv     ← Daily CSV per sensor
│   └── {DeviceName}_pending.csv      ← Fallback when time not synced
├── /calibrations.json                ← Per-sensor calibration records
└── (system reserved: ~512 KB)
```

**CSV format:**
```
Timestamp,Device,pH,Temperature,ReadingNumber
2026-05-05 18:54:32,Fermenter-1,4.52,18.5,123
```

Header is written only when the file is created (checked via `SPIFFS.exists()`).

### On Raspberry Pi (Tilt Pi Server)

```
/home/pi/phloat/
├── phloat.db              ← SQLite3: ph_data + config tables
├── config.json            ← Runtime configuration
├── credentials.json       ← Google Service Account key (optional)
├── phloat_server.py       ← Flask application
├── configure_sheets.py    ← Interactive config helper
├── setup_google_sheets.sh ← Documentation script
└── venv/                  ← Python virtual environment
```

**SQLite schema (`phloat.db`):**
```sql
CREATE TABLE ph_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_name TEXT NOT NULL,
    pH REAL NOT NULL,
    temperature REAL,
    timestamp DATETIME NOT NULL,
    reading_number INTEGER,
    matched_tilt_color TEXT,
    matched_tilt_sg REAL,
    matched_tilt_temp REAL,
    uploaded_to_sheets BOOLEAN DEFAULT 0
);

CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

### In Google Sheets

- One spreadsheet per brewery.
- One sheet tab per pH sensor (named exactly as `deviceName`).
- Separate sheet tabs for Tilt data (names contain "Tilt", e.g., "Tilt Red").
- Sheets are created on first data arrival with frozen header row.

---

## 5. Configuration System

### pHloat Sensor (Preferences NVS — namespace `"phloat"`)

| Key | Type | Default | Description |
|---|---|---|---|
| `configured` | bool | `false` | Whether the device has been set up |
| `deviceName` | string | `""` | Human-readable sensor label |
| `relayMac` | string | `""` | Target relay MAC (colon-separated hex) |
| `apPassword` | string | `"phloat123"` | Config-mode AP password (min 8 chars) |
| `pmk` | string | `""` | ESP-NOW PMK as 32 hex chars (16 bytes) |
| `tempPin` | uint8 | `4` | OneWire GPIO pin for DS18B20 |
| `readCount` | uint32 | `0` | Total readings taken (persistent across sleep) |

### pHloat Relay (Preferences NVS — namespace `"relay-config"`)

| Key | Type | Default | Description |
|---|---|---|---|
| `wifiSSID` | string | `""` | Client WiFi network |
| `wifiPass` | string | `""` | Client WiFi password |
| `sheetURL` | string | `""` | Google Apps Script HTTPS URL |
| `apPassword` | string | `"phloat123"` | Fallback AP password |
| `pmk` | string | `""` | ESP-NOW PMK (32 hex chars) |
| `wifiEnabled` | bool | `false` | Whether to connect as STA |
| `sheetsEnabled` | bool | `false` | Whether to POST to Google Sheets |
| `ntpServer` | string | `"pool.ntp.org"` | NTP server hostname |
| `tzOffset` | int32 | `-18000` | Timezone offset in seconds (EST default) |
| `apiKey` | string | `""` | Optional X-API-Key for write endpoints |

### Tilt Pi Server (`config.json`)

| Key | Type | Default | Description |
|---|---|---|---|
| `google_sheets_enabled` | bool | `false` | Enable gspread upload |
| `google_sheet_id` | string | `""` | Google Sheets document ID |
| `credentials_file` | string | `"credentials.json"` | Service account JSON path |
| `tilt_db_path` | string | `"/home/pi/tilt_data.db"` | Path to Tilt Pi SQLite DB |
| `auto_match_tilt` | bool | `true` | Run timestamp matching on ingest |
| `port` | int | `5000` | Flask server port |

### Compile-Time Constants (Sensor)

```cpp
#define PH_SENSOR_ADDR   0x63     // Atlas pH OEM I2C address
#define I2C_SDA          8        // Default SDA pin
#define I2C_SCL          9        // Default SCL pin
#define CONFIG_BUTTON     0        // GPIO 0 (BOOT) — hold LOW to enter config
#define TEMP_PIN_DEFAULT  4        // Default OneWire data pin
#define SLEEP_DURATION    60        // Seconds between readings
#define DEFAULT_AP_PASSWORD "phloat123"
```

### Compile-Time Constants (Relay)

```cpp
#define DEFAULT_AP_PASSWORD  "phloat123"
#define DEFAULT_PMK          ""
#define MAX_SENSORS          10
#define DATA_DIR             "/data"
#define CALIBRATION_FILE     "/calibrations.json"
```

---

## 6. Core Algorithm / Business Logic

### A. Sensor Reading & Temperature Compensation

1. **I2C pH read:** Send `'R'` to `0x63`. Wait 900 ms. Read status byte + ASCII float.
2. **OneWire temp read:** If DS18B20 present, request temperatures and read °C.
3. **Nernst compensation:** If both readings are valid (`0 < pH < 14`, `-40 < temp < 125`):
   ```
   compensated_pH = raw_pH + (25.0 - temp) * 0.03
   ```
   This applies a slope of ~0.03 pH units per °C deviation from 25 °C.
4. **Validation:** Only transmit if `pH > 0 && pH < 14`.

### B. Piecewise Linear 3-Point Calibration (Relay)

Each sensor stores three raw readings taken in pH 4, 7, and 10 buffers:

```
struct CalibrationData {
    float ph4_reading;
    float ph7_reading;
    float ph10_reading;
    bool calibrated;
    unsigned long calibrationTime;
};
```

**Calibration formula:**

```
if raw_pH <= ph7_reading:
    slopeLow = ph7_reading - ph4_reading
    if |slopeLow| < 0.01: return raw_pH   // guard div-by-zero
    return 4.0 + (raw_pH - ph4_reading) * 3.0 / slopeLow
else:
    slopeHigh = ph10_reading - ph7_reading
    if |slopeHigh| < 0.01: return raw_pH
    return 7.0 + (raw_pH - ph7_reading) * 3.0 / slopeHigh
```

**Validation at save time:** `ph4 < ph7 < ph10` must hold strictly.

### C. Timestamp Matching (Google Apps Script)

When a pH reading arrives, the script searches all sheets whose name contains `"Tilt"` (case-insensitive). For each Tilt sheet:

1. Detect columns by header text: `time`/`date` → timestamp, `gravity`/`sg` → SG, `color`/`name` → color.
2. Scan every row (starting at row 2) and compute `abs(pH_time - tilt_time)`.
3. Return the closest match where `diff <= TIME_MATCH_WINDOW * 1000` ms (default 60 s).
4. If multiple Tilt sheets match, the first one with a valid match wins (sheet iteration order).

### D. Timestamp Matching (Tilt Pi Server)

1. Probe the Tilt Pi SQLite database (`tilt_data.db`) for tables named `data`, `tilt_data`, `readings`, or `tilt_readings`.
2. Introspect columns to find `timestamp`, `gravity`/`sg`, `color`/`name`, and `temp`.
3. Query with:
   ```sql
   SELECT ... FROM {table}
   WHERE ABS(strftime('%s', timestamp_col) - ?) <= ?
   ORDER BY ABS(strftime('%s', timestamp_col) - ?)
   LIMIT 1
   ```
4. Bind target epoch and `TIME_MATCH_WINDOW` (60 s).

---

## 7. Data Ingestion / Input Layer

### Path 1: ESP-NOW (Sensor → Relay)

- **Payload:** `SensorData` struct (packed, no padding assumed — structs match exactly on both sides).
  ```cpp
  struct SensorData {
      char deviceName[32];
      float pH;
      float temperature;
      uint32_t readingNumber;
      uint64_t timestamp;   // overwritten by relay with NTP time
  };
  ```
- **Size check:** `data_len != sizeof(SensorData)` → reject.
- **Peer model:** No pre-registration required. The sensor adds the relay MAC as a peer at TX time. The relay uses `esp_now_register_recv_cb()` with a global callback.

### Path 2: HTTPS POST (Relay → Google Sheets)

- **URL:** User-provided Google Apps Script Web App URL (enforced HTTPS; `http://` is rewritten to `https://`).
- **Headers:** `Content-Type: application/json`
- **Body:**
  ```json
  {
    "device": "Fermenter-1",
    "pH": "4.52",
    "temperature": "18.5",
    "timestamp": "2026-05-05 18:54:32",
    "readingNumber": 123
  }
  ```
  Note: `pH` and `temperature` are serialized as formatted `String(..., 2)` and `String(..., 1)`, which means they arrive as string values in JSON.

### Path 3: HTTP POST (Relay → Tilt Pi, or Sensor → Tilt Pi)

- **Endpoint:** `POST http://<pi-ip>:5000/api/ph`
- **Body:** Same JSON shape as above.
- **Rate limit:** Token bucket, 30 req/min per IP, burst of 10. Returns HTTP 429 if exceeded.

### Path 4: HTTP GET (Tilt → Google Sheets, direct)

- **Endpoint:** `GET <apps-script-url>?color=Red&gravity=1.050&temp=68&timestamp=...`
- **Handled by:** `doGet()` in `GoogleAppsScript.js`
- Creates/appends to a sheet named `"Tilt " + color`.

---

## 8. Field / Schema Mapping

### Sensor Data Structure (Wire Format)

| Offset | Field | Type | Notes |
|---|---|---|---|
| 0 | `deviceName` | `char[32]` | Null-terminated if shorter; uninitialized tail possible |
| 32 | `pH` | `float` | IEEE-754 little-endian (ESP32 default) |
| 36 | `temperature` | `float` | °C; sentinel `-127.0` if no DS18B20 |
| 40 | `readingNumber` | `uint32_t` | Monotonic counter since first boot |
| 44 | `timestamp` | `uint64_t` | Sensor-side `millis()`; overwritten by relay with `time_t` |

### Relay CSV Output

| Column | Source | Format |
|---|---|---|
| `Timestamp` | NTP-synced local time | `YYYY-MM-DD HH:MM:SS` |
| `Device` | `SensorData.deviceName` | As-is |
| `pH` | Calibrated `SensorData.pH` | `%.2f` |
| `Temperature` | `SensorData.temperature` | `%.1f` |
| `ReadingNumber` | `SensorData.readingNumber` | `%lu` |

### Google Apps Script Sheet Headers (pH sensor sheets)

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| Timestamp | pH | Temperature (°C) | Specific Gravity | Tilt Color | Reading # |

### Google Apps Script Sheet Headers (Tilt sheets via `doGet`)

| A | B | C | D |
|---|---|---|---|
| Timestamp | Color | Temperature (°F) | Specific Gravity |

### Tilt Pi Server Headers (gspread upload)

| Timestamp | pH | pH Temp (°C) | Tilt Color | Specific Gravity | Tilt Temp (°F) | Reading # | Match Status |

---

## 9. Web Dashboard / API Surface

### pHloat Relay (ESP32 WebServer, port 80)

All routes serve from the same `WebServer` instance. ElegantOTA hooks `/update` for OTA firmware uploads.

| Method | Route | Auth | Role |
|---|---|---|---|
| GET | `/` | No | Dashboard (HTML) — status cards, navigation |
| GET | `/config` | No | Configuration page (HTML form) |
| POST | `/saveConfig` | **Yes** (`X-API-Key` header) | Save WiFi, NTP, Sheets URL, PMK, API key |
| GET | `/calibration` | No | Calibration wizard (HTML) — auto-discovers sensors from `/data/*.csv` |
| POST | `/saveCalibration` | **Yes** | Save 3-point calibration for a named sensor |
| GET | `/data` | No | Data review page (HTML) — lists files with download/delete |
| GET | `/download?file=/data/...` | No | Stream file as `text/csv` |
| POST | `/deleteData` | **Yes** | Delete a SPIFFS file by path |
| GET | `/status` | No | JSON: MAC, WiFi status, sheets enabled, time sync, IP |
| GET | `/storageInfo` | No | JSON: total/used/free bytes, file list under `/data/` |

**Auth model:**
- Read endpoints (`GET`) are open.
- Write endpoints (`POST /saveConfig`, `POST /saveCalibration`, `POST /deleteData`) require `X-API-Key` header if an API key is stored in Preferences.
- If no API key is configured (`storedKey.length() == 0`), `requireAuth()` returns `true` (auth disabled).

**Request/response shapes:**
- `POST /saveConfig` body: JSON with keys `wifiEnabled`, `wifiSSID`, `wifiPassword`, `ntpServer`, `timezoneOffset`, `sheetsEnabled`, `googleSheetURL`, `apPassword`, `pmk`, `apiKey`.
- `POST /saveCalibration` body: JSON `{sensor, ph4, ph7, ph10}`.
- `POST /deleteData` body: JSON `{file: "/data/Fermenter-1_20260505.csv"}`.
- All write endpoints return `{"success": true|false, "error": "..."}`.

### Tilt Pi Server (Flask, port 5000)

| Method | Route | Role |
|---|---|---|
| GET | `/` | Dashboard (HTML) — system status, recent readings, quick links |
| POST | `/api/ph` | Ingest pH data; runs Tilt matching; optional background gspread upload |
| GET | `/api/status` | JSON: total readings, device count, Tilt DB found, sheets enabled |
| GET | `/api/recent` | JSON: last 10 `ph_data` rows |
| GET | `/data` | HTML table of last 100 readings |
| GET | `/config` | JSON dump of current `config.json` |

**Rate limiting:** Token-bucket per `request.remote_addr` on `/api/ph` only.

---

## 10. Report / Output Generation

### Local CSV Files (Relay)

- **Naming:** `/data/{deviceName}_{YYYYMMDD}.csv` when time is synced; `/data/{deviceName}_pending.csv` otherwise.
- **Rotation:** Daily by localtime date. Files append until midnight.
- **Download:** Served via `/download?file=...` with MIME `text/csv`.
- **Retention:** Manual; user deletes via web UI. No automatic rotation or compression.

### Google Sheets (Cloud)

- **Creation:** One sheet per `deviceName` on first data arrival.
- **Headers:** Written once with `setFrozenRows(1)`.
- **Formatting:** Timestamp column gets `yyyy-mm-dd hh:mm:ss`; pH gets `0.00`; temp gets `0.0`; SG gets `0.0000`.
- **Auto-resize:** `autoResizeColumns(1, 6)` after every append.

### Google Sheets (Tilt Pi Server via gspread)

- **Worksheet creation:** Per-device; headers written on first use.
- **Data row:** `[timestamp, pH, temp, tilt_color, tilt_sg, tilt_temp, reading_num, match_status]`.
- **Async upload:** A background `threading.Thread` is spawned after DB insert so the HTTP response is not blocked by gspread latency.

---

## 11. Security Model

### Transport Security

| Link | Protection |
|---|---|
| Sensor → Relay | ESP-NOW PMK (16 bytes) when `pmk` is exactly 32 hex chars. Without PMK, ESP-NOW runs unencrypted. |
| Relay → Google Sheets | HTTPS enforced. `http://` URLs are rewritten to `https://`. No certificate pinning. |
| Relay → Tilt Pi | HTTP (plain text) over local LAN. No TLS. |
| Browser → Relay/Tilt Pi | HTTP (plain text) over local LAN. |

### Access Control

- **Relay write endpoints:** Protected by optional `X-API-Key` header. Key stored in Preferences namespace `"relay-config"`, key `"apiKey"`. If empty, no auth required.
- **Tilt Pi server:** No authentication on any endpoint. Relies on network perimeter security.

### Path Traversal Prevention

- `/download` and `/deleteData` reject paths containing `".."` or not starting with `"/"`.
- File enumeration in `/storageInfo` and `/data` filters to `/data/` prefix and skips directory entries (`!path.endsWith("/")`).

### Injection Defense

- **Relay:** All incoming JSON is parsed with `ArduinoJson` (`StaticJsonDocument`). No SQL or shell commands are executed. File operations use `SPIFFS.open()` with literal paths only.
- **Tilt Pi:** Uses parameterized SQLite queries (`?` placeholders). No string concatenation into SQL.
- **Google Apps Script:** Reads `postData.contents` once; no eval or dynamic execution.

### Secrets Handling

- WiFi passwords and PMK are stored in cleartext in ESP32 NVS (Preferences). There is no encryption at rest.
- Google Service Account `credentials.json` on the Pi is a standard OAuth2 JSON file with a private key; filesystem permissions should be `600`.

---

## 12. Conventions & Invariants

### Atomic Writes

- **Relay CSV:** `SPIFFS.open(filename, FILE_APPEND)` is used. SPIFFS does not guarantee atomic multi-line writes, but each `println()` maps to a separate flash operation. In the event of power loss during write, the last line may be truncated.
- **Relay calibration JSON:** Opened with `FILE_WRITE`, serialized, then closed. If power is lost during serialization, the file may be partially written and will be rejected on next `loadCalibrations()` (falls back to `numCalibratedSensors = 0`).
- **Tilt Pi SQLite:** SQLite transactional by default; `INSERT` is atomic per statement.

### Idempotent Migrations

- **Tilt Pi:** `init_db()` runs `CREATE TABLE IF NOT EXISTS` for both `ph_data` and `config`. Safe to call repeatedly.
- **Relay:** No explicit migration logic. Calibration JSON is version-agnostic (extra fields are ignored by ArduinoJson deserialization).

### Encoding Quirks

- **ESP32 source files:** Plain UTF-8. Raw string literals (`R"rawliteral(...)rawliteral"`) embed HTML/JS/CSS without escaping.
- **Google Apps Script:** Standard JavaScript (UTF-8).
- **CSV timestamps:** Formatted with `strftime("%Y-%m-%d %H:%M:%S", ...)` — ASCII-safe.

### Slug / Naming Rules

- **Device names:** Free text, up to 31 chars (`char[32]`). Used as filenames and sheet names. Avoid `/`, `\`, and control characters to prevent SPIFFS/sheet naming issues.
- **Duplicate handling:** Not explicitly handled. Two sensors with the same name write to the same CSV file and the same Google Sheet tab.
- **MAC format:** Colon-separated hex, e.g., `AA:BB:CC:DD:EE:FF`. Parsed with `sscanf("%hhx:%hhx:...")`.

### Backward-Compatibility Guarantees

- **Sensor ↔ Relay wire protocol:** The `SensorData` struct size is hard-coded on both sides. Any change to the struct (field order, types, padding) breaks interoperability. Both .ino files must be recompiled and flashed together.
- **Calibration JSON:** The relay only reads keys `device`, `ph4`, `ph7`, `ph10`, `calibrated`, `time`. Adding new keys is safe; removing keys causes defaults to zero/false.

---

## 13. Startup Sequence

### pHloat Sensor

1. `Serial.begin(115200)`
2. `preferences.begin("phloat", false)`
3. Load config from NVS; fill defaults for missing optional fields.
4. Check `CONFIG_BUTTON` (GPIO 0). If LOW or `!configured` → **enter config mode**:
   - `WiFi.mode(WIFI_AP)`
   - Start AP with SSID `pHloat-<efuseMacHex>` and `apPassword`
   - Start `WebServer` on port 80
   - Loop forever handling clients (no deep sleep)
5. **Normal mode:**
   - `Wire.begin(I2C_SDA, I2C_SCL)`
   - Init DS18B20 on `tempPin`
   - `readPH()` → `readTemperature()`
   - Apply Nernst compensation
   - Validate range; if valid → `sendDataViaESPNow()`
   - Increment `readCount` in NVS
   - `goToSleep()`:
     - `preferences.end()`
     - Delete heap-allocated `DallasTemperature` / `OneWire`
     - `esp_sleep_enable_timer_wakeup(SLEEP_DURATION * 1e6)`
     - `esp_deep_sleep_start()`
6. On wake, the ESP32-S3 restarts from `setup()` (cold boot). `loop()` is never reached in normal mode.

### pHloat Relay

1. `Serial.begin(115200)`
2. `SPIFFS.begin(true)` — format on failure
3. `loadConfig()` from Preferences namespace `"relay-config"`
4. `loadCalibrations()` from `/calibrations.json`
5. Print MAC address (for sensor pairing)
6. If `wifiEnabled` → `initWiFi()` then `initTime()`
7. `initESPNow()` — set PMK if configured, register RX callback
8. `setupWebServer()` — bind all routes
9. `ElegantOTA.begin(&server)` — register `/update`
10. `server.begin()` on port 80
11. If WiFi not connected → fall back to AP mode (`pHloat-Relay`)
12. `loop()` runs forever:
    - `server.handleClient()`
    - `ElegantOTA.loop()`
    - NTP re-sync every 3600 s if WiFi is up

### Tilt Pi Server

1. Parse CLI / load `config.json`
2. `init_db()` — create SQLite tables if missing
3. Print startup banner with port, endpoints, and paths
4. `app.run(host='0.0.0.0', port=config['port'], debug=False)`
5. Flask handles requests asynchronously via Werkzeug threaded server.

---

## 14. How to Add a Feature

Use this checklist when extending pHloat:

- [ ] **Schema / wire format** — If the sensor payload changes, update `SensorData` in **both** `pHloat_Sensor.ino` and `pHloat_Relay.ino`. Re-flash all devices.
- [ ] **Calibration** — If adding a new compensation formula, modify `calibratePH()` in `pHloat_Relay.ino`. Update `CalibrationData` struct and `/saveCalibration` handler.
- [ ] **Storage / persistence** — If adding new NVS keys, choose a unique key name, set a safe default in `loadConfig()`, and add a `put`/`get` pair. For SPIFFS files, use `/data/` prefix and enforce path traversal checks.
- [ ] **API / web layer** — Add route in `setupWebServer()` (relay) or Flask decorator (Tilt Pi). If it mutates state, protect it with `requireAuth()` (relay) or add your own auth middleware (Tilt Pi).
- [ ] **Output / report** — Update CSV header generation, Google Apps Script sheet headers, and Tilt Pi `upload_to_google_sheets()` column mapping.
- [ ] **UI** — Modify the embedded HTML in `pHloat_Relay_WebUI.ino` (relay) or the `render_template_string` blocks in `phloat_server.py` (Tilt Pi).
- [ ] **Documentation** — Update `README.md` user-facing sections. Update this `TECHNICAL_SPECS.md` for structural changes.

---

## 15. Glossary

| Term | Definition |
|---|---|
| **AP** | Access Point — WiFi mode where the ESP32 broadcasts its own network for initial configuration |
| **Atlas pH OEM** | Atlas Scientific pH OEM circuit — an I2C pH sensor module (address `0x63`) |
| **BNC** | Bayonet Neill-Concelman connector used for pH probe attachment |
| **DS18B20** | Maxim 1-Wire digital temperature sensor; used for temperature compensation |
| **ElegantOTA** | Arduino library providing over-the-air firmware updates via a web upload form |
| **ESP-NOW** | Espressif's proprietary wireless protocol for direct device-to-device communication without a router |
| **GAS** | Google Apps Script — JavaScript runtime in Google Workspace for automating Sheets/Docs |
| **gspread** | Python library for reading/writing Google Sheets via the Sheets API v4 |
| **I2C** | Inter-Integrated Circuit bus; used between ESP32-S3 and Atlas pH OEM |
| **LiPo** | Lithium-polymer battery; typical sensor power source (3.7 V, 2000 mAh) |
| **Nernst equation** | Relates pH electrode potential to temperature; approximated here as 0.03 pH/°C |
| **NTP** | Network Time Protocol; relay synchronizes real-time clock via `pool.ntp.org` |
| **NVS** | Non-Volatile Storage — ESP32 flash-backed key-value store accessed via Arduino `Preferences` |
| **OneWire** | Dallas Semiconductor 1-Wire bus protocol; used for DS18B20 temp probe |
| **OTA** | Over-The-Air firmware update; relay supports this via ElegantOTA on `/update` |
| **pHloat** | Project codename; portmanteau of "pH" and "float" (fermentation context) |
| **PMK** | Primary Master Key — 16-byte ESP-NOW encryption key, supplied as 32 hex characters |
| **SG** | Specific Gravity — a measure of wort density from a Tilt Hydrometer |
| **SPIFFS** | SPI Flash File System — lightweight filesystem on ESP32 flash used for CSV and JSON storage |
| **STA** | Station mode — ESP32 connects to an existing WiFi access point |
| **Tilt** | Tilt Hydrometer — a Bluetooth LE floating hydrometer that logs gravity and temperature |
| **Tilt Pi** | Raspberry Pi software that receives Tilt BLE broadcasts and logs them to a local database |
| **TIME_MATCH_WINDOW** | ±60 second window for correlating a pH reading with the nearest Tilt reading by timestamp |

---

*End of Technical Specifications*
