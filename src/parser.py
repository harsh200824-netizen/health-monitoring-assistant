import re

TIME_12H = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b")
TIME_24H = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
DOSAGE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mg|mcg|ml|iu|units?|tablets?|pills?|capsules?|drops?|g)\b"
)

# metric_type: (keyword regex, default unit)
METRICS = {
    "blood_sugar": (r"sugar|glucose", "mg/dL"),
    "weight": (r"weigh(?:t|ed)?", "kg"),
    "temperature": (r"temperature|temp|fever", "°C"),
    "heart_rate": (r"heart\s*rate|pulse", "bpm"),
}


def extract_time(text):
    """Return time as 'HH:MM' (24h) or None."""
    m = TIME_12H.search(text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        ampm = m.group(3)
        if not 1 <= hour <= 12 or minute > 59:
            return None
        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"
    m = TIME_24H.search(text)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return None


def extract_dosage(text):
    m = DOSAGE.search(text)
    return f"{m.group(1)}{m.group(2)}" if m else None


def clean_name(text):
    """Keep only the medicine name (cut at dosage, time, 'at', etc.)."""
    text = re.split(
        r"\s+(?:at|every|daily|each|today|now|just|already|for)\b|\s+\d", text.strip()
    )[0]
    return text.strip(" .,!?").title()


def extract_metric(t):
    """Find a health reading in the message. Returns dict or None."""
    # Blood pressure like 120/80
    m = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", t)
    if m:
        return {
            "metric_type": "blood_pressure",
            "value": f"{m.group(1)}/{m.group(2)}",
            "unit": "mmHg",
        }
    # Other metrics: keyword followed by a number
    for metric_type, (keywords, unit) in METRICS.items():
        m = re.search(rf"(?:{keywords})\D{{0,15}}?(\d+(?:\.\d+)?)", t)
        if m:
            value = float(m.group(1))
            if metric_type == "temperature" and value > 45:
                unit = "°F"
            return {"metric_type": metric_type, "value": m.group(1), "unit": unit}
    return None


def parse_message(text):
    """Turn a user message into {'intent': ..., ...fields}."""
    t = text.strip().lower()
    if not t:
        return {"intent": "unknown"}

    # 1. Help
    if re.search(r"\b(help|what can you do)\b", t):
        return {"intent": "help"}

    # 2. Delete a medication
    m = re.match(r"(?:delete|remove|stop)\s+(?:medication\s+|medicine\s+)?(.+)", t)
    if m:
        return {"intent": "delete_medication", "name": clean_name(m.group(1))}

    # 3. List medications
    if (
        re.search(r"\b(show|list|what|my|view)\b.*\b(medications?|medicines?|meds)\b", t)
        and extract_time(t) is None
    ):
        return {"intent": "list_medications"}

    # 4. Show saved health data
    if re.search(r"\b(show|view|history|list|see)\b", t):
        if re.search(r"\b(bp|blood pressure)\b", t):
            return {"intent": "show_metrics", "metric_type": "blood_pressure"}
        for metric_type, (keywords, _) in METRICS.items():
            if re.search(keywords, t):
                return {"intent": "show_metrics", "metric_type": metric_type}
        if re.search(r"\b(metrics?|readings?|health data|records?)\b", t):
            return {"intent": "show_metrics", "metric_type": None}

    # 5. Log a health reading ("my BP is 120/80", "weight 70")
    metric = extract_metric(t)
    if metric:
        return {"intent": "log_metric", **metric}

    # 6. Log a dose taken ("I took Metformin")
    m = re.search(r"\b(?:took|taken|had)\s+(?:my\s+|the\s+)?(.+)", t)
    if m:
        return {"intent": "log_dose", "name": clean_name(m.group(1))}

    # 7. Add a medication ("Take Metformin 500mg at 9am")
    if re.search(r"\b(take|taking|remind|add)\b", t):
        name_part = re.sub(
            r"^(?:please\s+)?"
            r"(?:remind me to\s+|remind me\s+|add medication\s+|add medicine\s+"
            r"|add\s+|i need to\s+|i have to\s+)?"
            r"(?:(?:take|taking)\s+)?",
            "",
            t,
        )
        name = clean_name(name_part)
        if name:
            return {
                "intent": "add_medication",
                "name": name,
                "dosage": extract_dosage(t),
                "time": extract_time(t),
            }

    return {"intent": "unknown"}