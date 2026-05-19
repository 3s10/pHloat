# pHloat Tilt Pi Integration Guide

## Overview

This guide explains how to set up your Raspberry Pi running Tilt Pi to receive pH data from pHloat sensors and combine it with Tilt Hydrometer data. This is the **recommended setup** for brewers already using Tilt Pi.

## Why Use Tilt Pi Integration?

**Benefits:**
- ✅ **Central Hub**: One Raspberry Pi handles both Tilt and pHloat data
- ✅ **Easier Setup**: No need to configure Google Sheets on each relay
- ✅ **Better Matching**: Direct access to Tilt database for precise matching
- ✅ **Lower Power**: pHloat relays can be eliminated (sensors talk directly to Pi)
- ✅ **Unified Dashboard**: View all fermentation data in one place
- ✅ **Local Storage**: Keep all data on your brewery network

## System Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  pHloat     │      │  pHloat     │      │  pHloat     │
│  Sensor #1  │      │  Sensor #2  │      │  Sensor #3  │
│ (ESP32-S3)  │      │ (ESP32-S3)  │      │ (ESP32-S3)  │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       │ WiFi               │ WiFi               │ WiFi
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                            │
                     ┌──────▼───────┐
                     │ Raspberry Pi │
                     │   (Tilt Pi)  │
                     │              │
                     │  - Tilt BLE  │
                     │  - pHloat    │
                     │    Server    │
                     └──────┬───────┘
                            │
                            │
                    ┌───────▼────────┐
                    │ Google Sheets  │
                    │  (combined)    │
                    │  pH + Tilt SG  │
                    └────────────────┘
```

## Prerequisites

- Raspberry Pi 3, 4, or 5
- Tilt Pi already installed and working
- Tilt Hydrometer(s) logging data
- Internet connection
- SSH access to Raspberry Pi

## Quick Installation

### Method 1: Automated Install (Recommended)

```bash
# SSH into your Raspberry Pi
ssh pi@<raspberry-pi-ip>

# Download and run installer
cd ~
wget https://raw.githubusercontent.com/your-repo/phloat/main/install-phloat-tiltpi.sh
chmod +x install-phloat-tiltpi.sh
./install-phloat-tiltpi.sh
```

The installer will:
1. Install Python dependencies
2. Create pHloat server application
3. Set up systemd service
4. Configure automatic startup
5. Create configuration files

**Installation time:** 5-10 minutes

### Method 2: Manual Install

If you prefer to install manually or the automated script doesn't work:

```bash
# 1. Update system
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git

# 2. Create directory
mkdir -p ~/phloat
cd ~/phloat

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install Python packages
pip install flask requests gspread oauth2client

# 5. Copy the installer script from the pHloat project
# (or manually create phloat_server.py from the installer)

# 6. Create systemd service
sudo nano /etc/systemd/system/phloat-server.service
# (copy contents from installer)

# 7. Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable phloat-server
sudo systemctl start phloat-server
```

## Configuration

### Step 1: Configure pHloat Sensors (Modified Setup)

Instead of sending data to a pHloat Relay, your sensors will send directly to the Tilt Pi.

**Option A: Use pHloat Relay as WiFi Bridge**
- Keep the relay hardware
- Use it ONLY to receive ESP-NOW from sensors
- Configure it to forward to Tilt Pi instead of Google Sheets

**Option B: Modify Sensors to Use WiFi Directly**
- Change sensor code to use WiFi instead of ESP-NOW
- Send HTTP POST directly to Tilt Pi
- Slightly higher power consumption but simpler

### Recommended: Use pHloat Relay as Bridge

1. **Configure pHloat Relay:**
   - Access relay web interface
   - Go to Configuration
   - WiFi: Enable and enter your network credentials
   - Google Sheets URL: Enter `http://<tilt-pi-ip>:5000/api/ph`
   - Enable "Google Sheets Upload" (it's actually sending to Tilt Pi)
   - Save and reboot

2. **Configure pHloat Sensors:**
   - Same as before - they communicate with relay via ESP-NOW
   - No changes needed to sensor configuration

3. **Verify Tilt Pi is receiving data:**
   ```bash
   # Check pHloat server logs
   sudo journalctl -u phloat-server -f
   
   # You should see:
   # "Received pH data: Fermenter-1 - pH 4.52 at 2024-02-08T14:30:00"
   # "  Matched with Tilt Red: SG 1.050"
   ```

### Step 2: Configure Tilt Database Path

The pHloat server needs to know where Tilt Pi stores its data.

```bash
cd ~/phloat
nano config.json
```

Update the `tilt_db_path` if needed:

```json
{
  "google_sheets_enabled": false,
  "google_sheet_id": "",
  "credentials_file": "/home/pi/phloat/credentials.json",
  "tilt_db_path": "/home/pi/tilt_data.db",  ← Check this path
  "auto_match_tilt": true,
  "port": 5000
}
```

**Finding your Tilt database:**

```bash
# Common locations:
/home/pi/tilt_data.db
/home/pi/.tilt/tilt_data.db
/var/lib/tilt/tilt_data.db

# Search for it:
sudo find /home -name "*.db" 2>/dev/null | grep -i tilt
```

Restart after changes:
```bash
sudo systemctl restart phloat-server
```

### Step 3: (Optional) Configure Google Sheets

If you want the Tilt Pi to upload combined data to Google Sheets:

#### 3.1 Create Google Cloud Service Account

1. Go to https://console.cloud.google.com
2. Create a new project or select existing
3. Enable Google Sheets API:
   - APIs & Services → Enable APIs and Services
   - Search for "Google Sheets API"
   - Click Enable

4. Create Service Account:
   - APIs & Services → Credentials
   - Create Credentials → Service Account
   - Name: "pHloat Tilt Pi"
   - Create and Continue
   - Skip optional steps
   - Done

5. Create Key:
   - Click on the service account you just created
   - Keys → Add Key → Create New Key
   - Choose JSON
   - Download the JSON file

6. Share Google Sheet:
   - Open your Google Sheet
   - Click Share
   - Add the service account email (from JSON file)
   - Give it Editor access

#### 3.2 Configure pHloat Server

```bash
cd ~/phloat

# Copy your downloaded credentials file here
# Rename it to credentials.json
mv ~/Downloads/your-project-*.json credentials.json

# Run configuration helper
python3 configure_sheets.py

# It will ask for:
# 1. Google Sheet ID (from URL)
# 2. Enable Google Sheets? (y/n)

# Restart service
sudo systemctl restart phloat-server
```

## Usage

### Accessing the Dashboard

Open a web browser and go to:
```
http://<raspberry-pi-ip>:5000
```

**Dashboard features:**
- System status
- Recent pH readings
- Tilt matching status
- Configuration links

### API Endpoints

The pHloat server provides several API endpoints:

**POST /api/ph** - Receive pH data
```bash
curl -X POST http://<pi-ip>:5000/api/ph \
  -H "Content-Type: application/json" \
  -d '{
    "device": "Fermenter-1",
    "pH": 4.52,
    "temperature": 18.5,
    "timestamp": "2024-02-08T14:30:00",
    "readingNumber": 123
  }'
```

**GET /api/status** - Server status
```bash
curl http://<pi-ip>:5000/api/status
```

**GET /api/recent** - Recent readings
```bash
curl http://<pi-ip>:5000/api/recent
```

### Viewing Data

**Web Interface:**
- Dashboard: `http://<pi-ip>:5000`
- All Data: `http://<pi-ip>:5000/data`
- Configuration: `http://<pi-ip>:5000/config`

**Database:**
```bash
cd ~/phloat
sqlite3 phloat.db

# View recent readings
SELECT device_name, pH, matched_tilt_color, matched_tilt_sg, timestamp 
FROM ph_data 
ORDER BY timestamp DESC 
LIMIT 10;

# Exit
.quit
```

**Google Sheets:**
- Each pHloat sensor gets its own sheet
- Columns: Timestamp, pH, pH Temp, Tilt Color, SG, Tilt Temp, Reading #, Match Status

## Data Matching

The pHloat server automatically matches pH readings with Tilt data:

**Matching Algorithm:**
1. pHloat reading arrives with timestamp
2. Server queries Tilt database
3. Finds Tilt reading within ±60 seconds
4. Uses closest match
5. Stores combined data
6. Uploads to Google Sheets (if enabled)

**Match Status:**
- "Matched" - Found Tilt data within 60 seconds
- "No Tilt Data" - No Tilt reading in time window

**Adjusting Match Window:**

Edit `~/phloat/config.json`:
```json
{
  "time_match_window": 120  ← Change to 120 seconds (±2 minutes)
}
```

## Monitoring & Troubleshooting

### Check Service Status

```bash
# Is service running?
sudo systemctl status phloat-server

# View logs (real-time)
sudo journalctl -u phloat-server -f

# View recent logs
sudo journalctl -u phloat-server -n 50

# Restart service
sudo systemctl restart phloat-server
```

### Common Issues

**1. Service won't start**

```bash
# Check logs
sudo journalctl -u phloat-server -n 50

# Common causes:
# - Python dependencies not installed
# - Port 5000 already in use
# - Permissions issues

# Try running manually to see errors:
cd ~/phloat
source venv/bin/activate
python3 phloat_server.py
```

**2. Not receiving pH data**

```bash
# Check if port is accessible
curl http://<pi-ip>:5000/api/status

# Check firewall
sudo ufw status
sudo ufw allow 5000/tcp  # If needed

# Check pHloat relay configuration
# Make sure URL is: http://<pi-ip>:5000/api/ph
```

**3. Tilt data not matching**

```bash
# Check Tilt database path
cat ~/phloat/config.json | grep tilt_db_path

# Verify Tilt database exists
ls -l /home/pi/tilt_data.db  # (or your path)

# Check Tilt database has data
sqlite3 /home/pi/tilt_data.db "SELECT COUNT(*) FROM data;"

# View pHloat logs for matching status
sudo journalctl -u phloat-server -f | grep Matched
```

**4. Google Sheets not updating**

```bash
# Check if enabled
cat ~/phloat/config.json | grep google_sheets_enabled

# Check credentials file exists
ls -l ~/phloat/credentials.json

# Check logs for upload errors
sudo journalctl -u phloat-server | grep -i sheets

# Test manually
cd ~/phloat
source venv/bin/activate
python3 -c "import gspread; print('OK')"
```

### Performance

**Resource Usage:**
- CPU: <5% on Raspberry Pi 4
- RAM: ~50-100 MB
- Disk: ~1 MB per day (depends on reading frequency)

**Database Maintenance:**

```bash
# Check database size
ls -lh ~/phloat/phloat.db

# Clean old data (keep last 90 days)
cd ~/phloat
sqlite3 phloat.db "DELETE FROM ph_data WHERE timestamp < datetime('now', '-90 days');"
sqlite3 phloat.db "VACUUM;"
```

## Advanced Configuration

### Custom Port

```bash
nano ~/phloat/config.json
# Change "port": 5000 to desired port
sudo systemctl restart phloat-server
```

### Multiple Tilt Databases

If you have multiple Tilt Pi instances or databases:

```python
# Edit ~/phloat/phloat_server.py
# Modify find_matching_tilt_reading() function
# to search multiple databases
```

### Custom Matching Logic

Edit `~/phloat/phloat_server.py` and modify the `find_matching_tilt_reading()` function:

```python
def find_matching_tilt_reading(timestamp, time_window=TIME_MATCH_WINDOW):
    # Add your custom logic here
    # e.g., prefer certain Tilt colors, weight by temperature, etc.
    pass
```

### Email Alerts

Add email notifications when pH goes out of range:

```bash
# Install mail support
sudo apt-get install ssmtp mailutils

# Edit phloat_server.py to add:
def send_email_alert(device_name, pH):
    if pH < 4.0 or pH > 5.0:
        # Send email
        pass
```

## Backup & Restore

### Backup

```bash
# Backup everything
cd ~
tar -czf phloat-backup-$(date +%Y%m%d).tar.gz phloat/

# Backup just database
cp ~/phloat/phloat.db ~/phloat-backup-$(date +%Y%m%d).db
```

### Restore

```bash
# Restore from backup
cd ~
tar -xzf phloat-backup-20240208.tar.gz

# Restart service
sudo systemctl restart phloat-server
```

## Upgrading

```bash
# Pull latest code
cd ~/phloat
git pull  # (if using git)

# Or re-run installer
./install-phloat-tiltpi.sh

# Restart service
sudo systemctl restart phloat-server
```

## Uninstall

```bash
# Stop and disable service
sudo systemctl stop phloat-server
sudo systemctl disable phloat-server

# Remove service file
sudo rm /etc/systemd/system/phloat-server.service
sudo systemctl daemon-reload

# Remove files
rm -rf ~/phloat

# (Optional) Remove Python packages
sudo apt-get remove python3-venv
```

## Integration with Existing Tilt Pi Software

### Tilt Pi (Official)

The pHloat server runs alongside Tilt Pi without conflicts:
- Tilt Pi handles Bluetooth
- pHloat handles HTTP/WiFi
- Both use same Tilt database (read-only for pHloat)

### BrewPi

If you're using BrewPi with Tilt:
- pHloat can read BrewPi's Tilt data
- Set `tilt_db_path` to BrewPi's database location

### Fermentrack

Compatible with Fermentrack:
- Both can run on same Pi
- Use different ports
- pHloat: 5000, Fermentrack: 8080

## FAQ

**Q: Do I still need the pHloat Relay hardware?**
A: Yes, recommended as a WiFi/ESP-NOW bridge. Alternatively, you can modify sensors to use WiFi directly.

**Q: Can I use this without Tilt Hydrometers?**
A: Yes! The system works standalone. It just won't match with Tilt data.

**Q: How accurate is the timestamp matching?**
A: Very accurate. Matches within ±60 seconds (configurable). Since both Tilt and pHloat use NTP, they're usually within seconds.

**Q: Can I view historical data?**
A: Yes, via the web interface or directly querying the SQLite database.

**Q: Does this interfere with existing Tilt logging?**
A: No. pHloat only reads from the Tilt database, never writes.

**Q: Can I run this on Tilt Pi Zero?**
A: Technically yes, but not recommended. Pi 3+ recommended for better performance.

**Q: What if my Tilt database structure is different?**
A: The code auto-detects table/column names. If it doesn't work, you may need to edit `find_matching_tilt_reading()`.

## Support

**Check Logs:**
```bash
sudo journalctl -u phloat-server -f
```

**Test Connectivity:**
```bash
curl http://localhost:5000/api/status
```

**Common Log Messages:**

✅ Good:
- "Received pH data: Fermenter-1 - pH 4.52"
- "Matched with Tilt Red: SG 1.050"
- "Uploaded to Google Sheets: Fermenter-1"

⚠️ Warnings:
- "Tilt database not found" → Check tilt_db_path
- "No Tilt data table found" → Verify Tilt Pi is logging
- "Credentials file not found" → Add credentials.json

❌ Errors:
- "Port 5000 already in use" → Change port or stop conflicting service
- "Permission denied" → Check file permissions
- "Module not found" → Reinstall Python dependencies

## Next Steps

1. ✅ Install pHloat server on Tilt Pi
2. ✅ Configure pHloat Relay to send to Tilt Pi
3. ✅ Verify data is being received and matched
4. ✅ (Optional) Set up Google Sheets integration
5. ✅ Monitor your fermentations!

**Happy Brewing! 🍺**
