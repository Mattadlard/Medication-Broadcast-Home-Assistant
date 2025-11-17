"""Scheduling tests for Medication Broadcast Assistant.

These tests validate:
- interval schedules (every N hours)
- daily schedules with multiple dose times
- fixed-length courses ending cleanly
- refill scheduling logic
"""

from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import pytest

from homeassistant.util import dt as dt_util
from homeassistant.core import HomeAssistant

from custom_components.medication_broadcast.medication_manager import MedicationManager
from custom_components.medication_broadcast.const import (
    SCHEDULE_EVERY_N_HOURS,
    SCHEDULE_DAILY,
    SCHEDULE_COURSE,
)


def _utc(dt_str: str) -> datetime:
    """Create a timezone-aware UTC datetime."""
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt


@pytest.mark.asyncio
async def test_every_96_hours_schedule(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure next due = start + 96h, and lead time is correct."""
    fixed_now = _utc("2025-01-01T20:00:00")
    monkeypatch.setattr(dt_util, "utcnow", lambda: fixed_now)

    config = {
        "tts_service": "tts.google_translate_say",
        "default_media_players": [],
        "meds": [
            {
                "id": "patch",
                "name": "Patch",
                "instructions": "",
                "schedule": {
                    "type": SCHEDULE_EVERY_N_HOURS,
                    "interval": 96,
                    "start": "2025-01-01T20:00:00",
                    "lead_minutes": 15,
                },
            }
        ],
    }

    manager = MedicationManager(hass, config)
    await manager.async_setup()
    med = manager.get_medication("patch")
    assert med is not None

    assert med.due_at is not None
    expected_due = dt_util.as_local(fixed_now + timedelta(hours=96))
    assert abs((med.due_at - expected_due).total_seconds()) < 60

    assert med.next_trigger is not None
    diff = med.due_at - med.next_trigger
    assert round(diff.total_seconds() / 60) == 15


@pytest.mark.asyncio
async def test_daily_multiple_doses(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """The next upcoming dose should be selected correctly."""
    fixed_now = _utc("2025-02-03T07:00:00")
    monkeypatch.setattr(dt_util, "utcnow", lambda: fixed_now)

    config = {
        "tts_service": "tts.google_translate_say",
        "default_media_players": [],
        "meds": [
            {
                "id": "tablet",
                "name": "Tablet",
                "instructions": "",
                "schedule": {
                    "type": SCHEDULE_DAILY,
                    "dose_times": ["08:00", "20:00"],
                    "lead_minutes": 10,
                },
            }
        ],
    }

    manager = MedicationManager(hass, config)
    await manager.async_setup()
    med = manager.get_medication("tablet")
    assert med is not None

    assert med.due_at is not None
    local_now = dt_util.as_local(fixed_now)
    expected_due = local_now.replace(hour=8, minute=0, second=0, microsecond=0)
    assert med.due_at.hour == expected_due.hour
    assert med.due_at.minute == expected_due.minute

    later = _utc("2025-02-03T21:00:00")
    monkeypatch.setattr(dt_util, "utcnow", lambda: later)

    manager._schedule_next(med, initial=False)  # type: ignore[attr-defined]

    assert med.due_at is not None
    local_later = dt_util.as_local(later)
    expected_tomorrow = (local_later + timedelta(days=1)).replace(
        hour=8, minute=0, second=0, microsecond=0
    )
    assert med.due_at.date() == expected_tomorrow.date()
    assert med.due_at.hour == 8


@pytest.mark.asyncio
async def test_course_stops_after_end(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """Courses must end cleanly with no next dose."""
    fixed_now = _utc("2025-01-10T12:00:00")
    monkeypatch.setattr(dt_util, "utcnow", lambda: fixed_now)

    config = {
        "tts_service": "tts.google_translate_say",
        "default_media_players": [],
        "meds": [
            {
                "id": "antibiotic",
                "name": "Antibiotic",
                "instructions": "",
                "schedule": {
                    "type": SCHEDULE_COURSE,
                    "start_date": "2025-01-01",
                    "dose_times": ["08:00", "20:00"],
                    "course_length_days": 5,
                    "lead_minutes": 0,
                },
            }
        ],
    }

    manager = MedicationManager(hass, config)
    await manager.async_setup()
    med = manager.get_medication("antibiotic")
    assert med is not None

    assert med.due_at is None
    assert med.next_trigger is None


@pytest.mark.asyncio
async def test_refill_reminder_scheduled(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """Refill reminders should land at 09:00 on (refill_date minus N days)."""
    fixed_now = _utc("2025-03-01T08:00:00")
    monkeypatch.setattr(dt_util, "utcnow", lambda: fixed_now)

    config = {
        "tts_service": "tts.google_translate_say",
        "default_media_players": [],
        "meds": [
            {
                "id": "patch",
                "name": "Patch",
                "instructions": "",
                "schedule": {
                    "type": SCHEDULE_DAILY,
                    "time": "21:00",
                    "lead_minutes": 15,
                    "refill_date": "2025-04-01",
                    "refill_days_before": 7,
                },
            }
        ],
    }

    manager = MedicationManager(hass, config)
    await manager.async_setup()

    med = manager.get_medication("patch")
    assert med is not None
    assert med.refill_reminder_at is not None

    reminder = med.refill_reminder_at
    assert reminder.date() == date(2025, 3, 25)
    assert reminder.hour == 9
    assert reminder.minute == 0
