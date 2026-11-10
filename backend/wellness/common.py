"""Shared helpers for the wellness package."""

from datetime import date, datetime, timedelta, timezone

from src.database import TIMEZONE, get_connection, now_local

def now_local_text():
    """Local time as YYYY-MM-DD HH:MM:SS, the format used across the app."""
    return now_local().strftime(DATETIME_FMT)

DATE_FMT = "%Y-%m-%d"
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


class WellnessError(Exception):
    """Raised for invalid requests.  ``status`` maps to an HTTP status code."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def uid(user_id):
    """The JWT carries the user id as a string; the database uses integers."""
    try:
        return int(user_id)
    except (TypeError, ValueError):
        raise WellnessError("Invalid user id.", 401)


def today_local():
    return now_local().date()


def parse_date(value, field="date"):
    try:
        return datetime.strptime(str(value)[:10], DATE_FMT).date()
    except (TypeError, ValueError):
        raise WellnessError(f"Invalid {field}. Use YYYY-MM-DD.", 422)


def utc_text_to_local_dt(text):
    """``CURRENT_TIMESTAMP`` columns are stored in UTC; convert to local."""
    try:
        parsed = datetime.strptime(str(text)[:19], DATETIME_FMT)
    except (TypeError, ValueError):
        return now_local()
    return parsed.replace(tzinfo=timezone.utc).astimezone(TIMEZONE)


def clamp(value, low, high):
    return max(low, min(high, value))


def daterange(start, end):
    """Inclusive list of dates from ``start`` to ``end``."""
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def hhmm_to_minutes(text):
    hours, minutes = str(text).split(":")[:2]
    return int(hours) * 60 + int(minutes)


def percent(part, whole):
    return round(100.0 * part / whole, 1) if whole else None


__all__ = [
    "WellnessError", "uid", "today_local", "parse_date", "utc_text_to_local_dt",
    "clamp", "daterange", "hhmm_to_minutes", "percent", "get_connection",
    "now_local", "date", "datetime", "timedelta", "DATE_FMT", "DATETIME_FMT","now_local_text",
]
