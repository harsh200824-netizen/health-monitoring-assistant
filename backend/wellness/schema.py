#backend/wellness/schema.py
"""Tables added in Week 5-6.  Existing tables are never altered."""

from backend.wellness.common import get_connection


def init_wellness_db():
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS wellness_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                target_value REAL NOT NULL,
                unit TEXT NOT NULL,
                period TEXT NOT NULL DEFAULT 'daily',        -- daily | weekly
                direction TEXT NOT NULL DEFAULT 'at_least',  -- at_least | at_most
                source TEXT NOT NULL DEFAULT 'manual',       -- manual | fitness metric
                start_date TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS wellness_goal_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                log_date TEXT NOT NULL,
                value REAL NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL,
                UNIQUE (goal_id, log_date),
                FOREIGN KEY (goal_id) REFERENCES wellness_goals (id)
            );

            CREATE TABLE IF NOT EXISTS family_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caregiver_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                relationship TEXT,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending|accepted|declined|revoked
                share_medications INTEGER NOT NULL DEFAULT 1,
                share_fitness INTEGER NOT NULL DEFAULT 1,
                share_metrics INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                responded_at TEXT,
                UNIQUE (caregiver_id, member_id)
            );

            CREATE TABLE IF NOT EXISTS family_invite_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                code_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_family_invites_patient
                ON family_invite_codes (patient_id, expires_at, used_at);

            CREATE TABLE IF NOT EXISTS caregiver_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,         -- the recipient
                member_id INTEGER,                -- who the alert is about
                kind TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'info',
                message TEXT NOT NULL,
                dedupe_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                read_at TEXT,
                UNIQUE (user_id, dedupe_key)
            );

            CREATE INDEX IF NOT EXISTS idx_goal_logs_goal_date
                ON wellness_goal_logs (goal_id, log_date);
            CREATE INDEX IF NOT EXISTS idx_notifications_user
                ON caregiver_notifications (user_id, read_at);
            """
        )
        conn.commit()
    finally:
        conn.close()
