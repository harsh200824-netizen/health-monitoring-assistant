"""Simple real-time alerts.

Called right after a reading is saved. Each rule checks one value and
saves an alert if it is outside a safe range. The same alert is never
saved twice, because of the dedupe_key column.
"""

from backend.wellness.common import get_connection, now_local_text
from backend.wellness.metrics import normalize_metric, parse_reading

# (low_limit, high_limit, severity, message)
# A value below low_limit or above high_limit creates an alert.
RULES = {
    "blood_sugar": (70, 250, "attention",
                    "Blood sugar is outside the safe range. Contact your doctor if it stays high or low."),
    "spo2": (92, None, "urgent",
             "Oxygen level is low. If you feel unwell, seek medical help now."),
    "heart_rate": (50, 120, "attention",
                   "Heart rate is outside the expected range. Recheck at rest and contact your doctor if it stays this way."),
    "blood_pressure_systolic": (90, 160, "attention",
                                "Systolic blood pressure is outside the expected range. Contact your doctor."),
    "temperature": (35.0, 38.5, "attention",
                    "Body temperature is outside the expected range. Contact your doctor if it persists."),
}


def check_reading(user_id, metric_type, value):
    """Check one saved reading and save any alerts. Returns the new alerts."""
    created = []
    for name, number in parse_reading(metric_type, value):
        rule = RULES.get(normalize_metric(name))
        if not rule:
            continue
        low, high, severity, message = rule
        if (low is not None and number < low) or (high is not None and number > high):
            created.append(_save_alert(user_id, name, severity, f"{message} (reading: {number:g})", number))
    return created


def _save_alert(user_id, name, severity, message, number):
    # One alert per rule per hour, so repeated readings don't spam the list.
    hour_key = now_local_text()[:13]  # YYYY-MM-DD HH
    dedupe_key = f"{name}:{hour_key}"
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO alerts
               (user_id, rule, severity, message, status, dedupe_key, created_at)
               VALUES (?, ?, ?, ?, 'open', ?, ?)""",
            (int(user_id), name, severity, message, dedupe_key, now_local_text()),
        )
        conn.commit()
    finally:
        conn.close()
    return {"rule": name, "severity": severity, "message": message}


def list_alerts(user_id, open_only=True):
    conn = get_connection()
    try:
        query = "SELECT * FROM alerts WHERE CAST(user_id AS TEXT) = ?"
        if open_only:
            query += " AND status = 'open'"
        query += " ORDER BY created_at DESC, id DESC LIMIT 50"
        return [dict(r) for r in conn.execute(query, (str(user_id),)).fetchall()]
    finally:
        conn.close()


def acknowledge_alert(user_id, alert_id):
    conn = get_connection()
    try:
        cur = conn.execute(
            """UPDATE alerts SET status = 'acknowledged', acknowledged_at = ?
               WHERE id = ? AND CAST(user_id AS TEXT) = ?""",
            (now_local_text(), alert_id, str(user_id)),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()