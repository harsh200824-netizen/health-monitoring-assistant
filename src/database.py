import sqlite3
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Asia/Kolkata")
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "health.db"


def now_local():
    return datetime.now(TIMEZONE)


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist yet."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dosage TEXT,
            time TEXT NOT NULL,          -- 24h format, e.g. "09:00"
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS dose_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medication_id INTEGER NOT NULL,
            taken_at TEXT NOT NULL,
            FOREIGN KEY (medication_id) REFERENCES medications (id)
        );

        CREATE TABLE IF NOT EXISTS health_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_type TEXT NOT NULL,   -- e.g. "blood_pressure", "sugar", "weight"
            value TEXT NOT NULL,
            unit TEXT,
            recorded_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


# ---------- Medications ----------

def add_medication(name, dosage, time):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO medications (name, dosage, time) VALUES (?, ?, ?)",
        (name, dosage, time),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_medications(active_only=True):
    conn = get_connection()
    query = "SELECT * FROM medications"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY time"
    rows = [dict(r) for r in conn.execute(query).fetchall()]
    conn.close()
    return rows


def delete_medication(med_id):
    conn = get_connection()
    conn.execute("UPDATE medications SET active = 0 WHERE id = ?", (med_id,))
    conn.commit()
    conn.close()


# ---------- Dose log ----------

def log_dose(medication_id):
    conn = get_connection()
    conn.execute(
        "INSERT INTO dose_log (medication_id, taken_at) VALUES (?, ?)",
        (medication_id, now_local().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def get_dose_log():
    conn = get_connection()
    rows = [dict(r) for r in conn.execute("""
        SELECT d.id, m.name, m.dosage, d.taken_at
        FROM dose_log d JOIN medications m ON m.id = d.medication_id
        ORDER BY d.taken_at DESC
    """).fetchall()]
    conn.close()
    return rows


def get_doses_taken_today():
    """Return a set of medication ids already taken today."""
    today = now_local().strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT medication_id FROM dose_log WHERE date(taken_at) = ?",
        (today,),
    ).fetchall()
    conn.close()
    return {r["medication_id"] for r in rows}


# ---------- Health metrics ----------

def add_metric(metric_type, value, unit=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO health_metrics (metric_type, value, unit, recorded_at) VALUES (?, ?, ?, ?)",
        (metric_type, str(value), unit, now_local().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def get_metrics(metric_type=None):
    conn = get_connection()
    if metric_type:
        rows = conn.execute(
            "SELECT * FROM health_metrics WHERE metric_type = ? ORDER BY recorded_at DESC",
            (metric_type,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM health_metrics ORDER BY recorded_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]