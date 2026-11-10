"""Wellness goal tracking with progress analytics.

Goals are daily or weekly, and are either ``at_least`` (steps, water, sleep)
or ``at_most`` (screen time, sugar).  A goal is either logged manually or
tracked automatically from the fitness activities already stored by the app.
"""

import math
from statistics import mean

from backend.wellness.common import (
    DATE_FMT, WellnessError, clamp, get_connection, now_local, parse_date, percent,
    timedelta, today_local, uid, DATETIME_FMT,
)

AUTO_SOURCES = {
    "steps": "steps",
    "active_minutes": "duration_minutes",
    "calories": "calories_burned",
    "sleep_hours": "sleep_hours",
    "distance_km": "distance_km",
}
VALID_SOURCES = {"manual", *AUTO_SOURCES}
VALID_PERIODS = {"daily", "weekly"}
VALID_DIRECTIONS = {"at_least", "at_most"}


# ---------- data access ----------

def _day_values(conn, goal, start, end):
    """{date_string: value} for a goal between two dates (inclusive)."""
    if goal["source"] == "manual":
        rows = conn.execute(
            """SELECT log_date AS d, value FROM wellness_goal_logs
               WHERE goal_id = ? AND log_date BETWEEN ? AND ?""",
            (goal["id"], start.isoformat(), end.isoformat()),
        ).fetchall()
        return {r["d"]: r["value"] for r in rows}

    column = AUTO_SOURCES[goal["source"]]  # whitelisted, safe to interpolate
    rows = conn.execute(
        f"""SELECT date(recorded_at) AS d, SUM({column}) AS value
            FROM fitness_activities
            WHERE CAST(user_id AS TEXT) = ? AND date(recorded_at) BETWEEN ? AND ?
              AND {column} IS NOT NULL
            GROUP BY date(recorded_at)""",
        (str(goal["user_id"]), start.isoformat(), end.isoformat()),
    ).fetchall()
    return {r["d"]: r["value"] for r in rows}


# ---------- analytics ----------

def _bucket_start(day, period):
    return day if period == "daily" else day - timedelta(days=day.weekday())


def _trend(values):
    if len(values) < 4:
        return "not_enough_data"
    half = len(values) // 2
    older, newer = mean(values[:half]), mean(values[half:])
    if older == 0:
        return "up" if newer > 0 else "flat"
    change = (newer - older) / older
    return "up" if change > 0.05 else "down" if change < -0.05 else "flat"


def goal_progress_percent(value, target, direction):
    if target <= 0:
        return 0.0
    if direction == "at_most":
        if value <= target:
            return 100.0
        return round(max(0.0, 100.0 - (value - target) / target * 100.0), 1)
    return round(min(value / target * 100.0, 100.0), 1)


def analyse_goal(goal, day_values, today=None):
    today = today or today_local()
    period, target, direction = goal["period"], goal["target_value"], goal["direction"]
    step = timedelta(days=1 if period == "daily" else 7)
    first = _bucket_start(parse_date(goal["start_date"]), period)
    current_bucket = _bucket_start(today, period)

    buckets, cursor = [], current_bucket
    for _ in range(14 if period == "daily" else 8):
        if cursor < first:
            break
        buckets.append(cursor)
        cursor -= step
    buckets.reverse()

    rows = []
    for b in buckets:
        span = [(b + timedelta(days=i)).isoformat() for i in range((step.days))]
        present = [day_values[d] for d in span if d in day_values]
        value = round(sum(present), 2) if present else 0.0
        has_data = bool(present)
        met = (value >= target) if direction == "at_least" else (has_data and value <= target)
        rows.append({
            "bucket_start": b.isoformat(), "value": value, "has_data": has_data,
            "met": bool(met), "is_current": b == current_bucket,
        })

    current = rows[-1] if rows else {"value": 0.0, "has_data": False, "met": False}
    past = [r for r in rows if not r["is_current"]]

    # Streak: consecutive met buckets ending now.  At-most goals are only final
    # once the period is over, so the open period never counts for them.
    streak_rows = past + ([current] if direction == "at_least" and rows else [])
    streak = 0
    for r in reversed(streak_rows):
        if r["met"]:
            streak += 1
        elif r["is_current"]:
            continue  # open period not met yet: judge by the closed ones
        else:
            break
    best = run = 0
    for r in rows:
        if r["met"] and not (direction == "at_most" and r["is_current"]):
            run += 1
            best = max(best, run)
        elif not r["is_current"]:
            run = 0

    counted = [r for r in past if direction == "at_least" or r["has_data"]]
    if direction == "at_least" and current["met"]:
        counted.append(current)
    success_rate = percent(sum(1 for r in counted if r["met"]), len(counted))

    recent = [r["value"] for r in rows[-7:] if r["has_data"]]
    prog = goal_progress_percent(current["value"], target, direction)

    if direction == "at_most":
        status = ("no_data" if not current["has_data"]
                  else "within_limit" if current["value"] <= target else "exceeded")
    elif current["met"]:
        status = "completed"
    elif current["value"] <= 0:
        status = "not_started"
    elif period == "weekly":
        elapsed = (today.weekday() + 1) / 7.0
        status = "on_track" if prog >= elapsed * 100 * 0.8 else "behind"
    else:
        status = "in_progress"

    return {
        "current_value": round(current["value"], 2),
        "progress_percent": prog,
        "status": status,
        "streak": streak,
        "best_streak": best,
        "success_rate_percent": success_rate,
        "average_recent": round(mean(recent), 2) if recent else None,
        "trend": _trend([r["value"] for r in past if r["has_data"]]),
        "history": [
            {"bucket_start": r["bucket_start"], "value": r["value"], "met": r["met"]}
            for r in rows[-7:]
        ],
    }


# ---------- CRUD ----------

def create_goal(user_id, title, target_value, unit, period="daily",
                direction="at_least", source="manual"):
    user_id = uid(user_id)
    title, unit = (title or "").strip(), (unit or "").strip()
    if not title or not unit:
        raise WellnessError("Title and unit are required.", 422)
    if len(title) > 80 or len(unit) > 30:
        raise WellnessError("Title or unit is too long.", 422)
    if period not in VALID_PERIODS:
        raise WellnessError("Period must be 'daily' or 'weekly'.", 422)
    if direction not in VALID_DIRECTIONS:
        raise WellnessError("Direction must be 'at_least' or 'at_most'.", 422)
    if source not in VALID_SOURCES:
        raise WellnessError(f"Source must be one of: {', '.join(sorted(VALID_SOURCES))}.", 422)
    if not math.isfinite(target_value) or target_value <= 0:
        raise WellnessError("Target must be a positive number.", 422)

    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO wellness_goals
               (user_id, title, target_value, unit, period, direction, source,
                start_date, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, title, target_value, unit, period, direction, source,
             today_local().isoformat(), now_local().strftime(DATETIME_FMT)),
        )
        conn.commit()
        return {"id": cur.lastrowid, "message": "Goal created."}
    finally:
        conn.close()


def _owned_goal(conn, user_id, goal_id):
    row = conn.execute(
        "SELECT * FROM wellness_goals WHERE id = ? AND user_id = ? AND active = 1",
        (goal_id, user_id),
    ).fetchone()
    if row is None:
        raise WellnessError("Goal not found.", 404)
    return dict(row)


def list_goals(user_id):
    user_id = uid(user_id)
    today = today_local()
    conn = get_connection()
    try:
        goals = [dict(r) for r in conn.execute(
            "SELECT * FROM wellness_goals WHERE user_id = ? AND active = 1 ORDER BY id DESC",
            (user_id,),
        ).fetchall()]
        out = []
        for g in goals:
            period_days = 14 if g["period"] == "daily" else 8 * 7 + 7
            start = today - timedelta(days=period_days)
            values = _day_values(conn, g, start, today)
            out.append({**g, "analytics": analyse_goal(g, values, today)})
        return out
    finally:
        conn.close()


def log_goal_value(user_id, goal_id, value, log_date=None, mode="add", note=""):
    user_id = uid(user_id)
    if not math.isfinite(value) or value < 0:
        raise WellnessError("Value must be zero or greater.", 422)
    if mode not in {"add", "set"}:
        raise WellnessError("Mode must be 'add' or 'set'.", 422)
    today = today_local()
    day = parse_date(log_date, "log_date") if log_date else today
    if day > today:
        raise WellnessError("You cannot log a future date.", 422)
    if day < today - timedelta(days=365):
        raise WellnessError("That date is too far in the past.", 422)

    conn = get_connection()
    try:
        goal = _owned_goal(conn, user_id, goal_id)
        if goal["source"] != "manual":
            raise WellnessError(
                "This goal is tracked automatically from your fitness activities.", 400)
        row = conn.execute(
            "SELECT value FROM wellness_goal_logs WHERE goal_id = ? AND log_date = ?",
            (goal_id, day.isoformat()),
        ).fetchone()
        new_value = value if (row is None or mode == "set") else row["value"] + value
        conn.execute(
            """INSERT INTO wellness_goal_logs (goal_id, user_id, log_date, value, note, created_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(goal_id, log_date) DO UPDATE SET value = excluded.value,
                   note = COALESCE(NULLIF(excluded.note, ''), note)""",
            (goal_id, user_id, day.isoformat(), new_value, (note or "")[:200],
             now_local().strftime(DATETIME_FMT)),
        )
        conn.commit()
        values = _day_values(conn, goal, today - timedelta(days=120), today)
        return {
            "message": "Progress logged.",
            "log_date": day.isoformat(),
            "day_total": round(new_value, 2),
            "analytics": analyse_goal(goal, values, today),
        }
    finally:
        conn.close()


def archive_goal(user_id, goal_id):
    user_id = uid(user_id)
    conn = get_connection()
    try:
        goal = _owned_goal(conn, user_id, goal_id)
        conn.execute("UPDATE wellness_goals SET active = 0 WHERE id = ?", (goal_id,))
        conn.commit()
        return {"message": f"Goal '{goal['title']}' archived."}
    finally:
        conn.close()


def goal_history(user_id, goal_id, days=30):
    """Per-day values for charts."""
    user_id = uid(user_id)
    days = int(clamp(days, 1, 365))
    today = today_local()
    start = today - timedelta(days=days - 1)
    conn = get_connection()
    try:
        goal = _owned_goal(conn, user_id, goal_id)
        values = _day_values(conn, goal, start, today)
    finally:
        conn.close()
    return {
        "goal_id": goal_id, "title": goal["title"], "unit": goal["unit"],
        "target_value": goal["target_value"], "period": goal["period"],
        "points": [
            {"date": (start + timedelta(days=i)).isoformat(),
             "value": round(values.get((start + timedelta(days=i)).isoformat(), 0.0), 2)}
            for i in range(days)
        ],
    }
