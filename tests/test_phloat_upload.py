"""Tests for checking an upload before it is stored (tiltpi/phloat_upload.py).

Each test hands parse_upload() a message like a device would send and checks what comes back,
or checks that a bad message is refused. Run with:
    python -m unittest discover tests
"""
import sys
import unittest
from pathlib import Path

# Let Python find the hub's modules, which live in the tiltpi folder next to this one.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiltpi"))

from phloat_upload import UPLOAD_AUTH_HEADER, parse_upload, verify_upload_token


class TestUploadContract(unittest.TestCase):
    def test_v1_payload_still_accepted(self):
        up = parse_upload({
            "device": "Fermenter-1",
            "pH": "4.52",
            "temperature": 18.5,
            "timestamp": "2026-06-10T12:00:00Z",
            "readingNumber": 7,
        })
        self.assertEqual(up["device"], "Fermenter-1")
        self.assertEqual(up["kind"], "phloat")
        self.assertEqual(up["metrics"], {"ph": 4.52, "temp_c": 18.5})
        self.assertEqual(up["ts"], "2026-06-10T12:00:00Z")

    def test_esphome_payload(self):
        up = parse_upload({"device": "phloat-1", "pH": 4.4, "battery": 3.91, "temperature": 19.0,
                           "sg": 1.012, "tiltTemp": 66.2, "tiltColor": "0x10"})
        self.assertEqual(up["metrics"], {"ph": 4.4, "temp_c": 19.0, "sg": 1.012, "battery_v": 3.91})
        self.assertEqual(up["color"], "red")
        self.assertIsNone(up["ts"])

    def test_free_form_metrics_without_ph(self):
        up = parse_upload({"device": "fv1-temps", "metrics": {"jacket_temp_c": 11.5, "rod_temp_c": 21}})
        self.assertEqual(up["kind"], "node")
        self.assertEqual(up["metrics"], {"jacket_temp_c": 11.5, "rod_temp_c": 21.0})

    def test_rejects_bad_uploads(self):
        for bad in (None, {"device": "x"}, {"device": "x", "pH": 15}, {"device": "x", "pH": "nan"},
                    {"device": "x", "metrics": {"DROP TABLE": 1}}, {"device": "x", "pH": 4, "tiltColor": "0x99"}):
            with self.assertRaises((ValueError, TypeError), msg=repr(bad)):
                parse_upload(bad)

    def test_verify_token(self):
        config = {"upload_secret": "secret-token"}
        self.assertEqual(verify_upload_token("secret-token", config), (True, None))
        self.assertEqual(verify_upload_token("wrong", config), (False, "Unauthorized"))
        self.assertEqual(verify_upload_token("x", {}), (False, "Upload secret not configured"))

    def test_auth_header_constant(self):
        self.assertEqual(UPLOAD_AUTH_HEADER, "X-pHloat-Token")


if __name__ == "__main__":
    unittest.main()
