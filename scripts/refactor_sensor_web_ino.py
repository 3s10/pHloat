#!/usr/bin/env python3
"""Replace inline HTML in sensor handleRoot with template-based handler."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SENSOR = ROOT / "pHloat_Sensor" / "pHloat_Sensor.ino"

HANDLER = '''
#include "web_ui_templates.h"
#include "phloat_web.h"

void handleRoot() {
  String html = phloat_load_template(TPL_CONFIG);
  phloat_tpl_replace(html, "{{DEVICE_NAME}}", String(config.deviceName));
  phloat_tpl_replace(html, "{{RELAY_MAC}}", String(config.relayMac));
  phloat_tpl_replace(html, "{{AP_PASSWORD}}", String(config.apPassword));
  phloat_tpl_replace(html, "{{PMK}}", String(config.pmk));
  phloat_tpl_replace(html, "{{TEMP_PIN}}", String(config.tempPin));
  server.send(200, "text/html", html);
}
'''


def main() -> None:
    text = SENSOR.read_text(encoding="utf-8")
    start = text.index("void handleRoot() {")
    end = text.index("void handleSave() {", start)
    SENSOR.write_text(text[:start] + HANDLER.strip() + "\n\n" + text[end:], encoding="utf-8")
    print(f"Refactored {SENSOR}")


if __name__ == "__main__":
    main()
