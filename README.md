# pHloat pH Monitoring System

A complete ESP32-based pH monitoring system for brewery fermentation, designed to work alongside Tilt Hydrometers and integrate with Google Sheets.

## System Overview

The pHloat system consists of two components:

1. **pHloat pH Sensor** (ESP32-S3) - Battery-powered sensor that reads pH every minute
2. **pHloat Relay** (ESP32) - Central hub that receives data, calibrates sensors, and uploads to Google Sheets

## Features

- ✅ 1-minute reading intervals with deep sleep for battery efficiency
- ✅ ESP-NOW wireless communication (no WiFi needed for sensors)
- ✅ Web-based configuration and calibration
- ✅ 3-point pH calibration (pH 4, 7, 10)
- ✅ Multiple sensor support (up to 10 sensors)
- ✅ Google Sheets integration with Tilt data matching
- ✅ Local data storage with download capability
- ✅ Storage management with alerts
- ✅ Real-time NTP time synchronization

## Hardware Requirements

### pHloat pH Sensor (per sensor)
- ESP32-S3 development board
- Atlas Scientific pH OEM Circuit (I²C mode)
- Atlas Scientific pH probe
- BNC connector
- Battery (LiPo 3.7V recommended, 2000mAh+ for ~60 days)
- Battery charging circuit (optional but recommended)
- Waterproof enclosure

### pHloat Relay (one per brewery)
- ESP32 development board (any variant)
- USB power supply (always-on)
- Optional: SD card module for extended storage

## Wiring Diagrams

### pH Sensor Wiring

```
ESP32-S3              Atlas Scientific pH OEM
=========             =======================
GPIO 8 (SDA)  ------>  SDA
GPIO 9 (SCL)  ------>  SCL
3.3V          ------>  VCC
GND           ------>  GND

Atlas Scientific pH OEM    pH Probe
========================   =========
PRB (BNC connector) -----> pH Probe (BNC)
```

**Important Notes:**
- The Atlas Scientific pH OEM operates at 3.3V (perfect for ESP32)
- Use I²C mode (default on pH OEM)
- Keep I²C wires as short as possible for reliability
- The pH probe MUST be kept hydrated - store in storage solution when not in use

### Power Considerations

**pH Sensor (Battery-Powered):**
- Deep sleep current: ~10µA
- Active current: ~50mA for ~1 second
- Average: ~0.8mA
- 2000mAh battery = ~104 days runtime (1 reading/minute)

**Relay (Wall-Powered):**
- Continuous operation via USB
- Current draw: ~150mA

## Software Setup

### 1. Arduino IDE Configuration

1. Install Arduino IDE (version 2.0+)
2. Add ESP32 board support:
   - Go to File → Preferences
   - Add to "Additional Board Manager URLs": 
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to Tools → Board → Board Manager
   - Search for "esp32" and install "esp32 by Espressif Systems"

3. Install required libraries:
   - Open Arduino IDE
   - Go to Tools → Manage Libraries
   - Search and install:
     - **ArduinoJson** by Benoit Blanchon (version 6.21.0 or higher)
     - This is required for JSON parsing in the web interface
   
4. IMPORTANT - Atlas Scientific I2C Communication:
   - The code uses direct I2C Wire library commands
   - No separate Atlas library needed
   - Commands are sent via Wire.write() following Atlas protocol

### 2. Upload pH Sensor Sketch

1. Open `pHloat_Sensor/pHloat_Sensor.ino`
2. Select board: Tools → Board → ESP32S3 Dev Module
3. Configure board settings:
   - USB CDC On Boot: Enabled
   - Flash Size: 4MB (or your board's size)
   - Partition Scheme: Default
4. Connect ESP32-S3 via USB
5. Select correct COM port
6. Click Upload

### 3. Upload Relay Sketch

1. Open `pHloat_Relay/pHloat_Relay.ino`
2. **IMPORTANT:** Make sure `pHloat_Relay_WebUI.ino` is in the same folder
3. Select board: Tools → Board → ESP32 Dev Module (or your specific board)
4. Connect ESP32 via USB
5. Select correct COM port
6. Click Upload

### 4. Initial Configuration

#### Configure pH Sensor:

1. Power on the pH sensor while holding the BOOT button (GPIO 0)
2. Connect to WiFi network: `pHloat-XXXXXXXX`
3. Password: `phloat123`
4. Open browser to `192.168.4.1`
5. Enter:
   - Device name (e.g., "Fermenter-1")
   - Relay MAC address (get this from relay serial monitor)
6. Save - sensor will reboot and start taking readings

#### Configure Relay:

1. Power on relay
2. Note the MAC address printed in Serial Monitor
3. If WiFi not configured, connect to `pHloat-Relay` AP (password: `phloat123`)
4. Open browser to `192.168.4.1` (or relay's IP if WiFi configured)
5. Go to Configuration page
6. Enter:
   - WiFi SSID and password
   - NTP server (default: pool.ntp.org)
   - Timezone offset in seconds (e.g., -18000 for EST)
   - Google Sheets URL (optional, see below)
7. Save - relay will reboot and connect to WiFi

## Google Sheets Integration

You have **two options** for Google Sheets integration:

### Option 1: Direct Upload (pHloat Relay → Google Sheets)

Each pHloat Relay uploads directly to Google Sheets using Google Apps Script.

**Pros:**
- Simple setup
- Works anywhere with WiFi
- No additional hardware

**Cons:**
- Each relay needs Google Sheets configured
- Multiple relays = multiple configurations

**Setup:** See "Setup Google Apps Script" section below

### Option 2: Tilt Pi Integration (Recommended for Tilt Users)

If you already have a Raspberry Pi running Tilt Pi, use it as a central hub!

**Pros:**
- ✅ Central hub for both Tilt and pHloat data
- ✅ Better timestamp matching (direct database access)
- ✅ Unified dashboard
- ✅ One Google Sheets configuration
- ✅ Lower power (relays can be eliminated)

**Cons:**
- Requires Raspberry Pi
- Slightly more complex initial setup

**Setup:** See **TILT_PI_INTEGRATION.md** for complete instructions

---

## Setup Google Apps Script (Option 1 - Direct Upload)

1. Create a new Google Sheet for your fermentation data
2. Go to Extensions → Apps Script
3. Delete any existing code
4. Copy and paste the contents of `GoogleAppsScript.js`
5. Save the project (name it "pHloat Logger")
6. Click "Deploy" → "New deployment"
7. Settings:
   - Type: Web app
   - Execute as: Me
   - Who has access: Anyone
8. Click "Deploy"
9. Copy the Web App URL
10. Paste this URL into the pHloat Relay configuration

### Tilt Integration:

The Google Apps Script automatically searches for Tilt data sheets and matches pH readings by timestamp (±1 minute). 

**Expected Tilt sheet format:**
- Sheet name contains "Tilt" (e.g., "Tilt Red", "Tilt Orange")
- Columns must include: Timestamp, Gravity (or SG), optionally Color

The script will:
1. Create a new sheet for each pH sensor
2. Log pH and temperature readings
3. Find the closest Tilt reading within 1 minute
4. Add Specific Gravity and Tilt Color to the same row

## Calibration Procedure

**IMPORTANT:** Always calibrate pH sensors before first use and periodically during use.

### 3-Point Calibration:

You'll need pH calibration buffers: pH 4.0, 7.0, and 10.0

1. Access the Relay web interface
2. Go to "Calibration" page
3. Select the sensor to calibrate
4. Follow the procedure:
   
   **Step 1: pH 7.0 (mid-point)**
   - Rinse probe with distilled water
   - Place in pH 7.0 buffer
   - Wait 2-3 minutes for stable reading
   - Note the raw pH reading from sensor data
   - Enter in "pH 7.0 Buffer Reading" field
   
   **Step 2: pH 4.0 (low point)**
   - Rinse probe thoroughly
   - Place in pH 4.0 buffer
   - Wait 2-3 minutes
   - Note the reading
   - Enter in "pH 4.0 Buffer Reading" field
   
   **Step 3: pH 10.0 (high point)**
   - Rinse probe thoroughly
   - Place in pH 10.0 buffer
   - Wait 2-3 minutes
   - Note the reading
   - Enter in "pH 10.0 Buffer Reading" field

5. Click "Save Calibration"

**Calibration Tips:**
- Always start with pH 7, then pH 4, then pH 10
- Rinse probe between each buffer
- Wait for readings to stabilize
- Calibrate at the temperature you'll be measuring (or use temperature compensation)
- Re-calibrate every 30 days or when you notice drift

## Usage

### Normal Operation:

1. **Sensors:**
   - Wake every 60 seconds
   - Take pH and temperature reading
   - Send via ESP-NOW to relay
   - Return to deep sleep
   - Battery indicator: LED flashes once per reading

2. **Relay:**
   - Receives data from all sensors
   - Applies calibration corrections
   - Saves data locally
   - Uploads to Google Sheets (if enabled)
   - Provides web interface for monitoring

### Monitoring Data:

**Via Web Interface:**
1. Connect to relay's IP address
2. Click "Data Review"
3. View all data files
4. Download CSV files for analysis
5. Delete old files to free space

**Via Google Sheets:**
1. Open your fermentation Google Sheet
2. Each sensor has its own sheet
3. Data includes: Timestamp, pH, Temperature, Specific Gravity (from Tilt), Tilt Color
4. Use built-in Google Sheets features for charts and analysis

### Storage Management:

- The relay monitors storage space
- Reserves 512KB for current logging
- Alerts appear when free space drops below 512KB
- Critical alert at 100KB free
- Manually delete old files through web interface

## Troubleshooting

### pH Sensor Not Sending Data:

1. Check MAC address is correct in sensor config
2. Verify relay is powered on
3. Check distance between sensor and relay (ESP-NOW range ~100m)
4. View serial monitor for error messages

### Incorrect pH Readings:

1. Check calibration is current (within 30 days)
2. Verify probe is properly hydrated
3. Check probe is not fouled (clean with probe cleaner)
4. Ensure probe junction is not clogged
5. Check temperature compensation is working

### WiFi Connection Issues:

1. Verify SSID and password are correct
2. Check WiFi signal strength at relay location
3. Ensure router allows 2.4GHz connections (ESP32 doesn't support 5GHz)
4. Try rebooting router

### Google Sheets Not Updating:

1. Verify deployment URL is correct
2. Check Apps Script permissions are set correctly
3. View Apps Script logs (View → Logs in Apps Script editor)
4. Ensure relay has internet connection
5. Check that "Enable Google Sheets Upload" is checked in relay config

### Battery Life Issues:

1. Verify deep sleep is working (serial monitor shows "Going to sleep")
2. Check battery capacity (should be 2000mAh minimum)
3. Verify no LEDs are staying on during sleep
4. Consider reducing reading frequency if needed (edit SLEEP_DURATION in code)

## Advanced Configuration

### Changing Reading Interval:

Edit `pHloat_Sensor.ino`:
```cpp
#define SLEEP_DURATION 60  // Change to desired seconds (e.g., 300 = 5 minutes)
```

### Adding More Sensors:

Edit `pHloat_Relay.ino`:
```cpp
#define MAX_SENSORS 10  // Increase if you need more than 10 sensors
```

### Custom I²C Pins:

Edit `pHloat_Sensor.ino`:
```cpp
#define I2C_SDA 8  // Change to your preferred GPIO
#define I2C_SCL 9  // Change to your preferred GPIO
```

## pH Probe Care

**Daily:**
- Ensure probe is submerged in fermentation or storage solution
- Never let probe dry out

**Weekly:**
- Rinse with distilled water
- Check for buildup on glass bulb

**Monthly:**
- Clean with pH probe cleaning solution
- Re-calibrate
- Check electrolyte level (if refillable probe)

**Storage:**
- Store in pH 4.0 buffer or storage solution
- NEVER store in distilled water (damages probe)
- Keep protective cap on when not in use

## Bill of Materials (BOM)

### Per pH Sensor:
| Item | Quantity | Approx. Cost | Notes |
|------|----------|--------------|-------|
| ESP32-S3 Dev Board | 1 | $8-15 | Any ESP32-S3 with battery charging |
| Atlas Scientific pH OEM | 1 | $60 | From Atlas Scientific |
| pH Probe (BNC) | 1 | $50-100 | Atlas or third-party |
| LiPo Battery 3.7V 2000mAh | 1 | $8-12 | JST connector |
| Waterproof enclosure | 1 | $10-15 | IP67 rated |
| Misc (wire, connectors) | - | $5 | - |
| **Total per sensor** | | **~$140-200** | |

### For Relay:
| Item | Quantity | Approx. Cost | Notes |
|------|----------|--------------|-------|
| ESP32 Dev Board | 1 | $6-10 | Any ESP32 variant |
| USB Power Supply | 1 | $5 | 5V 1A minimum |
| Enclosure (optional) | 1 | $8 | - |
| **Total for relay** | | **~$15-25** | |

## License

This project is released under the MIT License. Feel free to modify and use for personal or commercial applications.

## Credits

Created for homebrewers and craft brewers who want to monitor pH during fermentation alongside their Tilt Hydrometers.

## Support

For issues, questions, or contributions, please open an issue on the project repository.

## Version History

- v1.0.0 - Initial release
  - ESP-NOW communication
  - Web UI for configuration and calibration
  - Google Sheets integration
  - Tilt data matching
  - Local storage management
  - Deep sleep for battery efficiency
