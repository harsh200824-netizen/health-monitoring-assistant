"""Chart-ready datasets for the wellness dashboard."""

from backend.wellness import adherence, goals
from backend.wellness.common import clamp
from backend.wellness.metrics import fitness_daily, metric_series


def get_visualization(user_id, days=14):
    days = int(clamp(days, 7, 90))
    adh = adherence.get_adherence(user_id, days)
    series = metric_series(user_id, days=max(days, 30))
    goal_rows = goals.list_goals(user_id)

    return {
        "period_days": days,
        "adherence_daily": adh["daily"],
        "adherence_by_medication": [
            {"name": m["name"], "percent": m["adherence_percent"],
             "taken": m["taken"], "expected": m["expected"]}
            for m in adh["by_medication"]
        ],
        "fitness_daily": fitness_daily(user_id, days),
        "metric_series": {name: points[-30:] for name, points in series.items()},
        "goal_overview": [
            {"id": g["id"], "title": g["title"], "unit": g["unit"],
             "percent": g["analytics"]["progress_percent"],
             "status": g["analytics"]["status"],
             "streak": g["analytics"]["streak"]}
            for g in goal_rows
        ],
    }
