import os
import re

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from src.database import (
    add_medication,
    add_metric,
    delete_medication,
    get_medications,
    get_metrics,
    log_dose,
)
from src.scheduler import format_time_12h, get_alerts, get_schedule_status

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_PROMPT = """You are a health monitoring assistant for tracking medications and health readings.
Use your tools to do what the user asks. You may call several tools for one message.
Never guess: if a medicine name or time is missing, ask the user.
Keep replies short and friendly. You are NOT a doctor: never diagnose or change doses.
If a reading is flagged abnormal, tell the user to contact their doctor."""


def agent_available():
    return bool(os.getenv("GOOGLE_API_KEY"))


def _find_medication(name):
    name = (name or "").strip().lower()
    for med in get_medications():
        med_name = med["name"].lower()
        if name and (name in med_name or med_name in name):
            return med
    return None


def _flag_reading(metric_type, value):
    """Simple range check. Informational only, not medical advice."""
    try:
        if metric_type == "blood_pressure":
            sys_, dia = [int(x) for x in value.split("/")]
            if sys_ >= 180 or dia >= 120:
                return "VERY HIGH, contact a doctor now"
            if sys_ >= 140 or dia >= 90:
                return "HIGH"
            if sys_ < 90 or dia < 60:
                return "LOW"
        elif metric_type == "blood_sugar":
            v = float(value)
            if v > 250:
                return "VERY HIGH"
            if v > 180:
                return "HIGH"
            if v < 70:
                return "LOW"
        elif metric_type == "heart_rate":
            v = float(value)
            if v > 100:
                return "HIGH"
            if v < 50:
                return "LOW"
        elif metric_type == "temperature":
            v = float(value)
            fever = v > 100.4 if v > 45 else v > 38
            if fever:
                return "FEVER"
    except (ValueError, TypeError):
        return None
    return None


@tool
def add_medication_tool(name: str, dosage: str, time_24h: str) -> str:
    """Add a daily medication reminder. time_24h must be HH:MM in 24-hour format, e.g. '21:30'. dosage is like '500mg' (use '' if unknown)."""
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", time_24h):
        return "Error: time must be HH:MM in 24-hour format."
    add_medication(name.strip().title(), dosage.strip(), time_24h)
    return f"Added {name} {dosage} daily at {format_time_12h(time_24h)}."


@tool
def log_dose_tool(name: str) -> str:
    """Record that the user took a medicine just now."""
    med = _find_medication(name)
    if not med:
        return f"No medication named {name} found."
    log_dose(med["id"])
    return f"Logged dose of {med['name']}."


@tool
def log_health_metric(metric_type: str, value: str, unit: str = "") -> str:
    """Save a health reading. metric_type must be one of: blood_pressure, blood_sugar, weight, temperature, heart_rate. For blood_pressure value looks like '120/80'. Units: mmHg, mg/dL, kg, C or F, bpm."""
    add_metric(metric_type, value, unit)
    flag = _flag_reading(metric_type, value)
    if flag:
        return f"Saved {metric_type} {value} {unit}. WARNING: reading looks {flag}."
    return f"Saved {metric_type} {value} {unit}. Looks within the usual range."


@tool
def get_today_schedule() -> str:
    """Get all medications with today's status (taken, due, missed or upcoming)."""
    schedule = get_schedule_status()
    if not schedule:
        return "No medications saved."
    return "\n".join(
        f"{m['name']} {m['dosage'] or ''} at {format_time_12h(m['time'])}: {m['status']}"
        for m in schedule
    )


@tool
def get_current_alerts() -> str:
    """Get medicines that are due now or missed."""
    alerts = get_alerts()
    if not alerts:
        return "No alerts. Nothing is due or missed right now."
    return "\n".join(a["message"] for a in alerts)


@tool
def get_recent_readings(metric_type: str = "") -> str:
    """Get the latest saved health readings. Leave metric_type empty for all types."""
    rows = get_metrics(metric_type or None)[:8]
    if not rows:
        return "No readings saved."
    return "\n".join(
        f"{r['metric_type']}: {r['value']} {r['unit']} ({r['recorded_at'][:16]})"
        for r in rows
    )


@tool
def remove_medication(name: str) -> str:
    """Stop and remove a medication."""
    med = _find_medication(name)
    if not med:
        return f"No medication named {name} found."
    delete_medication(med["id"])
    return f"Removed {med['name']}."


TOOLS = [
    add_medication_tool,
    log_dose_tool,
    log_health_metric,
    get_today_schedule,
    get_current_alerts,
    get_recent_readings,
    remove_medication,
]
TOOL_MAP = {t.name: t for t in TOOLS}


def _text(content):
    if isinstance(content, str):
        return content
    return "".join(
        p.get("text", "") if isinstance(p, dict) else str(p) for p in content
    )


def run_agent(user_text, history=None):
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0).bind_tools(TOOLS)

    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for m in (history or [])[-6:]:
        cls = HumanMessage if m["role"] == "user" else AIMessage
        messages.append(cls(content=m["content"]))
    messages.append(HumanMessage(content=user_text))

    for _ in range(6):
        ai = llm.invoke(messages)
        messages.append(ai)
        if not ai.tool_calls:
            return _text(ai.content)
        for call in ai.tool_calls:
            try:
                result = TOOL_MAP[call["name"]].invoke(call["args"])
            except Exception as e:
                result = f"Error: {e}"
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    return "Sorry, I couldn't finish that. Please try again."