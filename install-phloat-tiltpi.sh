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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/tiltpi/phloat_server.py" "$PHLOAT_DIR/phloat_server.py"
cp "$SCRIPT_DIR/tiltpi/phloat_helpers.py" "$PHLOAT_DIR/phloat_helpers.py"
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
  "port": $PHLOAT_PORT,
  "upload_secret": ""
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
