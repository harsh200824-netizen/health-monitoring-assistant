#metrics.py
"""Read-side helpers for health metrics and fitness data."""

import re

from backend.wellness.common import (
    clamp, daterange, get_connection, timedelta, today_local, uid,
)

ALIASES = {
    "pulse": "heart_rate", "hr": "heart_rate", "bpm": "heart_rate",
    "bp": "blood_pressure", "glucose": "blood_sugar", "sugar": "blood_sugar",
    "blood_glucose": "blood_sugar", "temp": "temperature", "body_temperature": "temperature",
    "oxygen": "spo2", "oxygen_saturation": "spo2", "body_weight": "weight",
}

# (typical_low, typical_high, concern_low, concern_high)
REFERENCE = {
    "heart_rate": (60, 100, 40, 120, "bpm"),
    "spo2": (95, 100, 92, 101, "%"),
    "blood_sugar": (70, 140, 54, 250, "mg/dL"),
    "temperature": (36.1, 37.5, 35.0, 38.5, "\u00b0C"),
    "blood_pressure_systolic": (90, 129, 80, 160, "mmHg"),
    "blood_pressure_diastolic": (60, 84, 50, 100, "mmHg"),
}


def normalize_metric(name):
    key = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
    return ALIASES.get(key, key)


def parse_reading(metric_type, raw, unit=""):
    """Return [(normalized_name, float_value)].  Blood pressure gives two."""
    name = normalize_metric(metric_type)
    text = str(raw).strip()
    if name == "blood_pressure" and "/" in text:
        try:
            sys_, dia = (float(p) for p in text.split("/", 1))
            return [("blood_pressure_systolic", sys_), ("blood_pressure_diastolic", dia)]
        except ValueError:
            return []
    try:
        value = float(text)
    except ValueError:
        return []
    if value != value or value in (float("inf"), float("-inf")):
        return []
    if name == "temperature" and value > 45:          # Fahrenheit -> Celsius
        value = round((value - 32) * 5 / 9, 1)
    if name == "blood_sugar" and (value < 30 or "mmol" in str(unit).lower()):
        value = round(value * 18.0, 1)                # mmol/L -> mg/dL
    return [(name, value)]


def user_metric_rows(user_id, days=None):
    """Rows from health_metrics for this user.

    The existing import/chat code stores readings without a user id, so rows
    with no owner are included to stay consistent with the rest of the app.
    """
    user_id = uid(user_id)
    conn = get_connection()
    try:
        query = ("SELECT * FROM health_metrics "
                 "WHERE (user_id IS NULL OR CAST(user_id AS TEXT) = ?)")
        params = [str(user_id)]
        if days:
            cutoff = (today_local() - timedelta(days=days - 1)).isoformat()
            query += " AND date(recorded_at) >= ?"
            params.append(cutoff)
        query += " ORDER BY recorded_at ASC, id ASC"
        return [dict(r) for r in conn.execute(query, params).fetchall()]
    finally:
        conn.close()


def metric_series(user_id, days=30):
    """{metric_name: [{date, recorded_at, value, unit}]} for numeric readings."""
    series = {}
    for row in user_metric_rows(user_id, days):
        for name, value in parse_reading(row["metric_type"], row["value"], row.get("unit")):
            series.setdefault(name, []).append({
                "date": str(row["recorded_at"])[:10],
                "recorded_at": row["recorded_at"],
                "value": value,
                "unit": row.get("unit") or REFERENCE.get(name, (0, 0, 0, 0, ""))[4],
            })
    return series


def fitness_daily(user_id, days=14):
    """One row per day (including empty days) from fitness_activities."""
    user_id = uid(user_id)
    days = int(clamp(days, 1, 365))
    today = today_local()
    start = today - timedelta(days=days - 1)
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT date(recorded_at) AS d,
                      SUM(steps) AS steps, SUM(duration_minutes) AS duration_minutes,
                      SUM(calories_burned) AS calories_burned, SUM(distance_km) AS distance_km,
                      SUM(sleep_hours) AS sleep_hours, COUNT(*) AS sessions
               FROM fitness_activities
               WHERE CAST(user_id AS TEXT) = ? AND date(recorded_at) BETWEEN ? AND ?
               GROUP BY date(recorded_at)""",
            (str(user_id), start.isoformat(), today.isoformat()),
        ).fetchall()
    finally:
        conn.close()
    by_day = {r["d"]: dict(r) for r in rows}
    out = []
    for day in daterange(start, today):
        key = day.isoformat()
        row = by_day.get(key, {})
        out.append({
            "date": key,
            "steps": row.get("steps") or 0,
            "duration_minutes": row.get("duration_minutes") or 0,
            "calories_burned": row.get("calories_burned") or 0,
            "distance_km": round(row.get("distance_km") or 0, 2),
            "sleep_hours": round(row.get("sleep_hours") or 0, 2),
            "sessions": row.get("sessions") or 0,
            "has_data": key in by_day,
        })
    return out


def assess_reading(name, value):
    """Return None, 'info' (outside typical) or 'attention' (well outside)."""
    ref = REFERENCE.get(name)
    if not ref:
        return None
    low, high, c_low, c_high, _unit = ref
    if value < c_low or value > c_high:
        return "attention"
    if value < low or value > high:
        return "info"
    return None
