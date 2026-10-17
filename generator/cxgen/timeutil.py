"""Time helpers. All internal timestamps are naive UTC datetimes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import CLOSE_HOUR_ET, OPEN_HOUR_ET, OPEN_WEEKDAYS

ET = ZoneInfo("America/New_York")
UTC = timezone.utc


def to_local(ts_utc: datetime, tz: str | ZoneInfo) -> datetime:
    zone = ZoneInfo(tz) if isinstance(tz, str) else tz
    return ts_utc.replace(tzinfo=UTC).astimezone(zone).replace(tzinfo=None)


def from_local(ts_local: datetime, tz: str | ZoneInfo) -> datetime:
    zone = ZoneInfo(tz) if isinstance(tz, str) else tz
    return ts_local.replace(tzinfo=zone).astimezone(UTC).replace(tzinfo=None)


def is_open(ts_utc: datetime) -> bool:
    et = to_local(ts_utc, ET)
    return et.weekday() in OPEN_WEEKDAYS and OPEN_HOUR_ET <= et.hour < CLOSE_HOUR_ET


def next_open(ts_utc: datetime) -> datetime:
    """The first moment at or after ts_utc when the contact center is open."""
    if is_open(ts_utc):
        return ts_utc
    et = to_local(ts_utc, ET)
    day = et.date()
    if et.hour >= CLOSE_HOUR_ET or et.weekday() not in OPEN_WEEKDAYS:
        day = day + timedelta(days=1)
    elif et.hour < OPEN_HOUR_ET:
        pass
    while day.weekday() not in OPEN_WEEKDAYS:
        day = day + timedelta(days=1)
    opening = datetime(day.year, day.month, day.day, OPEN_HOUR_ET)
    return from_local(opening, ET)


def add_open_minutes(ts_utc: datetime, minutes: float) -> datetime:
    """Advance by business (open) minutes, skipping closed hours exactly."""
    current = next_open(ts_utc)
    remaining = float(minutes)
    while True:
        et = to_local(current, ET)
        close = et.replace(hour=CLOSE_HOUR_ET, minute=0, second=0, microsecond=0)
        available = (close - et).total_seconds() / 60.0
        if remaining <= available:
            return current + timedelta(minutes=remaining)
        remaining -= available
        current = next_open(from_local(close, ET))
