#!/usr/bin/env python3
"""pHloat hub web server.

WHAT THIS PROGRAM DOES
    It runs on the Raspberry Pi and waits for two kinds of visitor on the local network:
      1. Devices (the pHloat sensor, the fermenter controller) sending readings. They POST a
         small JSON message to /api/ph or /api/readings.
      2. People with a web browser. Those pages are defined in ui.py.

RELATED FILES
    tilt_listener.py        a separate program that logs the Tilt over Bluetooth
    backup.py               snapshots, restore, run export
    db.py                   the database
    phloat_upload.py        checks that an upload is well formed
    controller_settings.py  settings the hub sends back to a controller

WORDS USED BELOW
    Flask    A small Python library for writing web servers. `@app.post("/x")` means
             "when a POST request arrives for /x, run the function underneath".
    JSON     A plain-text way of writing data, e.g. {"device": "phloat-1", "pH": 4.31}.
    HTTP status codes   The number every web reply carries: 200 = fine, 400 = your request
             was wrong, 401 = wrong password, 429 = slow down, 503 = not ready.
"""

import os
import threading
import time

from flask import Flask, jsonify, request

import controller_settings
from db import add_readings, connect, device_id, latest_readings, load_config, utc_now
from phloat_upload import UPLOAD_AUTH_HEADER, parse_upload, public_config_snapshot, verify_upload_token
from ui import ui

# ---------------------------------------------------------------------------------------------
# Create the web application and attach the browser pages from ui.py.
# ---------------------------------------------------------------------------------------------
app = Flask(__name__)
# The secret key signs the one-shot status messages ("Saved.") shown after a form is submitted.
# A fresh random key at every start is fine: it only means such a message is lost on restart.
app.secret_key = os.urandom(24)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024    # refuse uploads over 4 MB (recipe files are small)
app.register_blueprint(ui)                            # adds every page defined in ui.py
config = load_config()                                # read config.json once, at start-up

# ---------------------------------------------------------------------------------------------
# Rate limiting: stop a faulty device from flooding the database.
#
# Method: a "token bucket", one per sender address. Each sender has a bucket holding up to 30
# tokens. Every upload costs one token. Tokens refill at half a token per second (30 a minute).
# A sender with an empty bucket is refused until it refills. Normal devices upload a few times
# a minute and never notice.
#
# The lock makes sure two uploads handled at the same moment don't both read and write the
# same bucket and corrupt its count.
# ---------------------------------------------------------------------------------------------
_rate_buckets = {}
_rate_lock = threading.Lock()


def check_rate_limit(client_ip):
    """Return True if this sender may upload now, False if it is going too fast."""
    now = time.time()
    with _rate_lock:
        bucket = _rate_buckets.get(client_ip, {"tokens": 30, "last": now})
        # Add the tokens earned since this sender's last upload, up to the maximum of 30.
        bucket["tokens"] = min(30, bucket["tokens"] + (now - bucket["last"]) * 0.5)
        bucket["last"] = now
        _rate_buckets[client_ip] = bucket
        if bucket["tokens"] < 1.0:
            return False
        bucket["tokens"] -= 1.0
    return True


def _error(message, status):
    """Build an error reply in the same JSON shape every device expects."""
    return jsonify({"status": "error", "message": message}), status


# ---------------------------------------------------------------------------------------------
# The upload address. Two paths, one function:
#   /api/ph        what the pHloat sensor posts to
#   /api/readings  the same thing under a clearer name, used by the controller
# ---------------------------------------------------------------------------------------------
@app.post("/api/ph")
@app.post("/api/readings")
def receive_readings():
    # Step 1: is the sender allowed? Every device sends the shared secret in a request header.
    ok, auth_error = verify_upload_token(request.headers.get(UPLOAD_AUTH_HEADER, ""), config)
    if not ok:
        # 401 = wrong secret. 503 = the hub itself has no secret set yet, so nothing can be accepted.
        return _error(auth_error, 401 if auth_error == "Unauthorized" else 503)

    # Step 2: is the sender going too fast?
    if not check_rate_limit(request.remote_addr or "127.0.0.1"):
        return _error("Rate limit exceeded", 429)

    # Step 3: is the message well formed? parse_upload raises an error describing what is wrong.
    try:
        upload = parse_upload(request.get_json(silent=True))
    except (ValueError, TypeError) as exc:
        return _error(str(exc), 400)

    # Step 4: store it. `try ... finally` guarantees the database is closed even if a step fails.
    conn = connect()
    try:
        dev = device_id(conn, upload["kind"], upload["device"], upload["color"])
        if upload["metrics"]:
            add_readings(conn, dev, upload["metrics"], upload["ts"])
        if upload["status"]:
            conn.execute("UPDATE devices SET status = ? WHERE id = ?", (upload["status"], dev))
            conn.commit()
        # Step 5: a controller also reports the settings it is running. Record them and look up
        # what the hub wants them to be. That answer rides back in this reply, which is how the
        # hub changes a controller without ever having to connect to it.
        desired = controller_settings.sync(conn, dev, upload["settings"], utc_now()) if upload["settings"] else {}
    finally:
        conn.close()
    if upload["metrics"]:
        print(f"Stored {upload['device']}: {upload['metrics']}")
    return jsonify({"status": "success", "message": "Data received", "stored": len(upload["metrics"]),
                    "settings": desired})


# ---------------------------------------------------------------------------------------------
# Two read-only addresses, handy for checking the hub from a browser or a script.
# ---------------------------------------------------------------------------------------------
@app.get("/api/status")
def api_status():
    """Is the hub alive, and how much has it stored? Never reveals the upload secret."""
    conn = connect()
    try:
        total, newest = conn.execute("SELECT COUNT(*), MAX(ts) FROM readings").fetchone()
        devices = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    finally:
        conn.close()
    return jsonify({"status": "online", "total_readings": total, "newest_reading": newest,
                    "total_devices": devices, "config": public_config_snapshot(config)})


@app.get("/api/recent")
def api_recent():
    """The newest value of every measurement on every device."""
    conn = connect()
    try:
        return jsonify({"readings": latest_readings(conn)})
    finally:
        conn.close()


# ---------------------------------------------------------------------------------------------
# Start the server when this file is run directly (the systemd service does exactly that).
# ---------------------------------------------------------------------------------------------
if __name__ == "__main__":
    connect().close()   # opening the database once creates the file and tables on first run
    # host="0.0.0.0" means "answer on the Pi's network address", so other devices on the LAN can
    # reach it. Flask's built-in server is fine for a home network. Never forward this port
    # from your router to the internet: the hub has no logins.
    app.run(host="0.0.0.0", port=config.get("port", 5000), debug=False)
