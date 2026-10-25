from backend.database.database import (
    get_health_summary,
    get_dose_log,
    get_metrics
)


def health_summary_tool():
    """Get a summary of the patient's stored health data."""
    return get_health_summary()


def dose_history_tool():
    """Get the patient's medication dose history."""
    return get_dose_log()


def health_metrics_tool():
    """Get the patient's recorded health metrics."""
    return get_metrics()