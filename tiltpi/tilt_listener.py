#!/usr/bin/env python3
"""Tilt listener: hear every Tilt hydrometer in Bluetooth range and log it to the database.

This is the program that replaces TiltPi. It runs on the Raspberry Pi as its own service,
separate from the web server, and does one job forever: listen, decode, store.

It needs the `bleak` library (a Python Bluetooth library). On Linux, bleak talks to the
system's Bluetooth service, so this runs as an ordinary user. It does not need root.

How a Tilt's message is decoded is explained in phloat_helpers.py.
"""

import asyncio
import time

from bleak import BleakScanner

import ha_publish
from db import add_readings, connect, device_id, load_config
from phloat_helpers import parse_tilt

# Bluetooth messages carry a "company ID" saying whose layout they use. A Tilt uses Apple's
# iBeacon layout, so its data arrives filed under Apple's ID, which is 0x004C.
APPLE = 0x004C


async def main():
    # A Tilt broadcasts about once a second. Storing every broadcast would be roughly 86,000
    # rows a day per Tilt, and fermentation changes over hours, so only one reading per Tilt is
    # kept per interval (default 60 seconds; change tilt_log_interval_seconds in config.json).
    config = load_config()
    interval = config["tilt_log_interval_seconds"]
    conn = connect()
    loop = asyncio.get_running_loop()
    last_stored = {}   # Bluetooth address -> the time its last reading was stored

    def on_advert(device, advert):
        """Called by bleak for EVERY Bluetooth broadcast it hears, from any device nearby."""
        # Try to decode it as a Tilt. For phones, headphones and so on this returns None.
        tilt = parse_tilt(advert.manufacturer_data.get(APPLE, b""))
        # Ignore non-Tilts, and Tilts that were stored less than `interval` seconds ago.
        # time.monotonic() is a stopwatch that never jumps, unlike the wall clock.
        if tilt is None or time.monotonic() - last_stored.get(device.address, -interval) < interval:
            return
        last_stored[device.address] = time.monotonic()
        color, sg, temp_c = tilt
        # A Tilt is identified by its Bluetooth address (unique per Tilt) plus its colour.
        # rssi is the signal strength: a number like -70; closer to 0 means a stronger signal.
        dev = device_id(conn, "tilt", device.address, color)
        add_readings(conn, dev, {"sg": sg, "temp_c": temp_c, "rssi": advert.rssi})
        print(f"Tilt {color} {device.address}: SG {sg:.4f}, {temp_c:.1f} C, {advert.rssi} dBm")
        # Pass the reading on to Home Assistant, if that is set up (see ha_publish.py).
        # run_in_executor does the sending on a helper thread, so a slow or absent
        # Home Assistant can never make this listener miss Bluetooth messages.
        if config["ha_url"]:
            name = conn.execute("SELECT name FROM devices WHERE id = ?", (dev,)).fetchone()["name"]
            states = ha_publish.states_for_tilt(color, device.address, name, sg, temp_c, advert.rssi)
            loop.run_in_executor(None, ha_publish.publish, config, states)

    # Start scanning. `async with` keeps the scanner running until the block ends, and
    # waiting on an Event that is never set means the block never ends: listen forever.
    async with BleakScanner(on_advert):
        await asyncio.Event().wait()


# Run main() only when this file is started directly.
if __name__ == "__main__":
    asyncio.run(main())
