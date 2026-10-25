from backend.database.database import (
    get_medications,
    get_dose_log,
    get_metrics
)


def get_health_analytics():
    """Calculate basic health analytics from stored data."""

    medications = get_medications(active_only=True)
    dose_log = get_dose_log()
    metrics = get_metrics()

    return {
        "active_medications": len(medications),
        "total_doses_recorded": len(dose_log),
        "total_health_metrics": len(metrics),
        "medications": medications,
        "recent_doses": dose_log[:5],
        "recent_metrics": metrics[:5]
    }