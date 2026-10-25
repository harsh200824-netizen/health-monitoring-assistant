import sqlite3
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "health.db"

TIMEZONE = ZoneInfo("Asia/Kolkata")



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
    
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'patient',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );


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

        CREATE TABLE IF NOT EXISTS fitness_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_type TEXT NOT NULL,
            duration_minutes INTEGER,
            steps INTEGER,
            distance_km REAL,
            calories_burned INTEGER,
            sleep_hours REAL,
            notes TEXT,
            recorded_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS health_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_type TEXT NOT NULL,
            target_value REAL NOT NULL,
            unit TEXT NOT NULL,
            created_at TEXT NOT NULL,
            active INTEGER DEFAULT 1
        );
    """)
    conn.commit()
    conn.close()

def migrate_user_id():
    conn = get_connection()

    try:
        tables = [
            "medications",
            "health_metrics",
            "fitness_activities",
            "health_goals",
        ]

        for table in tables:
            columns = [
                row["name"]
                for row in conn.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            ]

            if "user_id" not in columns:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN user_id INTEGER"
                )

        # Assign the existing test fitness record to testuser1.
        conn.execute(
            """
            UPDATE fitness_activities
            SET user_id = 1
            WHERE user_id IS NULL
            """
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
# ---------- Medications ----------


def add_medication(name, dosage, time, user_id):
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO medications (name, dosage, time, user_id)
            VALUES (?, ?, ?, ?)
            """,
            (name, dosage, time, user_id),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_medications(user_id, active_only=True):
    conn = get_connection()
    try:
        query = "SELECT * FROM medications WHERE user_id = ?"
        params = [user_id]

        if active_only:
            query += " AND active = 1"

        query += " ORDER BY time"

        rows = [
            dict(r)
            for r in conn.execute(query, params).fetchall()
        ]
        return rows
    finally:
        conn.close()


def delete_medication(med_id, user_id):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE medications
            SET active = 0
            WHERE id = ? AND user_id = ?
            """,
            (med_id, user_id),
        )
        conn.commit()
    finally:
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

# ---------- Fitness Tracking ----------

def add_fitness_activity(
    activity_type,
    duration_minutes=None,
    steps=None,
    distance_km=None,
    calories_burned=None,
    sleep_hours=None,
    notes=""
):
    conn = get_connection()

    cur = conn.execute(
        """
        INSERT INTO fitness_activities (
            activity_type,
            duration_minutes,
            steps,
            distance_km,
            calories_burned,
            sleep_hours,
            notes,
            recorded_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            activity_type.strip().lower(),
            duration_minutes,
            steps,
            distance_km,
            calories_burned,
            sleep_hours,
            notes,
            now_local().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )

    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return new_id


def get_fitness_activities(limit=50):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM fitness_activities
        ORDER BY recorded_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]




def get_fitness_summary():
    """Return summary statistics from recorded fitness activities."""
    conn = get_connection()

    row = conn.execute("""
        SELECT
            COUNT(*) AS total_activities,
            COALESCE(SUM(duration_minutes), 0) AS total_duration_minutes,
            COALESCE(SUM(steps), 0) AS total_steps,
            COALESCE(SUM(distance_km), 0) AS total_distance_km,
            COALESCE(SUM(calories_burned), 0) AS total_calories,
            COALESCE(SUM(sleep_hours), 0) AS total_sleep_hours
        FROM fitness_activities
    """).fetchone()

    conn.close()
    return dict(row)



def add_health_goal(goal_type, target_value, unit):
    conn = get_connection()

    cur = conn.execute(
        """
        INSERT INTO health_goals
        (goal_type, target_value, unit, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            goal_type.strip().lower(),
            target_value,
            unit.strip(),
            now_local().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )

    conn.commit()
    goal_id = cur.lastrowid
    conn.close()
    return goal_id


def get_health_goals():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM health_goals
        WHERE active = 1
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()
    return [dict(row) for row in rows]


def get_health_goal_progress():
    conn = get_connection()

    goals = conn.execute(
        "SELECT * FROM health_goals WHERE active = 1 ORDER BY id DESC"
    ).fetchall()

    today = now_local().strftime("%Y-%m-%d")

    activities = conn.execute(
        """
        SELECT
            COALESCE(SUM(steps), 0) AS total_steps,
            COALESCE(SUM(duration_minutes), 0) AS total_duration,
            COALESCE(SUM(distance_km), 0) AS total_distance,
            COALESCE(SUM(calories_burned), 0) AS total_calories,
            COALESCE(SUM(sleep_hours), 0) AS total_sleep
        FROM fitness_activities
        WHERE date(recorded_at) = ?
        """,
        (today,),
    ).fetchone()

    conn.close()

    totals = {
        "steps": activities["total_steps"],
        "duration": activities["total_duration"],
        "distance": activities["total_distance"],
        "calories": activities["total_calories"],
        "sleep": activities["total_sleep"],
    }

    results = []

    for goal in goals:
        goal_type = goal["goal_type"].strip().lower()
        current = totals.get(goal_type)

        if current is None:
            current = 0

        target = goal["target_value"]
        percentage = min(round((current / target) * 100, 1), 100)

        results.append({
            "id": goal["id"],
            "goal_type": goal_type,
            "current_value": current,
            "target_value": target,
            "unit": goal["unit"],
            "progress_percent": percentage,
            "completed": current >= target,
        })

    return results

