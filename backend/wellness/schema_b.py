"""Track B schema: health profile, alerts, ML predictions and indexes.

Everything here is additive. Existing tables are not changed.
Safe to run on every startup because every statement uses IF NOT EXISTS.
"""

from backend.wellness.common import get_connection

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS health_profiles (
    user_id INTEGER PRIMARY KEY,
    age INTEGER CHECK (age IS NULL OR (age >= 0 AND age <= 120)),
    sex TEXT CHECK (sex IS NULL OR sex IN ('female', 'male', 'other')),
    conditions TEXT NOT NULL DEFAULT '',     -- free text, comma separated
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    rule TEXT NOT NULL,                       -- e.g. 'spo2_low', 'missed_doses_3d'
    severity TEXT NOT NULL CHECK (severity IN ('info', 'attention', 'urgent')),
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged')),
    dedupe_key TEXT NOT NULL,                 -- stops the same alert firing every minute
    created_at TEXT NOT NULL,                 -- local time, YYYY-MM-DD HH:MM:SS
    acknowledged_at TEXT,
    UNIQUE (user_id, dedupe_key),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS ml_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    risk_score REAL NOT NULL CHECK (risk_score >= 0 AND risk_score <= 1),
    risk_label TEXT NOT NULL,                 -- 'lower' | 'moderate' | 'higher'
    features_json TEXT NOT NULL,              -- the inputs, so results can be explained
    model_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS idx_alerts_user_status
    ON alerts (user_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_predictions_user
    ON ml_predictions (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_metrics_user_time
    ON health_metrics (user_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_doses_medication_time
    ON dose_log (medication_id, taken_at);
CREATE INDEX IF NOT EXISTS idx_fitness_user_time
    ON fitness_activities (user_id, recorded_at);
"""


def init_schema_b():
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def now_text():
    """Local timestamp in the same format the rest of the app uses."""
    from src.database import now_local
    return now_local().strftime("%Y-%m-%d %H:%M:%S")