from src.database import get_medications, get_doses_taken_today, now_local

DUE_WINDOW_MIN = 60  # after this many minutes late, a dose counts as "missed"


def _to_minutes(time_str):
    h, m = time_str.split(":")
    return int(h) * 60 + int(m)


def format_time_12h(time_str):
    """'21:30' -> '9:30 PM'"""
    h, m = time_str.split(":")
    h = int(h)
    suffix = "AM" if h < 12 else "PM"
    h = h % 12 or 12
    return f"{h}:{m} {suffix}"


def get_schedule_status():
    """Every active medication with today's status."""
    now = now_local()
    now_min = now.hour * 60 + now.minute
    taken_ids = get_doses_taken_today()

    schedule = []
    for med in get_medications():
        late = now_min - _to_minutes(med["time"])
        if med["id"] in taken_ids:
            status = "taken"
        elif late < 0:
            status = "upcoming"
        elif late <= DUE_WINDOW_MIN:
            status = "due"
        else:
            status = "missed"
        schedule.append({**med, "status": status, "minutes_late": max(late, 0)})
    return schedule


def get_alerts():
    """Alert messages for medicines that are due or missed."""
    alerts = []
    for med in get_schedule_status():
        label = f"{med['name']} {med['dosage'] or ''}".strip()
        when = format_time_12h(med["time"])
        if med["status"] == "due":
            alerts.append(
                {"level": "due", "message": f"⏰ Time to take {label} (scheduled {when})"}
            )
        elif med["status"] == "missed":
            alerts.append(
                {"level": "missed", "message": f"⚠️ Missed: {label} (scheduled {when})"}
            )
    return alerts