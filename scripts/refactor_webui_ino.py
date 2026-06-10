#!/usr/bin/env python3
"""Replace inline HTML handlers in pHloat_Relay_WebUI.ino with template-based handlers."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBUI = ROOT / "pHloat_Relay" / "pHloat_Relay_WebUI.ino"

HANDLERS = '''
#include "web_ui_templates.h"
#include "phloat_web.h"

// ═══════════════════════════════════════════════════════════════
//  DASHBOARD (/)
// ═══════════════════════════════════════════════════════════════

void handleRoot() {
  server.send(200, "text/html", phloat_load_template(TPL_DASHBOARD));
}

// ═══════════════════════════════════════════════════════════════
//  CONFIGURATION PAGE (/config)
// ═══════════════════════════════════════════════════════════════

void handleConfig() {
  preferences.begin("relay-config", true);
  String apiKey = preferences.getString("apiKey", "");
  preferences.end();

  String html = phloat_load_template(TPL_CONFIG);
  phloat_tpl_replace(html, "{{WIFI_SSID}}", String(relayConfig.wifiSSID));
  phloat_tpl_replace(html, "{{NTP_SERVER}}", String(relayConfig.ntpServer));
  phloat_tpl_replace(html, "{{TIMEZONE_OFFSET}}", String(relayConfig.timezoneOffset));
  phloat_tpl_replace(html, "{{UPLOAD_URL}}", String(relayConfig.googleSheetURL));
  phloat_tpl_replace(html, "{{AP_PASSWORD}}", String(relayConfig.apPassword));
  phloat_tpl_replace(html, "{{PMK}}", String(relayConfig.pmk));
  phloat_tpl_replace(html, "{{API_KEY}}", apiKey);
  phloat_tpl_replace(html, "{{UPLOAD_SECRET}}", String(relayConfig.uploadSecret));
  phloat_tpl_replace(html, "{{WIFI_ENABLED}}", relayConfig.wifiEnabled ? "true" : "false");
  phloat_tpl_replace(html, "{{SHEETS_ENABLED}}", relayConfig.sheetsEnabled ? "true" : "false");
  server.send(200, "text/html", html);
}

// ═══════════════════════════════════════════════════════════════
//  CALIBRATION PAGE (/calibration)
// ═══════════════════════════════════════════════════════════════

void handleCalibration() {
  String sensorList = "[";
  File root = SPIFFS.open("/");
  bool first = true;

  while (true) {
    File f = root.openNextFile();
    if (!f) break;

    String name = String(f.name());
    f.close();

    if (!name.startsWith("/data/") || !name.endsWith(".csv")) continue;

    int slash = name.lastIndexOf('/');
    int under = name.indexOf('_', slash + 1);
    if (under <= slash) continue;

    String dev = name.substring(slash + 1, under);
    if (sensorList.indexOf("\\"" + dev + "\\"") >= 0) continue;

    if (!first) sensorList += ",";
    sensorList += "\\"" + dev + "\\"";
    first = false;
  }
  root.close();
  sensorList += "]";

  String html = phloat_load_template(TPL_CALIBRATION);
  phloat_tpl_replace(html, "{{SENSOR_LIST_JSON}}", sensorList);
  server.send(200, "text/html", html);
}

// ═══════════════════════════════════════════════════════════════
//  DATA PAGE (/data)
// ═══════════════════════════════════════════════════════════════

void handleData() {
  server.send(200, "text/html", phloat_load_template(TPL_DATA));
}
'''


def main() -> None:
    text = WEBUI.read_text(encoding="utf-8")
    start = text.index("// ── Shared auth check")
    tail_start = text.index("// ═══════════════════════════════════════════════════════════════\n//  SAVE CONFIG")
    head = text[:start]
    tail = text[tail_start:]
    WEBUI.write_text(head + HANDLERS + "\n" + tail, encoding="utf-8")
    print(f"Refactored {WEBUI}")


if __name__ == "__main__":
    main()
