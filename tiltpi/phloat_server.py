#!/usr/bin/env python3
"""
pHloat Tilt Pi Integration Server

Receives pH data from pHloat sensors via HTTP POST
Matches pH readings with Tilt data by timestamp
Uploads combined data to Google Sheets
Provides local web interface for monitoring
"""

from flask import Flask, request, jsonify
import html
import json
import sqlite3
import os
from datetime import datetime, timedelta
import threading
import time

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
from phloat_upload import (
    UPLOAD_AUTH_HEADER,
    TIME_MATCH_WINDOW,
    get_upload_secret,
    public_config_snapshot,
    validate_reading_payload,
    verify_upload_token,
)
from tilt_matching import find_matching_tilt_reading

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
        'port': 5000,
        # Bind address. Default 0.0.0.0 so the relay can POST from the LAN.
        # Read endpoints (/data, /api/recent, /api/status) are UNAUTHENTICATED
        # and expose pH history + redacted config to anyone who can reach this
        # host — treat the network as the trust boundary, or set bind_host to a
        # specific interface / front it with a firewall. Only /api/ph (writes)
        # requires the upload token.
        'bind_host': '0.0.0.0',
        'upload_secret': os.environ.get('PHLOAT_UPLOAD_SECRET', ''),
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
_rate_last_sweep = 0.0
_RATE_SWEEP_INTERVAL = 300.0   # evict idle IPs every 5 minutes
_RATE_IDLE_TTL = 120.0         # drop a bucket unseen for 2 minutes

def check_rate_limit(client_ip):
    global _rate_last_sweep
    now = time.time()
    with _rate_lock:
        # Bound memory: periodically drop buckets for IPs that went idle, so a
        # scan across many source IPs can't grow the dict without limit.
        if now - _rate_last_sweep > _RATE_SWEEP_INTERVAL:
            for ip in [ip for ip, b in _rate_buckets.items() if now - b["last"] > _RATE_IDLE_TTL]:
                del _rate_buckets[ip]
            _rate_last_sweep = now
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
            # Add headers. Keyword args so this works on gspread 5.12+ and 6.x
            # (positional update(range, values) was removed in gspread 6).
            worksheet.update(range_name='A1:H1', values=[[
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
    # Static HTML (no user input in the template) — return directly rather than
    # running it through the Jinja renderer, which would treat any stray {{ }}
    # as a template expression (SSTI surface).
    return html

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
        ok, auth_error = verify_upload_token(
            request.headers.get(UPLOAD_AUTH_HEADER, ''), config)
        if not ok:
            status = 401 if auth_error == 'Unauthorized' else 503
            return jsonify({'status': 'error', 'message': auth_error}), status

        # Rate limit: 30 req/min per IP
        client_ip = request.remote_addr or '127.0.0.1'
        if not check_rate_limit(client_ip):
            return jsonify({'status': 'error', 'message': 'Rate limit exceeded'}), 429

        data = request.get_json()
        device_name, pH, temperature, timestamp, reading_number = validate_reading_payload(data)
        
        # Find matching Tilt data
        tilt_match = None
        if config.get('auto_match_tilt', True):
            tilt_match = find_matching_tilt_reading(timestamp, config, TILT_DB_PATH)
        
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
        
    except (ValueError, TypeError) as e:
        # Bad client input — log detail server-side, return a generic 400 so we
        # don't echo internal exception text back to the caller.
        print(f"Invalid pH payload: {e}")
        return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400
    except Exception as e:
        print(f"Error receiving pH data: {e}")
        return jsonify({'status': 'error', 'message': 'Internal error'}), 500

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
        'config': public_config_snapshot(config, TILT_DB_PATH)
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
    
    # Simple HTML table view. Escape every DB-derived string: device_name is
    # sanitized on ingest, but matched_tilt_color/timestamp come from the Tilt
    # DB and must not be able to inject markup (stored XSS).
    def esc(v):
        return html.escape(str(v)) if v is not None else "N/A"

    html_out = '<html><head><title>pHloat Data</title></head><body>'
    html_out += '<h1>pHloat pH Data</h1><a href="/">Back to Dashboard</a><br><br>'
    html_out += '<table border="1"><tr>'
    html_out += '<th>Device</th><th>pH</th><th>Temp</th><th>Timestamp</th>'
    html_out += '<th>Tilt Color</th><th>SG</th></tr>'

    for row in rows:
        html_out += f'<tr><td>{esc(row["device_name"])}</td>'
        html_out += f'<td>{row["pH"]:.2f}</td>'
        html_out += f'<td>{esc(row["temperature"]) if row["temperature"] else "N/A"}</td>'
        html_out += f'<td>{esc(row["timestamp"])}</td>'
        html_out += f'<td>{esc(row["matched_tilt_color"]) if row["matched_tilt_color"] else "N/A"}</td>'
        html_out += f'<td>{esc(row["matched_tilt_sg"]) if row["matched_tilt_sg"] else "N/A"}</td></tr>'

    html_out += '</table></body></html>'
    return html_out

@app.route('/config')
def view_config():
    """Configuration page (secrets redacted)"""
    return jsonify(public_config_snapshot(config, TILT_DB_PATH))

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
    app.run(host=config.get('bind_host', '0.0.0.0'), port=port, debug=False)