"""Wellness report generation: JSON, CSV and a printable HTML page."""

import csv
import html
import io
from statistics import mean

from backend.wellness import adherence, goals
from backend.wellness.common import clamp, now_local
from backend.wellness.insights import DISCLAIMER, generate_wellness_insights
from backend.wellness.metrics import fitness_daily, metric_series


def _fitness_summary(rows):
    logged = [r for r in rows if r["has_data"]]

    def total(key):
        return round(sum(r[key] for r in rows), 1)

    def avg(key):
        vals = [r[key] for r in rows if r[key]]
        return round(mean(vals), 1) if vals else None

    return {
        "days_with_activity": len(logged),
        "total_steps": int(total("steps")),
        "total_active_minutes": int(total("duration_minutes")),
        "total_calories": int(total("calories_burned")),
        "total_distance_km": total("distance_km"),
        "average_steps_per_active_day": avg("steps"),
        "average_sleep_hours": avg("sleep_hours"),
    }


def _metrics_summary(series):
    out = []
    for name, points in series.items():
        values = [p["value"] for p in points]
        out.append({
            "metric": name, "readings": len(values), "latest": values[-1],
            "unit": points[-1]["unit"], "min": min(values), "max": max(values),
            "average": round(mean(values), 1),
            "change_since_first": round(values[-1] - values[0], 1),
            "latest_date": points[-1]["date"],
        })
    return out


def generate_wellness_report(user_id, days=30):
    days = int(clamp(days, 7, 180))
    adh = adherence.get_adherence(user_id, days)
    insight_data = generate_wellness_insights(user_id, min(days, 30))
    return {
        "report_title": "Medication & Wellness Report",
        "generated_at": now_local().isoformat(),
        "period": {"days": days, "start": adh["start_date"], "end": adh["end_date"]},
        "wellness_score": insight_data["wellness_score"],
        "adherence": {"overall": adh["overall"], "by_medication": adh["by_medication"]},
        "fitness": _fitness_summary(fitness_daily(user_id, days)),
        "readings": _metrics_summary(metric_series(user_id, days)),
        "goals": [
            {"title": g["title"], "period": g["period"], "direction": g["direction"],
             "target": g["target_value"], "unit": g["unit"], **{
                 k: g["analytics"][k] for k in (
                     "current_value", "progress_percent", "status", "streak",
                     "best_streak", "success_rate_percent", "trend")}}
            for g in goals.list_goals(user_id)
        ],
        "insights": insight_data["insights"],
        "disclaimer": DISCLAIMER,
    }


def report_to_csv(report):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["section", "item", "field", "value"])
    w.writerow(["report", "period", "start", report["period"]["start"]])
    w.writerow(["report", "period", "end", report["period"]["end"]])
    w.writerow(["report", "wellness_score", "score", report["wellness_score"]["score"]])
    for k, v in report["adherence"]["overall"].items():
        w.writerow(["adherence", "overall", k, v])
    for med in report["adherence"]["by_medication"]:
        for k in ("expected", "taken", "missed", "adherence_percent",
                  "current_streak", "longest_streak"):
            w.writerow(["adherence", med["name"], k, med[k]])
    for k, v in report["fitness"].items():
        w.writerow(["fitness", "summary", k, v])
    for r in report["readings"]:
        for k in ("readings", "latest", "min", "max", "average", "change_since_first"):
            w.writerow(["readings", r["metric"], k, r[k]])
    for g in report["goals"]:
        for k in ("target", "current_value", "progress_percent", "status",
                  "streak", "success_rate_percent", "trend"):
            w.writerow(["goals", g["title"], k, g[k]])
    for i in report["insights"]:
        w.writerow(["insights", i["severity"], i["title"], i["message"]])
    w.writerow(["note", "disclaimer", "", report["disclaimer"]])
    return out.getvalue()


def report_to_html(report):
    e = html.escape

    def rows(pairs):
        return "".join(f"<tr><th>{e(str(k))}</th><td>{e(str(v))}</td></tr>" for k, v in pairs)

    meds = "".join(
        f"<tr><td>{e(m['name'])}</td><td>{m['taken']}/{m['expected']}</td>"
        f"<td>{e(str(m['adherence_percent']))}%</td><td>{m['current_streak']}</td></tr>"
        for m in report["adherence"]["by_medication"]) or "<tr><td colspan=4>No medications</td></tr>"
    goal_rows = "".join(
        f"<tr><td>{e(g['title'])}</td><td>{g['current_value']} / {g['target']} {e(g['unit'])}</td>"
        f"<td>{g['progress_percent']}%</td><td>{e(g['status'].replace('_', ' '))}</td></tr>"
        for g in report["goals"]) or "<tr><td colspan=4>No goals</td></tr>"
    read_rows = "".join(
        f"<tr><td>{e(r['metric'].replace('_', ' '))}</td><td>{r['latest']:g} {e(r['unit'] or '')}</td>"
        f"<td>{r['min']:g}-{r['max']:g}</td><td>{r['readings']}</td></tr>"
        for r in report["readings"]) or "<tr><td colspan=4>No readings</td></tr>"
    insight_rows = "".join(
        f"<li><strong>{e(i['title'])}</strong> &ndash; {e(i['message'])}"
        + (f"<br><em>{e(i['recommendation'])}</em>" if i["recommendation"] else "") + "</li>"
        for i in report["insights"])
    score = report["wellness_score"]["score"]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{e(report['report_title'])}</title>
<style>body{{font-family:Arial,sans-serif;max-width:820px;margin:30px auto;color:#1c2733;padding:0 16px}}
h1{{margin-bottom:4px}}h2{{border-bottom:2px solid #37adad;padding-bottom:4px;margin-top:28px}}
table{{border-collapse:collapse;width:100%;margin:8px 0}}th,td{{border:1px solid #cfd8e0;padding:6px 8px;text-align:left;font-size:13px}}
th{{background:#eef3f6}}li{{margin:6px 0;font-size:13px}}.note{{font-size:11px;color:#555;margin-top:28px}}</style></head><body>
<h1>{e(report['report_title'])}</h1>
<div>Period: {e(report['period']['start'])} to {e(report['period']['end'])} &middot; Generated {e(report['generated_at'][:16].replace('T', ' '))}</div>
<h2>Wellness score: {e(str(score if score is not None else 'n/a'))}</h2>
<h2>Medication adherence</h2>
<table>{rows((k.replace('_', ' '), v) for k, v in report['adherence']['overall'].items())}</table>
<table><tr><th>Medication</th><th>Doses</th><th>Adherence</th><th>Streak</th></tr>{meds}</table>
<h2>Fitness &amp; sleep</h2><table>{rows((k.replace('_', ' '), v) for k, v in report['fitness'].items())}</table>
<h2>Health readings</h2><table><tr><th>Metric</th><th>Latest</th><th>Range</th><th>Readings</th></tr>{read_rows}</table>
<h2>Goals</h2><table><tr><th>Goal</th><th>Current</th><th>Progress</th><th>Status</th></tr>{goal_rows}</table>
<h2>Insights</h2><ul>{insight_rows}</ul>
<p class="note">{e(report['disclaimer'])}</p></body></html>"""
