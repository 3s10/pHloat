# pHloat Quick Start Guide

## First Time Setup (15 minutes)

### Step 1: Upload Code (5 min)
1. Open Arduino IDE
2. Upload `pHloat_Sensor.ino` to ESP32-S3
3. Upload `pHloat_Relay.ino` to ESP32

### Step 2: Wire Hardware (5 min)
```
pH Sensor Connections:
ESP32-S3 GPIO 8 (SDA) → Atlas pH OEM SDA
ESP32-S3 GPIO 9 (SCL) → Atlas pH OEM SCL
ESP32-S3 3.3V → Atlas pH OEM VCC
ESP32-S3 GND → Atlas pH OEM GND

Relay: Just plug in USB power
```

### Step 3: Configure Relay (3 min)
1. Power on relay, note MAC address from serial monitor
2. Connect to WiFi AP: `pHloat-Relay` (password: `phloat123`)
3. Open browser to `192.168.4.1`
4. Enter your WiFi credentials
5. Save and reboot

### Step 4: Configure Sensor (2 min)
1. Hold BOOT button while powering on sensor
2. Connect to WiFi AP: `pHloat-XXXXXXXX` (password: `phloat123`)
3. Open browser to `192.168.4.1`
4. Enter device name and relay MAC address
5. Save and reboot

## Calibration (10 minutes)

**You need:** pH 4.0, 7.0, and 10.0 buffer solutions

1. Access relay web interface
2. Go to Calibration page
3. Select your sensor
4. **pH 7 Buffer:**
   - Rinse probe with distilled water
   - Place in pH 7 buffer
   - Wait 2-3 minutes
   - Enter the raw reading
5. **pH 4 Buffer:**
   - Rinse probe
   - Place in pH 4 buffer
   - Wait 2-3 minutes
   - Enter the reading
6. **pH 10 Buffer:**
   - Rinse probe
   - Place in pH 10 buffer
   - Wait 2-3 minutes
   - Enter the reading
7. Click Save

**Done!** Your sensor is now calibrated and taking readings every minute.

## Google Sheets Setup (Optional, 10 minutes)

### Step 1: Create Apps Script
1. Create new Google Sheet
2. Extensions → Apps Script
3. Paste code from `GoogleAppsScript.js`
4. Save

### Step 2: Deploy
1. Click Deploy → New deployment
2. Type: Web app
3. Execute as: Me
4. Access: Anyone
5. Copy the URL

### Step 3: Configure Relay
1. Access relay web interface
2. Go to Configuration
3. Paste URL in "Google Apps Script Web App URL"
4. Check "Enable Google Sheets Upload"
5. Save

## Daily Use

### Monitoring
- **Web Interface:** Go to relay IP address → Data Review
- **Google Sheets:** Open your spreadsheet, data auto-updates every minute

### Downloading Data
1. Access relay web interface
2. Click "Data Review"
3. Click "Download" next to any file

### Battery Status
- 2000mAh battery lasts ~60-100 days
- LED flashes on each reading
- Recharge when LED gets dim

### Probe Care
- Keep probe wet (in fermentation or storage solution)
- Never let it dry out
- Clean monthly with probe cleaner
- Recalibrate every 30 days

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| No data appearing | Check relay is powered on, verify MAC address in sensor config |
| Wrong pH readings | Recalibrate sensor |
| WiFi won't connect | Check SSID/password, ensure 2.4GHz network |
| Sheets not updating | Verify Apps Script URL, check permissions |
| Low battery warning | Recharge or replace battery |

## Key Specifications

- Reading interval: 60 seconds
- Battery life: 60-100 days (2000mAh LiPo)
- Wireless range: ~100 meters (ESP-NOW)
- Storage: Up to 100+ days of data (depends on SPIFFS size)
- Multiple sensors: Up to 10 sensors per relay
- pH accuracy: ±0.01 pH (after calibration)
- Temperature range: 0-100°C
- Waterproof: Use IP67 enclosure

## Support Contacts

- Documentation: See README.md for full details
- Troubleshooting: See Troubleshooting section in README.md
- Calibration help: See Calibration Procedure in README.md

## Safety Notes

⚠️ **Important:**
- Never let pH probe dry out
- Use waterproof enclosure for sensors
- Keep electronics away from liquids
- Properly dispose of batteries
- Use certified USB power supplies
