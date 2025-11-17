"""Home Assistant entry point for Medication Broadcast Assistant."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.discovery import async_load_platform

from .const import (
    DOMAIN,
    SERVICE_MARK_TAKEN,
    SERVICE_SNOOZE,
    SERVICE_CREATE_TEMP_COURSE,
)
from .medication_manager import MedicationManager

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration from configuration.yaml."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    manager = MedicationManager(hass, conf)
    await manager.async_setup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["manager"] = manager

    _register_services(hass, manager)

    # YAML path: load platforms via discovery
    hass.async_create_task(async_load_platform(hass, "sensor", DOMAIN, {}, config))
    hass.async_create_task(async_load_platform(hass, "binary_sensor", DOMAIN, {}, config))

    _LOGGER.info("Medication Broadcast Assistant set up from YAML.")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup from a config entry (optional; mainly for global options)."""
    manager = MedicationManager(hass, entry.data)
    await manager.async_setup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["manager"] = manager

    _register_services(hass, manager)

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "binary_sensor"])
    _LOGGER.info("Medication Broadcast Assistant set up from config entry.")
    return True


def _register_services(hass: HomeAssistant, manager: MedicationManager) -> None:
    """Register mark_taken, snooze and create_temp_course services."""

    async def _handle_mark_taken(call: ServiceCall) -> None:
        med_id = call.data.get("med_id")
        await manager.async_mark_taken(med_id)

    async def _handle_snooze(call: ServiceCall) -> None:
        med_id = call.data.get("med_id")
        minutes = int(call.data.get("minutes", 10))
        await manager.async_snooze(med_id, minutes)

    async def _handle_create_temp_course(call: ServiceCall) -> None:
        data = dict(call.data)
        try:
            await manager.async_create_temp_course(data)
        except ValueError as exc:
            _LOGGER.error("create_temp_course failed: %s", exc)

    hass.services.async_register(DOMAIN, SERVICE_MARK_TAKEN, _handle_mark_taken)
    hass.services.async_register(DOMAIN, SERVICE_SNOOZE, _handle_snooze)
    hass.services.async_register(DOMAIN, SERVICE_CREATE_TEMP_COURSE, _handle_create_temp_course)

