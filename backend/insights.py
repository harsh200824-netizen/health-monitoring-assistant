#backend/insights.py
from backend.database.database import (
    get_medications,
    get_dose_log,
    get_metrics
)


def generate_health_insights(user_id: str):
    """Generate insights from the logged-in user's health data."""

    medications = get_medications(
        user_id=user_id,
        active_only=True
    )

    dose_log = get_dose_log()
    metrics = get_metrics()

    insights = []

    # Medication insight
    if len(medications) == 0:
        insights.append(
            "No active medications are currently recorded."
        )
    else:
        insights.append(
            f"You currently have {len(medications)} "
            "active medication(s) recorded."
        )

    # Dose insight
    if len(dose_log) == 0:
        insights.append(
            "No medication doses have been recorded yet."
        )
    else:
        insights.append(
            f"There are {len(dose_log)} medication dose "
            "record(s) in your history."
        )

    # Health metric insight
    if len(metrics) == 0:
        insights.append(
            "No health measurements have been recorded yet."
        )
    else:
        latest_metric = metrics[0]

        insights.append(
            f"Your latest recorded health metric is "
            f"{latest_metric['metric_type']}: "
            f"{latest_metric['value']} "
            f"{latest_metric.get('unit', '')}."
        )

    return {
        "insights": insights,
        "medication_count": len(medications),
        "dose_count": len(dose_log),
        "metric_count": len(metrics)
    }
