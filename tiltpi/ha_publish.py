"""Send Tilt readings from the hub to Home Assistant, for dashboards and alerts.

WHY THIS EXISTS
    The pHloat sensor and the fermenter controller talk to Home Assistant themselves. A Tilt
    can't: it only broadcasts over Bluetooth, and the hub is the thing that hears it. So for a
    fermenter that has a Tilt and nothing else, the hub passes the readings along.

HOW
    Home Assistant has a web address for setting a sensor's value:
        POST http://<home assistant>:8123/api/states/sensor.<name>
    with a password-like "long-lived access token" in the request header. The hub calls it each
    time it stores a Tilt reading (once a minute per Tilt by default). The connection is made
    BY the Pi, on the local network; nothing connects in to the Pi.

    Home Assistant is only ever told values here. Nothing is read back and no setting changes:
    it stays a display.

SETTING IT UP
    In config.json:
        "ha_url":   "http://homeassistant.local:8123"
        "ha_token": "<a long-lived access token: Home Assistant > your profile > Security>"
    Leave ha_url empty to switch this off (the default). The token is a secret: it is left out
    of every backup, so it must be typed in again after a restore.

LIMIT
    Sensors created this way live in Home Assistant's memory. After Home Assistant restarts
    they reappear at the hub's next reading (within a minute).
"""

import json
import urllib.request


def states_for_tilt(color: str, address: str, name: str | None, sg: float, temp_c: float, rssi: int) -> list[tuple]:
    """Work out what to tell Home Assistant about one Tilt reading.

    Returns a list of (entity id, value, attributes). Keeping this separate from the sending
    makes it easy to test without a Home Assistant.

    The entity id (the sensor's permanent name in Home Assistant) is built from the Tilt's
    colour and the last four characters of its Bluetooth address, so two red Tilts stay apart
    and renaming a Tilt on the hub never breaks a dashboard. The label people see
    ("friendly_name") does follow the hub's name for the device.
    """
    tail = "".join(ch for ch in address.lower() if ch.isalnum())[-4:]
    base = f"sensor.tilt_{color}_{tail}"
    label = name or f"{color.title()} Tilt"
    return [
        (f"{base}_gravity", f"{sg:.4f}",
         {"friendly_name": f"{label} gravity", "unit_of_measurement": "SG", "state_class": "measurement", "icon": "mdi:beer"}),
        (f"{base}_temperature", f"{temp_c:.1f}",
         {"friendly_name": f"{label} temperature", "unit_of_measurement": "°C", "device_class": "temperature",
          "state_class": "measurement"}),
        (f"{base}_signal", str(rssi),
         {"friendly_name": f"{label} signal", "unit_of_measurement": "dBm", "device_class": "signal_strength",
          "state_class": "measurement"}),
    ]


def _post(url: str, token: str, body: dict) -> None:
    """Send one JSON message to Home Assistant. Gives up after 5 seconds."""
    request = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    urllib.request.urlopen(request, timeout=5).close()


def publish(config: dict, states: list[tuple], post=_post) -> bool:
    """Send the states to Home Assistant. Returns True if they were all accepted.

    Does nothing (and returns False) when Home Assistant is not configured.
    A failure is printed and swallowed, never raised: Home Assistant being off must not stop
    the hub from logging. `post` can be replaced by a stand-in, which is how the tests check
    this without a network.
    """
    url, token = (config.get("ha_url") or "").rstrip("/"), config.get("ha_token") or ""
    if not url or not token:
        return False
    try:
        for entity_id, state, attributes in states:
            post(f"{url}/api/states/{entity_id}", token, {"state": state, "attributes": attributes})
        return True
    except Exception as exc:                 # network down, wrong token, Home Assistant restarting...
        print(f"Home Assistant not updated: {exc}")
        return False
