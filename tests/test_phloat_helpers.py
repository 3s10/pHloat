"""Tests for cleaning device names (tiltpi/phloat_helpers.py).

A device sends its own name, and that name is used in file names and on pages, so anything
other than letters, digits, "-" and "_" must be stripped. Run with:
    python -m unittest discover tests
"""
import sys
import unittest
from pathlib import Path

# Let Python find the hub's modules, which live in the tiltpi folder next to this one.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiltpi"))

from phloat_helpers import sanitize_device_name


class TestSanitizeDeviceName(unittest.TestCase):
    def test_strips_path_characters(self):
        self.assertEqual(sanitize_device_name('../etc/passwd'), 'etcpasswd')

    def test_keeps_valid_name(self):
        self.assertEqual(sanitize_device_name('Fermenter-1'), 'Fermenter-1')

    def test_empty_becomes_sensor(self):
        self.assertEqual(sanitize_device_name('!!!'), 'Sensor')


if __name__ == '__main__':
    unittest.main()
