"""Sensors for Medication Broadcast Assistant.

Icon source for any tablet-style artwork used with this integration:
"Tablet icons created by Freepik - Flaticon" – https://www.flaticon.com/free-icons/tablet

Each med becomes a sensor:
- state: next reminder time (lead) or "none"
- attributes: due_at, overdue, course_end, refill info, etc.
"""

from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .medication_manager import MedicationManager, Medication


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager: MedicationManager = hass.data[DOMAIN]["manager"]
    _create_entities(manager, async_add_entities)


async def async_setup_platform(
    hass: HomeAssistant,
    config,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    manager: MedicationManager = hass.data[DOMAIN]["manager"]
    _create_entities(manager, async_add_entities)


def _create_entities(manager: MedicationManager, async_add_entities: AddEntitiesCallback) -> None:
    entities = [MedicationNextSensor(manager, med) for med in manager.all_medications()]
    async_add_entities(entities, True)


class MedicationNextSensor(SensorEntity):
    """Sensor showing next reminder time for one medication."""

    _attr_icon = "mdi:pill"

    def __init__(self, manager: MedicationManager, med: Medication) -> None:
        self._manager = manager
        self._med_id = med.med_id
        self._attr_unique_id = f"{DOMAIN}_{med.med_id}_next"
        self._attr_name = f"Medication next – {med.name}"

    @property
    def _med(self) -> Optional[Medication]:
        return self._manager.get_medication(self._med_id)

    @property
    def native_value(self) -> Optional[str]:
        med = self._med
        if not med or not med.next_trigger:
            return "none"
        return dt_util.as_local(med.next_trigger).isoformat(timespec="minutes")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        med = self._med
        if not med:
            return {}

        attrs: dict[str, Any] = {
            "med_id": med.med_id,
            "name": med.name,
            "enabled": med.enabled,
            "temporary": med.temporary,
            "schedule_type": med.schedule_type,
            "instructions": med.instructions,
            "lead_minutes": med.lead_minutes,
            "interval": med.interval,
            "dose_times": med.dose_times or ([med.time] if med.time else []),
            "weekdays": med.weekdays,
            "course_end": med.course_end.isoformat() if med.course_end else None,
            "pending_ack": med.pending_ack,
            "escalated": med.escalated,
            "due_at": med.due_at.isoformat(timespec="minutes") if med.due_at else None,
            "refill_date": med.refill_date.isoformat() if med.refill_date else None,
            "refill_days_before": med.refill_days_before,
            "refill_reminder_at": med.refill_reminder_at.isoformat(timespec="minutes")
            if med.refill_reminder_at
            else None,
        }

        if med.due_at and med.pending_ack:
            now = dt_util.as_local(dt_util.utcnow())
            diff = (now - med.due_at).total_seconds() / 60.0
            attrs["overdue_minutes"] = max(0, round(diff))
        else:
            attrs["overdue_minutes"] = 0

        return attrs

    async def async_update(self) -> None:
        return
