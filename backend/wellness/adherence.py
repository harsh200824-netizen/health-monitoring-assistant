"""Medication adherence monitoring.

Model: every active medication has one scheduled time per day.  A day counts
as *taken* when a dose is logged on that date, and as *missed* when the date
has passed (or today's dose is more than ``GRACE_MINUTES`` late) with no dose.
A dose that is not yet due, or is inside the grace window, is *pending* and is
not counted for or against adherence.
"""

import re

from backend.wellness.common import (
    WellnessError, clamp, daterange, get_connection, hhmm_to_minutes, now_local,
    percent, timedelta, today_local, uid, utc_text_to_local_dt,
)
from src.database import add_medication, delete_medication, log_dose

GRACE_MINUTES = 60
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


# ---------- helpers ----------

def _user_medications(conn, user_id, active_only=True):
    query = "SELECT * FROM medications WHERE CAST(user_id AS TEXT) = ?"
    if active_only:
        query += " AND active = 1"
    query += " ORDER BY time, id"
    return [dict(r) for r in conn.execute(query, (str(user_id),)).fetchall()]


def _taken_dates(conn, med_ids, start, end):
    """{medication_id: set(date strings)} for doses logged in [start, end]."""
    result = {mid: set() for mid in med_ids}
    if not med_ids:
        return result
    marks = ",".join("?" for _ in med_ids)
    rows = conn.execute(
        f"""
        SELECT medication_id, date(taken_at) AS d
        FROM dose_log
        WHERE medication_id IN ({marks}) AND date(taken_at) BETWEEN ? AND ?
        """,
        [*med_ids, start.isoformat(), end.isoformat()],
    ).fetchall()
    for row in rows:
        result[row["medication_id"]].add(row["d"])
    return result


def _day_state(created, sched_min, day, today, now_min, taken):
    """Return 'taken', 'missed' or None (pending / not expected)."""
    if day.isoformat() in taken:
        return "taken"
    if day < created.date():
        return None
    # Added later in the day than its scheduled time: not expected that day.
    if day == created.date() and sched_min < created.hour * 60 + created.minute:
        return None
    if day < today:
        return "missed"
    if now_min - sched_min > GRACE_MINUTES:
        return "missed"
    return None


def _today_status(sched_min, now_min, taken_today):
    late = now_min - sched_min
    if taken_today:
        return "taken", 0
    if late < 0:
        return "upcoming", 0
    if late <= GRACE_MINUTES:
        return "due", late
    return "missed", late


def _streaks(states):
    """``states`` is a chronological list of 'taken'/'missed'/None."""
    longest = run = 0
    for state in states:
        if state == "taken":
            run += 1
            longest = max(longest, run)
        elif state == "missed":
            run = 0
    current = 0
    for state in reversed(states):
        if state is None:
            if current == 0:
                continue  # pending today: look at the days before it
            break
        if state == "taken":
            current += 1
        else:
            break
    return current, longest


def grade(adherence_percent):
    if adherence_percent is None:
        return "no_data"
    if adherence_percent >= 90:
        return "excellent"
    if adherence_percent >= 75:
        return "good"
    if adherence_percent >= 50:
        return "fair"
    return "needs_attention"


# ---------- public API ----------

def get_adherence(user_id, days=30):
    user_id = uid(user_id)
    days = int(clamp(days, 1, 365))
    today = today_local()
    now = now_local()
    now_min = now.hour * 60 + now.minute
    start = today - timedelta(days=days - 1)
    window = daterange(start, today)

    conn = get_connection()
    try:
        meds = _user_medications(conn, user_id)
        ids = [m["id"] for m in meds]
        taken = _taken_dates(conn, ids, start, today)
        last_rows = {}
        if ids:
            marks = ",".join("?" for _ in ids)
            for r in conn.execute(
                f"""SELECT medication_id, MAX(taken_at) AS last_taken
                    FROM dose_log WHERE medication_id IN ({marks})
                    GROUP BY medication_id""",
                ids,
            ).fetchall():
                last_rows[r["medication_id"]] = r["last_taken"]
    finally:
        conn.close()

    daily = {d.isoformat(): {"expected": 0, "taken": 0} for d in window}
    by_medication, today_list = [], []
    total_expected = total_taken = 0

    for med in meds:
        sched = hhmm_to_minutes(med["time"])
        created = utc_text_to_local_dt(med.get("created_at"))
        med_taken = taken[med["id"]]
        states = []
        for day in window:
            state = _day_state(created, sched, day, today, now_min, med_taken)
            states.append(state)
            if state:
                daily[day.isoformat()]["expected"] += 1
                if state == "taken":
                    daily[day.isoformat()]["taken"] += 1

        exp = sum(1 for s in states if s)
        tak = sum(1 for s in states if s == "taken")
        total_expected += exp
        total_taken += tak
        current, longest = _streaks(states)
        status, late = _today_status(sched, now_min, today.isoformat() in med_taken)

        by_medication.append({
            "id": med["id"], "name": med["name"], "dosage": med["dosage"],
            "time": med["time"], "expected": exp, "taken": tak,
            "missed": exp - tak, "adherence_percent": percent(tak, exp),
            "grade": grade(percent(tak, exp)),
            "current_streak": current, "longest_streak": longest,
            "last_taken": last_rows.get(med["id"]),
        })
        today_list.append({
            "id": med["id"], "name": med["name"], "dosage": med["dosage"],
            "time": med["time"], "status": status, "minutes_late": late,
        })

    overall = percent(total_taken, total_expected)
    return {
        "period_days": days,
        "start_date": start.isoformat(),
        "end_date": today.isoformat(),
        "overall": {
            "expected": total_expected, "taken": total_taken,
            "missed": total_expected - total_taken,
            "adherence_percent": overall, "grade": grade(overall),
        },
        "by_medication": by_medication,
        "daily": [
            {"date": d, "expected": v["expected"], "taken": v["taken"],
             "adherence_percent": percent(v["taken"], v["expected"])}
            for d, v in daily.items()
        ],
        "today": today_list,
    }


def missed_by_time_of_day(user_id, days=30):
    """Count missed doses by part of day, used for pattern insights."""
    data = get_adherence(user_id, days)
    buckets = {"morning": 0, "afternoon": 0, "evening": 0, "night": 0}
    for med in data["by_medication"]:
        hour = int(med["time"].split(":")[0])
        key = ("morning" if 5 <= hour < 12 else "afternoon" if 12 <= hour < 17
               else "evening" if 17 <= hour < 21 else "night")
        buckets[key] += med["missed"]
    return buckets


def get_today_schedule(user_id):
    return get_adherence(user_id, 1)["today"]


# ---------- medication management (new, authenticated endpoints) ----------

def add_user_medication(user_id, name, dosage, time_text):
    user_id = uid(user_id)
    name = (name or "").strip()
    if not name:
        raise WellnessError("Medication name cannot be empty.", 422)
    if not TIME_RE.match(time_text or ""):
        raise WellnessError("Time must be 24-hour HH:MM, e.g. 09:00.", 422)
    med_id = add_medication(name, (dosage or "").strip(), time_text, user_id)
    return {"id": med_id, "name": name, "dosage": dosage or "", "time": time_text}


def _owned_medication(conn, user_id, med_id):
    row = conn.execute(
        "SELECT * FROM medications WHERE id = ? AND CAST(user_id AS TEXT) = ? AND active = 1",
        (med_id, str(user_id)),
    ).fetchone()
    if row is None:
        raise WellnessError("Medication not found.", 404)
    return dict(row)


def log_user_dose(user_id, med_id):
    """Log today's dose.  Idempotent per day so double taps do not skew stats."""
    user_id = uid(user_id)
    conn = get_connection()
    try:
        med = _owned_medication(conn, user_id, med_id)
        already = conn.execute(
            "SELECT 1 FROM dose_log WHERE medication_id = ? AND date(taken_at) = ?",
            (med_id, today_local().isoformat()),
        ).fetchone()
    finally:
        conn.close()
    if already:
        return {"message": f"{med['name']} is already logged for today.", "already_logged": True}
    log_dose(med_id)
    return {"message": f"Logged today's dose of {med['name']}.", "already_logged": False}


def deactivate_user_medication(user_id, med_id):
    user_id = uid(user_id)
    conn = get_connection()
    try:
        med = _owned_medication(conn, user_id, med_id)
    finally:
        conn.close()
    delete_medication(med_id, user_id)
    return {"message": f"{med['name']} was removed from your active medications."}
