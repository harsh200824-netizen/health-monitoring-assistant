"""Simple ML risk estimate (logistic regression).

This is a student project model. It is trained on a small SYNTHETIC dataset
generated in this file, not on real patient data. Its output is only an
estimate for awareness and is never a diagnosis.
"""

import json

import numpy as np
from sklearn.linear_model import LogisticRegression

from backend.wellness.common import get_connection, now_local_text, uid
from backend.wellness.metrics import metric_series
from backend.wellness import adherence
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MODEL_VERSION = "logreg-synthetic-v1"
FEATURES = ["adherence_percent", "avg_blood_sugar", "avg_systolic_bp", "avg_sleep_hours", "avg_steps"]
RISK_LABELS = ["lower", "moderate", "higher"]


def _build_training_data(seed=42):
    """Make a small, reproducible, clearly synthetic dataset.

    Rule used to make labels: more risk when adherence is low and
    blood sugar / blood pressure are high, and when sleep and steps are low.
    """
    rng = np.random.default_rng(seed)
    n = 300
    adh = rng.uniform(30, 100, n)
    sugar = rng.uniform(70, 220, n)
    sbp = rng.uniform(100, 170, n)
    sleep = rng.uniform(4, 9.5, n)
    steps = rng.uniform(1000, 12000, n)

    score = (
        (100 - adh) / 100 * 2.0
        + (sugar - 100) / 100 * 1.5
        + (sbp - 120) / 40 * 1.5
        + (7 - sleep) / 3 * 0.8
        + (7000 - steps) / 7000 * 0.8
    )
    labels = np.where(score > 1.6, 2, np.where(score > 0.8, 1, 0))
    X = np.column_stack([adh, sugar, sbp, sleep, steps])
    return X, labels


_model = None


def _get_model():
    global _model
    if _model is None:
        X, y = _build_training_data()
        _model = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000),
        )
        _model.fit(X, y)
    return _model

def _user_features(user_id, days=30):
    """Build the five input values from the user's own stored data."""
    adh = adherence.get_adherence(user_id, days)
    series = metric_series(user_id, days)
    from backend.wellness.metrics import fitness_daily
    fit = fitness_daily(user_id, 7)

    def avg(name, default):
        points = series.get(name, [])
        return round(sum(p["value"] for p in points) / len(points), 1) if points else default

    logged_sleep = [d["sleep_hours"] for d in fit if d["sleep_hours"]]
    logged_steps = [d["steps"] for d in fit if d["steps"]]

    return {
        "adherence_percent": adh["overall"]["adherence_percent"] if adh["overall"]["expected"] else 100.0,
        "avg_blood_sugar": avg("blood_sugar", 100.0),
        "avg_systolic_bp": avg("blood_pressure_systolic", 120.0),
        "avg_sleep_hours": round(sum(logged_sleep) / len(logged_sleep), 1) if logged_sleep else 7.5,
        "avg_steps": round(sum(logged_steps) / len(logged_steps)) if logged_steps else 7000,
    }


def predict_risk_from_features(features):
    """Score a feature dict without saving anything."""
    model = _get_model()
    x = np.array([[
        features["adherence_percent"],
        features["avg_blood_sugar"],
        features["avg_systolic_bp"],
        features["avg_sleep_hours"],
        features["avg_steps"],
    ]])
    probs = model.predict_proba(x)[0]
    label_index = int(np.argmax(probs))
    return {
        "risk_score": round(float(sum(p * (i / 2) for i, p in enumerate(probs))), 3),
        "risk_label": RISK_LABELS[label_index],
        "probabilities": {RISK_LABELS[i]: round(float(p), 3) for i, p in enumerate(probs)},
    }

def predict_risk(user_id):
    """Estimate risk for one user and save the result."""
    user_id = uid(user_id)
    features = _user_features(user_id)
    x = np.array([[
        features["adherence_percent"],
        features["avg_blood_sugar"],
        features["avg_systolic_bp"],
        features["avg_sleep_hours"],
        features["avg_steps"],
    ]])

    model = _get_model()
    probs = model.predict_proba(x)[0]
    label_index = int(np.argmax(probs))
    # Expected risk level on a 0-1 scale: 0 = lower, 0.5 = moderate, 1 = higher
    risk_score = float(sum(p * (i / 2) for i, p in enumerate(probs)))

    result = {
        "risk_score": round(risk_score, 3),
        "risk_label": RISK_LABELS[label_index],
        "probabilities": {RISK_LABELS[i]: round(float(p), 3) for i, p in enumerate(probs)},
        "features": features,
        "model_version": MODEL_VERSION,
        "disclaimer": "Estimate from a student model trained on synthetic data. Not a diagnosis.",
    }

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO ml_predictions
               (user_id, risk_score, risk_label, features_json, model_version, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, result["risk_score"], result["risk_label"],
             json.dumps(features), MODEL_VERSION, now_local_text()),
        )
        conn.commit()
    finally:
        conn.close()
    return result