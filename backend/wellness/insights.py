#backend/wellness/insights.py
"""Rule-based health insights, recommendations and a wellness score.

Everything here is transparent and deterministic: each insight is produced by
a simple rule over the user's own data.  Nothing is a diagnosis.
"""

from statistics import mean

from backend.wellness import adherence, goals
from backend.wellness.metrics import assess_reading, fitness_daily, metric_series

DISCLAIMER = (
    "These insights are generated from the data you recorded and are for "
    "awareness only. They are not a diagnosis or medical advice. Talk to a "
    "qualified healthcare professional about any health concern."
)
SEVERITY_ORDER = {"attention": 0, "info": 1, "positive": 2}
PRETTY = {
    "heart_rate": "Heart rate", "spo2": "Oxygen saturation", "blood_sugar": "Blood sugar",
    "temperature": "Body temperature", "blood_pressure_systolic": "Systolic blood pressure",
    "blood_pressure_diastolic": "Diastolic blood pressure",
}


def _item(category, severity, title, message, recommendation=None):
    return {"category": category, "severity": severity, "title": title,
            "message": message, "recommendation": recommendation}


# ---------- individual rule groups ----------

def _medication_insights(adh):
    items = []
    meds = adh["by_medication"]
    overall = adh["overall"]
    if not meds:
        return [_item("medication", "info", "No medications tracked",
                      "Add your medications to start monitoring adherence.",
                      "Use the Medications tab to add a medicine and its daily time.")]
    pct = overall["adherence_percent"]
    if pct is None:
        items.append(_item("medication", "info", "Adherence will appear soon",
                           "There are no completed dose days yet to measure.",
                           "Log each dose as you take it so trends can be calculated."))
    elif pct >= 90:
        items.append(_item("medication", "positive", "Excellent adherence",
                           f"You took {overall['taken']} of {overall['expected']} expected doses "
                           f"({pct}%) over the last {adh['period_days']} days.",
                           "Keep your routine going."))
    elif pct >= 75:
        items.append(_item("medication", "info", "Good adherence, room to improve",
                           f"Adherence is {pct}% over the last {adh['period_days']} days.",
                           "Tie each dose to a daily habit such as meals or brushing teeth."))
    else:
        items.append(_item("medication", "attention", "Doses are being missed often",
                           f"Adherence is {pct}% ({overall['missed']} missed doses in "
                           f"{adh['period_days']} days).",
                           "Set phone alarms, try a weekly pill organizer, and speak to your "
                           "doctor or pharmacist if side effects or cost are the reason."))
    for med in meds:
        if med["adherence_percent"] is not None and med["expected"] >= 3 \
                and med["adherence_percent"] < 60:
            items.append(_item("medication", "attention", f"{med['name']} is often missed",
                               f"Only {med['taken']} of {med['expected']} doses logged "
                               f"({med['adherence_percent']}%).",
                               f"Consider moving {med['name']} to a time that fits your day better."))
        if med["current_streak"] >= 7:
            items.append(_item("medication", "positive", f"{med['current_streak']}-day streak",
                               f"{med['name']} has been taken {med['current_streak']} days in a row.",
                               None))
    overdue = [m for m in adh["today"] if m["status"] == "missed"]
    due = [m for m in adh["today"] if m["status"] == "due"]
    if overdue:
        names = ", ".join(m["name"] for m in overdue)
        items.append(_item("medication", "attention", "Dose overdue today",
                           f"Not logged yet today: {names}.",
                           "If you already took it, log it now. If not, follow the guidance on "
                           "your medicine leaflet or ask your pharmacist about a late dose."))
    elif due:
        items.append(_item("medication", "info", "Dose due now",
                           "Due now: " + ", ".join(m["name"] for m in due) + ".", None))
    return items


def _time_of_day_insight(user_id, days=30):
    buckets = adherence.missed_by_time_of_day(user_id, days)
    total = sum(buckets.values())
    if total >= 3:
        part, count = max(buckets.items(), key=lambda kv: kv[1])
        if count / total >= 0.6:
            return [_item("medication", "info", f"Most missed doses are in the {part}",
                          f"{count} of {total} missed doses were scheduled in the {part}.",
                          f"Try an extra reminder around your {part} doses.")]
    return []


def _fitness_insights(days_rows):
    items = []
    last7, prev7 = days_rows[-7:], days_rows[-14:-7]
    logged = [d for d in last7 if d["has_data"]]
    if not logged:
        return [_item("fitness", "info", "No recent activity logged",
                      "No fitness activity was recorded in the last 7 days.",
                      "Log a walk or workout to unlock activity insights.")]
    minutes = sum(d["duration_minutes"] for d in last7)
    if minutes >= 150:
        items.append(_item("fitness", "positive", "Activity target reached",
                           f"You logged {minutes} active minutes this week, meeting the common "
                           "150-minute weekly guideline.", None))
    else:
        items.append(_item("fitness", "info", "Active minutes below the usual guideline",
                           f"You logged {minutes} active minutes in the last 7 days.",
                           "Adults are commonly advised to aim for about 150 minutes of moderate "
                           "activity a week; short brisk walks add up."))
    step_days = [d["steps"] for d in last7 if d["steps"]]
    if step_days:
        avg = round(mean(step_days))
        prev = [d["steps"] for d in prev7 if d["steps"]]
        text = f"Average of {avg:,} steps on the days you logged steps."
        if prev:
            change = (avg - mean(prev)) / mean(prev) * 100 if mean(prev) else 0
            if change >= 10:
                items.append(_item("fitness", "positive", "Steps are trending up",
                                   text + f" That is {round(change)}% higher than the week before.", None))
            elif change <= -10:
                items.append(_item("fitness", "info", "Steps dropped from last week",
                                   text + f" That is {abs(round(change))}% lower than the week before.",
                                   "Try a short walk after meals to bring it back up."))
    sleep = [d["sleep_hours"] for d in last7 if d["sleep_hours"]]
    if len(sleep) >= 3:
        avg_sleep = round(mean(sleep), 1)
        if avg_sleep < 7:
            items.append(_item("sleep", "info", "Sleep is on the short side",
                               f"You averaged {avg_sleep} hours of sleep on logged nights.",
                               "Most adults do best with 7-9 hours. A fixed bedtime and less screen "
                               "time before bed can help."))
        elif avg_sleep > 9:
            items.append(_item("sleep", "info", "Long sleep durations",
                               f"You averaged {avg_sleep} hours of sleep on logged nights.",
                               "If you often feel unrested despite long sleep, mention it to your doctor."))
        else:
            items.append(_item("sleep", "positive", "Healthy sleep range",
                               f"You averaged {avg_sleep} hours of sleep on logged nights.", None))
    if len(logged) < 3:
        items.append(_item("fitness", "info", "Be more consistent",
                           f"Activity was logged on {len(logged)} of the last 7 days.",
                           "Aim for movement on most days of the week."))
    return items


def _metric_insights(user_id):
    items = []
    series = metric_series(user_id, days=60)
    for name, points in series.items():
        latest = points[-1]
        level = assess_reading(name, latest["value"])
        label = PRETTY.get(name, name.replace("_", " ").capitalize())
        if level:
            items.append(_item(
                "readings", level, f"{label} outside the typical range",
                f"Latest {label.lower()} reading is {latest['value']:g} {latest['unit']}".strip()
                + f" (recorded {latest['date']}).",
                "A single reading is not a diagnosis. Recheck it at rest, and talk to a clinician "
                "if it stays out of range or you feel unwell. Seek urgent care for severe symptoms."))
    weight = series.get("weight", [])
    if len(weight) >= 2:
        latest = weight[-1]
        first = weight[0]
        change = latest["value"] - first["value"]
        unit = (latest["unit"] or "kg").lower()
        threshold = 4.4 if unit.startswith("lb") else 2.0
        if abs(change) >= threshold:
            direction = "gained" if change > 0 else "lost"
            items.append(_item("readings", "info", "Noticeable weight change",
                               f"Your recorded weight {direction} {abs(change):.1f} {latest['unit'] or 'kg'} "
                               f"between {first['date']} and {latest['date']}.",
                               "If this was unintentional, check in with your doctor."))
    return items


def _goal_insights(goal_rows):
    items = []
    for g in goal_rows:
        a = g["analytics"]
        if a["status"] == "completed":
            items.append(_item("goals", "positive", f"Goal reached: {g['title']}",
                               f"You hit your {g['period']} target of {g['target_value']:g} {g['unit']}.",
                               None))
        if a["streak"] >= 3:
            items.append(_item("goals", "positive", f"{a['streak']}-{'day' if g['period'] == 'daily' else 'week'} streak",
                               f"'{g['title']}' has been met {a['streak']} periods in a row.", None))
        if a["success_rate_percent"] is not None and a["success_rate_percent"] < 50 \
                and a["trend"] != "not_enough_data":
            items.append(_item("goals", "info", f"'{g['title']}' is hard to hit",
                               f"You met this goal in {a['success_rate_percent']}% of recent periods.",
                               "Consider lowering the target slightly so it becomes a habit, then "
                               "raise it again."))
    if not goal_rows:
        items.append(_item("goals", "info", "No wellness goals yet",
                           "Goals make progress visible.",
                           "Create a goal such as daily water, steps or sleep."))
    return items


# ---------- wellness score ----------

def _activity_score(days_rows):
    last7 = days_rows[-7:]
    parts = []
    logged_days = [d for d in last7 if d["has_data"]]
    if not logged_days:
        return None
    parts.append(min(100.0, sum(d["duration_minutes"] for d in last7) / 150 * 100))
    steps = [d["steps"] for d in last7 if d["steps"]]
    if steps:
        parts.append(min(100.0, mean(steps) / 7000 * 100))
    sleep = [d["sleep_hours"] for d in last7 if d["sleep_hours"]]
    if sleep:
        avg = mean(sleep)
        parts.append(100.0 if 7 <= avg <= 9 else max(0.0, 100 - abs(avg - 8) * 25))
    return mean(parts)


def wellness_score(adh, goal_rows, days_rows):
    components, weights = {}, {"medication": 0.4, "goals": 0.3, "activity": 0.3}
    if adh["overall"]["adherence_percent"] is not None:
        components["medication"] = adh["overall"]["adherence_percent"]
    if goal_rows:
        components["goals"] = mean(g["analytics"]["progress_percent"] for g in goal_rows)
    act = _activity_score(days_rows)
    if act is not None:
        components["activity"] = act
    if not components:
        return {"score": None, "label": "no_data", "components": {}}
    total_w = sum(weights[k] for k in components)
    score = round(sum(components[k] * weights[k] for k in components) / total_w)
    label = ("great" if score >= 85 else "good" if score >= 70
             else "fair" if score >= 50 else "needs_attention")
    return {"score": score, "label": label,
            "components": {k: round(v) for k, v in components.items()}}


# ---------- public ----------

def generate_wellness_insights(user_id, days=30):
    adh = adherence.get_adherence(user_id, days)
    goal_rows = goals.list_goals(user_id)
    fit_rows = fitness_daily(user_id, 14)

    items = []
    items += _medication_insights(adh)
    items += _time_of_day_insight(user_id, days)
    items += _fitness_insights(fit_rows)
    items += _metric_insights(user_id)
    items += _goal_insights(goal_rows)
    items.sort(key=lambda i: SEVERITY_ORDER[i["severity"]])

    return {
        "wellness_score": wellness_score(adh, goal_rows, fit_rows),
        "insights": items,
        "counts": {s: sum(1 for i in items if i["severity"] == s) for s in SEVERITY_ORDER},
        "disclaimer": DISCLAIMER,
    }
