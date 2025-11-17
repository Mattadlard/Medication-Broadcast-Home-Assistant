"""Config flow for Medication Broadcast Assistant.

This only handles global options (TTS, notify, default speakers).
Actual meds are still configured in YAML for now.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .const import (
    DOMAIN,
    CONF_TTS_SERVICE,
    CONF_NOTIFY_SERVICE,
    CONF_DEFAULT_MEDIA_PLAYERS,
)


class MedicationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the integration."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Medication Broadcast", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_TTS_SERVICE, default="tts.google_translate_say"): str,
                vol.Optional(CONF_NOTIFY_SERVICE): str,
                vol.Optional(CONF_DEFAULT_MEDIA_PLAYERS, default=[]): [str],
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)
