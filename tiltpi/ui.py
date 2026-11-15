"""The hub's web pages: overview, batches, the batch log, charts, controllers, devices, trash.

HOW A PAGE IS MADE
    Each function below with an `@ui.get(...)` or `@ui.post(...)` line above it handles one web
    address. It reads what it needs from the database, then calls render_template(), which
    fills in an HTML file from the templates/ folder and sends the result to the browser.
    This is "server-rendered": the Pi builds the finished page, so the pages work with
    JavaScript switched off and with the internet down. Nothing is loaded from other websites.

    The one piece of JavaScript is static/chart.js, which adds hover values and zoom to charts
    that have already been drawn here on the server.

GET AND POST
    GET  = "show me a page"       (following a link)
    POST = "do something"         (pressing a button on a form)
    After a POST the function answers with redirect(...), which sends the browser to a normal
    page. That way pressing the browser's refresh button never repeats the action.

SECURITY NOTE
    ponytail: there are no logins and no CSRF tokens. The hub is LAN-only by design (it must
    never be reachable from the internet). Add both before that ever changes.
    Two protections are always on: every value shown on a page is escaped by the template
    engine (so text typed by a user can't become HTML), and every SQL value goes in through a
    `?` placeholder (so it can't become SQL).
"""

import json
from datetime import datetime, timedelta, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from markupsafe import Markup, escape

import backup
import controller_settings
import recipe as recipe_reader
from db import TRASH_DAYS, TRASH_TABLES, connect, load_config, purge_deleted, utc_now

# A Blueprint is a bundle of pages that phloat_server.py attaches to the web application.
ui = Blueprint("ui", __name__)

# ---------------------------------------------------------------------------------------------
# Fixed lists used by the pages.
# ---------------------------------------------------------------------------------------------
# The kinds of entry offered in the batch log's drop-down.
EVENT_KINDS = ["note", "pressure", "dissolved_oxygen", "gravity_sample", "temperature_setpoint",
               "dry_hop", "yeast_pitch", "transfer", "other"]
# Friendly names for the stored metric names.
METRIC_LABELS = {"sg": "Gravity", "ph": "pH", "temp_c": "Temperature (°C)", "battery_v": "Battery (V)",
                 "rssi": "Signal (dBm)"}
CHART_ORDER = ["sg", "ph", "temp_c"]              # these charts come first, in this order
LINE_COLORS = ["#c2410c", "#0f766e", "#6d28d9", "#be185d", "#1d4ed8", "#4d7c0f"]   # one per line on a chart
BATCH_FIELDS = ("name", "fermenter_tag", "yeast", "recipe_name", "notes")          # plain text fields of a batch
TS = "%Y-%m-%dT%H:%M:%SZ"                         # the timestamp format used in the database
# A long run can hold tens of thousands of points per line. Sending them all would make the
# page slow, so each line is thinned to about this many.
# ponytail: this is plain "keep every Nth point", so zooming far into a long run looks coarse.
MAX_CHART_POINTS = 2000


# ---------------------------------------------------------------------------------------------
# Small helpers. The ones registered at the bottom of this block can be used inside templates.
# ---------------------------------------------------------------------------------------------
def _epoch(ts: str) -> float:
    """A database timestamp -> seconds since 1970 (a plain number that can be plotted)."""
    return datetime.strptime(ts, TS).replace(tzinfo=timezone.utc).timestamp()


def local(ts: str | None, fmt: str = "%d %b %H:%M") -> str:
    """Stored UTC -> the hub's local time, as text for display. Empty in, empty out."""
    if not ts:
        return ""
    return datetime.strptime(ts, TS).replace(tzinfo=timezone.utc).astimezone().strftime(fmt)


def to_utc(local_value: str) -> str:
    """The reverse: a date-and-time typed into a form (hub's local time) -> stored UTC.

    A blank field means "now".
    """
    if not local_value:
        return utc_now()
    return datetime.fromisoformat(local_value).astimezone(timezone.utc).strftime(TS)


def device_label(d) -> str:
    """What to call a device on a page: its typed name, else 'Red Tilt', else its identifier."""
    if d["name"]:
        return d["name"]
    return f"{d['color'].title()} Tilt" if d["kind"] == "tilt" and d["color"] else d["ident"]


def digits(metric: str) -> int:
    """How many decimal places suit each measurement (gravity 1.012, pH 4.31, temperature 19.2)."""
    return 3 if metric == "sg" else 2 if metric in ("ph", "battery_v") else 1


def fmt_value(metric: str, value: float) -> str:
    """A number as text with the right number of decimal places."""
    return f"{value:.{digits(metric)}f}"


def days_left(deleted_at: str) -> int:
    """How many whole days a deleted item has before it is purged."""
    gone = datetime.strptime(deleted_at, TS).replace(tzinfo=timezone.utc) + timedelta(days=TRASH_DAYS)
    return max(0, (gone - datetime.now(timezone.utc)).days)


# Make these available inside the HTML templates.
ui.add_app_template_filter(local, "local")                    # used as {{ value | local }}
ui.add_app_template_global(device_label)
ui.add_app_template_global(fmt_value)
ui.add_app_template_global(days_left)
ui.add_app_template_global(METRIC_LABELS, "METRIC_LABELS")
ui.add_app_template_global(TRASH_DAYS, "TRASH_DAYS")


# ---------------------------------------------------------------------------------------------
# Drawing a chart.
#
# A chart is drawn as SVG: a picture described in text ("a line from here to there"), which
# the browser draws sharply at any size. The work is turning each reading into a position:
#     x: its time, scaled from "first reading .. last reading" onto "left edge .. right edge"
#     y: its value, scaled from "lowest .. highest" onto "bottom .. top"
# The same readings are also attached as JSON so chart.js can redraw the chart when you
# hover or zoom.
# ---------------------------------------------------------------------------------------------
def svg_chart(series: dict[str, list[tuple[str, float]]], metric: str) -> Markup:
    """Return the HTML for one chart.

    `series` maps a line's label to its readings: {"Red Tilt": [(time, value), ...], ...}
    """
    # The drawing is 640 units wide and 220 tall; the margins leave room for the axis labels.
    width, height, left, bottom, top = 640, 220, 52, 22, 10
    points = [p for line in series.values() for p in line]
    if not points:
        return Markup("")

    # Find the range of times and values so everything can be scaled to fit.
    times = [_epoch(ts) for ts, _ in points]
    t0, t1 = min(times), max(times)
    lo, hi = min(v for _, v in points), max(v for _, v in points)
    # Add a little space above and below so the line doesn't touch the frame. The `or` chain
    # covers a perfectly flat line (hi == lo), which would otherwise divide by zero below.
    pad = (hi - lo) * 0.08 or abs(hi) * 0.01 or 1
    lo, hi = lo - pad, hi + pad

    def x(ts):
        """Time -> horizontal position."""
        return left + (_epoch(ts) - t0) / ((t1 - t0) or 1) * (width - left - 8)

    def y(v):
        """Value -> vertical position. SVG counts downward, so a high value gets a small y."""
        return top + (hi - v) / (hi - lo) * (height - top - bottom)

    out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(METRIC_LABELS.get(metric, metric))} chart">']
    # Five horizontal grid lines, each labelled with its value.
    for i in range(5):
        v = lo + (hi - lo) * i / 4
        out.append(f'<line class="grid" x1="{left}" x2="{width - 8}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                   f'<text class="tick" x="{left - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{fmt_value(metric, v)}</text>')
    # The start and end times under the chart.
    first, last = min(points)[0], max(points)[0]
    out.append(f'<text class="tick" x="{left}" y="{height - 5}">{escape(local(first))}</text>'
               f'<text class="tick" x="{width - 8}" y="{height - 5}" text-anchor="end">{escape(local(last))}</text>')

    # One line per device, plus the same data collected into `payload` for chart.js.
    payload = {"digits": digits(metric), "series": []}
    for i, (label, line) in enumerate(series.items()):
        line = line[::max(1, len(line) // MAX_CHART_POINTS)]      # thin out very long lines
        color = LINE_COLORS[i % len(LINE_COLORS)]
        payload["series"].append({"label": label, "color": color, "points": [[_epoch(ts), v] for ts, v in line]})
        if len(line) == 1:
            # A single reading can't make a line, so draw a dot.
            out.append(f'<circle cx="{x(line[0][0]):.1f}" cy="{y(line[0][1]):.1f}" r="3" fill="{color}"/>')
        else:
            coords = " ".join(f"{x(ts):.1f},{y(v):.1f}" for ts, v in line)
            out.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{coords}"/>')
    out.append("</svg>")
    legend = "".join(f'<span><i style="background:{s["color"]}"></i>{escape(s["label"])}</span>' for s in payload["series"])
    # Markup() tells the template engine "this text is HTML I built on purpose, don't escape it".
    # Everything that came from a user (labels) was passed through escape() above.
    return Markup(f'<div class="plot" data-chart="{escape(json.dumps(payload))}">{"".join(out)}</div>'
                  f'<div class="legend">{legend}</div>')


# ---------------------------------------------------------------------------------------------
# Database helpers shared by several pages.
# ---------------------------------------------------------------------------------------------
def _latest(conn, where: str, args: tuple) -> list:
    """Newest value of each measurement for the devices matching `where` (deleted devices excluded).

    `where` is always a fixed piece of SQL written in this file, never user input.
    """
    return conn.execute(
        "SELECT d.id AS device_id, d.kind, d.ident, d.color, d.name, r.metric, r.value, MAX(r.ts) AS ts "
        f"FROM readings r JOIN devices d ON d.id = r.device_id WHERE d.deleted_at IS NULL AND {where} "
        "GROUP BY r.device_id, r.metric ORDER BY d.kind DESC, d.ident, r.metric", args).fetchall()


def _batch_or_404(conn, batch_id: int):
    """Fetch a batch, or answer "404 Not Found" if it does not exist or has been deleted."""
    batch = conn.execute("SELECT * FROM batches WHERE id = ? AND deleted_at IS NULL", (batch_id,)).fetchone()
    if batch is None:
        conn.close()
        abort(404)
    return batch


def _live_devices(conn) -> list:
    """Every device that has not been deleted."""
    return conn.execute("SELECT * FROM devices WHERE deleted_at IS NULL ORDER BY kind DESC, ident").fetchall()


# ---------------------------------------------------------------------------------------------
# The overview page ("/"): what is fermenting now, spare devices, finished runs.
# ---------------------------------------------------------------------------------------------
@ui.get("/")
def overview():
    conn = connect()
    # Active batches (no end time yet), each with the newest readings from its devices.
    active = []
    for batch in conn.execute("SELECT * FROM batches WHERE ended_at IS NULL AND deleted_at IS NULL ORDER BY started_at DESC"):
        latest = _latest(conn, "r.device_id IN (SELECT device_id FROM batch_devices WHERE batch_id = ?) AND r.ts >= ?",
                         (batch["id"], batch["started_at"] or ""))
        active.append((batch, latest))
    finished = conn.execute("SELECT * FROM batches WHERE ended_at IS NOT NULL AND deleted_at IS NULL "
                            "ORDER BY ended_at DESC LIMIT 20").fetchall()
    # Devices that are reporting but are not on any active batch: a Tilt waiting to be assigned.
    unassigned = _latest(conn, "r.device_id NOT IN (SELECT bd.device_id FROM batch_devices bd JOIN batches b "
                               "ON b.id = bd.batch_id WHERE b.ended_at IS NULL AND b.deleted_at IS NULL)", ())
    conn.close()
    return render_template("overview.html", active=active, finished=finished, unassigned=unassigned)


# ---------------------------------------------------------------------------------------------
# Creating and editing a batch. Both use the same form (templates/batch_form.html).
# GET shows the form; POST saves what was typed.
# ---------------------------------------------------------------------------------------------
@ui.route("/batches/new", methods=["GET", "POST"])
def batch_new():
    conn = connect()
    if request.method == "POST":
        batch_id = _save_batch(conn, None)
        conn.close()
        return redirect(url_for("ui.batch", batch_id=batch_id))
    devices = _live_devices(conn)
    conn.close()
    return render_template("batch_form.html", batch=None, devices=devices, assigned=set())


@ui.route("/batches/<int:batch_id>/edit", methods=["GET", "POST"])
def batch_edit(batch_id):
    conn = connect()
    batch = _batch_or_404(conn, batch_id)
    if request.method == "POST":
        _save_batch(conn, batch_id)
        conn.close()
        return redirect(url_for("ui.batch", batch_id=batch_id))
    devices = _live_devices(conn)
    # The set of device ids already on this batch, so their boxes start ticked.
    assigned = {r[0] for r in conn.execute("SELECT device_id FROM batch_devices WHERE batch_id = ?", (batch_id,))}
    conn.close()
    return render_template("batch_form.html", batch=batch, devices=devices, assigned=assigned)


def _save_batch(conn, batch_id):
    """Save the batch form. `batch_id` is None for a new batch. Returns the batch's id."""
    # Read the text fields; an empty box is stored as "nothing" (None) rather than "".
    values = {k: request.form.get(k, "").strip() or None for k in BATCH_FIELDS}
    if not values["name"]:
        conn.close()
        abort(400, "A batch needs a name.")
    if batch_id is None:
        # New batch: create the row. A blank start time means "started now".
        batch_id = conn.execute("INSERT INTO batches (name, started_at) VALUES (?, ?)",
                                (values["name"], to_utc(request.form.get("started_at", "")))).lastrowid
    elif request.form.get("started_at"):
        # Existing batch: only change the start time if one was typed.
        conn.execute("UPDATE batches SET started_at = ? WHERE id = ?", (to_utc(request.form["started_at"]), batch_id))
    conn.execute("UPDATE batches SET name = ?, fermenter_tag = ?, yeast = ?, recipe_name = ?, notes = ? WHERE id = ?",
                 (*values.values(), batch_id))
    recipe = request.files.get("recipe_file")
    if recipe and recipe.filename:
        # The recipe file is stored exactly as uploaded (BeerXML, Brewfather JSON, any text),
        # reading at most 2 MB. recipe.py then tries to read a summary out of it: ingredients,
        # gravities, mash steps. A file it can't understand is still kept attached.
        text = recipe.read(2_000_000).decode("utf-8", "replace")
        summary = recipe_reader.parse_recipe(text)
        conn.execute("UPDATE batches SET recipe_file = ?, recipe_json = ? WHERE id = ?",
                     (text, json.dumps(summary) if summary else None, batch_id))
        if summary:
            # Fill in the recipe name and yeast from the file, but only where the form left them
            # blank: something typed by hand always wins over the file.
            yeast = ", ".join(" ".join(filter(None, (y.get("lab"), y.get("name")))) for y in summary["yeasts"])
            conn.execute("UPDATE batches SET recipe_name = COALESCE(recipe_name, ?), yeast = COALESCE(yeast, ?) WHERE id = ?",
                         (summary.get("name"), yeast or None, batch_id))
            flash(f"Recipe read as {summary['format']}: {len(summary['fermentables'])} fermentables, "
                  f"{len(summary['hops'])} hop additions.")
        else:
            flash("The recipe file is attached, but it isn't a BeerXML or Brewfather file the hub can read, "
                  "so no ingredients were filled in.")
    # Replace the batch's device list with the boxes that were ticked.
    conn.execute("DELETE FROM batch_devices WHERE batch_id = ?", (batch_id,))
    conn.executemany("INSERT INTO batch_devices VALUES (?, ?)",
                     [(batch_id, int(d)) for d in request.form.getlist("devices")])
    conn.commit()
    return batch_id


# ---------------------------------------------------------------------------------------------
# One batch's page: details, newest values, charts, and the log.
# ---------------------------------------------------------------------------------------------
@ui.get("/batches/<int:batch_id>")
def batch(batch_id):
    conn = connect()
    b = _batch_or_404(conn, batch_id)
    # Every reading from this batch's devices between its start and end times.
    rows = conn.execute(
        "SELECT r.ts, r.metric, r.value, d.kind, d.ident, d.color, d.name FROM readings r "
        "JOIN devices d ON d.id = r.device_id JOIN batch_devices bd ON bd.device_id = d.id "
        "WHERE bd.batch_id = ? AND d.deleted_at IS NULL AND r.ts >= COALESCE(?, '') AND r.ts <= COALESCE(?, '9999') "
        "ORDER BY r.ts", (batch_id, b["started_at"], b["ended_at"])).fetchall()
    # Sort the readings into {metric: {device label: [(time, value), ...]}}: one chart per
    # metric, one line per device.
    by_metric = {}
    for r in rows:
        by_metric.setdefault(r["metric"], {}).setdefault(device_label(r), []).append((r["ts"], r["value"]))
    # Gravity, pH and temperature first; then any other metric in alphabetical order.
    # Signal strength and battery voltage are diagnostics, so they get no chart.
    order = [m for m in CHART_ORDER if m in by_metric] + sorted(m for m in by_metric if m not in CHART_ORDER + ["rssi", "battery_v"])
    charts = [(METRIC_LABELS.get(m, m), svg_chart(by_metric[m], m)) for m in order]
    latest = _latest(conn, "r.device_id IN (SELECT device_id FROM batch_devices WHERE batch_id = ?) "
                           "AND r.ts >= COALESCE(?, '') AND r.ts <= COALESCE(?, '9999')",
                     (batch_id, b["started_at"], b["ended_at"]))
    events = conn.execute("SELECT * FROM events WHERE batch_id = ? AND deleted_at IS NULL ORDER BY ts DESC",
                          (batch_id,)).fetchall()
    devices = conn.execute("SELECT d.* FROM devices d JOIN batch_devices bd ON bd.device_id = d.id "
                           "WHERE bd.batch_id = ? AND d.deleted_at IS NULL", (batch_id,)).fetchall()
    conn.close()
    # The recipe summary is stored as JSON text; turn it back into a dictionary for the page.
    recipe_summary = json.loads(b["recipe_json"]) if b["recipe_json"] else None
    return render_template("batch.html", batch=b, charts=charts, latest=latest, events=events, devices=devices,
                           kinds=EVENT_KINDS, runs_remote=load_config()["runs_remote"], recipe=recipe_summary)


# ---------------------------------------------------------------------------------------------
# Adding a log entry: a note, or a number measured by hand (pressure, dissolved oxygen, ...).
# ---------------------------------------------------------------------------------------------
@ui.post("/batches/<int:batch_id>/events")
def event_add(batch_id):
    conn = connect()
    _batch_or_404(conn, batch_id)
    note = request.form.get("note", "").strip()
    raw_value = request.form.get("value", "").strip()
    try:
        value = float(raw_value) if raw_value else None
    except ValueError:
        # Someone typed words in the number box. Don't lose them: keep the text in the note.
        value = None
        flash(f"'{raw_value}' isn't a number, so it was saved in the note instead.")
        note = f"{note} [{raw_value}]".strip()
    if note or value is not None:                      # ignore a completely empty form
        kind = request.form.get("kind", "note")
        conn.execute("INSERT INTO events (ts, batch_id, kind, note, value, unit) VALUES (?, ?, ?, ?, ?, ?)",
                     (to_utc(request.form.get("ts", "")), batch_id, kind if kind in EVENT_KINDS else "other",
                      note or None, value, request.form.get("unit", "").strip() or None))
        conn.commit()
    conn.close()
    return redirect(url_for("ui.batch", batch_id=batch_id) + "#log")   # "#log" scrolls back to the log


# ---------------------------------------------------------------------------------------------
# Editing a log entry. GET shows the entry in a form; POST saves the changes.
# ---------------------------------------------------------------------------------------------
@ui.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
def event_edit(event_id):
    conn = connect()
    event = conn.execute("SELECT * FROM events WHERE id = ? AND deleted_at IS NULL", (event_id,)).fetchone()
    if event is None:
        conn.close()
        abort(404)
    if request.method == "POST":
        raw_value = request.form.get("value", "").strip()
        try:
            value = float(raw_value) if raw_value else None
        except ValueError:
            # Unlike adding an entry, an edit with a bad number is refused outright, so a typing
            # slip can't quietly wipe a measurement that was already recorded.
            conn.close()
            flash(f"'{raw_value}' isn't a number. Nothing was changed.")
            return redirect(url_for("ui.event_edit", event_id=event_id))
        kind = request.form.get("kind", event["kind"])
        # A blank "When" keeps the entry's original time.
        ts = to_utc(request.form["ts"]) if request.form.get("ts") else event["ts"]
        conn.execute("UPDATE events SET ts = ?, kind = ?, note = ?, value = ?, unit = ? WHERE id = ?",
                     (ts, kind if kind in EVENT_KINDS else "other", request.form.get("note", "").strip() or None,
                      value, request.form.get("unit", "").strip() or None, event_id))
        conn.commit()
        conn.close()
        return redirect(url_for("ui.batch", batch_id=event["batch_id"]) + "#log")
    conn.close()
    return render_template("event_form.html", event=event, kinds=EVENT_KINDS)


# ---------------------------------------------------------------------------------------------
# Marking a batch complete. This is the "export, upload, verify, prune" step.
# ---------------------------------------------------------------------------------------------
@ui.post("/batches/<int:batch_id>/complete")
def batch_complete(batch_id):
    conn = connect()
    b = _batch_or_404(conn, batch_id)
    if b["ended_at"] is None:
        conn.execute("UPDATE batches SET ended_at = ? WHERE id = ?", (utc_now(), batch_id))
        conn.commit()
    conn.close()
    # From here on, any failure leaves the readings in the database. The batch stays marked
    # complete and the button on its page becomes "Archive", which runs this again.
    try:
        if not load_config()["runs_remote"]:
            # No Google Drive destination set: export to the Pi only, and prune nothing.
            out = backup.export_run(batch_id)
            flash(f"Marked complete and exported to {out}. No runs_remote is set, so nothing was uploaded "
                  "and the readings stay in the database.")
        else:
            out = backup.archive_run(batch_id)         # export, upload, verify, then prune
            flash(f"Archived: exported to {out}, uploaded, verified, and pruned from the database.")
    except (Exception, SystemExit) as exc:
        flash(f"Marked complete, but archiving failed ({exc}). The readings are still in the database; "
              "press Archive to try again.")
    return redirect(url_for("ui.batch", batch_id=batch_id))


# ---------------------------------------------------------------------------------------------
# Controllers: see each fermenter controller and change its settings.
# How the settings reach the controller is explained in controller_settings.py.
# ---------------------------------------------------------------------------------------------
@ui.route("/controllers", methods=["GET"])
def controllers():
    conn = connect()
    rows = []
    # A "controller" is any device that has reported settings.
    for d in conn.execute("SELECT * FROM devices WHERE deleted_at IS NULL AND id IN "
                          "(SELECT device_id FROM device_settings) ORDER BY ident").fetchall():
        settings = {r["key"]: r for r in conn.execute("SELECT * FROM device_settings WHERE device_id = ?", (d["id"],))}
        # Build one form field per setting, in the order of the SPEC table.
        fields = []
        for key, spec in controller_settings.SPEC.items():
            if key in settings:
                desired, reported = json.loads(settings[key]["desired"]), json.loads(settings[key]["reported"])
                # "pending" = the hub wants one value and the controller is still running another.
                fields.append({"key": key, "label": spec[0], "kind": spec[1], "spec": spec, "value": desired,
                               "reported": reported, "pending": desired != reported})
        seen = max((s["reported_at"] or "" for s in settings.values()), default="")   # last check-in time
        latest = _latest(conn, "r.device_id = ?", (d["id"],))
        rows.append({"device": d, "fields": fields, "seen": seen, "latest": latest,
                     "pending": sum(f["pending"] for f in fields)})
    conn.close()
    return render_template("controllers.html", controllers=rows)


@ui.post("/controllers/<int:device_id>")
def controller_save(device_id):
    """Save the settings form. It is all-or-nothing: one bad value and nothing is changed."""
    values, errors = {}, []
    for key, spec in controller_settings.SPEC.items():
        if spec[1] == "bool":
            # A browser sends nothing at all for an unticked checkbox, so "missing" means off.
            raw = request.form.get(key, "off")
        elif key not in request.form:
            continue
        else:
            raw = request.form[key]
        try:
            values[key] = controller_settings.clean(key, raw)     # checks type and range
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        flash("Nothing was changed. " + " ".join(errors))
    else:
        conn = connect()
        controller_settings.set_desired(conn, device_id, values)
        conn.close()
        flash("Saved. The controller picks the settings up at its next check-in, within about 15 seconds.")
    return redirect(url_for("ui.controllers"))


# ---------------------------------------------------------------------------------------------
# Devices: rename. Then delete, the trash, and restore, shared by batches, log entries and devices.
# ---------------------------------------------------------------------------------------------
@ui.get("/devices")
def devices():
    conn = connect()
    rows = _live_devices(conn)
    # {device id: time of its newest reading}
    last_seen = dict(conn.execute("SELECT device_id, MAX(ts) FROM readings GROUP BY device_id").fetchall())
    conn.close()
    return render_template("devices.html", devices=rows, last_seen=last_seen)


@ui.post("/devices/<int:device_id>/rename")
def device_rename(device_id):
    """Set a device's display name (at most 60 characters). A blank name restores the default label."""
    conn = connect()
    conn.execute("UPDATE devices SET name = ? WHERE id = ?", (request.form.get("name", "").strip()[:60] or None, device_id))
    conn.commit()
    conn.close()
    return redirect(url_for("ui.devices"))


# `<any(batches, events, devices):table>` only matches those three words, so `table` can safely
# be placed into the SQL text below. Any other word in the address gets "404 Not Found".
@ui.post("/<any(batches, events, devices):table>/<int:row_id>/delete")
def delete(table, row_id):
    """Soft delete: the row is hidden at once, stays in the trash for TRASH_DAYS, then is purged."""
    conn = connect()
    conn.execute(f"UPDATE {table} SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL", (utc_now(), row_id))
    conn.commit()
    conn.close()
    flash(f"Deleted. You can restore it from the trash for {TRASH_DAYS} days.")
    # Go back to the page the delete button was on. Only addresses on this site are accepted
    # (they start with a single "/"); anything else could be a link to another website.
    target = request.form.get("next", "")
    return redirect(target if target.startswith("/") and not target.startswith("//") else url_for("ui.overview"))


@ui.get("/trash")
def trash():
    conn = connect()
    purge_deleted(conn)        # first remove anything whose 7 days are up
    items = {table: conn.execute(f"SELECT * FROM {table} WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC").fetchall()
             for table in TRASH_TABLES}
    conn.close()
    return render_template("trash.html", items=items)


@ui.post("/trash/<any(batches, events, devices):table>/<int:row_id>/restore")
def restore(table, row_id):
    """Undo a delete by clearing the row's deleted_at mark."""
    conn = connect()
    conn.execute(f"UPDATE {table} SET deleted_at = NULL WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()
    flash("Restored.")
    return redirect(url_for("ui.trash"))
