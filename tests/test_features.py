"""Tests for recipe reading, the Home Assistant feed, and editing a log entry.

Run every test with:
    python -m unittest discover tests        (needs flask)
"""

import importlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Let Python find the hub's modules, which live in the tiltpi folder next to this one.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiltpi"))

import ha_publish
from recipe import parse_recipe

# A small but complete BeerXML recipe, as brewing software would export it.
BEERXML = """<?xml version="1.0" encoding="UTF-8"?>
<RECIPES><RECIPE>
  <NAME>House Pale</NAME><OG>1.052</OG><FG>1.011</FG><BATCH_SIZE>23.0</BATCH_SIZE>
  <STYLE><NAME>American Pale Ale</NAME></STYLE>
  <FERMENTABLES>
    <FERMENTABLE><NAME>Maris Otter</NAME><AMOUNT>4.5</AMOUNT></FERMENTABLE>
    <FERMENTABLE><NAME>Crystal 60</NAME><AMOUNT>0.4</AMOUNT></FERMENTABLE>
  </FERMENTABLES>
  <HOPS><HOP><NAME>Citra</NAME><AMOUNT>0.030</AMOUNT><USE>Boil</USE><TIME>10</TIME><ALPHA>12.5</ALPHA></HOP></HOPS>
  <YEASTS><YEAST><NAME>US-05</NAME><LABORATORY>Fermentis</LABORATORY><PRODUCT_ID>US-05</PRODUCT_ID></YEAST></YEASTS>
  <MASH><MASH_STEPS><MASH_STEP><NAME>Sacch</NAME><STEP_TEMP>66</STEP_TEMP><STEP_TIME>60</STEP_TIME></MASH_STEP></MASH_STEPS></MASH>
</RECIPE></RECIPES>"""

# The same recipe in the shape of a Brewfather JSON export.
BREWFATHER = json.dumps({
    "name": "House Pale", "og": 1.052, "fg": 1.011, "batchSize": 23, "style": {"name": "American Pale Ale"},
    "fermentables": [{"name": "Maris Otter", "amount": 4.5}],
    "hops": [{"name": "Citra", "amount": 30, "use": "Boil", "time": 10, "alpha": 12.5}],
    "yeasts": [{"name": "US-05", "laboratory": "Fermentis", "productId": "US-05"}],
    "mash": {"steps": [{"name": "Sacch", "stepTemp": 66, "stepTime": 60}]},
})


class TestRecipe(unittest.TestCase):
    # Both formats must come out in the same shape, with the same units.
    def test_beerxml(self):
        r = parse_recipe(BEERXML)
        self.assertEqual((r["format"], r["name"], r["style"], r["og"], r["fg"], r["batch_size_l"]),
                         ("BeerXML", "House Pale", "American Pale Ale", 1.052, 1.011, 23.0))
        self.assertEqual(r["fermentables"], [{"name": "Maris Otter", "kg": 4.5}, {"name": "Crystal 60", "kg": 0.4}])
        self.assertEqual(r["hops"], [{"name": "Citra", "g": 30.0, "use": "Boil", "minutes": 10.0, "alpha": 12.5}])   # kg -> g
        self.assertEqual(r["yeasts"], [{"name": "US-05", "lab": "Fermentis", "product": "US-05"}])
        self.assertEqual(r["mash"], [{"name": "Sacch", "temp_c": 66.0, "minutes": 60.0}])

    def test_brewfather(self):
        r = parse_recipe(BREWFATHER)
        self.assertEqual((r["format"], r["name"], r["og"], r["batch_size_l"]), ("Brewfather", "House Pale", 1.052, 23.0))
        self.assertEqual(r["hops"][0]["g"], 30.0)
        self.assertEqual(r["mash"], [{"name": "Sacch", "temp_c": 66.0, "minutes": 60.0}])
        # A batch export nests the recipe one level down; a list wraps it.
        self.assertEqual(parse_recipe(json.dumps({"recipe": json.loads(BREWFATHER)}))["name"], "House Pale")
        self.assertEqual(parse_recipe("[" + BREWFATHER + "]")["name"], "House Pale")

    # Anything that isn't a recipe gives None instead of an error, including the XML trick
    # (an ENTITY definition) that can make a tiny file expand without limit.
    def test_unreadable_files_are_refused_quietly(self):
        bomb = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><RECIPES><RECIPE><NAME>&a;</NAME></RECIPE></RECIPES>'
        for junk in ("", "just some notes", "<RECIPES><RECIPE>", "{not json", "{}", "[]", '{"name": ""}',
                     "<HTML><BODY/></HTML>", bomb, None):
            self.assertIsNone(parse_recipe(junk), repr(junk))
        # Missing pieces are simply left out.
        self.assertEqual(parse_recipe("<RECIPE><NAME>Bare</NAME></RECIPE>")["fermentables"], [])


class TestHomeAssistant(unittest.TestCase):
    def test_states_for_tilt(self):
        states = ha_publish.states_for_tilt("red", "C4:3A:11:9E:02:7B", None, 1.0123, 19.44, -71)
        self.assertEqual([s[0] for s in states], ["sensor.tilt_red_027b_gravity", "sensor.tilt_red_027b_temperature",
                                                  "sensor.tilt_red_027b_signal"])
        self.assertEqual([s[1] for s in states], ["1.0123", "19.4", "-71"])
        self.assertEqual(states[0][2]["friendly_name"], "Red Tilt gravity")
        # A name given on the hub changes the label, never the entity id.
        renamed = ha_publish.states_for_tilt("red", "C4:3A:11:9E:02:7B", "FV-03 Tilt", 1.0, 20, -60)
        self.assertEqual((renamed[0][0], renamed[0][2]["friendly_name"]), ("sensor.tilt_red_027b_gravity", "FV-03 Tilt gravity"))

    def test_publish(self):
        states = ha_publish.states_for_tilt("red", "C4:3A:11:9E:02:7B", None, 1.01, 19, -70)
        sent = []
        config = {"ha_url": "http://ha.local:8123/", "ha_token": "tok"}
        self.assertTrue(ha_publish.publish(config, states, post=lambda url, token, body: sent.append((url, token, body))))
        self.assertEqual(sent[0][:2], ("http://ha.local:8123/api/states/sensor.tilt_red_027b_gravity", "tok"))
        self.assertEqual(sent[0][2]["state"], "1.0100")
        self.assertEqual(len(sent), 3)

        # Not configured: nothing is sent. Home Assistant down: reported as False, never an error.
        sent.clear()
        self.assertFalse(ha_publish.publish({"ha_url": "", "ha_token": ""}, states, post=lambda *a: sent.append(a)))
        self.assertFalse(ha_publish.publish({"ha_url": "http://ha.local:8123", "ha_token": ""}, states, post=lambda *a: sent.append(a)))
        self.assertEqual(sent, [])

        def down(*args):
            raise OSError("connection refused")
        self.assertFalse(ha_publish.publish(config, states, post=down))


class TestPages(unittest.TestCase):
    # Same arrangement as tests/test_hub.py: a throwaway data folder and an in-memory web server.
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["PHLOAT_DATA"] = self.tmp
        os.environ.pop("PHLOAT_UPLOAD_SECRET", None)
        Path(self.tmp, "config.json").write_text(json.dumps({"upload_secret": "s3cret", "ha_token": "tok"}))
        import phloat_server
        self.client = importlib.reload(phloat_server).app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def upload_recipe(self, url, content, **fields):
        data = {"name": "Pale 12", **fields, "recipe_file": (io.BytesIO(content.encode()), "recipe.txt")}
        return self.client.post(url, data=data, content_type="multipart/form-data")

    def test_recipe_upload_fills_the_batch(self):
        self.upload_recipe("/batches/new", BEERXML)
        page = self.client.get("/batches/1").get_data(as_text=True)
        for expected in ("House Pale", "American Pale Ale", "Maris Otter", "4.5 kg", "Citra", "30.0 g",
                         "Fermentis US-05", "read as BeerXML", "1.052"):
            self.assertIn(expected, page)

        # Something typed into the form wins over the file.
        self.upload_recipe("/batches/new", BREWFATHER, recipe_name="My own name", yeast="House strain gen 4")
        page = self.client.get("/batches/2").get_data(as_text=True)
        self.assertIn("My own name", page)
        self.assertIn("<dd>House strain gen 4</dd>", page)      # the batch's yeast field keeps what was typed
        self.assertNotIn("<dd>Fermentis US-05</dd>", page)      # (the recipe section below still lists the file's yeast)

        # An unreadable file is still attached; the batch still saves.
        self.assertEqual(self.upload_recipe("/batches/new", "mash at 66, hop late").status_code, 302)
        self.assertIn("attached, not readable", self.client.get("/batches/3").get_data(as_text=True))

        # The export carries both the original file and the summary; batch.csv carries neither.
        import backup
        out = backup.export_run(1)
        self.assertEqual((out / "recipe.txt").read_text(encoding="utf-8"), BEERXML)
        self.assertEqual(json.loads((out / "recipe_summary.json").read_text(encoding="utf-8"))["name"], "House Pale")
        self.assertNotIn("Maris Otter", (out / "batch.csv").read_text(encoding="utf-8"))

    def test_edit_log_entry(self):
        self.client.post("/batches/new", data={"name": "Pale 12"})
        self.client.post("/batches/1/events", data={"kind": "pressure", "note": "spundng set", "value": "21", "unit": "psi",
                                                    "ts": "2026-11-02T09:30"})
        form = self.client.get("/events/1/edit").get_data(as_text=True)
        self.assertIn("spundng set", form)

        # Correct the typo and the number; leave "When" blank.
        self.client.post("/events/1/edit", data={"kind": "pressure", "note": "spunding set", "value": "12", "unit": "psi", "ts": ""})
        page = self.client.get("/batches/1").get_data(as_text=True)
        self.assertIn("spunding set", page)
        self.assertIn("12.0 psi", page)
        self.assertNotIn("spundng", page)
        import db
        conn = db.connect()
        before = conn.execute("SELECT ts FROM events").fetchone()[0]
        conn.close()
        self.assertTrue(before.startswith("2026-11-02"))          # the original time was kept

        # A bad number is refused and nothing changes. A deleted or unknown entry can't be edited.
        self.client.post("/events/1/edit", data={"kind": "pressure", "note": "x", "value": "lots", "unit": "psi"})
        self.assertIn("12.0 psi", self.client.get("/batches/1").get_data(as_text=True))
        self.client.post("/events/1/delete")
        self.assertEqual(self.client.get("/events/1/edit").status_code, 404)
        self.assertEqual(self.client.get("/events/99/edit").status_code, 404)

    def test_secrets_stay_out_of_backups_and_old_databases_upgrade(self):
        import backup
        import db
        import sqlite3
        import zipfile
        snap, _ = backup.snapshot()
        with zipfile.ZipFile(snap) as z:
            saved = json.loads(z.read("config.json"))
        self.assertNotIn("ha_token", saved)
        self.assertNotIn("upload_secret", saved)

        # A database from before the recipe_json column existed gains it the next time it is opened.
        old = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, old, ignore_errors=True)
        os.environ["PHLOAT_DATA"] = old
        raw = sqlite3.connect(Path(old, "phloat.db"))
        raw.execute("CREATE TABLE batches (id INTEGER PRIMARY KEY, name TEXT NOT NULL, recipe_file TEXT)")
        raw.execute("INSERT INTO batches (name) VALUES ('Old batch')")
        raw.commit()
        raw.close()
        conn = db.connect()
        self.assertEqual(conn.execute("SELECT name, recipe_json FROM batches").fetchone()[:], ("Old batch", None))
        conn.close()


if __name__ == "__main__":
    unittest.main()
