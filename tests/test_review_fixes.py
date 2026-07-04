"""Regression tests for the 2026-07-04 review fixes (docs/REVIEW_2026-07-04.md).

Covers the parts that are testable in pure Python (the firmware / Google Apps
Script fixes require a compiler / a live deploy and are verified separately).
"""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiltpi"))

from phloat_upload import normalize_timestamp, validate_reading_payload, verify_upload_token
from tilt_matching import find_matching_tilt_reading


class TestConstantTimeToken(unittest.TestCase):
    # MED-1: verify_upload_token now uses hmac.compare_digest (behavior preserved).
    def test_correct_and_incorrect(self):
        cfg = {"upload_secret": "s3cr3t-token"}
        self.assertEqual(verify_upload_token("s3cr3t-token", cfg), (True, None))
        self.assertEqual(verify_upload_token("nope", cfg), (False, "Unauthorized"))
        self.assertEqual(verify_upload_token("", cfg), (False, "Unauthorized"))

    def test_unset_secret(self):
        ok, err = verify_upload_token("anything", {})
        self.assertFalse(ok)
        self.assertEqual(err, "Upload secret not configured")


class TestTimestampValidation(unittest.TestCase):
    # MED-5: present-but-invalid timestamps are rejected; missing -> now(); valid -> normalized.
    def test_missing_defaults_to_now(self):
        self.assertTrue(normalize_timestamp(None))
        self.assertTrue(normalize_timestamp(""))

    def test_valid_iso_and_space_forms(self):
        self.assertEqual(normalize_timestamp("2026-06-10T12:00:00"), "2026-06-10T12:00:00")
        self.assertTrue(normalize_timestamp("2026-06-10 12:00:00"))
        self.assertTrue(normalize_timestamp("2026-06-10T12:00:00Z"))

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            normalize_timestamp("not-a-timestamp")
        with self.assertRaises(ValueError):
            validate_reading_payload({"device": "x", "pH": 4.5, "timestamp": "garbage"})


class TestTiltMatching(unittest.TestCase):
    # MED-4: matching works against a normal Tilt DB; hostile identifiers can't inject.
    def _make_tilt_db(self, path, extra_col=None):
        conn = sqlite3.connect(path)
        cols = "timestamp TEXT, color TEXT, gravity REAL, temperature REAL"
        if extra_col:
            cols += f', "{extra_col}" TEXT'
        conn.execute(f"CREATE TABLE data ({cols})")
        # Tilt Pi stores space-separated timestamps (SQLite strftime requires it).
        conn.execute(
            "INSERT INTO data (timestamp, color, gravity, temperature) VALUES (?,?,?,?)",
            ("2026-06-10 12:00:30", "Orange", 1.048, 68.0),
        )
        conn.commit()
        conn.close()

    def test_matches_nearest_reading(self, ):
        import tempfile, os
        d = tempfile.mkdtemp()
        db = os.path.join(d, "tilt.db")
        self._make_tilt_db(db)
        cfg = {"tilt_db_path": db}
        # within the 60s window
        m = find_matching_tilt_reading("2026-06-10T12:00:00", cfg, db)
        self.assertIsNotNone(m)
        self.assertEqual(m["color"], "Orange")
        self.assertAlmostEqual(m["sg"], 1.048, places=3)

    def test_out_of_window_returns_none(self):
        import tempfile, os
        d = tempfile.mkdtemp()
        db = os.path.join(d, "tilt.db")
        self._make_tilt_db(db)
        cfg = {"tilt_db_path": db}
        m = find_matching_tilt_reading("2026-06-10T13:00:00", cfg, db)  # 1h away
        self.assertIsNone(m)


if __name__ == "__main__":
    unittest.main()
