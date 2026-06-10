import re

DEVICE_NAME_RE = re.compile(r'[^A-Za-z0-9_-]')


def sanitize_device_name(name):
    cleaned = DEVICE_NAME_RE.sub('', str(name or ''))
    return cleaned or 'Sensor'
