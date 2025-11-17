"""Binary sensors for Medication Broadcast Assistant.

Icon source for any refill-style artwork used with this integration:
"Refill icons created by Freepik - Flaticon" – https://www.flaticon.com/free-icons/refill

These answer: "Is this medication due or overdue right now and not acknowledged?"
"""

from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
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
    entities = [MedicationDueBinarySensor(manager, med) for med in manager.all_medications()]
    async_add_entities(entities, True)


class MedicationDueBinarySensor(BinarySensorEntity):
    """Binary sensor: on when a med is due/overdue and not acknowledged."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, manager: MedicationManager, med: Medication) -> None:
        self._manager = manager
        self._med_id = med.med_id
        self._attr_unique_id = f"{DOMAIN}_{med.med_id}_due"
        self._attr_name = f"Medication due – {med.name}"

    @property
    def _med(self) -> Optional[Medication]:
        return self._manager.get_medication(self._med_id)

    @property
    def is_on(self) -> bool:
        med = self._med
        if not med or not med.enabled or not med.due_at:
            return False

        if not med.pending_ack:
            return False

        now = dt_util.as_local(dt_util.utcnow())
        return now >= med.due_at

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
            "pending_ack": med.pending_ack,
            "escalated": med.escalated,
            "due_at": med.due_at.isoformat(timespec="minutes") if med.due_at else None,
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
