"""Config flow for Cecotec GrassHopper integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .api import GrassHopperAPI
from .const import CONF_ACCOUNT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def validate_credentials(
    hass: HomeAssistant, email: str, password: str
) -> dict[str, str] | None:
    """Validate credentials by attempting login. Returns error dict or None."""
    api = GrassHopperAPI(email, password, hass.config.language)
    login_ok = await hass.async_add_executor_job(api.login)
    if not login_ok:
        return {"base": "invalid_auth"}
    # Fetch device list to confirm account has at least one mower
    devices = await hass.async_add_executor_job(api.fetch_device_list)
    if not devices:
        return {"base": "no_devices"}
    api.unload()
    return None


class GrassHopperConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cecotec GrassHopper."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            account_name = user_input[CONF_ACCOUNT_NAME]

            # Check for duplicate
            await self.async_set_unique_id(email.lower())
            self._abort_if_unique_id_configured()

            # Validate credentials
            error = await validate_credentials(self.hass, email, password)
            if error:
                errors.update(error)
            else:
                return self.async_create_entry(
                    title=account_name,
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                        CONF_ACCOUNT_NAME: account_name,
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ACCOUNT_NAME, default="My GrassHopper"): str,
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "app_name": "Conga GrassHopper 500 Map",
            },
        )
