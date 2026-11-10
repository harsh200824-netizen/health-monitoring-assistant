"""Create demo data so the Week 5-6 Wellness tracker can be tried immediately.

    python scripts/seed_wellness_demo.py

Creates two accounts (password: DemoPass123):
  demo_patient    - 3 medications with 3 weeks of dose history, activity,
                    readings and goals
  demo_caregiver  - already linked to demo_patient (all sharing on)

Safe to re-run: it stops if the demo users already exist.
"""

import random
import sys
from datetime import timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pwdlib import PasswordHash  # noqa: E402

from backend.wellness.schema import init_wellness_db  # noqa: E402
from src.database import get_connection, init_db, migrate_user_id, now_local  # noqa: E402

PASSWORD = "DemoPass123"
FMT = "%Y-%m-%d %H:%M:%S"


def main():
    init_db()
    migrate_user_id()
    init_wellness_db()
    random.seed(7)
    hasher = PasswordHash.recommended()
    conn = get_connection()
    try:
        if conn.execute("SELECT 1 FROM users WHERE username IN ('demo_patient','demo_caregiver')").fetchone():
            print("Demo users already exist - nothing to do.")
            return
        ids = {}
        for name in ("demo_patient", "demo_caregiver"):
            ids[name] = conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'patient')",
                (name, hasher.hash(PASSWORD)),
            ).lastrowid
        patient, caregiver = ids["demo_patient"], ids["demo_caregiver"]
        now = now_local()
        today = now.date()
        created = (now - timedelta(days=21)).astimezone(timezone.utc).strftime(FMT)

        meds = [("Metformin", "500 mg", "08:00", 0.9), ("Vitamin D", "1000 IU", "13:00", 0.75),
                ("Atorvastatin", "10 mg", "21:00", 0.6)]
        for name, dosage, time_text, reliability in meds:
            med_id = conn.execute(
                "INSERT INTO medications (name, dosage, time, user_id, created_at) VALUES (?,?,?,?,?)",
                (name, dosage, time_text, patient, created)).lastrowid
            for back in range(1, 22):
                if random.random() < reliability:
                    day = today - timedelta(days=back)
                    conn.execute("INSERT INTO dose_log (medication_id, taken_at) VALUES (?, ?)",
                                 (med_id, f"{day} {time_text[:2]}:{random.randint(0, 25):02d}:00"))

        for back in range(0, 14):
            day = today - timedelta(days=back)
            if random.random() < 0.85:
                conn.execute(
                    """INSERT INTO fitness_activities (user_id, activity_type, duration_minutes,
                       steps, distance_km, calories_burned, sleep_hours, notes, recorded_at)
                       VALUES (?, 'walking', ?, ?, ?, ?, ?, '', ?)""",
                    (patient, random.randint(15, 50), random.randint(3500, 11000),
                     round(random.uniform(2, 8), 1), random.randint(120, 380),
                     round(random.uniform(5.5, 8.5), 1), f"{day} 07:30:00"))
        for back in range(0, 10):
            day = today - timedelta(days=back)
            conn.execute("INSERT INTO health_metrics (metric_type, value, unit, recorded_at, user_id) VALUES ('heart_rate', ?, 'bpm', ?, ?)",
                         (str(random.randint(64, 92)), f"{day} 08:00:00", patient))
            conn.execute("INSERT INTO health_metrics (metric_type, value, unit, recorded_at, user_id) VALUES ('weight', ?, 'kg', ?, ?)",
                         (str(round(74.5 - back * 0.05, 1)), f"{day} 08:05:00", patient))
        conn.execute("INSERT INTO health_metrics (metric_type, value, unit, recorded_at, user_id) VALUES ('blood_pressure', '138/88', 'mmHg', ?, ?)",
                     (f"{today} 08:10:00", patient))

        goals = [("Drink water", 8, "glasses", "daily", "at_least", "manual"),
                 ("Daily steps", 8000, "steps", "daily", "at_least", "steps"),
                 ("Weekly active minutes", 150, "minutes", "weekly", "at_least", "active_minutes"),
                 ("Screen time", 3, "hours", "daily", "at_most", "manual")]
        for title, target, unit, period, direction, source in goals:
            goal_id = conn.execute(
                """INSERT INTO wellness_goals (user_id, title, target_value, unit, period, direction,
                   source, start_date, created_at) VALUES (?,?,?,?,?,?,?,?,?)""",
                (patient, title, target, unit, period, direction, source,
                 (today - timedelta(days=13)).isoformat(), now.strftime(FMT))).lastrowid
            if source == "manual":
                for back in range(0, 14):
                    value = random.randint(4, 10) if title == "Drink water" else round(random.uniform(1.5, 4.5), 1)
                    conn.execute("INSERT INTO wellness_goal_logs (goal_id, user_id, log_date, value, created_at) VALUES (?,?,?,?,?)",
                                 (goal_id, patient, (today - timedelta(days=back)).isoformat(), value, now.strftime(FMT)))

        conn.execute(
            """INSERT INTO family_links (caregiver_id, member_id, relationship, status,
               share_medications, share_fitness, share_metrics, created_at, responded_at)
               VALUES (?, ?, 'parent', 'accepted', 1, 1, 1, ?, ?)""",
            (caregiver, patient, now.strftime(FMT), now.strftime(FMT)))
        conn.commit()
    finally:
        conn.close()
    print(f"Done. Log in as demo_patient or demo_caregiver (password: {PASSWORD}).")


if __name__ == "__main__":
    main()
