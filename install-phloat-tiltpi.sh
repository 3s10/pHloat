#!/bin/bash
#
# pHloat hub installer for a Raspberry Pi (Raspberry Pi OS, Pi 3 or newer).
#
# Sets up, running straight from this checkout:
#   phloat-server          receives readings from pHloat nodes on the LAN
#   phloat-tilt            logs every Tilt in Bluetooth range (replaces TiltPi)
#   phloat-backup.timer    nightly snapshot, pushed to the rclone remote if one is configured
#
# Usage:  git clone <this repo> && cd pHloat_Project && ./install-phloat-tiltpi.sh
# Re-running is safe. It never touches an existing database or config.json.

# Stop at the first error instead of carrying on (-e), treat an unset variable as an error (-u),
# and notice a failure anywhere in a chain of commands (pipefail).
set -euo pipefail

# Work out where things are: this checkout (REPO), the data folder (DATA), the private Python
# environment (VENV), and which user the services should run as.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${PHLOAT_DATA:-$HOME/phloat-data}"
VENV="$REPO/venv"
RUN_USER="$(id -un)"

echo "pHloat hub: code $REPO, data $DATA, user $RUN_USER"

# Install the system programs the hub needs: Python, the Bluetooth service, and rclone (which
# copies backups to Google Drive).
sudo apt-get update
sudo apt-get install -y python3 python3-venv bluez rclone

# A "virtual environment" is a private folder of Python libraries just for the hub, so
# installing them can't disturb anything else on the Pi. flask = web server, bleak = Bluetooth.
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install flask bleak

# Create the data folder and, the first time only, a config.json containing a freshly generated
# upload secret. An existing config.json is never touched.
mkdir -p "$DATA"
if [ ! -f "$DATA/config.json" ]; then
    # Generated on the Pi and written only to config.json (mode 600). Copy it into each node's secrets.yaml.
    SECRET="$("$VENV/bin/python" -c 'import secrets; print(secrets.token_urlsafe(24))')"
    umask 077
    cat > "$DATA/config.json" << EOF
{
  "port": 5000,
  "upload_secret": "$SECRET",
  "tilt_log_interval_seconds": 60,
  "backup_remote": "",
  "runs_remote": "",
  "full_backup_every_days": 7
}
EOF
    echo "Created $DATA/config.json with a new upload secret."
fi

# systemd is the part of Linux that starts programs at boot and restarts them if they crash.
# Each program needs a small "unit" file describing it. This function writes one.
unit() {   # unit <name> <description> <script and args>
    sudo tee "/etc/systemd/system/$1.service" > /dev/null << EOF
[Unit]
Description=$2
After=network-online.target bluetooth.target

[Service]
User=$RUN_USER
WorkingDirectory=$REPO/tiltpi
Environment=PHLOAT_DATA=$DATA
ExecStart=$VENV/bin/python $REPO/tiltpi/$3
$4

[Install]
WantedBy=multi-user.target
EOF
}

unit phloat-server "pHloat hub server" "phloat_server.py" "Restart=always
RestartSec=10"
unit phloat-tilt "pHloat Tilt listener" "tilt_listener.py" "Restart=always
RestartSec=10"
unit phloat-backup "pHloat nightly backup" "backup.py backup" "Type=oneshot"

# A timer unit: run the backup once a night at 03:15. "Persistent" means a run missed because
# the Pi was off happens at the next start.
sudo tee /etc/systemd/system/phloat-backup.timer > /dev/null << EOF
[Unit]
Description=pHloat nightly backup

[Timer]
OnCalendar=*-*-* 03:15:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Tell systemd to read the new files, then switch the services on (enable = start at every boot,
# --now = also start right away).
sudo systemctl daemon-reload
sudo systemctl disable phloat-backup.service 2> /dev/null || true   # the timer starts it, not boot
sudo systemctl enable --now phloat-server phloat-tilt phloat-backup.timer

echo
echo "Hub:      http://$(hostname -I | awk '{print $1}'):5000"
echo "Logs:     sudo journalctl -u phloat-server -u phloat-tilt -f"
echo "Secret:   in $DATA/config.json (upload_secret)"
echo "Backups:  run 'rclone config' to add a Google Drive remote, then set backup_remote in config.json"
echo "Restore:  PHLOAT_DATA=$DATA $VENV/bin/python $REPO/tiltpi/backup.py restore"
echo "TiltPi:   if it is installed, stop it so two programs don't share the Bluetooth radio."
