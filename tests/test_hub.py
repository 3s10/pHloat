"""End-to-end checks for the hub: Tilt decoding, intake over HTTP, backup -> wipe -> restore, CSV export.

  python -m unittest discover tests      (needs flask)
"""

import importlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiltpi"))

from phloat_helpers import parse_tilt


# Build the 23 bytes a Tilt would broadcast, so the decoder can be tested without a real Tilt.
def beacon(color_byte, major, minor):
    uuid = bytes.fromhex("a495bb") + bytes([color_byte]) + bytes.fromhex("c5b14b44b5121370f02d74de")
    return b"\x02\x15" + uuid + major.to_bytes(2, "big") + minor.to_bytes(2, "big") + b"\xc5"


# Tests for decoding a Tilt broadcast (tiltpi/phloat_helpers.py).
# Each method whose name starts with test_ is one test; it passes if no assert fails.
class TestParseTilt(unittest.TestCase):
    def test_standard_tilt(self):
        self.assertEqual(parse_tilt(beacon(0x30, 68, 1050)), ("black", 1.05, 20.0))

    def test_tilt_pro(self):
        self.assertEqual(parse_tilt(beacon(0x10, 680, 10505)), ("red", 1.0505, 20.0))

    def test_not_a_tilt(self):
        self.assertIsNone(parse_tilt(b""))
        self.assertIsNone(parse_tilt(beacon(0x90, 68, 1050)))                    # unknown colour
        self.assertIsNone(parse_tilt(b"\x02\x15" + bytes(16) + bytes(5)))        # some other iBeacon


# Tests for the hub as a whole. They talk to the web server exactly as a device or browser
# would, but in memory: no network, no real Pi, and a throwaway database.
class TestHub(unittest.TestCase):
    # Runs before EVERY test: make an empty temporary data folder with a known upload secret,
    # point the hub at it, and start a fresh copy of the web application.
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["PHLOAT_DATA"] = self.tmp
        os.environ.pop("PHLOAT_UPLOAD_SECRET", None)
        Path(self.tmp, "config.json").write_text(json.dumps({"upload_secret": "s3cret"}))
        import phloat_server
        self.server = importlib.reload(phloat_server)   # pick up this test's config
        self.client = self.server.app.test_client()

    # Runs after every test: delete the temporary folder.
    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # Shortcut: send an upload the way a device does, with the secret in the header.
    def post(self, body, token="s3cret", path="/api/ph"):
        return self.client.post(path, json=body, headers={"X-pHloat-Token": token})

    # A wrong secret is refused; an impossible pH and an empty upload are rejected.
    def test_intake_auth_and_validation(self):
        self.assertEqual(self.post({"device": "phloat-1", "pH": 4.4}, token="nope").status_code, 401)
        self.assertEqual(self.post({"device": "phloat-1", "pH": 99}).status_code, 400)
        self.assertEqual(self.post({"device": "phloat-1"}).status_code, 400)

    # A good upload is stored and shows up in the API and on the overview page.
    def test_intake_stores_and_reports(self):
        r = self.post({"device": "phloat-1", "pH": 4.4, "sg": 1.012, "temperature": 19, "battery": 3.9,
                       "tiltColor": "0x10"})
        self.assertEqual((r.status_code, r.json["stored"]), (200, 4))
        r = self.post({"device": "fv1-temps", "metrics": {"jacket_temp_c": 11.5}}, path="/api/readings")
        self.assertEqual(r.status_code, 200)

        recent = {(x["ident"], x["metric"]): x for x in self.client.get("/api/recent").json["readings"]}
        self.assertEqual(recent[("phloat-1", "ph")]["value"], 4.4)
        self.assertEqual(recent[("phloat-1", "ph")]["color"], "red")
        self.assertEqual(recent[("fv1-temps", "jacket_temp_c")]["kind"], "node")
        status = self.client.get("/api/status").json
        self.assertEqual((status["total_readings"], status["total_devices"]), (5, 2))
        self.assertNotIn("s3cret", json.dumps(status))
        self.assertIn("phloat-1", self.client.get("/").get_data(as_text=True))

    # Sixteen nights of backups: the right mix of full and delta snapshots is made, old ones are
    # pruned, and a restore into an empty folder brings every reading back.
    def test_full_delta_prune_restore(self):
        import backup
        import db
        from datetime import datetime, timedelta
        day0 = datetime(2026, 11, 1, 3, 15)
        names = []
        for day in range(16):                                   # 16 nightly runs, one new reading each night
            self.post({"device": "phloat-1", "pH": 4.0 + day / 100})
            if day == 9:                                        # an edit to a small table mid-week
                conn = db.connect()
                conn.execute("INSERT INTO batches (name, fermenter_tag) VALUES ('Pale 12', 'FV-03')")
                conn.commit()
                conn.close()
            path, _ = backup.snapshot(day0 + timedelta(days=day))
            names.append(path.name)
        kinds = [n.rsplit("-", 1)[1][:-4] for n in names]
        self.assertEqual(kinds, ["full"] + ["delta"] * 6 + ["full"] + ["delta"] * 6 + ["full", "delta"])
        kept = [p.name for p in backup._snapshots(backup.backups_dir())]
        self.assertEqual(kept, names[7:])                       # two newest fulls + everything after the older one

        # A dead Pi: brand new, empty data folder, snapshots pulled back down.
        snaps = backup.backups_dir()
        fresh = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, fresh, ignore_errors=True)
        os.environ["PHLOAT_DATA"] = fresh
        self.assertEqual(backup.restore(snaps), [])
        conn = db.connect()
        self.assertEqual(conn.execute("SELECT COUNT(*), MAX(value) FROM readings").fetchone()[:], (16, 4.15))
        self.assertEqual(conn.execute("SELECT fermenter_tag FROM batches").fetchone()[0], "FV-03")
        conn.close()
        restored = db.load_config()
        self.assertEqual(restored["upload_secret"], "")         # secrets never go in a snapshot
        self.assertEqual(restored["full_backup_every_days"], 7)

        with self.assertRaises(SystemExit):                     # won't overwrite a live database
            backup.restore(snaps)

        # Lose a delta: restore still works, and says what is missing.
        older = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, older, ignore_errors=True)
        for n in names[7:14]:
            if n != names[10]:
                shutil.copy(snaps / n, older)
        warnings = backup.restore(Path(older), force=True)
        self.assertEqual(len(warnings), 1)
        conn = db.connect()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 13)
        conn.close()

        # A corrupt full is refused and the live database is left alone.
        bad = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, bad, ignore_errors=True)
        Path(bad, "phloat-20270101-000000-full.zip").write_bytes(b"not a zip")
        with self.assertRaises(Exception):
            backup.restore(Path(bad), force=True)
        conn = db.connect()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 13)
        conn.close()

    # Create a batch, log entries, view the page, then mark it complete under three conditions:
    # no Drive configured, upload failing, upload succeeding. Readings are pruned only in the last.
    def test_ui_batch_lifecycle(self):
        import backup
        import db
        from unittest import mock
        self.post({"device": "phloat-1", "pH": 4.4, "sg": 1.05, "temperature": 19})
        self.post({"device": "phloat-1", "pH": 4.3, "sg": 1.04, "temperature": 19.5})
        self.assertIn("Devices not on a batch", self.client.get("/").get_data(as_text=True))

        r = self.client.post("/batches/new", data={"name": "Pale <12>", "fermenter_tag": "FV-03", "devices": ["1"],
                                                    "started_at": "2026-01-01T00:00"})
        self.assertEqual(r.status_code, 302)
        self.client.post("/batches/1/events", data={"kind": "dissolved_oxygen", "note": "stirred 60 s before pitch",
                                                    "value": "8.1", "unit": "ppm"})
        self.client.post("/batches/1/events", data={"kind": "pressure", "value": "twelve"})   # not a number
        page = self.client.get("/batches/1").get_data(as_text=True)
        for expected in ("Pale &lt;12&gt;", "FV-03", "<polyline", "Gravity", "stirred 60 s before pitch",
                         "8.1 ppm", "[twelve]", "Mark complete"):
            self.assertIn(expected, page)
        self.assertNotIn("Pale <12>", page)                     # user text is escaped
        home = self.client.get("/").get_data(as_text=True)
        self.assertIn("Fermenting now", home)
        self.assertNotIn("Devices not on a batch", home)
        self.assertEqual(self.client.get("/batches/99").status_code, 404)
        self.assertEqual(self.client.post("/batches/new", data={"name": " "}).status_code, 400)

        def readings():
            conn = db.connect()
            try:
                return conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
            finally:
                conn.close()

        # No remote configured: exported locally, nothing pruned.
        self.client.post("/batches/1/complete")
        self.assertTrue(Path(self.tmp, "runs", "1-Pale-12", "readings.csv").exists())
        self.assertEqual(readings(), 6)
        self.assertIn("Archive", self.client.get("/batches/1").get_data(as_text=True))

        Path(self.tmp, "config.json").write_text(json.dumps({"upload_secret": "s3cret", "runs_remote": "gdrive:runs"}))
        # Upload fails: still nothing pruned.
        with mock.patch.object(backup, "upload_run", side_effect=RuntimeError("drive is down")):
            self.client.post("/batches/1/complete")
        self.assertEqual(readings(), 6)
        self.assertIn("drive is down", self.client.get("/batches/1").get_data(as_text=True))
        # Upload verified: readings pruned, record and log kept.
        with mock.patch.object(backup, "upload_run") as upload:
            self.client.post("/batches/1/complete")
        upload.assert_called_once()
        self.assertEqual(readings(), 0)
        page = self.client.get("/batches/1").get_data(as_text=True)
        self.assertIn("Archived", page)
        self.assertIn("stirred 60 s before pitch", page)
        self.assertNotIn("Mark complete", page)

    # Rename a device; delete and restore; and check that items older than 7 days are purged.
    def test_rename_delete_trash_purge(self):
        import db
        self.post({"device": "phloat-1", "pH": 4.4})
        self.client.post("/batches/new", data={"name": "Pale 12", "devices": ["1"]})
        self.client.post("/batches/1/events", data={"note": "a mistake"})

        self.client.post("/devices/1/rename", data={"name": "FV-03 pH"})
        self.assertIn("FV-03 pH", self.client.get("/batches/1").get_data(as_text=True))
        self.assertIn("data-chart=", self.client.get("/batches/1").get_data(as_text=True))   # hover/zoom data

        # Delete a log entry, then the batch: both vanish from the pages and sit in the trash.
        self.client.post("/events/1/delete", data={"next": "/batches/1"})
        self.assertNotIn("a mistake", self.client.get("/batches/1").get_data(as_text=True))
        r = self.client.post("/events/1/delete", data={"next": "//evil.example"})
        self.assertEqual(r.headers["Location"], "/")                    # never redirects off-site
        self.client.post("/batches/1/delete")
        self.assertEqual(self.client.get("/batches/1").status_code, 404)
        self.assertNotIn("Pale 12", self.client.get("/").get_data(as_text=True))
        trash = self.client.get("/trash").get_data(as_text=True)
        self.assertIn("Pale 12", trash)
        self.assertIn("a mistake", trash)
        self.assertEqual(self.client.post("/users/1/delete").status_code, 404)   # only the three tables

        # Restore the batch within the window: it comes back with its device.
        self.client.post("/trash/batches/1/restore")
        self.assertIn("FV-03 pH", self.client.get("/batches/1").get_data(as_text=True))

        # Day 6: still there. Day 8: purged for good, with the device's readings.
        self.client.post("/devices/1/delete")
        self.assertNotIn("FV-03 pH", self.client.get("/devices").get_data(as_text=True))
        conn = db.connect()
        conn.execute("UPDATE events SET deleted_at = '2000-01-01T00:00:00Z'")
        conn.commit()
        conn.close()
        trash = self.client.get("/trash").get_data(as_text=True)
        self.assertNotIn("a mistake", trash)                            # past 7 days: gone
        self.assertIn("FV-03 pH", trash)                                # deleted just now: kept
        conn = db.connect()
        conn.execute("UPDATE devices SET deleted_at = '2000-01-01T00:00:00Z'")
        conn.commit()
        conn.close()
        self.client.get("/trash")
        conn = db.connect()
        counts = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("devices", "readings", "events", "batches")]
        conn.close()
        self.assertEqual(counts, [0, 0, 0, 1])

    # The hub adopts a new controller's settings, sends changes back at the next check-in, shows
    # them as pending until applied, overrules changes made elsewhere, and refuses bad values.
    def test_controller_settings_sync(self):
        checkin = {"device": "fermenter-1", "status": "Cooling",
                   "settings": {"target_c": 19, "mode": "auto", "deadband_c": 0.3, "kp": 0.5, "warm_fluid_max_c": 35,
                                "tilt_color": "red", "prefer_well_probe": False, "bogus": 1, "ki": "not a number"}}
        # First check-in: the hub adopts what the controller is running. Junk keys and values are dropped.
        r = self.post(checkin, path="/api/readings")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["settings"], {"target_c": 19.0, "mode": "auto", "deadband_c": 0.3, "kp": 0.5,
                                              "warm_fluid_max_c": 35.0, "tilt_color": "red", "prefer_well_probe": False})
        page = self.client.get("/controllers").get_data(as_text=True)
        self.assertIn("fermenter-1", page)
        self.assertIn("Cooling", page)
        self.assertNotIn("waiting for the controller", page)

        # Change the target on the hub: the next check-in is told, and the page shows it as pending.
        form = {"target_c": "18.5", "mode": "cool", "deadband_c": "0.3", "kp": "0.5", "warm_fluid_max_c": "35",
                "tilt_color": "red"}
        self.assertEqual(self.client.post("/controllers/1", data=form).status_code, 302)
        self.assertIn("2 changes waiting", self.client.get("/controllers").get_data(as_text=True))
        r = self.post(checkin, path="/api/readings")
        self.assertEqual((r.json["settings"]["target_c"], r.json["settings"]["mode"]), (18.5, "cool"))

        # The controller applies it and reports back: nothing pending. A change made elsewhere is overruled.
        checkin["settings"].update(target_c=18.5, mode="cool")
        self.post(checkin, path="/api/readings")
        self.assertNotIn("waiting for the controller", self.client.get("/controllers").get_data(as_text=True))
        checkin["settings"]["target_c"] = 25
        self.assertEqual(self.post(checkin, path="/api/readings").json["settings"]["target_c"], 18.5)

        # Out-of-range values from the form are refused and nothing changes.
        for bad in ({"warm_fluid_max_c": "80"}, {"target_c": "hot"}, {"mode": "turbo"}):
            self.client.post("/controllers/1", data={**form, **bad})
            r = self.post(checkin, path="/api/readings")
            self.assertEqual((r.json["settings"]["warm_fluid_max_c"], r.json["settings"]["target_c"],
                              r.json["settings"]["mode"]), (35.0, 18.5, "cool"), bad)

        # A check-in with readings but no settings still works, and one with neither is refused.
        self.assertEqual(self.post({"device": "fermenter-1", "metrics": {"beer_temp_c": 19.1}}, path="/api/readings").json["settings"], {})
        self.assertEqual(self.post({"device": "fermenter-1", "status": "x"}, path="/api/readings").status_code, 400)

    # A run export contains only this batch's devices and time window, in spreadsheet layout.
    def test_export_run(self):
        import backup
        import db
        self.post({"device": "phloat-1", "pH": 4.4, "timestamp": "2026-11-02T10:00:00Z"})
        self.post({"device": "phloat-1", "pH": 5.0, "timestamp": "2026-11-20T10:00:00Z"})   # after the run ended
        self.post({"device": "other", "pH": 3.0, "timestamp": "2026-11-02T10:00:00Z"})      # not in this batch
        conn = db.connect()
        tilt = db.device_id(conn, "tilt", "AA:BB:CC:DD:EE:FF", "red")
        db.add_readings(conn, tilt, {"sg": 1.05, "temp_c": 20.0}, "2026-11-02T10:00:00Z")
        conn.execute("INSERT INTO batches (id, name, fermenter_tag, recipe_file, started_at, ended_at) "
                     "VALUES (1, 'Pale #12', 'FV-03', '<RECIPES/>', '2026-11-01T00:00:00Z', '2026-11-10T00:00:00Z')")
        conn.execute("INSERT INTO batch_devices SELECT 1, id FROM devices WHERE ident IN ('phloat-1', 'AA:BB:CC:DD:EE:FF')")
        conn.execute("INSERT INTO events (ts, batch_id, kind, note, value, unit) "
                     "VALUES ('2026-11-01T09:00:00Z', 1, 'dissolved_oxygen', 'stirred 60 s before pitch', 8.1, 'ppm')")
        conn.commit()
        conn.close()

        out = backup.export_run(1)
        self.assertEqual(out.name, "1-Pale-12")
        self.assertEqual((out / "readings.csv").read_text().splitlines(),
                         ["ts_utc,phloat-1_ph,red_tilt_sg,red_tilt_temp_c", "2026-11-02T10:00:00Z,4.4,1.05,20.0"])
        self.assertIn("stirred 60 s before pitch,8.1,ppm", (out / "events.csv").read_text())
        self.assertIn("FV-03", (out / "batch.csv").read_text())
        self.assertEqual((out / "recipe.txt").read_text(), "<RECIPES/>")

        all_rows = Path(self.tmp, "out.csv")
        self.assertEqual(backup.export_csv(all_rows), 5)


if __name__ == "__main__":
    unittest.main()
