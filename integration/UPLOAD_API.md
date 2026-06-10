# pHloat Remote Upload API

Single contract for relay firmware, Google Apps Script, and Tilt Pi.

See `integration/upload_contract.json` for the machine-readable schema.

## Endpoints

| Destination | URL example | HTTPS |
|-------------|-------------|-------|
| Google Apps Script | `https://script.google.com/macros/s/.../exec` | Required (relay upgrades http→https) |
| Tilt Pi | `http://192.168.1.50:5000/api/ph` | Optional on LAN |

## Request

```
POST /…
Content-Type: application/json
X-pHloat-Token: <shared secret>
```

```json
{
  "device": "Fermenter-1",
  "pH": "4.52",
  "temperature": "18.5",
  "timestamp": "2026-06-10 12:00:00",
  "readingNumber": 42
}
```

## Relay configuration

On the relay **Configuration** page:

1. Enable **Remote upload**
2. Set **Upload URL** to either endpoint above
3. Set **Upload Token** to match `PHLOAT_UPLOAD_SECRET` (GAS Script Properties) or `upload_secret` in Tilt Pi `config.json`

The relay uses one code path (`uploadReadingRemote`) for both destinations.

## Tilt matching

- **Tilt Pi:** SQLite query in `tiltpi/tilt_matching.py` (±60 s window)
- **Google Apps Script:** Sheet scan in `GoogleAppsScript.js` (same window, closest row across all Tilt sheets)

## Editing Web UI HTML

HTML lives in `web/relay/*.html` and `web/sensor/config.html`. After edits:

```bash
python scripts/embed_web_ui.py
```

Then reflash the ESP32 sketch.
