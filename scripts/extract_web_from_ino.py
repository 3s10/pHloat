#!/usr/bin/env python3
"""One-time helper: extract R\"rawliteral\" HTML blocks from .ino files into web/*.html."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPLACEMENTS = [
    (r'\+\s*String\(relayConfig\.wifiSSID\)\s*\+', '{{WIFI_SSID}}'),
    (r'\+\s*String\(relayConfig\.ntpServer\)\s*\+', '{{NTP_SERVER}}'),
    (r'\+\s*String\(relayConfig\.timezoneOffset\)\s*\+', '{{TIMEZONE_OFFSET}}'),
    (r'\+\s*String\(relayConfig\.googleSheetURL\)\s*\+', '{{UPLOAD_URL}}'),
    (r'\+\s*String\(relayConfig\.apPassword\)\s*\+', '{{AP_PASSWORD}}'),
    (r'\+\s*String\(relayConfig\.pmk\)\s*\+', '{{PMK}}'),
    (r'\+\s*String\(relayConfig\.uploadSecret\)\s*\+', '{{UPLOAD_SECRET}}'),
    (r'\+\s*String\(relayConfig\.wifiEnabled \? "true" : "false"\)\s*\+', '{{WIFI_ENABLED}}'),
    (r'\+\s*String\(relayConfig\.sheetsEnabled \? "true" : "false"\)\s*\+', '{{SHEETS_ENABLED}}'),
    (r'\+\s*sensorList\s*\+', '{{SENSOR_LIST_JSON}}'),
    (r'\+\s*String\(config\.deviceName\)\s*\+', '{{DEVICE_NAME}}'),
    (r'\+\s*String\(config\.relayMac\)\s*\+', '{{RELAY_MAC}}'),
    (r'\+\s*String\(config\.apPassword\)\s*\+', '{{AP_PASSWORD}}'),
    (r'\+\s*String\(config\.pmk\)\s*\+', '{{PMK}}'),
    (r'\+\s*String\(config\.tempPin\)\s*\+', '{{TEMP_PIN}}'),
]

API_KEY_PATTERN = re.compile(
    r'\+\s*String\(\[&\]\(\)\s*\{[\s\S]*?preferences\.getString\("apiKey"[\s\S]*?\}\(\)\)\s*\+',
    re.MULTILINE,
)


def strip_ino_html(block: str) -> str:
    text = block
    text = API_KEY_PATTERN.sub('{{API_KEY}}', text)
    for pattern, repl in REPLACEMENTS:
        text = re.sub(pattern, repl, text)
    text = re.sub(r'\)rawliteral"\s*\+\s*R"rawliteral\(', '', text)
    text = re.sub(r'\)rawliteral"\s*\+\s*R"rawliteral\(', '', text)
    text = re.sub(r'R"rawliteral\(', '', text)
    text = re.sub(r'\)rawliteral";?', '', text)
    return text.strip()


def extract_handler(html_blob: str, handler_name: str) -> str | None:
    marker = f"void {handler_name}()"
    idx = html_blob.find(marker)
    if idx < 0:
        return None
    sub = html_blob[idx:]
    start = sub.find('R"rawliteral(')
    if start < 0:
        return None
    start += len('R"rawliteral(')
    end = sub.find(')rawliteral";', start)
    if end < 0:
        end = sub.find(')rawliteral"', start)
    chunk = sub[start:end]
    return strip_ino_html(chunk)


def write_if_missing(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        print(f"skip existing {path}")
        return
    path.write_text(content + "\n", encoding="utf-8")
    print(f"wrote {path}")


def main() -> None:
    relay_ino = (ROOT / "pHloat_Relay" / "pHloat_Relay_WebUI.ino").read_text(encoding="utf-8")
    sensor_ino = (ROOT / "pHloat_Sensor" / "pHloat_Sensor.ino").read_text(encoding="utf-8")

    relay_map = {
        "dashboard": "handleRoot",
        "config": "handleConfig",
        "calibration": "handleCalibration",
        "data": "handleData",
    }
    for name, handler in relay_map.items():
        content = extract_handler(relay_ino, handler)
        if content:
            write_if_missing(ROOT / "web" / "relay" / f"{name}.html", content)

    sensor_content = extract_handler(sensor_ino, "handleRoot")
    if sensor_content:
        write_if_missing(ROOT / "web" / "sensor" / "config.html", sensor_content)


if __name__ == "__main__":
    main()
