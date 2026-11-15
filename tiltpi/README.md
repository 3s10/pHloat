# pHloat hub (Raspberry Pi)

**Status (2026-11-15): 27 automated tests pass on Windows/Python 3.12 (intake, Tilt decoding, backups and restore, run export, batch pages, archive-on-complete, trash, controller settings sync, recipe reading, log editing, the Home Assistant feed). Batch pages, chart hover and drag-to-zoom checked in a desktop browser with fake data; the Controllers page, the recipe section, phone width and touch not viewed. Never run on a Pi. The Tilt listener has never heard a real Tilt, no rclone command has ever run, no controller has ever checked in, nothing has ever been sent to a real Home Assistant, and the installer has only been syntax-checked.**

Replaces TiltPi and the old Google Sheets server. One Pi on the LAN, never reachable from the internet; its only internet traffic is outbound (backups).

| File | What it does |
|---|---|
| `phloat_server.py` | Receives readings on `POST /api/ph` and `/api/readings` (token header). Plain status page at `/`. |
| `tilt_listener.py` | Logs every Tilt in Bluetooth range: gravity, temperature, signal, keyed by colour + Bluetooth address. |
| `ui.py`, `templates/`, `static/` | The pages: overview, batch create/edit, log, charts, devices (rename), trash. `static/chart.js` adds hover values and drag-to-zoom; without JavaScript the charts still draw. Nothing loads from the internet. |
| `controller_settings.py` | The settings a fermenter controller takes from the hub, their allowed ranges, and the sync. |
| `backup.py` | `backup`, `restore`, `export-run`, `archive-run`, `export-csv`. |
| `recipe.py` | Reads a BeerXML or Brewfather recipe file into a summary (ingredients, gravities, mash). |
| `ha_publish.py` | Sends each Tilt reading to Home Assistant, if that is switched on. |
| `db.py` | SQLite schema and config. |
| `phloat_upload.py`, `phloat_helpers.py` | Upload validation, Tilt decoding. |

## Data

Everything lives in one folder (`PHLOAT_DATA`, default `~/phloat-data`): `phloat.db`, `config.json`, `backups/`.

- `readings`: time (UTC), device, metric, value. Metrics so far: `ph`, `sg`, `temp_c`, `battery_v`, `rssi`, and from the controller `beer_temp_c`, `coolant_temp_c`, `warm_fluid_temp_c`, `ambient_temp_c`, `setpoint_c`, `cool_pump_pct`, `warm_pump_pct`. Any node can send new ones with no schema change.
- `devices`: Tilts (by Bluetooth address + colour), pHloats and other nodes (by name).
- `device_settings`: for each controller setting, the value the hub wants and the value the controller last reported.
- `batches`, `batch_devices`, `events`: written from the pages. A batch owns its devices' readings between its start and end.

The Tilt listener stores one row per Tilt per `tilt_log_interval_seconds` (default 60), not every broadcast.

## Recipes

Attach a recipe file when creating or editing a batch. The file is always kept exactly as uploaded. If it is BeerXML or a Brewfather JSON export, the hub also reads a summary out of it (style, target gravities, batch size, fermentables, hops, yeast, mash steps), shows it in a fold-out on the batch page, and fills in the batch's recipe name and yeast where you left them blank. Anything you type wins over the file. A file it can't read is still attached.

BeerXML follows the published standard. The Brewfather field names were written from memory and have not been checked against a real export.

## Log entries

Each entry on a batch's log has **Edit** and **Delete**. Editing with the "When" box left blank keeps the original time. A value that isn't a number is refused, so a slip can't wipe a recorded measurement.

## Home Assistant

The pHloat sensor and the controller report to Home Assistant themselves. A Tilt can't, so the hub passes each stored Tilt reading on: gravity, temperature and signal, as `sensor.tilt_<colour>_<last 4 of its Bluetooth address>_gravity` and so on. Switch it on in `config.json`:

```
"ha_url": "http://homeassistant.local:8123",
"ha_token": "<a long-lived access token from your Home Assistant profile>"
```

The Pi makes the connection; nothing connects in. Home Assistant is only ever told values. If Home Assistant is off or unreachable the hub carries on logging. Sensors made this way live in Home Assistant's memory, so after it restarts they reappear at the next Tilt reading (within a minute). The token is a secret and is left out of every backup.

## Controllers

A fermenter controller appears on the **Controllers** page the first time it checks in. The page shows its status line, its newest readings and every setting. Saving the form changes the hub's master copy; the controller picks the change up at its next check-in (about 15 seconds) and the page shows it as "waiting" until the controller confirms it. A value outside its allowed range is refused and nothing is changed. How the sync works is described at the top of `controller_settings.py`.

## Delete and recover

Batches, log entries and devices are soft-deleted: hidden at once, listed under **Trash** with a Restore button for 7 days (`TRASH_DAYS` in `db.py`), then removed for good by the nightly backup run or the next visit to the Trash page. A purged device takes its readings with it; a purged batch takes its log but not its devices' readings.

## Install

```
./install-phloat-tiltpi.sh
```

It generates the upload secret into `config.json` on the Pi. Copy that value into each node's `esphome/secrets.yaml` as `phloat_upload_secret`.

## Backup and restore

1. On the Pi, run `rclone config` once and add a Google Drive remote (for example `gdrive`).
2. In `config.json` set `"backup_remote": "gdrive:phloat-backups"` and `"runs_remote": "gdrive:phloat-runs"`.
3. The timer runs `backup.py backup` nightly at 03:15:
   - a **full** copy when the newest full is 7 days old (`full_backup_every_days`);
   - otherwise a **delta**: readings added since the previous snapshot, plus complete copies of the small editable tables (devices, batches, events).
4. Retention: the two newest fulls and every delta after the older one, so one to two weeks. Older snapshots are deleted on the Pi and on Drive.

New Pi after a failure: clone the repo, run the installer, `rclone config`, stop the two services, then

```
PHLOAT_DATA=~/phloat-data venv/bin/python tiltpi/backup.py restore --force
```

Restore rebuilds from the newest full plus its deltas. A missing delta doesn't stop it; it prints which readings are missing.

Snapshots never contain the upload secret, the Home Assistant token or the Drive credentials. After a restore, put the upload secret (and the Home Assistant token, if used) back in `config.json` (the nodes still hold it in their `secrets.yaml`), or the hub answers 503.

## Finished runs

Pressing **Mark complete** on a batch (or `backup.py archive-run <batch id>`) does, in order:

1. Export to `data/runs/<id>-<name>/`:
   - `readings.csv`: one row per timestamp, one column per device and measurement;
   - `events.csv`: notes and manual measurements;
   - `batch.csv`: the batch record; `recipe.txt`: the imported recipe file.
2. Upload to `runs_remote/<id>-<name>/files/` and verify it with `rclone check`.
3. Upload a second copy to `.../sheets/` converted to native Google Sheets (`--drive-import-formats csv`).
4. Only then delete that run's readings from the database. The batch record and log stay.

If `runs_remote` isn't set, or any upload step fails, the batch is marked complete but nothing is deleted; the button becomes **Archive** to retry. The rclone flags are from memory of its Drive options and have never been run. Run exports are never pruned: after archiving, Drive and the Pi's `data/runs/` hold the only copies of those readings.

## Check

```
pip install flask bleak
python -m unittest discover tests
```

## Not done yet

- An archived run has no charts because its readings are gone from the database.
- Charts send at most 2000 points per line, so zooming far into a long run is coarse.
- No logins or CSRF protection: LAN-only by design.
- The weekly full copy grows with the readings of batches still in progress. Finished batches are pruned when archived.
- A full restore drill on real hardware.
