"""Small shared helpers: cleaning device names and decoding a Tilt's radio broadcast.

These have no dependencies on the rest of the hub, which makes them easy to test on their own
(see tests/test_phloat_helpers.py and tests/test_hub.py).
"""

import re
import struct

# ---------------------------------------------------------------------------------------------
# Device names.
# A device sends its own name with every upload, and that name ends up in file names and on web
# pages. Anything other than letters, digits, underscore and hyphen is stripped so a name can
# never contain a slash, a quote or other characters that mean something special elsewhere.
# ---------------------------------------------------------------------------------------------
DEVICE_NAME_RE = re.compile(r'[^A-Za-z0-9_-]')   # matches every character that is NOT allowed


def sanitize_device_name(name):
    """Return `name` with unsafe characters removed; 'Sensor' if nothing is left."""
    cleaned = DEVICE_NAME_RE.sub('', str(name or ''))
    return cleaned or 'Sensor'


# ---------------------------------------------------------------------------------------------
# Tilt hydrometers.
#
# A Tilt has no connection or pairing. About once a second it shouts a short radio message that
# anything nearby can hear. It uses Apple's "iBeacon" message layout, which was designed for
# shop beacons, and reuses its fields:
#
#     bytes 0-1    02 15          marks the message as an iBeacon
#     bytes 2-17   16-byte ID     a495bbX0-c5b1-4b44-b512-1370f02d74de, where X is the colour
#     bytes 18-19  "major"        temperature in whole degrees Fahrenheit
#     bytes 20-21  "minor"        specific gravity x 1000   (1050 means 1.050)
#     byte  22     transmit power (not used here)
#
# A Tilt Pro is more precise: it sends temperature x 10 and gravity x 10000.
# The only thing that tells Tilts apart is the colour digit, so each colour is a different ID.
# ---------------------------------------------------------------------------------------------
TILT_COLORS = {0x10: 'red', 0x20: 'green', 0x30: 'black', 0x40: 'purple',
               0x50: 'orange', 0x60: 'blue', 0x70: 'yellow', 0x80: 'pink'}
_TILT_UUID_HEAD = bytes.fromhex('a495bb')                       # ID bytes before the colour byte
_TILT_UUID_TAIL = bytes.fromhex('c5b14b44b5121370f02d74de')     # ID bytes after the colour byte


def parse_tilt(mfg: bytes):
    """Decode the 23 bytes of an iBeacon message.

    Returns (colour name, specific gravity, temperature in Celsius),
    or None if the message is not from a Tilt (most Bluetooth messages are not).
    """
    # Reject anything that is the wrong length, is not an iBeacon, or does not carry a Tilt ID.
    if (len(mfg) != 23 or mfg[:2] != b'\x02\x15' or mfg[2:5] != _TILT_UUID_HEAD
            or mfg[6:18] != _TILT_UUID_TAIL or mfg[5] not in TILT_COLORS):
        return None
    # '>HH' = two unsigned 16-bit numbers, most significant byte first ("big-endian").
    major, minor = struct.unpack('>HH', mfg[18:22])
    # A normal gravity reading is around 1000 (1.000). A value of 5000 or more can only be the
    # Tilt Pro's x 10000 scale (around 10000), so that is how the two models are told apart.
    pro = minor >= 5000
    temp_f = major / 10 if pro else major
    return TILT_COLORS[mfg[5]], minor / (10000 if pro else 1000), round((temp_f - 32) / 1.8, 2)
