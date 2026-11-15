"""Settings a fermenter controller accepts from the hub. The hub holds the master copy.

THE PROBLEM
    You want to change a controller's target temperature (and everything else) from the hub's
    web page. The obvious way, the hub connecting to the controller, needs the hub to know the
    controller's network address and needs the controller to run its own little web server.

THE METHOD USED INSTEAD
    The controller already contacts the hub every 15 seconds. So the settings travel on that
    existing conversation, and the controller never needs an open port:

      1. Controller -> hub:  "Here are the settings I am running."            ("reported")
      2. Hub -> controller:  "Here is what they should be."  (in the reply)   ("desired")
      3. The controller applies any that differ and saves them in its own flash memory,
         so it keeps working with the last settings even if the hub disappears.

    The first time the hub hears from a controller it has no opinion yet, so it adopts the
    controller's reported settings as the desired ones.

    The hub always wins: if a setting is changed anywhere else (for example in Home Assistant),
    the controller reports the new value, the hub answers with its own, and it is put back.

WHERE IT IS STORED
    Table `device_settings` (see db.py), one row per setting per controller, holding both the
    desired and the last reported value. If they differ, the change is still "waiting".

KEEP IN STEP
    The same setting names and the same allowed ranges are checked again inside
    esphome/fermenter_controller.yaml. Change a range here and change it there too.
"""

import json
import math

from phloat_helpers import TILT_COLORS

# ---------------------------------------------------------------------------------------------
# The list of settings. This table drives everything: validation, the web form, and the labels.
#   number:  key: (label, "float" or "int", lowest allowed, highest allowed, unit)
#   choice:  key: (label, "choice", [allowed options])
#   on/off:  key: (label, "bool")
# ---------------------------------------------------------------------------------------------
SPEC = {
    "target_c": ("Target temperature", "float", 0, 30, "°C"),
    "mode": ("Mode", "choice", ["auto", "cool", "heat", "off"]),      # auto = heat or cool as needed
    "deadband_c": ("Dead zone either side of target", "float", 0.1, 3, "°C"),
    # PID gains: how hard the controller reacts. Explained in esphome/README.md.
    "kp": ("PID gain: proportional", "float", 0, 10, ""),
    "ki": ("PID gain: integral", "float", 0, 1, ""),
    "kd": ("PID gain: derivative", "float", 0, 100, ""),
    "warm_fluid_max_c": ("Never pump warming fluid hotter than", "float", 20, 45, "°C"),
    "min_delta_c": ("Fluid must differ from the beer by at least", "float", 0, 10, "°C"),
    "pump_min_pct": ("Slowest useful pump speed", "float", 0, 100, "%"),
    "tilt_color": ("Tilt to follow", "choice", sorted(TILT_COLORS.values())),
    "tilt_timeout_s": ("Tilt counts as lost after", "int", 60, 3600, "s"),
    "prefer_well_probe": ("Use the thermowell probe first, Tilt as backup", "bool"),
}


def clean(key: str, raw):
    """Check one setting. Returns the value in its proper type, or raises ValueError.

    Used for values typed into the web form AND for values a controller reports, so nothing
    out of range can be stored from either direction.
    """
    if key not in SPEC:
        raise ValueError(f"Unknown setting: {key}")
    label, kind = SPEC[key][0], SPEC[key][1]

    if kind == "bool":
        # A web form sends text ("on"); a controller sends a real true/false.
        if isinstance(raw, str):
            return raw.strip().lower() in ("1", "true", "on", "yes")
        return bool(raw)

    if kind == "choice":
        value = str(raw).strip().lower()
        if value not in SPEC[key][2]:
            raise ValueError(f"{label}: must be one of {', '.join(SPEC[key][2])}")
        return value

    # Otherwise it is a number: must parse, must be finite, must be inside the allowed range.
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{label}: '{raw}' is not a number") from None
    lower, upper = SPEC[key][2], SPEC[key][3]
    if not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"{label}: must be between {lower} and {upper}")
    # Rounding to 5 decimal places stops tiny floating-point differences (0.30000001 vs 0.3)
    # from making a setting look "changed" when it is not.
    return int(round(value)) if kind == "int" else round(value, 5)


def clean_reported(raw) -> dict:
    """Settings as a controller reports them: keep the valid ones, quietly drop the rest.

    Dropping (rather than refusing the whole upload) means one odd value never stops the
    controller's readings from being logged.
    """
    out = {}
    for key, value in (raw if isinstance(raw, dict) else {}).items():
        try:
            out[key] = clean(key, value)
        except ValueError:
            pass
    return out


def sync(conn, device_id: int, reported: dict, ts: str) -> dict:
    """Record what the controller says it is running; return what it SHOULD be running.

    The SQL does two different things depending on whether the hub has seen this setting before:
      - never seen:  insert a row with desired = reported (adopt the controller's value)
      - seen before: update only `reported`; `desired` is left exactly as the hub has it
    """
    for key, value in reported.items():
        conn.execute(
            "INSERT INTO device_settings (device_id, key, desired, reported, reported_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (device_id, key) DO UPDATE SET reported = excluded.reported, reported_at = excluded.reported_at",
            (device_id, key, json.dumps(value), json.dumps(value), ts))
    conn.commit()
    # Values are stored as JSON text so a number, a word and true/false all fit in one column.
    return {row["key"]: json.loads(row["desired"]) for row in
            conn.execute("SELECT key, desired FROM device_settings WHERE device_id = ?", (device_id,))}


def set_desired(conn, device_id: int, values: dict) -> None:
    """Change what the hub wants (called when the Controllers page form is saved).

    UPDATE only touches settings the controller has already reported, so the hub can never
    invent a setting the controller does not have.
    """
    for key, value in values.items():
        conn.execute("UPDATE device_settings SET desired = ? WHERE device_id = ? AND key = ?",
                     (json.dumps(clean(key, value)), device_id, key))
    conn.commit()
