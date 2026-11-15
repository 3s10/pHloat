"""Checking an upload before anything is stored.

A device's upload is the one place where data from outside enters the hub, so every field is
checked here. The rule: nothing reaches the database unless this file has looked at it.

The agreed message format is written down in integration/upload_contract.json, which is shared
by the firmware and the hub. A typical upload from the pHloat sensor:

    POST /api/ph
    X-pHloat-Token: <the shared secret>
    {"device": "phloat-1", "pH": 4.31, "temperature": 19.2, "sg": 1.012, "battery": 3.9,
     "tiltColor": "0x10"}

and from the fermenter controller:

    {"device": "fermenter-1", "status": "Cooling",
     "metrics": {"beer_temp_c": 19.4, "coolant_temp_c": 2.1},
     "settings": {"target_c": 19, "mode": "auto"}}
"""

import hmac
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from controller_settings import clean_reported
from phloat_helpers import TILT_COLORS, sanitize_device_name

# ---------------------------------------------------------------------------------------------
# Load the shared contract file once, when this module is first imported.
# ---------------------------------------------------------------------------------------------
CONTRACT_PATH = Path(__file__).resolve().parents[1] / "integration" / "upload_contract.json"
with CONTRACT_PATH.open(encoding="utf-8") as f:
    UPLOAD_CONTRACT = json.load(f)

UPLOAD_AUTH_HEADER = UPLOAD_CONTRACT["auth_header"]   # the header name: "X-pHloat-Token"

# Fields with their own name in the message, and the metric name each is stored under.
FIELD_METRICS = {"pH": "ph", "temperature": "temp_c", "sg": "sg", "battery": "battery_v"}
# Any other measurement arrives inside "metrics": {...}. Its name must look like a simple
# identifier: starts with a lowercase letter, then lowercase letters, digits or underscores,
# at most 40 characters. That keeps odd text out of the database and out of CSV headers.
METRIC_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


# ---------------------------------------------------------------------------------------------
# The shared secret ("token").
# Every device is given the same secret string and sends it with each upload. It is a simple
# password that stops other things on the network from writing into the database.
# ---------------------------------------------------------------------------------------------
def get_upload_secret(config: dict) -> str:
    """The secret, from the PHLOAT_UPLOAD_SECRET environment variable or from config.json."""
    return os.environ.get("PHLOAT_UPLOAD_SECRET") or config.get("upload_secret") or ""


def verify_upload_token(supplied: str, config: dict) -> tuple[bool, str | None]:
    """Check the secret a device sent. Returns (True, None) or (False, reason)."""
    expected = get_upload_secret(config)
    if not expected:
        # No secret set on the hub: refuse everything rather than accept anything.
        return False, "Upload secret not configured"
    # compare_digest compares in a way that takes the same time whether the first or the last
    # character is wrong, so the time taken gives no hint about how close a guess was.
    if not hmac.compare_digest(str(supplied).encode(), expected.encode()):
        return False, "Unauthorized"
    return True, None


def _number(name: str, raw) -> float:
    """Turn a value into a number, refusing 'not a number' and infinity."""
    value = float(raw)                       # raises an error for text such as "abc"
    if not math.isfinite(value):
        raise ValueError(f"{name} is not a finite number")
    return value


# ---------------------------------------------------------------------------------------------
# The main check.
# ---------------------------------------------------------------------------------------------
def parse_upload(data: dict) -> dict:
    """Validate one upload and return its contents in a tidy, trusted form.

    Returns a dictionary with:
        device    the device's name, cleaned
        kind      "phloat" if the upload contains a pH reading, otherwise "node"
        color     Tilt colour name, or None
        ts        the reading's time in UTC text form, or None meaning "use the time it arrived"
        metrics   {metric name: number}
        settings  a controller's current settings, already validated (may be empty)
        status    a short status line, or None
    Raises ValueError (or TypeError) with a readable message if the upload is not acceptable.
    """
    if not isinstance(data, dict):
        raise ValueError("Missing JSON body")

    # --- measurements: the named fields first, then anything in "metrics" ---------------------
    metrics = {}
    for field, metric in FIELD_METRICS.items():
        if data.get(field) not in (None, ""):
            metrics[metric] = _number(field, data[field])
    extra = data.get("metrics") or {}
    if not isinstance(extra, dict):
        raise ValueError("metrics must be an object")
    for name, raw in extra.items():
        if not METRIC_NAME_RE.match(str(name)):
            raise ValueError(f"Bad metric name: {name!r}")
        metrics[name] = _number(name, raw)

    # --- controller settings (invalid or unknown ones are silently dropped) -------------------
    settings = clean_reported(data.get("settings"))

    # An upload must carry something: readings, or a controller's settings check-in.
    if not metrics and not settings:
        raise ValueError("No readings in upload")
    # pH only exists between 0 and 14. Anything else is a broken sensor or a broken message.
    if "ph" in metrics and not 0 <= metrics["ph"] <= 14:
        raise ValueError("Invalid pH value")

    # --- Tilt colour: accepted as a name ("red") or as the Tilt's ID byte ("0x10") -------------
    color = None
    if data.get("tiltColor") not in (None, ""):
        raw = str(data["tiltColor"]).lower()
        # int(raw, 0) reads "0x10" as hexadecimal and "16" as decimal.
        color = raw if raw in TILT_COLORS.values() else TILT_COLORS.get(int(raw, 0))
        if color is None:
            raise ValueError("Unknown Tilt colour")

    # --- timestamp: optional. Stored in UTC whatever form it arrives in ------------------------
    ts = None
    if data.get("timestamp"):
        # "Z" on the end of a time means UTC; Python's parser wants it written as +00:00.
        parsed = datetime.fromisoformat(str(data["timestamp"]).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()   # no time zone given: assume the hub's local time
        ts = parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "device": sanitize_device_name(data.get("device")),
        "kind": "phloat" if "ph" in metrics else "node",
        "color": color,
        "ts": ts,
        "metrics": metrics,
        "settings": settings,
        "status": str(data.get("status") or "")[:80] or None,   # at most 80 characters
    }


def public_config_snapshot(config: dict) -> dict:
    """The parts of the configuration that are safe to show on /api/status.

    It says WHETHER a secret is set, never what it is.
    """
    return {
        "port": config.get("port", 5000),
        "upload_secret_configured": bool(get_upload_secret(config)),
        "backup_remote_configured": bool(config.get("backup_remote")),
        "tilt_log_interval_seconds": config.get("tilt_log_interval_seconds"),
        "upload_contract_version": UPLOAD_CONTRACT["version"],
    }
