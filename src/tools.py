import re

from langchain_core.tools import tool

from src.chatbot import _find_medication
from src.database import add_medication, delete_medication, get_metrics, log_dose, add_metric
from src.scheduler import format_time_12h, get_schedule_status

VALID_METRICS = {
    "blood_pressure": "mmHg",
    "blood_sugar": "mg/dL",
    "weight": "kg",
    "temperature": "°C",
    "heart_rate": "bpm",
}


@tool
def add_medicine(name: str, dosage: str, time_24h: str) -> str:
    """Add a daily medicine reminder.
    name: medicine name, e.g. Metformin.
    dosage: e.g. 500mg (use empty string if unknown).
    time_24h: time in 24-hour HH:MM format, e.g. 09:00 or 21:30."""
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", time_24h.strip()):
        return "Error: time must be in HH:MM 24-hour format. Ask the user for the time."
    if not name.strip():
        return "Error: medicine name is missing. Ask the user."
    add_medication(name.strip().title(), dosage.strip(), time_24h.strip())
    return f"Added {name.title()} {dosage} daily at {format_time_12h(time_24h.strip())}."


@tool
def mark_dose_taken(name: str) -> str:
    """Mark a medicine as taken today. name: the medicine name."""
    med = _find_medication(name)
    if not med:
        return f"Error: no medicine named '{name}' found. Tell the user to add it first."
    log_dose(med["id"])
    return f"Logged: {med['name']} taken."


@tool
def remove_medicine(name: str) -> str:
    """Remove a medicine from the reminder list. name: the medicine name."""
    med = _find_medication(name)
    if not med:
        return f"Error: no medicine named '{name}' found."
    delete_medication(med["id"])
    return f"Removed {med['name']}."


@tool
def save_reading(metric_type: str, value: str) -> str:
    """Save a health reading.
    metric_type must be one of: blood_pressure, blood_sugar, weight, temperature, heart_rate.
    value: for blood_pressure use '120/80'; for others just the number, e.g. '140' or '98.6'.
    Blood sugar in mg/dL, weight in kg, temperature in Celsius (or Fahrenheit if above 45), heart rate in bpm."""
    metric_type = metric_type.strip().lower()
    if metric_type not in VALID_METRICS:
        return f"Error: metric_type must be one of {list(VALID_METRICS)}."
    unit = VALID_METRICS[metric_type]
    value = value.strip()

    if metric_type == "blood_pressure":
        m = re.fullmatch(r"(\d{2,3})\s*/\s*(\d{2,3})", value)
        if not m:
            return "Error: blood pressure must look like 120/80."
        sys_, dia = int(m.group(1)), int(m.group(2))
        if not (60 <= sys_ <= 260 and 30 <= dia <= 160) or sys_ <= dia:
            return "Error: this blood pressure looks impossible. Ask the user to check it."
        value = f"{sys_}/{dia}"
    else:
        try:
            number = float(value)
        except ValueError:
            return "Error: value must be a number."
        limits = {
            "blood_sugar": (20, 600),
            "weight": (2, 400),
            "temperature": (30, 113),
            "heart_rate": (20, 250),
        }
        low, high = limits[metric_type]
        if not low <= number <= high:
            return f"Error: {metric_type} value looks impossible. Ask the user to check it."
        if metric_type == "temperature" and number > 45:
            unit = "°F"

    add_metric(metric_type, value, unit)
    return f"Saved {metric_type}: {value} {unit}."


@tool
def show_readings(metric_type: str = "") -> str:
    """Show recent health readings (latest 6).
    metric_type: blood_pressure, blood_sugar, weight, temperature or heart_rate. Leave empty for all."""
    rows = get_metrics(metric_type.strip().lower() or None)[:6]
    if not rows:
        return "No readings saved yet."
    return "\n".join(
        f"{r['metric_type']}: {r['value']} {r['unit']} ({r['recorded_at'][:16]})" for r in rows
    )


@tool
def show_schedule() -> str:
    """Show today's medicines with status (taken, due, missed or upcoming)."""
    schedule = get_schedule_status()
    if not schedule:
        return "No medicines added yet."
    return "\n".join(
        f"{m['name']} {m['dosage'] or ''} at {format_time_12h(m['time'])}: {m['status']}"
        for m in schedule
    )


TOOLS = [add_medicine, mark_dose_taken, remove_medicine, save_reading, show_readings, show_schedule]