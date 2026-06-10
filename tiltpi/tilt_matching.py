"""Tilt timestamp matching shared by Tilt Pi ingestion."""

import os
import sqlite3
from datetime import datetime

from phloat_upload import TIME_MATCH_WINDOW


def find_matching_tilt_reading(timestamp: str, config: dict, default_tilt_db: str) -> dict | None:
    tilt_db = config.get("tilt_db_path", default_tilt_db)
    if not os.path.exists(tilt_db):
        print(f"Tilt database not found: {tilt_db}")
        return None

    try:
        conn = sqlite3.connect(tilt_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        tilt_table = next((t for t in ("data", "tilt_data", "readings", "tilt_readings") if t in tables), None)
        if not tilt_table:
            print(f"No Tilt data table found. Available tables: {tables}")
            conn.close()
            return None

        cursor.execute(f"PRAGMA table_info({tilt_table})")
        columns = [col[1] for col in cursor.fetchall()]

        timestamp_col = next((c for c in columns if "time" in c.lower() or "date" in c.lower()), None)
        color_col = next((c for c in columns if "color" in c.lower() or "name" in c.lower()), None)
        sg_col = next((c for c in columns if "gravity" in c.lower() or "sg" in c.lower()), None)
        temp_col = next((c for c in columns if "temp" in c.lower()), None)

        if not timestamp_col or not sg_col:
            print(f"Required columns not found in {tilt_table}")
            conn.close()
            return None

        target_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        target_epoch = target_time.timestamp()

        query = f"""
            SELECT {color_col or "'Unknown'"}, {sg_col}, {temp_col or 'NULL'}, {timestamp_col}
            FROM {tilt_table}
            WHERE ABS(strftime('%s', {timestamp_col}) - ?) <= ?
            ORDER BY ABS(strftime('%s', {timestamp_col}) - ?)
            LIMIT 1
        """
        cursor.execute(query, (target_epoch, TIME_MATCH_WINDOW, target_epoch))
        result = cursor.fetchone()
        conn.close()

        if not result:
            return None

        return {
            "color": result[0] if result[0] else "Unknown",
            "sg": float(result[1]) if result[1] else None,
            "temp": float(result[2]) if result[2] else None,
            "timestamp": result[3],
        }
    except Exception as exc:
        print(f"Error finding Tilt data: {exc}")
        return None
