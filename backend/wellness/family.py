"""Family health monitoring and caregiver notifications.

Privacy model: monitoring is consent based.  A caregiver *invites* another
registered user by username.  Nothing is visible until that person *accepts*,
and the member chooses what to share (medications, fitness, readings).  Either
side can end the link at any time.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

from backend.wellness import adherence
from backend.wellness.common import (
    DATETIME_FMT, WellnessError, clamp, get_connection, now_local, today_local, uid,
)
from backend.wellness.metrics import fitness_daily, metric_series

RELATIONSHIPS = {"parent", "child", "spouse", "sibling", "grandparent", "friend", "other"}
LOW_ADHERENCE_THRESHOLD = 70.0


def _now_text():
    return now_local().strftime(DATETIME_FMT)


def _flag(value):
    return 1 if value else 0


# ---------- notifications ----------

def notify(conn, user_id, kind, severity, message, dedupe_key, member_id=None):
    """Insert a notification once per (user, dedupe_key).  Returns True if new."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO caregiver_notifications
           (user_id, member_id, kind, severity, message, dedupe_key, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, member_id, kind, severity, message, dedupe_key, _now_text()),
    )
    return cur.rowcount > 0


def _member_alerts(member_id, name):
    """Current alerts about one member (medication-related)."""
    alerts = []
    today = today_local().isoformat()
    week = adherence.get_adherence(member_id, 7)
    for med in week["today"]:
        if med["status"] == "missed":
            alerts.append({
                "key": f"missed:{member_id}:{med['id']}:{today}",
                "kind": "missed_dose", "severity": "attention",
                "message": f"{name} has not logged {med['name']} "
                           f"(scheduled {med['time']}).",
            })
    overall = week["overall"]
    if overall["expected"] >= 3 and overall["adherence_percent"] is not None \
            and overall["adherence_percent"] < LOW_ADHERENCE_THRESHOLD:
        iso = today_local().isocalendar()
        alerts.append({
            "key": f"lowadh:{member_id}:{iso[0]}-{iso[1]}",
            "kind": "low_adherence", "severity": "attention",
            "message": f"{name}'s medication adherence is {overall['adherence_percent']}% "
                       "over the last 7 days.",
        })
    return alerts, week


def scan_notifications(user_id):
    """Create caregiver alerts for every accepted link that shares medications."""
    user_id = uid(user_id)
    created = 0
    conn = get_connection()
    try:
        links = conn.execute(
            """SELECT l.*, u.username AS member_name FROM family_links l
               JOIN users u ON u.id = l.member_id
               WHERE l.caregiver_id = ? AND l.status = 'accepted'
                 AND l.share_medications = 1""",
            (user_id,),
        ).fetchall()
        for link in links:
            alerts, _ = _member_alerts(link["member_id"], link["member_name"])
            for a in alerts:
                if notify(conn, user_id, a["kind"], a["severity"], a["message"],
                          a["key"], member_id=link["member_id"]):
                    created += 1
        conn.commit()
    finally:
        conn.close()
    return created


def list_notifications(user_id, unread_only=False, limit=50):
    user_id = uid(user_id)
    limit = int(clamp(limit, 1, 200))
    conn = get_connection()
    try:
        query = """SELECT n.id, n.kind, n.severity, n.message, n.created_at, n.read_at,
                          n.member_id, u.username AS member_name
                   FROM caregiver_notifications n
                   LEFT JOIN users u ON u.id = n.member_id
                   WHERE n.user_id = ?"""
        if unread_only:
            query += " AND n.read_at IS NULL"
        query += " ORDER BY n.id DESC LIMIT ?"
        rows = [dict(r) for r in conn.execute(query, (user_id, limit)).fetchall()]
        unread = conn.execute(
            "SELECT COUNT(*) FROM caregiver_notifications WHERE user_id = ? AND read_at IS NULL",
            (user_id,),
        ).fetchone()[0]
        return {"unread_count": unread, "notifications": rows}
    finally:
        conn.close()


def mark_notifications_read(user_id, ids=None):
    """Mark specific notifications (or all, when ``ids`` is empty) as read."""
    user_id = uid(user_id)
    conn = get_connection()
    try:
        if ids:
            marks = ",".join("?" for _ in ids)
            conn.execute(
                f"""UPDATE caregiver_notifications SET read_at = ?
                    WHERE user_id = ? AND read_at IS NULL AND id IN ({marks})""",
                [_now_text(), user_id, *[int(i) for i in ids]],
            )
        else:
            conn.execute(
                "UPDATE caregiver_notifications SET read_at = ? WHERE user_id = ? AND read_at IS NULL",
                (_now_text(), user_id),
            )
        conn.commit()
        return {"message": "Notifications updated."}
    finally:
        conn.close()


# ---------- patient-generated invitation codes ----------


def create_patient_invite_code(patient_id, lifetime_hours=24):
    """Create a one-time code that a caregiver can redeem to request access."""
    patient_id = uid(patient_id)
    code = secrets.token_urlsafe(9)
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    created = now_local()
    expires = created + timedelta(hours=lifetime_hours)
    conn = get_connection()
    try:
        patient = conn.execute("SELECT id FROM users WHERE id = ?", (patient_id,)).fetchone()
        if patient is None:
            raise WellnessError("Patient account was not found.", 404)
        conn.execute(
            """INSERT INTO family_invite_codes
               (patient_id, code_hash, expires_at, created_at)
               VALUES (?, ?, ?, ?)""",
            (patient_id, code_hash, expires.strftime(DATETIME_FMT),
             created.strftime(DATETIME_FMT)),
        )
        conn.commit()
        return {
            "invite_code": code,
            "expires_at": expires.strftime(DATETIME_FMT),
            "message": "Share this one-time code with your caregiver. It expires in 24 hours.",
        }
    finally:
        conn.close()


def request_access_with_code(caregiver_id, invite_code, relationship="other"):
    """Redeem a patient code; creates a pending link but grants no data access."""
    caregiver_id = uid(caregiver_id)
    invite_code = (invite_code or "").strip()
    relationship = (relationship or "other").strip().lower()
    if not invite_code or len(invite_code) > 100:
        raise WellnessError("Enter a valid invitation code.", 422)
    if relationship not in RELATIONSHIPS:
        raise WellnessError(f"Relationship must be one of: {', '.join(sorted(RELATIONSHIPS))}.", 422)

    code_hash = hashlib.sha256(invite_code.encode("utf-8")).hexdigest()
    conn = get_connection()
    try:
        # Serialize redemption so two caregivers cannot redeem the same code concurrently.
        conn.execute("BEGIN IMMEDIATE")
        invite = conn.execute(
            """SELECT id, patient_id, expires_at, used_at
               FROM family_invite_codes WHERE code_hash = ?""",
            (code_hash,),
        ).fetchone()
        if invite is None:
            raise WellnessError("Invalid invitation code.", 404)
        if invite["used_at"]:
            raise WellnessError("This invitation code has already been used.", 409)
        expires = datetime.strptime(invite["expires_at"], DATETIME_FMT)
        if expires < now_local().replace(tzinfo=None):
            raise WellnessError("This invitation code has expired.", 410)
        patient_id = int(invite["patient_id"])
        if patient_id == caregiver_id:
            raise WellnessError("You cannot request access to your own account.", 422)

        existing = conn.execute(
            "SELECT id, status FROM family_links WHERE caregiver_id = ? AND member_id = ?",
            (caregiver_id, patient_id),
        ).fetchone()
        if existing and existing["status"] in ("pending", "accepted"):
            raise WellnessError("A request or active connection already exists for this patient.", 409)

        now_text = _now_text()
        if existing:
            link_id = existing["id"]
            conn.execute(
                """UPDATE family_links SET status = 'pending', relationship = ?,
                   created_at = ?, responded_at = NULL,
                   share_medications = 0, share_fitness = 0, share_metrics = 0
                   WHERE id = ?""",
                (relationship, now_text, link_id),
            )
        else:
            link_id = conn.execute(
                """INSERT INTO family_links
                   (caregiver_id, member_id, relationship, status,
                    share_medications, share_fitness, share_metrics, created_at)
                   VALUES (?, ?, ?, 'pending', 0, 0, 0, ?)""",
                (caregiver_id, patient_id, relationship, now_text),
            ).lastrowid

        conn.execute(
            "UPDATE family_invite_codes SET used_at = ? WHERE id = ? AND used_at IS NULL",
            (now_text, invite["id"]),
        )
        notify(conn, patient_id, "family_access_request", "info",
               f"{_username(conn, caregiver_id)} requested caregiver access. Review the request in the Family tab.",
               f"family-request:{link_id}:{now_text}", member_id=caregiver_id)
        conn.commit()
        return {"id": link_id, "status": "pending",
                "message": "Access request sent. The patient must approve it before any health data is shared."}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------- links ----------

def _username(conn, user_id):
    row = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    return row["username"] if row else f"user {user_id}"


def invite_family_member(caregiver_id, username, relationship="other"):
    caregiver_id = uid(caregiver_id)
    username = (username or "").strip()
    relationship = (relationship or "other").strip().lower()
    if relationship not in RELATIONSHIPS:
        raise WellnessError(f"Relationship must be one of: {', '.join(sorted(RELATIONSHIPS))}.", 422)
    if not username:
        raise WellnessError("Enter the username of the person you want to monitor.", 422)

    conn = get_connection()
    try:
        member = conn.execute("SELECT id, username FROM users WHERE username = ?",
                              (username,)).fetchone()
        if member is None:
            raise WellnessError("No user with that username was found.", 404)
        if member["id"] == caregiver_id:
            raise WellnessError("You cannot add yourself.", 422)

        existing = conn.execute(
            "SELECT * FROM family_links WHERE caregiver_id = ? AND member_id = ?",
            (caregiver_id, member["id"]),
        ).fetchone()
        if existing and existing["status"] == "accepted":
            raise WellnessError("This person already shares their health data with you.", 409)
        if existing and existing["status"] == "pending":
            raise WellnessError("An invitation is already waiting for their response.", 409)

        if existing:  # previously declined or revoked: re-open
            conn.execute(
                """UPDATE family_links SET status = 'pending', relationship = ?,
                       created_at = ?, responded_at = NULL WHERE id = ?""",
                (relationship, _now_text(), existing["id"]),
            )
            link_id = existing["id"]
        else:
            link_id = conn.execute(
                """INSERT INTO family_links (caregiver_id, member_id, relationship, created_at)
                   VALUES (?, ?, ?, ?)""",
                (caregiver_id, member["id"], relationship, _now_text()),
            ).lastrowid

        notify(conn, member["id"], "family_invite", "info",
               f"{_username(conn, caregiver_id)} asked to monitor your health as a caregiver. "
               "Review the request in the Family tab.",
               f"invite:{link_id}:{_now_text()}", member_id=caregiver_id)
        conn.commit()
        return {"id": link_id, "message": f"Invitation sent to {member['username']}."}
    finally:
        conn.close()


def _link_for_member(conn, member_id, link_id):
    row = conn.execute("SELECT * FROM family_links WHERE id = ? AND member_id = ?",
                       (link_id, member_id)).fetchone()
    if row is None:
        raise WellnessError("Invitation not found.", 404)
    return dict(row)


def respond_to_invite(member_id, link_id, accept, share_medications=True,
                      share_fitness=True, share_metrics=False):
    member_id = uid(member_id)
    conn = get_connection()
    try:
        link = _link_for_member(conn, member_id, link_id)
        if link["status"] != "pending":
            raise WellnessError("This invitation has already been answered.", 409)
        status = "accepted" if accept else "declined"
        conn.execute(
            """UPDATE family_links SET status = ?, responded_at = ?,
                   share_medications = ?, share_fitness = ?, share_metrics = ? WHERE id = ?""",
            (status, _now_text(), _flag(share_medications), _flag(share_fitness),
             _flag(share_metrics), link_id),
        )
        who = _username(conn, member_id)
        notify(conn, link["caregiver_id"], "family_response", "info",
               f"{who} {'accepted' if accept else 'declined'} your caregiver request.",
               f"response:{link_id}:{status}:{_now_text()}", member_id=member_id)
        conn.commit()
        return {"message": "Invitation accepted." if accept else "Invitation declined."}
    finally:
        conn.close()


def update_sharing(member_id, link_id, share_medications, share_fitness, share_metrics):
    member_id = uid(member_id)
    conn = get_connection()
    try:
        link = _link_for_member(conn, member_id, link_id)
        if link["status"] != "accepted":
            raise WellnessError("Sharing can only be changed on an active link.", 409)
        conn.execute(
            """UPDATE family_links SET share_medications = ?, share_fitness = ?,
                   share_metrics = ? WHERE id = ?""",
            (_flag(share_medications), _flag(share_fitness), _flag(share_metrics), link_id),
        )
        conn.commit()
        return {"message": "Sharing preferences updated."}
    finally:
        conn.close()


def revoke_link(user_id, link_id):
    """Either the caregiver or the member can end a link."""
    user_id = uid(user_id)
    conn = get_connection()
    try:
        link = conn.execute(
            "SELECT * FROM family_links WHERE id = ? AND (caregiver_id = ? OR member_id = ?)",
            (link_id, user_id, user_id),
        ).fetchone()
        if link is None:
            raise WellnessError("Link not found.", 404)
        if link["status"] in ("revoked", "declined"):
            raise WellnessError("This link is already closed.", 409)
        conn.execute("UPDATE family_links SET status = 'revoked', responded_at = ? WHERE id = ?",
                     (_now_text(), link_id))
        other = link["member_id"] if user_id == link["caregiver_id"] else link["caregiver_id"]
        notify(conn, other, "family_revoked", "info",
               f"{_username(conn, user_id)} ended the caregiver connection.",
               f"revoked:{link_id}:{_now_text()}", member_id=user_id)
        conn.commit()
        return {"message": "Connection ended."}
    finally:
        conn.close()


def list_family(user_id):
    user_id = uid(user_id)
    conn = get_connection()
    try:
        monitoring = [dict(r) for r in conn.execute(
            """SELECT l.id, l.member_id, u.username AS member_name, l.relationship, l.status,
                      l.share_medications, l.share_fitness, l.share_metrics, l.created_at
               FROM family_links l JOIN users u ON u.id = l.member_id
               WHERE l.caregiver_id = ? AND l.status IN ('pending', 'accepted')
               ORDER BY l.id DESC""", (user_id,)).fetchall()]
        caregivers = [dict(r) for r in conn.execute(
            """SELECT l.id, l.caregiver_id, u.username AS caregiver_name, l.relationship,
                      l.status, l.share_medications, l.share_fitness, l.share_metrics,
                      l.created_at
               FROM family_links l JOIN users u ON u.id = l.caregiver_id
               WHERE l.member_id = ? AND l.status IN ('pending', 'accepted')
               ORDER BY l.id DESC""", (user_id,)).fetchall()]
    finally:
        conn.close()
    return {
        "monitoring": monitoring,
        "caregivers": [c for c in caregivers if c["status"] == "accepted"],
        "pending_requests": [c for c in caregivers if c["status"] == "pending"],
    }


# ---------- member data (caregiver view) ----------

def _accepted_link(conn, caregiver_id, member_id):
    row = conn.execute(
        """SELECT l.*, u.username AS member_name FROM family_links l
           JOIN users u ON u.id = l.member_id
           WHERE l.caregiver_id = ? AND l.member_id = ? AND l.status = 'accepted'""",
        (caregiver_id, member_id),
    ).fetchone()
    if row is None:
        raise WellnessError("You do not have access to this person's data.", 403)
    return dict(row)


def member_overview(caregiver_id, member_id):
    caregiver_id, member_id = uid(caregiver_id), uid(member_id)
    conn = get_connection()
    try:
        link = _accepted_link(conn, caregiver_id, member_id)
    finally:
        conn.close()

    result = {
        "member": {"id": member_id, "username": link["member_name"],
                   "relationship": link["relationship"]},
        "shared": {"medications": bool(link["share_medications"]),
                   "fitness": bool(link["share_fitness"]),
                   "readings": bool(link["share_metrics"])},
        "alerts": [], "medications": None, "fitness": None, "readings": None,
    }
    if link["share_medications"]:
        alerts, week = _member_alerts(member_id, link["member_name"])
        month = adherence.get_adherence(member_id, 30)
        result["alerts"] = alerts
        result["medications"] = {
            "today": week["today"],
            "adherence_7d": week["overall"]["adherence_percent"],
            "adherence_30d": month["overall"]["adherence_percent"],
            "grade_30d": month["overall"]["grade"],
            "by_medication": month["by_medication"],
            "daily": week["daily"],
        }
    if link["share_fitness"]:
        rows = fitness_daily(member_id, 7)
        result["fitness"] = {
            "daily": rows,
            "total_steps": sum(r["steps"] for r in rows),
            "active_minutes": sum(r["duration_minutes"] for r in rows),
            "average_sleep_hours": round(
                sum(r["sleep_hours"] for r in rows if r["sleep_hours"])
                / max(1, sum(1 for r in rows if r["sleep_hours"])), 1),
        }
    if link["share_metrics"]:
        result["readings"] = [
            {"metric": name, "latest": pts[-1]["value"], "unit": pts[-1]["unit"],
             "date": pts[-1]["date"]}
            for name, pts in metric_series(member_id, 60).items()
        ]
    return result


def family_dashboard(caregiver_id):
    """Summary card per accepted member plus unread notification count."""
    caregiver_id = uid(caregiver_id)
    scan_notifications(caregiver_id)
    conn = get_connection()
    try:
        links = [dict(r) for r in conn.execute(
            """SELECT l.*, u.username AS member_name FROM family_links l
               JOIN users u ON u.id = l.member_id
               WHERE l.caregiver_id = ? AND l.status = 'accepted' ORDER BY u.username""",
            (caregiver_id,)).fetchall()]
    finally:
        conn.close()

    members = []
    for link in links:
        card = {"link_id": link["id"], "member_id": link["member_id"],
                "username": link["member_name"], "relationship": link["relationship"],
                "adherence_7d": None, "doses_today": None, "alerts": 0}
        if link["share_medications"]:
            alerts, week = _member_alerts(link["member_id"], link["member_name"])
            today = week["today"]
            card["adherence_7d"] = week["overall"]["adherence_percent"]
            card["doses_today"] = {
                "total": len(today),
                "taken": sum(1 for m in today if m["status"] == "taken"),
                "missed": sum(1 for m in today if m["status"] == "missed"),
            }
            card["alerts"] = len(alerts)
        members.append(card)
    return {"members": members,
            "unread_notifications": list_notifications(caregiver_id, True, 1)["unread_count"]}
