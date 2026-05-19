#!/bin/bash
#
# pHloat Tilt Pi Integration Installer
# 
# This script configures a Raspberry Pi running Tilt Pi to:
# 1. Receive pHloat pH data via HTTP endpoint
# 2. Match pH data with Tilt readings by timestamp
# 3. Upload combined data to Google Sheets
# 4. Provide local web interface for monitoring
#
# Compatible with: Raspberry Pi 3/4/5, Raspbian/Raspberry Pi OS
# Tilt Pi: https://tilthydrometer.com/
#
# Installation:
#   curl -sSL https://your-server.com/install-phloat.sh | bash
# Or:
#   chmod +x install-phloat-tiltpi.sh
#   ./install-phloat-tiltpi.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PHLOAT_DIR="/home/pi/phloat"
PHLOAT_SERVICE="phloat-server"
PHLOAT_PORT=5000

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         pHloat Tilt Pi Integration Installer v1.0             ║"
echo "║                                                               ║"
echo "║  This will configure your Tilt Pi to receive pH data from     ║"
echo "║  pHloat sensors and combine it with Tilt Hydrometer data      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Check if running as pi user
if [ "$USER" != "pi" ]; then
    echo -e "${YELLOW}Warning: This script should be run as the 'pi' user${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}Step 1: Checking system requirements...${NC}"

# Check internet connection
if ! ping -c 1 google.com &> /dev/null; then
    echo -e "${RED}Error: No internet connection detected${NC}"
    echo "Please connect to the internet and try again"
    exit 1
fi

# Update package list
echo -e "${GREEN}Step 2: Updating package list...${NC}"
sudo apt-get update

# Install Python dependencies
echo -e "${GREEN}Step 3: Installing Python and dependencies...${NC}"
sudo apt-get install -y python3 python3-pip python3-venv

# Install required system packages
echo -e "${GREEN}Step 4: Installing system packages...${NC}"
sudo apt-get install -y git curl sqlite3

# Create pHloat directory
echo -e "${GREEN}Step 5: Creating pHloat directory...${NC}"
mkdir -p "$PHLOAT_DIR"
cd "$PHLOAT_DIR"

# Create Python virtual environment
echo -e "${GREEN}Step 6: Setting up Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo -e "${GREEN}Step 7: Installing Python packages...${NC}"
pip install --upgrade pip
pip install flask requests gspread oauth2client

echo -e "${GREEN}Step 8: Creating pHloat server application...${NC}"

# Create the main pHloat server script
cat > "$PHLOAT_DIR/phloat_server.py" << 'EOFPYTHON'
#!/usr/bin/env python3
"""
pHloat Tilt Pi Integration Server

Receives pH data from pHloat sensors via HTTP POST
Matches pH readings with Tilt data by timestamp
Uploads combined data to Google Sheets
Provides local web interface for monitoring
"""

from flask import Flask, request, jsonify, render_template_string
import json
import sqlite3
import os
from datetime import datetime, timedelta
import threading
import time
import requests

# Try to import Google Sheets libraries (optional)
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False
    print("Warning: Google Sheets libraries not available")

app = Flask(__name__)

# Configuration
DB_PATH = os.path.join(os.path.dirname(__file__), 'phloat.db')
TILT_DB_PATH = '/home/pi/tilt_data.db'  # Adjust if Tilt Pi uses different path
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
TIME_MATCH_WINDOW = 60  # seconds - match pH readings within ±60 seconds of Tilt

# Initialize database
def init_db():
    """Create database tables if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # pH data table
    c.execute('''CREATE TABLE IF NOT EXISTS ph_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  device_name TEXT NOT NULL,
                  pH REAL NOT NULL,
                  temperature REAL,
                  timestamp DATETIME NOT NULL,
                  reading_number INTEGER,
                  matched_tilt_color TEXT,
                  matched_tilt_sg REAL,
                  matched_tilt_temp REAL,
                  uploaded_to_sheets BOOLEAN DEFAULT 0)''')
    
    # Configuration table
    c.execute('''CREATE TABLE IF NOT EXISTS config
                 (key TEXT PRIMARY KEY,
                  value TEXT)''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized: {DB_PATH}")

# Load configuration
def load_config():
    """Load configuration from file"""
    default_config = {
        'google_sheets_enabled': False,
        'google_sheet_id': '',
        'credentials_file': 'credentials.json',
        'tilt_db_path': TILT_DB_PATH,
        'auto_match_tilt': True,
        'port': 5000
    }
    
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
            default_config.update(config)
    
    return default_config

def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

# Global config
config = load_config()

# ── Rate limiter for API endpoints ──────────────────────────
# Token bucket: 30 requests/minute per IP, burst of 10
_rate_buckets = {}
_rate_lock = threading.Lock()

def check_rate_limit(client_ip):
    now = time.time()
    with _rate_lock:
        bucket = _rate_buckets.get(client_ip, {"tokens": 30, "last": now})
        elapsed = now - bucket["last"]
        bucket["tokens"] = min(30, bucket["tokens"] + elapsed * (30.0 / 60.0))
        bucket["last"] = now
        if bucket["tokens"] < 1.0:
            _rate_buckets[client_ip] = bucket
            return False
        bucket["tokens"] -= 1.0
        _rate_buckets[client_ip] = bucket
    return True

def find_matching_tilt_reading(timestamp, time_window=TIME_MATCH_WINDOW):
    """
    Find Tilt reading closest to given timestamp within time window
    Returns dict with color, SG, temp or None if not found
    """
    tilt_db = config.get('tilt_db_path', TILT_DB_PATH)
    
    if not os.path.exists(tilt_db):
        print(f"Tilt database not found: {tilt_db}")
        return None
    
    try:
        conn = sqlite3.connect(tilt_db)
        c = conn.cursor()
        
        # Try to find Tilt data table (table name varies by Tilt Pi version)
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        
        # Common Tilt Pi table names
        tilt_table = None
        for table in ['data', 'tilt_data', 'readings', 'tilt_readings']:
            if table in tables:
                tilt_table = table
                break
        
        if not tilt_table:
            print(f"No Tilt data table found. Available tables: {tables}")
            conn.close()
            return None
        
        # Get column names
        c.execute(f"PRAGMA table_info({tilt_table})")
        columns = [col[1] for col in c.fetchall()]
        
        # Find column names (they vary between Tilt Pi versions)
        timestamp_col = next((col for col in columns if 'time' in col.lower() or 'date' in col.lower()), None)
        color_col = next((col for col in columns if 'color' in col.lower() or 'name' in col.lower()), None)
        sg_col = next((col for col in columns if 'gravity' in col.lower() or 'sg' in col.lower()), None)
        temp_col = next((col for col in columns if 'temp' in col.lower()), None)
        
        if not all([timestamp_col, sg_col]):
            print(f"Required columns not found in {tilt_table}")
            conn.close()
            return None
        
        # Convert timestamp to Unix epoch for comparison
        target_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        target_epoch = target_time.timestamp()
        
        # Query for readings within time window
        query = f"""
            SELECT {color_col or "'Unknown'"}, {sg_col}, {temp_col or 'NULL'}, {timestamp_col}
            FROM {tilt_table}
            WHERE ABS(strftime('%s', {timestamp_col}) - ?) <= ?
            ORDER BY ABS(strftime('%s', {timestamp_col}) - ?)
            LIMIT 1
        """
        
        c.execute(query, (target_epoch, time_window, target_epoch))
        result = c.fetchone()
        conn.close()
        
        if result:
            return {
                'color': result[0] if result[0] else 'Unknown',
                'sg': float(result[1]) if result[1] else None,
                'temp': float(result[2]) if result[2] else None,
                'timestamp': result[3]
            }
        
        return None
        
    except Exception as e:
        print(f"Error finding Tilt data: {e}")
        return None

def upload_to_google_sheets(data_id):
    """Upload pH data to Google Sheets"""
    if not config.get('google_sheets_enabled') or not GSHEETS_AVAILABLE:
        return False
    
    try:
        # Get credentials
        creds_file = config.get('credentials_file', 'credentials.json')
        if not os.path.exists(creds_file):
            print(f"Credentials file not found: {creds_file}")
            return False
        
        # Authenticate with Google Sheets
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
        client = gspread.authorize(creds)
        
        # Open spreadsheet
        sheet_id = config.get('google_sheet_id')
        if not sheet_id:
            print("No Google Sheet ID configured")
            return False
        
        spreadsheet = client.open_by_key(sheet_id)
        
        # Get data from database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""SELECT device_name, pH, temperature, timestamp, 
                            matched_tilt_color, matched_tilt_sg, matched_tilt_temp, reading_number
                     FROM ph_data WHERE id = ?""", (data_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return False
        
        device_name, pH, temp, timestamp, tilt_color, tilt_sg, tilt_temp, reading_num = row
        
        # Get or create worksheet for this device
        try:
            worksheet = spreadsheet.worksheet(device_name)
        except:
            worksheet = spreadsheet.add_worksheet(title=device_name, rows=1000, cols=10)
            # Add headers
            worksheet.update('A1:H1', [[
                'Timestamp', 'pH', 'pH Temp (°C)', 'Tilt Color', 
                'Specific Gravity', 'Tilt Temp (°F)', 'Reading #', 'Match Status'
            ]])
        
        # Prepare data row
        match_status = 'Matched' if tilt_color else 'No Tilt Data'
        new_row = [
            timestamp,
            pH,
            temp if temp else '',
            tilt_color if tilt_color else '',
            tilt_sg if tilt_sg else '',
            tilt_temp if tilt_temp else '',
            reading_num if reading_num else '',
            match_status
        ]
        
        # Append row
        worksheet.append_row(new_row)
        
        # Mark as uploaded
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE ph_data SET uploaded_to_sheets = 1 WHERE id = ?", (data_id,))
        conn.commit()
        conn.close()
        
        print(f"Uploaded to Google Sheets: {device_name} - pH {pH}")
        return True
        
    except Exception as e:
        print(f"Error uploading to Google Sheets: {e}")
        return False

@app.route('/')
def index():
    """Main dashboard page"""
    html = '''
<!DOCTYPE html>
<html>
<head>
    <title>pHloat Tilt Pi Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
            text-align: center;
        }
        h1 { color: #333; font-size: 2.5em; margin-bottom: 10px; }
        .subtitle { color: #666; font-size: 1.1em; }
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .card h2 { color: #667eea; margin-bottom: 15px; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th { background: #f5f5f5; font-weight: bold; }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
            margin-top: 10px;
        }
        .status-online { background: #4CAF50; color: white; }
        .status-offline { background: #f44336; color: white; }
        .btn {
            display: inline-block;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 10px;
        }
        .btn:hover { background: #764ba2; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 pHloat Tilt Pi Dashboard</h1>
            <p class="subtitle">pH Monitoring with Tilt Integration</p>
        </div>
        
        <div class="cards">
            <div class="card">
                <h2>System Status</h2>
                <p><strong>Server:</strong> <span class="status-badge status-online">Running</span></p>
                <p><strong>Port:</strong> ''' + str(config.get('port', 5000)) + '''</p>
                <p><strong>Database:</strong> ''' + ('Connected' if os.path.exists(DB_PATH) else 'Not Found') + '''</p>
                <p><strong>Tilt Database:</strong> ''' + ('Found' if os.path.exists(config.get('tilt_db_path', TILT_DB_PATH)) else 'Not Found') + '''</p>
                <p><strong>Google Sheets:</strong> ''' + ('Enabled' if config.get('google_sheets_enabled') else 'Disabled') + '''</p>
            </div>
            
            <div class="card">
                <h2>Quick Links</h2>
                <a href="/data" class="btn">View All Data</a><br>
                <a href="/config" class="btn">Configuration</a><br>
                <a href="/api/status" class="btn">API Status</a>
            </div>
            
            <div class="card">
                <h2>Recent Readings</h2>
                <div id="recentData">Loading...</div>
            </div>
        </div>
    </div>
    
    <script>
        function loadRecentData() {
            fetch('/api/recent')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('recentData');
                    if (data.readings.length === 0) {
                        container.innerHTML = '<p>No readings yet</p>';
                        return;
                    }
                    
                    let html = '<table><tr><th>Device</th><th>pH</th><th>Time</th></tr>';
                    data.readings.forEach(reading => {
                        html += `<tr>
                            <td>${reading.device_name}</td>
                            <td>${reading.pH.toFixed(2)}</td>
                            <td>${new Date(reading.timestamp).toLocaleString()}</td>
                        </tr>`;
                    });
                    html += '</table>';
                    container.innerHTML = html;
                });
        }
        
        loadRecentData();
        setInterval(loadRecentData, 10000);  // Refresh every 10 seconds
    </script>
</body>
</html>
    '''
    return render_template_string(html)

@app.route('/api/ph', methods=['POST'])
def receive_ph_data():
    """
    Receive pH data from pHloat sensors
    
    Expected JSON format:
    {
        "device": "Fermenter-1",
        "pH": 4.52,
        "temperature": 18.5,
        "timestamp": "2024-02-08T14:30:00",
        "readingNumber": 123
    }
    """
    try:
        # Rate limit: 30 req/min per IP
        client_ip = request.remote_addr or '127.0.0.1'
        if not check_rate_limit(client_ip):
            return jsonify({'status': 'error', 'message': 'Rate limit exceeded'}), 429

        data = request.get_json()
        
        device_name = data.get('device')
        pH = float(data.get('pH'))
        temperature = data.get('temperature')
        timestamp = data.get('timestamp', datetime.now().isoformat())
        reading_number = data.get('readingNumber')
        
        # Find matching Tilt data
        tilt_match = None
        if config.get('auto_match_tilt', True):
            tilt_match = find_matching_tilt_reading(timestamp)
        
        # Store in database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""INSERT INTO ph_data 
                     (device_name, pH, temperature, timestamp, reading_number,
                      matched_tilt_color, matched_tilt_sg, matched_tilt_temp)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (device_name, pH, temperature, timestamp, reading_number,
                   tilt_match['color'] if tilt_match else None,
                   tilt_match['sg'] if tilt_match else None,
                   tilt_match['temp'] if tilt_match else None))
        
        data_id = c.lastrowid
        conn.commit()
        conn.close()
        
        print(f"Received pH data: {device_name} - pH {pH:.2f} at {timestamp}")
        if tilt_match:
            print(f"  Matched with Tilt {tilt_match['color']}: SG {tilt_match['sg']}")
        
        # Upload to Google Sheets in background
        if config.get('google_sheets_enabled'):
            threading.Thread(target=upload_to_google_sheets, args=(data_id,)).start()
        
        return jsonify({
            'status': 'success',
            'message': 'Data received',
            'tilt_matched': tilt_match is not None,
            'tilt_color': tilt_match['color'] if tilt_match else None
        }), 200
        
    except Exception as e:
        print(f"Error receiving pH data: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM ph_data")
    total_readings = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT device_name) FROM ph_data")
    total_devices = c.fetchone()[0]
    conn.close()
    
    return jsonify({
        'status': 'online',
        'total_readings': total_readings,
        'total_devices': total_devices,
        'tilt_db_found': os.path.exists(config.get('tilt_db_path', TILT_DB_PATH)),
        'google_sheets_enabled': config.get('google_sheets_enabled', False),
        'config': config
    })

@app.route('/api/recent')
def api_recent():
    """Get recent pH readings"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""SELECT device_name, pH, temperature, timestamp, 
                        matched_tilt_color, matched_tilt_sg
                 FROM ph_data 
                 ORDER BY timestamp DESC 
                 LIMIT 10""")
    rows = c.fetchall()
    conn.close()
    
    readings = [dict(row) for row in rows]
    return jsonify({'readings': readings})

@app.route('/data')
def view_data():
    """View all data page"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""SELECT * FROM ph_data ORDER BY timestamp DESC LIMIT 100""")
    rows = c.fetchall()
    conn.close()
    
    # Simple HTML table view
    html = '<html><head><title>pHloat Data</title></head><body>'
    html += '<h1>pHloat pH Data</h1><a href="/">Back to Dashboard</a><br><br>'
    html += '<table border="1"><tr>'
    html += '<th>Device</th><th>pH</th><th>Temp</th><th>Timestamp</th>'
    html += '<th>Tilt Color</th><th>SG</th></tr>'
    
    for row in rows:
        html += f'<tr><td>{row["device_name"]}</td>'
        html += f'<td>{row["pH"]:.2f}</td>'
        html += f'<td>{row["temperature"] if row["temperature"] else "N/A"}</td>'
        html += f'<td>{row["timestamp"]}</td>'
        html += f'<td>{row["matched_tilt_color"] if row["matched_tilt_color"] else "N/A"}</td>'
        html += f'<td>{row["matched_tilt_sg"] if row["matched_tilt_sg"] else "N/A"}</td></tr>'
    
    html += '</table></body></html>'
    return html

@app.route('/config')
def view_config():
    """Configuration page"""
    return jsonify(config)

if __name__ == '__main__':
    print("Initializing pHloat server...")
    init_db()
    
    port = config.get('port', 5000)
    print(f"\n{'='*60}")
    print(f"pHloat Server Starting on Port {port}")
    print(f"{'='*60}")
    print(f"\nDashboard: http://localhost:{port}")
    print(f"API Endpoint: http://localhost:{port}/api/ph")
    print(f"\nConfigure your pHloat Relay to send data to:")
    print(f"  http://<raspberry-pi-ip>:{port}/api/ph")
    print(f"\n{'='*60}\n")
    
    # Flask's built-in server is fine for home/personal use on a local
    # network. For internet-facing deployments, replace with:
    #   pip install waitress
    #   from waitress import serve
    #   serve(app, host='0.0.0.0', port=port)
    app.run(host='0.0.0.0', port=port, debug=False)
EOFPYTHON

chmod +x "$PHLOAT_DIR/phloat_server.py"

echo -e "${GREEN}Step 9: Creating systemd service...${NC}"

# Create systemd service file
sudo tee /etc/systemd/system/phloat-server.service > /dev/null << EOFSERVICE
[Unit]
Description=pHloat Tilt Pi Integration Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=$PHLOAT_DIR
Environment="PATH=$PHLOAT_DIR/venv/bin"
ExecStart=$PHLOAT_DIR/venv/bin/python $PHLOAT_DIR/phloat_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOFSERVICE

# Create default configuration file
echo -e "${GREEN}Step 10: Creating configuration file...${NC}"

cat > "$PHLOAT_DIR/config.json" << EOFCONFIG
{
  "google_sheets_enabled": false,
  "google_sheet_id": "",
  "credentials_file": "$PHLOAT_DIR/credentials.json",
  "tilt_db_path": "$TILT_DB_PATH",
  "auto_match_tilt": true,
  "port": $PHLOAT_PORT
}
EOFCONFIG

# Create setup helper script
echo -e "${GREEN}Step 11: Creating setup helper script...${NC}"

cat > "$PHLOAT_DIR/setup_google_sheets.sh" << 'EOFHELPER'
#!/bin/bash
# Helper script to configure Google Sheets integration

echo "pHloat Google Sheets Setup"
echo "=========================="
echo ""
echo "To enable Google Sheets integration, you need:"
echo "1. A Google Cloud Project with Sheets API enabled"
echo "2. A Service Account with credentials.json file"
echo ""
echo "Steps:"
echo "1. Go to https://console.cloud.google.com"
echo "2. Create a new project (or use existing)"
echo "3. Enable Google Sheets API"
echo "4. Create Service Account credentials"
echo "5. Download credentials.json"
echo "6. Copy credentials.json to $PHLOAT_DIR/"
echo ""
echo "Then run: python3 $PHLOAT_DIR/configure_sheets.py"
echo ""
EOFHELPER

chmod +x "$PHLOAT_DIR/setup_google_sheets.sh"

# Create configuration helper Python script
cat > "$PHLOAT_DIR/configure_sheets.py" << 'EOFCONFIG'
#!/usr/bin/env python3
"""
Google Sheets configuration helper for pHloat
"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

def main():
    print("\npHloat Google Sheets Configuration")
    print("=" * 50)
    
    # Load existing config
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    print("\nCurrent settings:")
    print(f"  Enabled: {config.get('google_sheets_enabled', False)}")
    print(f"  Sheet ID: {config.get('google_sheet_id', 'Not set')}")
    print(f"  Credentials: {config.get('credentials_file', 'Not set')}")
    
    print("\n")
    
    # Get Google Sheet ID
    print("Enter your Google Sheet ID")
    print("(Found in URL: https://docs.google.com/spreadsheets/d/YOUR-SHEET-ID/edit)")
    sheet_id = input("Google Sheet ID: ").strip()
    
    # Check credentials file
    creds_file = config.get('credentials_file', 'credentials.json')
    if not os.path.exists(creds_file):
        print(f"\nWarning: Credentials file not found: {creds_file}")
        print("Please download your service account credentials.json and place it in:")
        print(f"  {os.path.dirname(__file__)}/")
        
        enable = input("\nEnable Google Sheets anyway? (y/n): ").strip().lower()
    else:
        print(f"\n✓ Credentials file found: {creds_file}")
        enable = input("\nEnable Google Sheets? (y/n): ").strip().lower()
    
    # Update config
    config['google_sheets_enabled'] = (enable == 'y')
    config['google_sheet_id'] = sheet_id
    
    # Save config
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n✓ Configuration saved!")
    print("\nRestart the pHloat server:")
    print("  sudo systemctl restart phloat-server")
    print("\n")

if __name__ == '__main__':
    main()
EOFCONFIG

chmod +x "$PHLOAT_DIR/configure_sheets.py"

# Reload systemd and enable service
echo -e "${GREEN}Step 12: Enabling pHloat service...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable phloat-server
sudo systemctl start phloat-server

# Wait a moment for service to start
sleep 2

# Check service status
if sudo systemctl is-active --quiet phloat-server; then
    echo -e "${GREEN}✓ pHloat server is running!${NC}"
else
    echo -e "${YELLOW}⚠ pHloat server failed to start${NC}"
    echo "Check logs with: sudo journalctl -u phloat-server -f"
fi

# Get Raspberry Pi IP address
PI_IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║             Installation Complete!                            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}pHloat server is now running on your Tilt Pi!${NC}"
echo ""
echo "📊 Dashboard: http://$PI_IP:$PHLOAT_PORT"
echo "🔌 API Endpoint: http://$PI_IP:$PHLOAT_PORT/api/ph"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Configure your pHloat Relay:"
echo "   - Access relay web interface"
echo "   - Go to Configuration"
echo "   - Enter Google Sheets URL: http://$PI_IP:$PHLOAT_PORT/api/ph"
echo "   - Enable Google Sheets upload"
echo "   - Save"
echo ""
echo "2. (Optional) Configure Google Sheets integration:"
echo "   cd $PHLOAT_DIR"
echo "   ./setup_google_sheets.sh  # Read instructions"
echo "   # Then copy your credentials.json to $PHLOAT_DIR/"
echo "   python3 configure_sheets.py"
echo ""
echo "3. View logs:"
echo "   sudo journalctl -u phloat-server -f"
echo ""
echo "4. Manage service:"
echo "   sudo systemctl status phloat-server"
echo "   sudo systemctl restart phloat-server"
echo "   sudo systemctl stop phloat-server"
echo ""
echo -e "${GREEN}Installation directory: $PHLOAT_DIR${NC}"
echo -e "${GREEN}Configuration file: $PHLOAT_DIR/config.json${NC}"
echo -e "${GREEN}Database: $PHLOAT_DIR/phloat.db${NC}"
echo ""
echo "Happy brewing! 🍺"
echo ""
