"""Cecotec Conga GrassHopper 500 integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .api import GrassHopperAPI
from .const import DATAHANDLER, DOMAIN, ROBOTS
from .coordinator import GrassHopperCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LAWN_MOWER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
]

# Service schemas
SERVICE_START_BORDER_MOWING = "start_border_mowing"
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cecotec GrassHopper from a config entry."""
    email: str = entry.data[CONF_EMAIL]
    password: str = entry.data[CONF_PASSWORD]

    api = GrassHopperAPI(email, password, hass.config.language)

    login_ok = await hass.async_add_executor_job(api.login)
    if not login_ok:
        raise ConfigEntryNotReady("Login to Cecotec GrassHopper cloud failed")

    devices = await hass.async_add_executor_job(api.fetch_device_list)
    if not devices:
        raise ConfigEntryNotReady("No GrassHopper devices found on this account")

    coordinators = [
        GrassHopperCoordinator(hass, api, device, entry) for device in devices
    ]

    # Initial data fetch
    for coordinator in coordinators:
        await coordinator.async_config_entry_first_refresh()

    # Start MQTT for real-time status push
    for coordinator in coordinators:
        await coordinator.async_setup()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATAHANDLER: api,
        ROBOTS: coordinators,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Register custom services
    async def handle_start_border_mowing(call: ServiceCall) -> None:
        """Handle start border mowing service call."""
        entity_id = call.data.get("entity_id")
        
        # Find the coordinator for this entity
        for coordinator in coordinators:
            if coordinator.entity_id == entity_id or f"{DOMAIN}.{coordinator.entity_id}" == entity_id:
                await hass.async_add_executor_job(
                    coordinator.api.send_command,
                    coordinator.device.device_sn,
                    4,  # CMD_BORDER
                )
                await coordinator.async_request_refresh()
                return
        
        _LOGGER.warning(f"Entity {entity_id} not found for border mowing command")

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_BORDER_MOWING,
        handle_start_border_mowing,
        schema=SERVICE_SCHEMA,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        api: GrassHopperAPI = entry_data[DATAHANDLER]
        # Stop MQTT connections
        for coordinator in entry_data[ROBOTS]:
            coordinator.stop_mqtt()
        api.unload()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
