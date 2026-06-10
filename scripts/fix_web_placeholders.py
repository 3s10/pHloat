#!/usr/bin/env python3
"""Normalize {{PLACEHOLDER}} formatting in web HTML sources."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FIXES = [
    (re.compile(r'value="\s*\n\s*\{\{WIFI_SSID\}\}\s*"'), 'value="{{WIFI_SSID}}"'),
    (re.compile(r'value="\s*\n\s*\{\{NTP_SERVER\}\}\s*"'), 'value="{{NTP_SERVER}}"'),
    (re.compile(r'value="\s*\n\s*\{\{TIMEZONE_OFFSET\}\}\s*"'), 'value="{{TIMEZONE_OFFSET}}"'),
    (re.compile(r'value="\s*\{\{UPLOAD_URL\}\}\s*"'), 'value="{{UPLOAD_URL}}"'),
    (re.compile(r'value="\s*\n\s*\{\{AP_PASSWORD\}\}\s*"'), 'value="{{AP_PASSWORD}}"'),
    (re.compile(r'value="\s*\n\s*\{\{PMK\}\}\s*"'), 'value="{{PMK}}"'),
    (re.compile(r'value="\)\s*\n\s*\{\{API_KEY\}\}\s*"'), 'value="{{API_KEY}}"'),
    (re.compile(r'value="\s*\n\s*\{\{UPLOAD_SECRET\}\}\s*"'), 'value="{{UPLOAD_SECRET}}"'),
    (re.compile(r'checked =\s*\n\s*\{\{WIFI_ENABLED\}\}\s*;'), 'checked = {{WIFI_ENABLED}};'),
    (re.compile(r'checked =\s*\n\s*\{\{SHEETS_ENABLED\}\}\s*;'), 'checked = {{SHEETS_ENABLED}};'),
    (re.compile(r'const sensors =\s*\{\{SENSOR_LIST_JSON\}\}\s*;'), 'const sensors = {{SENSOR_LIST_JSON}};'),
    (re.compile(r'value="\s*\n\s*\{\{DEVICE_NAME\}\}\s*"'), 'value="{{DEVICE_NAME}}"'),
    (re.compile(r'value="\s*\n\s*\{\{RELAY_MAC\}\}\s*"'), 'value="{{RELAY_MAC}}"'),
    (re.compile(r'value="\s*\n\s*\{\{TEMP_PIN\}\}\s*"'), 'value="{{TEMP_PIN}}"'),
]

UPLOAD_SECTION = """      <div class="section">
        <h2>Remote Upload</h2>
        <div class="checkbox-group">
          <input type="checkbox" id="sheetsEnabled" name="sheetsEnabled">
          <label for="sheetsEnabled">Enable remote upload</label>
        </div>
        <label for="googleSheetURL">Upload URL:</label>
        <input type="text" id="googleSheetURL" name="googleSheetURL"
               value="{{UPLOAD_URL}}"
               placeholder="https://script.google.com/... or http://192.168.1.50:5000/api/ph">
        <div class="help-text">Google Apps Script web app or Tilt Pi <code>/api/ph</code>. Same JSON body and <code>X-pHloat-Token</code> header.</div>
      </div>"""


def main() -> None:
    for html_path in (ROOT / "web").rglob("*.html"):
        text = html_path.read_text(encoding="utf-8")
        for pattern, repl in FIXES:
            text = pattern.sub(repl, text)

        if html_path.name == "config.html" and "web/relay" in html_path.as_posix():
            text = re.sub(
                r'      <div class="section">\s*<h2>Google Sheets Integration</h2>[\s\S]*?'
                r'<div class="help-text">Always use the HTTPS URL from your Apps Script deployment</div>\s*</div>',
                UPLOAD_SECTION,
                text,
                count=1,
            )

        html_path.write_text(text, encoding="utf-8")
        print(f"fixed {html_path}")


if __name__ == "__main__":
    main()
