from src.parser import parse_message
from src.database import (
    add_medication,
    get_medications,
    delete_medication,
    log_dose,
    add_metric,
    get_metrics,
)
from src.scheduler import get_schedule_status, format_time_12h

METRIC_LABELS = {
    "blood_pressure": "Blood pressure",
    "blood_sugar": "Blood sugar",
    "weight": "Weight",
    "temperature": "Temperature",
    "heart_rate": "Heart rate",
}

STATUS_ICONS = {"taken": "✅", "due": "⏰", "missed": "⚠️", "upcoming": "🕒"}

HELP_TEXT = """I can help you track medicines and health readings. Try:

- **Take Metformin 500mg at 9am**: add a daily reminder
- **I took Metformin**: mark a dose as taken
- **My BP is 120/80**: save blood pressure
- **sugar 140**, **weight 70**, **pulse 72**, **temperature 98.6**: save a reading
- **show my medications**: today's schedule
- **show my weight**: reading history
- **delete Metformin**: remove a medication

*This app is for tracking and reminders only. It is not medical advice.*"""


def _find_medication(name):
    name = (name or "").strip().lower()
    if not name:
        return None
    for med in get_medications():
        med_name = med["name"].lower()
        if name in med_name or med_name in name:
            return med
    return None


def handle_message(text):
    result = parse_message(text)
    intent = result["intent"]

    if intent == "help":
        return HELP_TEXT

    if intent == "add_medication":
        if not result.get("time"):
            return "I need a time for the reminder. Try: **Take Metformin 500mg at 9am**"
        dosage = result.get("dosage") or ""
        add_medication(result["name"], dosage, result["time"])
        label = f"{result['name']} {dosage}".strip()
        return (
            f"✅ Added **{label}**. I'll remind you daily at "
            f"**{format_time_12h(result['time'])}**."
        )

    if intent == "log_dose":
        med = _find_medication(result["name"])
        if not med:
            return f"I couldn't find **{result['name']}** in your medications. Type **show my medications** to see the list."
        log_dose(med["id"])
        return f"✅ Logged: you took **{med['name']}**. Good job!"

    if intent == "log_metric":
        add_metric(result["metric_type"], result["value"], result["unit"])
        label = METRIC_LABELS.get(result["metric_type"], result["metric_type"])
        return f"📝 Saved your **{label}**: {result['value']} {result['unit']}"

    if intent == "list_medications":
        schedule = get_schedule_status()
        if not schedule:
            return "You have no medications yet. Try: **Take Metformin 500mg at 9am**"
        lines = ["**Today's medications:**"]
        for med in schedule:
            icon = STATUS_ICONS[med["status"]]
            label = f"{med['name']} {med['dosage'] or ''}".strip()
            lines.append(
                f"- {icon} {label} at {format_time_12h(med['time'])} ({med['status']})"
            )
        return "\n".join(lines)

    if intent == "show_metrics":
        metric_type = result.get("metric_type")
        rows = get_metrics(metric_type)[:6]
        if not rows:
            return "No readings saved yet. Try: **My BP is 120/80**"
        lines = ["**Recent readings:**"]
        for r in rows:
            label = METRIC_LABELS.get(r["metric_type"], r["metric_type"])
            lines.append(f"- {label}: {r['value']} {r['unit']} ({r['recorded_at'][:16]})")
        return "\n".join(lines)

    if intent == "delete_medication":
        med = _find_medication(result["name"])
        if not med:
            return f"I couldn't find **{result['name']}** in your medications."
        delete_medication(med["id"])
        return f"🗑️ Removed **{med['name']}** from your medications."

    return "Sorry, I didn't understand that. Type **help** to see what I can do."