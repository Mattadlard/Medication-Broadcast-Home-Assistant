"""Tests for the medication due binary sensor."""

from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from homeassistant.util import dt as dt_util
from homeassistant.core import HomeAssistant

from custom_components.medication_broadcast.medication_manager import MedicationManager
from custom_components.medication_broadcast.binary_sensor import MedicationDueBinarySensor
from custom_components.medication_broadcast.const import SCHEDULE_DAILY


def _utc(dt_str: str) -> datetime:
    """Timezone-aware datetime builder."""
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt


@pytest.mark.asyncio
async def test_due_binary_sensor_behaviour(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sensor should only turn on when dose is due or overdue and not acknowledged."""
    fixed_now = _utc("2025-02-01T07:50:00")  # dose at 08:00, lead = 10m
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
                    "time": "08:00",
                    "lead_minutes": 10,
                },
            }
        ],
    }

    manager = MedicationManager(hass, config)
    await manager.async_setup()

    med = manager.get_medication("tablet")
    assert med is not None

    sensor = MedicationDueBinarySensor(manager, med)

    # Nothing acknowledged yet, so OFF
    assert sensor.is_on is False

    # Simulate reminder firing: pending ack becomes True
    med.pending_ack = True
    assert sensor.is_on is False

    # After due time, sensor should turn ON
    after_due = _utc("2025-02-01T08:05:00")
    monkeypatch.setattr(dt_util, "utcnow", lambda: after_due)

    assert sensor.is_on is True

    # Mark taken: OFF again
    med.pending_ack = False
    assert sensor.is_on is False
