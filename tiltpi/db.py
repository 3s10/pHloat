"""Storage and configuration for the pHloat hub.

WHAT THIS FILE IS
    Every other hub file (the web server, the Tilt listener, the backup tool) imports this
    one to find the database, open it, and read the settings file. Keeping that in one place
    means there is exactly one definition of "where the data lives" and "what tables exist".

WHERE THE DATA LIVES
    Everything that must survive a dead Raspberry Pi is in ONE folder:
        phloat.db     the SQLite database (a single file)
        config.json   the hub's settings
        backups/      snapshots made by backup.py
        runs/         CSV exports of finished fermentations
    The folder is named by the PHLOAT_DATA environment variable, or ~/phloat-data if that
    is not set. backup.py copies this folder; restoring it onto a new Pi brings everything back.

WORDS USED BELOW
    SQLite   A database stored in one ordinary file. No server program to install or run.
    schema   The list of tables and their columns.
    UTC      The world's reference clock (no time zones, no daylight saving). All timestamps
             are stored in UTC and only converted to local time when shown on a page.
    soft delete   Marking a row as deleted (setting `deleted_at`) instead of removing it, so
             it can be restored. A later "purge" removes it for real.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------------------------
# The schema: every table in the database.
#
# `CREATE TABLE IF NOT EXISTS` means this text can be run every time the hub starts: the first
# run creates the tables, later runs do nothing.
#
# The key design choice is the `readings` table. It is "long format": one row holds ONE number
# (for example "device 3, pH, 4.31, at 14:02"). A device that measures four things writes four
# rows. The benefit: a brand-new kind of measurement needs no new column, just a new `metric`
# name. Names in use today:
#     ph, sg (specific gravity), temp_c, battery_v, rssi (radio signal strength)
#     from the fermenter controller: beer_temp_c, coolant_temp_c, warm_fluid_temp_c,
#     ambient_temp_c, setpoint_c, cool_pump_pct, warm_pump_pct
#
# A batch does not own readings directly. A batch has a start time, an end time and a list of
# devices (`batch_devices`); its readings are "whatever those devices logged between those
# times". That lets a Tilt start logging before the batch has been typed in.
# ---------------------------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY,          -- a number SQLite assigns; other tables refer to a device by it
    kind TEXT NOT NULL,              -- 'tilt' | 'phloat' | 'node' (node = controller or other sensor board)
    ident TEXT NOT NULL,             -- Tilt: its Bluetooth address. Others: the device name it sends.
    color TEXT,                      -- Tilt colour (for a pHloat: the colour of the Tilt it follows)
    name TEXT,                       -- optional display name typed on the Devices page
    status TEXT,                     -- last status line a controller reported, e.g. "Cooling"
    deleted_at TEXT,                 -- soft delete: recoverable for TRASH_DAYS, then purged
    UNIQUE (kind, ident)             -- the same device can never be listed twice
);
CREATE TABLE IF NOT EXISTS readings (
    ts TEXT NOT NULL,                -- when, in UTC, written as YYYY-MM-DDTHH:MM:SSZ (sorts correctly as text)
    device_id INTEGER NOT NULL REFERENCES devices(id),
    metric TEXT NOT NULL,            -- what was measured (see the list above)
    value REAL NOT NULL              -- the number
);
-- An index is like the index of a book: it lets SQLite jump straight to one device's readings
-- of one metric in time order, instead of scanning every row. Charts depend on this.
CREATE INDEX IF NOT EXISTS readings_lookup ON readings (device_id, metric, ts);
CREATE TABLE IF NOT EXISTS device_settings (   -- controller settings; explained in controller_settings.py
    device_id INTEGER NOT NULL REFERENCES devices(id),
    key TEXT NOT NULL,               -- setting name, e.g. 'target_c'
    desired TEXT NOT NULL,           -- the value the hub wants, stored as JSON text
    reported TEXT,                   -- the value the controller last said it is running, as JSON text
    reported_at TEXT,                -- when it last said so
    PRIMARY KEY (device_id, key)     -- one row per setting per device
);
CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    fermenter_tag TEXT,              -- the asset tag on the tank, e.g. 'FV-03'
    yeast TEXT,
    recipe_name TEXT,
    recipe_file TEXT,                -- an imported BeerXML / Brewfather export, stored exactly as uploaded
    recipe_json TEXT,                -- a summary parsed from recipe_file (see recipe.py), as JSON text
    started_at TEXT,
    ended_at TEXT,                   -- empty while the batch is still fermenting
    archived_at TEXT,                -- set once the run is exported, uploaded and its readings pruned
    notes TEXT,
    deleted_at TEXT
);
CREATE TABLE IF NOT EXISTS batch_devices (     -- which devices are on which batch (a simple link table)
    batch_id INTEGER NOT NULL REFERENCES batches(id),
    device_id INTEGER NOT NULL REFERENCES devices(id),
    PRIMARY KEY (batch_id, device_id)
);
CREATE TABLE IF NOT EXISTS events (            -- the batch log: notes and hand-entered measurements
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    batch_id INTEGER REFERENCES batches(id),
    kind TEXT NOT NULL,              -- 'note', 'pressure', 'dissolved_oxygen', 'dry_hop', ...
    note TEXT,
    value REAL,                      -- optional number, e.g. 12 (psi)
    unit TEXT,
    deleted_at TEXT
);
"""

# ---------------------------------------------------------------------------------------------
# Columns added after the first version of the schema.
# `CREATE TABLE IF NOT EXISTS` never changes a table that already exists, so a database made by
# an older version of the hub would be missing any column added later. connect() adds each of
# these if it is not there yet. To add a column in future: put it in SCHEMA above AND list it
# here as (table, column, type).
# ---------------------------------------------------------------------------------------------
ADDED_COLUMNS = [
    ("batches", "recipe_json", "TEXT"),
]

# ---------------------------------------------------------------------------------------------
# Trash settings. A deleted batch, log entry or device stays recoverable for this many days.
# TRASH_TABLES lists the tables that have a `deleted_at` column.
# ---------------------------------------------------------------------------------------------
TRASH_DAYS = 7
TRASH_TABLES = ("batches", "events", "devices")

# ---------------------------------------------------------------------------------------------
# Default settings. config.json only needs to contain the ones you want to change; anything
# missing from the file falls back to the value here.
# ---------------------------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "port": 5000,                      # the web pages are at http://<pi address>:5000
    "upload_secret": "",               # shared password devices send with every upload
    "tilt_log_interval_seconds": 60,   # the Tilt listener stores one row per Tilt per this many seconds
    "backup_remote": "",               # where snapshots go: an rclone remote, e.g. "gdrive:phloat-backups"
    "runs_remote": "",                 # where finished-run exports go, e.g. "gdrive:phloat-runs"
    "full_backup_every_days": 7,       # a full copy this often; small "delta" snapshots in between
    "ha_url": "",                      # Home Assistant address, e.g. "http://homeassistant.local:8123" (see ha_publish.py)
    "ha_token": "",                    # Home Assistant long-lived access token (a secret; never backed up)
}


# ---------------------------------------------------------------------------------------------
# Finding the data folder and the files inside it.
# These are functions (not fixed values) so the tests can point PHLOAT_DATA at a temporary
# folder and have every part of the hub follow along.
# ---------------------------------------------------------------------------------------------
def data_dir() -> Path:
    """Return the data folder, creating it if it does not exist yet."""
    d = Path(os.environ.get("PHLOAT_DATA") or Path.home() / "phloat-data")
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    """Full path of the database file."""
    return data_dir() / "phloat.db"


def config_path() -> Path:
    """Full path of the settings file."""
    return data_dir() / "config.json"


def load_config() -> dict:
    """Read config.json and fill in defaults for anything it does not mention."""
    config = dict(DEFAULT_CONFIG)                       # start from a copy of the defaults
    if config_path().exists():
        config.update(json.loads(config_path().read_text(encoding="utf-8")))   # the file's values win
    return config


# ---------------------------------------------------------------------------------------------
# Opening the database.
# ---------------------------------------------------------------------------------------------
def connect() -> sqlite3.Connection:
    """Open the database (creating the file and tables on first use) and return the connection.

    The caller is responsible for calling .close() on the connection when finished.
    """
    conn = sqlite3.connect(db_path(), timeout=10)       # wait up to 10 s if another program is writing
    conn.row_factory = sqlite3.Row                      # rows can be read by column name: row["value"]
    # WAL ("write-ahead log") lets the web server and the Tilt listener, which are two separate
    # programs, write to the same file without locking each other out.
    conn.execute("PRAGMA journal_mode=WAL")
    # Make SQLite enforce the REFERENCES rules above (it ignores them unless asked).
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)                          # create any table that does not exist yet
    # Bring an older database up to date: add any column from ADDED_COLUMNS it does not have.
    for table, column, kind in ADDED_COLUMNS:
        existing = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")
    return conn


def utc_now() -> str:
    """The current time in UTC, in the text form every timestamp column uses."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------------------------
# Writing and reading.
# In the SQL below, each `?` is a placeholder that SQLite fills in from the list that follows.
# Never build SQL by gluing values into the text: placeholders are what stop a strange device
# name from being run as a database command ("SQL injection").
# ---------------------------------------------------------------------------------------------
def device_id(conn, kind: str, ident: str, color: str | None = None) -> int:
    """Return the id of a device, adding the device to the table the first time it is seen.

    If the device already exists and a colour is given, the colour is updated; if no colour is
    given, the stored one is kept (that is what COALESCE does: "first value that is not empty").
    """
    conn.execute(
        "INSERT INTO devices (kind, ident, color) VALUES (?, ?, ?) "
        "ON CONFLICT (kind, ident) DO UPDATE SET color = COALESCE(excluded.color, color)",
        (kind, ident, color),
    )
    return conn.execute("SELECT id FROM devices WHERE kind = ? AND ident = ?", (kind, ident)).fetchone()[0]


def add_readings(conn, dev_id: int, metrics: dict, ts: str | None = None) -> None:
    """Store one row per measurement. `metrics` looks like {"ph": 4.31, "temp_c": 19.2}.

    `ts` is the time of the reading; if it is left out, the current time is used.
    """
    ts = ts or utc_now()
    conn.executemany(
        "INSERT INTO readings (ts, device_id, metric, value) VALUES (?, ?, ?, ?)",
        [(ts, dev_id, metric, value) for metric, value in metrics.items()],
    )
    conn.commit()                                       # nothing is saved to disk until commit()


def latest_readings(conn) -> list[dict]:
    """Newest value of every metric on every device (used by the /api/recent address).

    GROUP BY makes one output row per (device, metric) pair, and MAX(r.ts) picks the newest
    time in each group; SQLite then returns the `value` from that same newest row.
    """
    rows = conn.execute(
        "SELECT d.kind, d.ident, d.color, r.metric, r.value, MAX(r.ts) AS ts "
        "FROM readings r JOIN devices d ON d.id = r.device_id "
        "GROUP BY r.device_id, r.metric ORDER BY d.kind, d.ident, r.metric"
    ).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------------------------
# Emptying the trash.
# ---------------------------------------------------------------------------------------------
def purge_deleted(conn) -> None:
    """Permanently remove anything that has sat in the trash longer than TRASH_DAYS.

    Called by the nightly backup and whenever the Trash page is opened.
    The order matters: rows that point AT a batch or device (its log entries, links, readings,
    settings) are removed first, then the batch or device itself. Doing it the other way round
    would break the REFERENCES rules and SQLite would refuse.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=TRASH_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    old = "deleted_at IS NOT NULL AND deleted_at < ?"   # "was deleted, and before the cutoff"
    # Log entries: ones deleted on their own, plus all entries of a batch that is being purged.
    conn.execute(f"DELETE FROM events WHERE {old} OR batch_id IN (SELECT id FROM batches WHERE {old})", (cutoff, cutoff))
    # Batch-to-device links of purged batches and purged devices.
    conn.execute(f"DELETE FROM batch_devices WHERE batch_id IN (SELECT id FROM batches WHERE {old}) "
                 f"OR device_id IN (SELECT id FROM devices WHERE {old})", (cutoff, cutoff))
    conn.execute(f"DELETE FROM batches WHERE {old}", (cutoff,))
    # A purged device takes its readings and settings with it.
    # A device that is still switched on simply shows up again the next time it reports.
    conn.execute(f"DELETE FROM readings WHERE device_id IN (SELECT id FROM devices WHERE {old})", (cutoff,))
    conn.execute(f"DELETE FROM device_settings WHERE device_id IN (SELECT id FROM devices WHERE {old})", (cutoff,))
    conn.execute(f"DELETE FROM devices WHERE {old}", (cutoff,))
    conn.commit()
