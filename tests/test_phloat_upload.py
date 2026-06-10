import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiltpi"))

from phloat_upload import UPLOAD_AUTH_HEADER, validate_reading_payload, verify_upload_token


class TestUploadContract(unittest.TestCase):
    def test_validate_payload(self):
        device, pH, temp, ts, num = validate_reading_payload({
            "device": "Fermenter-1",
            "pH": "4.52",
            "temperature": 18.5,
            "timestamp": "2026-06-10T12:00:00",
            "readingNumber": 7,
        })
        self.assertEqual(device, "Fermenter-1")
        self.assertAlmostEqual(pH, 4.52)
        self.assertEqual(temp, 18.5)
        self.assertEqual(num, 7)

    def test_rejects_invalid_ph(self):
        with self.assertRaises(ValueError):
            validate_reading_payload({"device": "x", "pH": 15})

    def test_verify_token(self):
        config = {"upload_secret": "secret-token"}
        ok, err = verify_upload_token("secret-token", config)
        self.assertTrue(ok)
        self.assertIsNone(err)

        ok, err = verify_upload_token("wrong", config)
        self.assertFalse(ok)
        self.assertEqual(err, "Unauthorized")

    def test_auth_header_constant(self):
        self.assertEqual(UPLOAD_AUTH_HEADER, "X-pHloat-Token")


if __name__ == "__main__":
    unittest.main()
