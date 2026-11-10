
from datetime import datetime

from backend.analytics import get_health_analytics
from backend.database.database import (
    get_health_summary,
    get_fitness_summary,
    get_health_goal_progress,
)


def generate_health_report(user_id):
    analytics = get_health_analytics(user_id=user_id)
    summary = get_health_summary()
    fitness = get_fitness_summary()
    goals = get_health_goal_progress()

    return {
        "report_title": "Smart Health Assistant Report",
        "generated_at": datetime.now().astimezone().isoformat(),
        "health_summary": summary,
        "analytics": analytics,
        "fitness_summary": fitness,
        "goal_progress": goals,
        "note": (
            "This report summarizes recorded data and is not a medical "
            "diagnosis. Consult a qualified healthcare professional "
            "for medical advice."
        ),
    }
