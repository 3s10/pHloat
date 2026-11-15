#!/usr/bin/env python3
"""Back up and restore the pHloat hub, and export finished fermentations.

HOW TO RUN IT (from the tiltpi folder, with the hub's Python):

  backup.py backup               make tonight's snapshot and push it to Google Drive
  backup.py restore              pull the snapshots back down and rebuild the database
  backup.py restore --dir D      rebuild from a folder of snapshots you already have
  backup.py export-run ID        write one batch as CSV files under <data>/runs/
  backup.py archive-run ID       export, upload, verify, then remove that run's readings
  backup.py export-csv out.csv   every reading in the database, one row per measurement

THE BACKUP SCHEME
  Uploading the whole database every night would grow without limit, so there are two kinds
  of snapshot, both zip files in <data>/backups/:

    phloat-<date>-<time>-full.zip    the entire database. Made when the newest full is
                                     `full_backup_every_days` old (default 7).
    phloat-<date>-<time>-delta.zip   only what changed since the previous snapshot:
                                       - the new rows of the `readings` table, and
                                       - complete copies of the small tables.
  Why the split inside a delta? Readings are only ever ADDED, so "rows newer than last time"
  captures every change. The small tables (devices, batches, log entries, settings) get
  EDITED, and an edit can't be found by "newer rows", so they are simply copied whole.
  They are tiny, so that costs nothing.

  To restore: take the newest full, then replay every delta made after it, in order.

  Retention: keep the two newest fulls and every delta after the older one (one to two weeks).
  Older snapshots are deleted on the Pi and on Drive. Run exports are never deleted.

WHAT IS NOT IN A SNAPSHOT
  The upload secret and the Home Assistant token are removed from the copy of config.json, and
  the Google Drive login lives in rclone's own settings on the Pi. After a restore, type the
  secrets back in.

NETWORK
  rclone is a separate, widely used program that copies files to cloud storage. Every
  connection here is made BY the Pi going outward; nothing ever connects in to the Pi.
"""

import argparse
import csv
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from db import config_path, connect, data_dir, db_path, load_config, purge_deleted, utc_now

# Settings that must never leave the Pi inside a snapshot.
SECRET_KEYS = ("upload_secret", "ha_token")
# The small, editable tables that every delta copies in full.
# Order matters: a table is listed AFTER the tables it refers to ("parents first").
SMALL_TABLES = ("devices", "batches", "batch_devices", "events", "device_settings")
# How the date and time are written into a snapshot's file name, e.g. 20261115-031500.
# Year first means sorting the names alphabetically also sorts them by time.
STAMP = "%Y%m%d-%H%M%S"


# ---------------------------------------------------------------------------------------------
# Small helpers for finding and reading snapshot files.
# (A leading underscore in a name is a Python convention for "used only inside this file".)
# ---------------------------------------------------------------------------------------------
def backups_dir() -> Path:
    """The folder snapshots are kept in, created on first use."""
    d = data_dir() / "backups"
    d.mkdir(exist_ok=True)
    return d


def _snapshots(folder: Path, kind: str = "*") -> list[Path]:
    """All snapshots in a folder, oldest first. `kind` can be "full", "delta" or "*" for both."""
    return sorted(folder.glob(f"phloat-*-{kind}.zip"))   # name order = time order (see STAMP)


def _stamp(path: Path) -> datetime:
    """Read the date and time back out of a snapshot's file name."""
    return datetime.strptime(path.name[len("phloat-"):len("phloat-") + 15], STAMP)


def _manifest(path: Path) -> dict:
    """Read a snapshot's manifest: a small note inside the zip saying what it contains.

    {"type": "full",  "last_rowid": N}                    readings up to row N are inside
    {"type": "delta", "after_rowid": M, "last_rowid": N}  readings M+1..N are inside
    A "rowid" is the hidden row number SQLite gives every row; it only ever counts upward,
    which is what makes "everything after row M" a reliable way to say "everything new".
    """
    with zipfile.ZipFile(path) as z:
        return json.loads(z.read("manifest.json"))


def _write_zip(out: Path, db_file: Path, manifest: dict, config: dict) -> None:
    """Pack one snapshot: the database piece, its manifest, and the settings minus secrets."""
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(db_file, "phloat.db")
        z.writestr("manifest.json", json.dumps(manifest))
        z.writestr("config.json", json.dumps({k: v for k, v in config.items() if k not in SECRET_KEYS}, indent=2))


# ---------------------------------------------------------------------------------------------
# Making a snapshot.
# ---------------------------------------------------------------------------------------------
def snapshot(now: datetime | None = None) -> tuple[Path, list[Path]]:
    """Write a full or a delta, whichever is due. Returns (new snapshot, old snapshots deleted).

    Safe to run while the hub is running and writing.
    `now` exists so the tests can pretend it is a different day.
    """
    now = now or datetime.now()
    config = load_config()

    # Step 1: decide which kind. A full is due if there has never been one, or the newest is old.
    fulls = _snapshots(backups_dir(), "full")
    full_due = not fulls or now - _stamp(fulls[-1]) >= timedelta(days=config["full_backup_every_days"])
    kind = "full" if full_due else "delta"
    out = backups_dir() / f"phloat-{now:{STAMP}}-{kind}.zip"

    # Step 2: build the database piece in a temporary folder, then zip it.
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "phloat.db"
        src = connect()
        if full_due:
            # SQLite's built-in "online backup" copies the whole database page by page and
            # gives a consistent copy even if another program writes halfway through.
            dst = sqlite3.connect(copy)
            src.backup(dst)
            dst.close()
            last = src.execute("SELECT COALESCE(MAX(rowid), 0) FROM readings").fetchone()[0]
            manifest = {"type": "full", "last_rowid": last}
        else:
            # A delta starts where the previous snapshot (full or delta) stopped.
            after = _manifest(_snapshots(backups_dir())[-1])["last_rowid"]
            # ATTACH opens a second, empty database file alongside the live one under the
            # name "delta", so rows can be copied from one to the other with plain SQL.
            src.execute("ATTACH DATABASE ? AS delta", (str(copy),))
            # BEGIN...COMMIT is a transaction: everything inside sees the database as it was
            # at one single instant, so the readings and the small tables match each other.
            src.execute("BEGIN")
            src.execute("CREATE TABLE delta.readings AS SELECT rowid AS rid, * FROM readings WHERE rowid > ?", (after,))
            for table in SMALL_TABLES:
                src.execute(f"CREATE TABLE delta.{table} AS SELECT * FROM {table}")
            last = src.execute("SELECT COALESCE(MAX(rid), ?) FROM delta.readings", (after,)).fetchone()[0]
            src.execute("COMMIT")
            src.execute("DETACH DATABASE delta")
            manifest = {"type": "delta", "after_rowid": after, "last_rowid": last}
        src.close()
        _write_zip(out, copy, manifest, config)

    # Step 3: retention. Keep the two newest fulls and everything made after the older of them.
    fulls = _snapshots(backups_dir(), "full")
    pruned = [p for p in _snapshots(backups_dir()) if len(fulls) >= 2 and p.name < fulls[-2].name]
    for old in pruned:
        old.unlink()                                   # unlink = delete the file
    return out, pruned


# ---------------------------------------------------------------------------------------------
# Restoring.
# ---------------------------------------------------------------------------------------------
def restore(folder: Path, force: bool = False) -> list[str]:
    """Rebuild the database from the newest full in `folder` plus every delta after it.

    Returns a list of warnings (for example, a missing delta). Raises SystemExit, with a
    message, if it cannot or should not proceed.

    Safety rule: the new database is built in a separate file next to the live one, and only
    swapped into place at the very end. If anything goes wrong on the way, the live database
    has not been touched.
    """
    if db_path().exists() and not force:
        raise SystemExit(f"{db_path()} already exists. Stop the hub and pass --force to overwrite it.")
    fulls = _snapshots(folder, "full")
    if not fulls:
        raise SystemExit(f"No full snapshot in {folder}.")
    full = fulls[-1]                                                   # newest full
    deltas = [p for p in _snapshots(folder, "delta") if p.name > full.name]   # deltas made after it
    warnings = []

    work = db_path().with_suffix(".restore")           # the scratch file the new database is built in
    work.unlink(missing_ok=True)
    try:
        # Step 1: unpack the full copy and make sure it is a healthy database.
        with zipfile.ZipFile(full) as z:
            work.write_bytes(z.read("phloat.db"))
            config_bytes = z.read("config.json")
        conn = sqlite3.connect(work)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]   # SQLite's self-test; "ok" = healthy
        except sqlite3.DatabaseError as exc:
            result = str(exc)
        if result != "ok":
            conn.close()
            raise SystemExit(f"{full.name} failed its integrity check: {result}")

        # Step 2: replay each delta in order.
        have = _manifest(full)["last_rowid"]           # the highest reading row restored so far
        with tempfile.TemporaryDirectory() as tmp:
            for i, delta in enumerate(deltas):
                manifest = _manifest(delta)
                # If this delta starts after where we are, a snapshot in between is missing.
                # Carry on (later data is still worth having) but say exactly what is lost.
                if manifest["after_rowid"] > have:
                    warnings.append(f"Gap before {delta.name}: readings {have + 1}-{manifest['after_rowid']} are missing.")
                piece = Path(tmp) / f"{i}.db"
                with zipfile.ZipFile(delta) as z:
                    piece.write_bytes(z.read("phloat.db"))
                    config_bytes = z.read("config.json")       # the newest snapshot's settings win
                conn.execute("ATTACH DATABASE ? AS delta", (str(piece),))
                conn.execute("BEGIN")
                # Add the new readings, keeping their original row numbers.
                conn.execute("INSERT OR REPLACE INTO readings (rowid, ts, device_id, metric, value) "
                             "SELECT rid, ts, device_id, metric, value FROM delta.readings")
                # Replace the small tables with the delta's copies. Empty them "children first"
                # (reverse order), then refill them "parents first".
                for table in reversed(SMALL_TABLES):
                    conn.execute(f"DELETE FROM {table}")
                for table in SMALL_TABLES:
                    conn.execute(f"INSERT INTO {table} SELECT * FROM delta.{table}")
                conn.execute("COMMIT")
                conn.execute("DETACH DATABASE delta")
                have = max(have, manifest["last_rowid"])

        # Step 3: tidy up archived runs. Deltas only ever ADD readings, so a run that was archived
        # (and pruned) after the full was made would reappear here. Remove its readings again.
        conn.execute(
            "DELETE FROM readings WHERE EXISTS (SELECT 1 FROM batches b JOIN batch_devices bd ON bd.batch_id = b.id "
            "WHERE b.archived_at IS NOT NULL AND bd.device_id = readings.device_id "
            "AND readings.ts >= COALESCE(b.started_at, '') AND readings.ts <= COALESCE(b.ended_at, '9999'))")
        conn.commit()
        conn.close()
    except BaseException:
        work.unlink(missing_ok=True)                   # failed: throw the scratch file away, keep the live one
        raise

    # Step 4: swap the finished file into place.
    # The -wal and -shm files are SQLite's working files for the OLD database; remove them so
    # they are not applied to the new one.
    for stale in (db_path().with_name("phloat.db-wal"), db_path().with_name("phloat.db-shm")):
        stale.unlink(missing_ok=True)
    work.replace(db_path())
    config_path().write_bytes(config_bytes)
    return warnings


# ---------------------------------------------------------------------------------------------
# Exporting a finished fermentation ("run") as spreadsheet-friendly files.
# ---------------------------------------------------------------------------------------------
def _slug(text: str) -> str:
    """Turn a batch name into something safe to use as a folder name: 'Pale #12' -> 'Pale-12'."""
    return re.sub(r"[^A-Za-z0-9_-]+", "-", text).strip("-") or "run"


def export_run(batch_id: int) -> Path:
    """Write one batch to <data>/runs/<id>-<name>/ and return that folder.

    Files written:
      readings.csv   one row per moment in time, one column per device + measurement
      events.csv     the batch log (notes and hand-entered numbers)
      batch.csv      the batch record itself
      recipe.txt     the attached recipe file, if there is one
      recipe_summary.json   the ingredients and targets read out of it, if it could be parsed
    """
    conn = connect()
    batch = conn.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
    if batch is None:
        conn.close()
        raise SystemExit(f"No batch {batch_id}.")
    out = data_dir() / "runs" / f"{batch_id}-{_slug(batch['name'])}"
    out.mkdir(parents=True, exist_ok=True)

    # --- readings.csv -------------------------------------------------------------------------
    # The database holds one row per number ("long" format). A person reading a spreadsheet
    # wants one row per time with the numbers side by side ("wide" format). This block pivots
    # long into wide. The result is sparse (some cells empty) because devices report at
    # different moments: the Tilt every minute, the pHloat every 15 minutes.
    # COALESCE(x, '') / COALESCE(x, '9999') mean "if the batch has no start/end, don't limit".
    rows = conn.execute(
        "SELECT r.ts, d.kind, d.ident, d.color, r.metric, r.value FROM readings r "
        "JOIN devices d ON d.id = r.device_id JOIN batch_devices bd ON bd.device_id = d.id "
        "WHERE bd.batch_id = ? AND d.deleted_at IS NULL "
        "AND r.ts >= COALESCE(?, '') AND r.ts <= COALESCE(?, '9999') ORDER BY r.ts",
        (batch_id, batch["started_at"], batch["ended_at"])).fetchall()
    table, columns = {}, []          # table: {time: {column name: value}}
    for r in rows:
        # Column name = which device + which measurement, e.g. "red_tilt_sg" or "phloat-1_ph".
        column = f"{r['color'] + '_tilt' if r['kind'] == 'tilt' and r['color'] else r['ident']}_{r['metric']}"
        if column not in columns:
            columns.append(column)
        table.setdefault(r["ts"], {})[column] = r["value"]
    columns.sort()
    with (out / "readings.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ts_utc", *columns])
        for ts, values in table.items():
            writer.writerow([ts, *(values.get(c, "") for c in columns)])   # "" where a device had no reading

    # --- events.csv ---------------------------------------------------------------------------
    with (out / "events.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ts_utc", "kind", "note", "value", "unit"])
        writer.writerows(tuple(e) for e in conn.execute(
            "SELECT ts, kind, note, value, unit FROM events WHERE batch_id = ? AND deleted_at IS NULL ORDER BY ts",
            (batch_id,)))

    # --- batch.csv and recipe.txt -------------------------------------------------------------
    fields = [k for k in batch.keys() if k not in ("recipe_file", "recipe_json")]   # the recipe gets its own files
    with (out / "batch.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        writer.writerow([batch[k] for k in fields])
    if batch["recipe_file"]:
        (out / "recipe.txt").write_text(batch["recipe_file"], encoding="utf-8")       # exactly as uploaded
    if batch["recipe_json"]:
        (out / "recipe_summary.json").write_text(batch["recipe_json"], encoding="utf-8")   # the parsed summary
    conn.close()
    return out


def export_csv(out: Path) -> int:
    """Write every reading in the database to one CSV file. Returns the number of rows."""
    conn = connect()
    rows = conn.execute(
        "SELECT r.ts, d.kind, d.ident, d.color, r.metric, r.value FROM readings r "
        "JOIN devices d ON d.id = r.device_id ORDER BY r.ts").fetchall()
    conn.close()
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ts_utc", "kind", "device", "tilt_color", "metric", "value"])
        writer.writerows(tuple(row) for row in rows)
    return len(rows)


# ---------------------------------------------------------------------------------------------
# Talking to Google Drive through rclone.
# ---------------------------------------------------------------------------------------------
def _rclone(*args: str) -> None:
    """Run the rclone program with the given arguments. check=True makes a failure raise an error."""
    subprocess.run(["rclone", *args], check=True)


def _remote(key: str) -> str:
    """Read an rclone destination ("backup_remote" or "runs_remote") from config.json."""
    remote = load_config()[key]
    if not remote:
        raise SystemExit(f'Set "{key}" in config.json first, e.g. "gdrive:phloat".')
    return remote.rstrip("/")


def upload_run(out: Path) -> None:
    """Upload a run folder and prove it arrived. Raises an error if any step fails.

    Two copies are uploaded:
      <run>/files/   the CSV files exactly as written. `rclone check` then compares them
                     with the originals, so this copy is PROVEN to be complete.
      <run>/sheets/  the same CSVs converted into native Google Sheets for easy reading.
                     A converted sheet is no longer the same bytes, so it can't be compared;
                     that is why the plain copy is the one that counts.
    """
    remote = f"{_remote('runs_remote')}/{out.name}"
    _rclone("copy", str(out), f"{remote}/files")
    _rclone("check", str(out), f"{remote}/files", "--one-way")
    _rclone("copy", str(out), f"{remote}/sheets", "--include", "*.csv", "--drive-import-formats", "csv")


def archive_run(batch_id: int) -> Path:
    """Export a finished run, upload it, and ONLY THEN delete its readings from the database.

    The order is the safety feature. If the export, the upload or the verification fails,
    an error is raised before the DELETE is reached, so nothing is lost.
    The batch record and its log stay in the database, so the run is still listed.
    """
    out = export_run(batch_id)       # 1. write the files on the Pi
    upload_run(out)                  # 2. upload and verify (raises on any failure)
    conn = connect()                 # 3. only now remove the readings
    batch = conn.execute("SELECT started_at, ended_at FROM batches WHERE id = ?", (batch_id,)).fetchone()
    conn.execute(
        "DELETE FROM readings WHERE device_id IN (SELECT device_id FROM batch_devices WHERE batch_id = ?) "
        "AND ts >= COALESCE(?, '') AND ts <= COALESCE(?, '9999')", (batch_id, batch["started_at"], batch["ended_at"]))
    conn.execute("UPDATE batches SET archived_at = ? WHERE id = ?", (utc_now(), batch_id))
    conn.commit()
    conn.close()
    return out


# ---------------------------------------------------------------------------------------------
# The command line: turns "backup.py restore --force" into a call to the functions above.
# ---------------------------------------------------------------------------------------------
def main(argv=None):
    # argparse reads the words typed after the program name and checks them.
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("backup")
    p_restore = sub.add_parser("restore")
    p_restore.add_argument("--dir", type=Path)
    p_restore.add_argument("--force", action="store_true")
    sub.add_parser("export-run").add_argument("batch_id", type=int)
    sub.add_parser("archive-run").add_argument("batch_id", type=int)
    sub.add_parser("export-csv").add_argument("out", type=Path)
    args = parser.parse_args(argv)

    if args.command == "backup":
        # Empty anything that has been in the trash more than 7 days, even if nobody opens that page.
        conn = connect()
        purge_deleted(conn)
        conn.close()
        path, pruned = snapshot()
        print(f"Snapshot: {path}")
        if load_config()["backup_remote"]:
            # "copy" only ever ADDS files to Drive, and old snapshots are deleted one by one by name.
            # rclone's "sync" (make Drive match this folder) is deliberately NOT used: a brand-new
            # Pi with an empty backups folder would then wipe every snapshot on Drive.
            _rclone("copy", str(backups_dir()), _remote("backup_remote"))
            for old in pruned:
                _rclone("deletefile", f"{_remote('backup_remote')}/{old.name}")
            print(f"Pushed to {_remote('backup_remote')}, pruned {len(pruned)}")
        else:
            print('No "backup_remote" set: snapshot kept locally only.')
    elif args.command == "restore":
        folder = args.dir
        if folder is None:                             # no folder given: fetch the snapshots from Drive
            _rclone("copy", _remote("backup_remote"), str(backups_dir()))
            folder = backups_dir()
        for warning in restore(folder, args.force):
            print("WARNING:", warning)
        print(f"Restored from {folder}. Re-enter upload_secret in {config_path()}, then start the hub.")
    elif args.command == "export-run":
        print(f"Run written to {export_run(args.batch_id)}")
    elif args.command == "archive-run":
        print(f"Run archived from {archive_run(args.batch_id)}; its readings are pruned from the database.")
    else:
        print(f"Wrote {export_csv(args.out)} rows to {args.out}")


# Run main() only when this file is started directly, not when another file imports it.
if __name__ == "__main__":
    sys.exit(main())
