"""Shared upload contract helpers for Tilt Pi server."""

import hmac
import json
import os
from datetime import datetime
from pathlib import Path

from phloat_helpers import sanitize_device_name

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "integration" / "upload_contract.json"
with CONTRACT_PATH.open(encoding="utf-8") as f:
    UPLOAD_CONTRACT = json.load(f)

UPLOAD_AUTH_HEADER = UPLOAD_CONTRACT["auth_header"]
TIME_MATCH_WINDOW = UPLOAD_CONTRACT["time_match_window_seconds"]


def get_upload_secret(config: dict) -> str:
    return os.environ.get("PHLOAT_UPLOAD_SECRET") or config.get("upload_secret") or ""


def verify_upload_token(supplied: str, config: dict) -> tuple[bool, str | None]:
    expected = get_upload_secret(config)
    if not expected:
        return False, "Upload secret not configured"
    # Constant-time compare so response timing can't be used to recover the token.
    if not hmac.compare_digest(str(supplied or ""), str(expected)):
        return False, "Unauthorized"
    return True, None


def normalize_timestamp(value) -> str:
    """Validate/normalize an incoming timestamp to ISO-8601.

    Missing (None/"") -> now(). A present but unparseable value raises
    ValueError (the Google Apps Script path already rejects these; the Tilt Pi
    path used to store them verbatim and silently break Tilt matching).
    """
    if value in (None, ""):
        return datetime.now().isoformat()
    text = str(value).strip()
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Invalid timestamp")
    return dt.isoformat()


def validate_reading_payload(data: dict) -> tuple[str, float, float | None, str, int | None]:
    if not data:
        raise ValueError("Missing JSON body")

    device_name = sanitize_device_name(data.get("device"))
    pH = float(data.get("pH"))
    if pH < 0 or pH > 14:
        raise ValueError("Invalid pH value")

    temperature_raw = data.get("temperature")
    temperature = float(temperature_raw) if temperature_raw not in (None, "") else None

    timestamp = normalize_timestamp(data.get("timestamp"))
    reading_number = data.get("readingNumber")
    reading_number = int(reading_number) if reading_number not in (None, "") else None

    return device_name, pH, temperature, timestamp, reading_number


def public_config_snapshot(config: dict, tilt_db_path: str) -> dict:
    return {
        "google_sheets_enabled": config.get("google_sheets_enabled", False),
        "auto_match_tilt": config.get("auto_match_tilt", True),
        "port": config.get("port", 5000),
        "tilt_db_path": config.get("tilt_db_path", tilt_db_path),
        "upload_secret_configured": bool(get_upload_secret(config)),
        "upload_contract_version": UPLOAD_CONTRACT["version"],
    }
