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
SERVICE_SET_SCHEDULE = "set_schedule"
SERVICE_SET_RAIN_DELAY = "set_rain_delay"
SERVICE_ADD_SCHEDULE_ENTRY = "add_schedule_entry"
SERVICE_REMOVE_SCHEDULE_ENTRY = "remove_schedule_entry"
SERVICE_CLEAR_SCHEDULE = "clear_schedule"

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
    }
)

SERVICE_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("schedule"): list,
    }
)

SERVICE_RAIN_DELAY_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("enabled"): bool,
        vol.Optional("duration", default=180): vol.All(int, vol.Range(min=30, max=720)),
    }
)

SERVICE_ADD_ENTRY_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("day"): vol.All(int, vol.Range(min=1, max=7)),
        vol.Required("start"): str,
        vol.Required("end"): str,
        vol.Optional("edge", default=True): bool,
    }
)

SERVICE_REMOVE_ENTRY_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("day"): vol.All(int, vol.Range(min=1, max=7)),
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
        for coordinator in coordinators:
            await hass.async_add_executor_job(
                coordinator.api.start_border,
                coordinator.device.device_sn,
            )
            await coordinator.async_request_refresh()
            return

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_BORDER_MOWING,
        handle_start_border_mowing,
        schema=SERVICE_SCHEMA,
    )

    # Set schedule service
    async def handle_set_schedule(call: ServiceCall) -> None:
        """Handle set schedule service call."""
        entity_id = call.data.get("entity_id")
        schedule_data = call.data.get("schedule", [])

        # Convert user-friendly format to API format
        api_entries = []
        for entry in schedule_data:
            day = entry.get("day", 1)
            start = entry.get("start", "09:00")
            end = entry.get("end", "12:00")
            edge = entry.get("edge", True)
            # Ensure HH:MM:SS format
            if start.count(":") == 1:
                start += ":00"
            if end.count(":") == 1:
                end += ":00"
            api_entries.append({
                "dayOfWeek": day,
                "startAt": start,
                "endAt": end,
                "trimFlag": edge,
            })

        for coordinator in coordinators:
            await hass.async_add_executor_job(
                coordinator.api.set_schedule,
                coordinator.device.device_sn,
                api_entries,
            )
            await coordinator.async_request_refresh()
            return

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE,
        handle_set_schedule,
        schema=SERVICE_SCHEDULE_SCHEMA,
    )

    # Set rain delay service
    async def handle_set_rain_delay(call: ServiceCall) -> None:
        """Handle set rain delay service call."""
        enabled = call.data.get("enabled", True)
        duration = call.data.get("duration", 180)

        for coordinator in coordinators:
            await hass.async_add_executor_job(
                coordinator.api.set_rain_delay,
                coordinator.device.device_sn,
                enabled,
                duration,
            )
            await coordinator.async_request_refresh()
            return

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_RAIN_DELAY,
        handle_set_rain_delay,
        schema=SERVICE_RAIN_DELAY_SCHEMA,
    )

    # Add schedule entry service
    async def handle_add_schedule_entry(call: ServiceCall) -> None:
        """Add a single schedule entry, preserving existing ones."""
        day = call.data.get("day")
        start = call.data.get("start", "09:00")
        end = call.data.get("end", "12:00")
        edge = call.data.get("edge", True)

        # Ensure HH:MM:SS format
        if start.count(":") == 1:
            start += ":00"
        if end.count(":") == 1:
            end += ":00"

        for coordinator in coordinators:
            # Get current schedule
            current = list(coordinator.device.schedule or [])

            # Remove existing entry for this day (replace it)
            current = [e for e in current if e.get("dayOfWeek") != day]

            # Add new entry
            current.append({
                "dayOfWeek": day,
                "startAt": start,
                "endAt": end,
                "trimFlag": edge,
            })

            # Sort by day
            current.sort(key=lambda e: e.get("dayOfWeek", 0))

            await hass.async_add_executor_job(
                coordinator.api.set_schedule,
                coordinator.device.device_sn,
                current,
            )
            await coordinator.async_request_refresh()
            return

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_SCHEDULE_ENTRY,
        handle_add_schedule_entry,
        schema=SERVICE_ADD_ENTRY_SCHEMA,
    )

    # Remove schedule entry service
    async def handle_remove_schedule_entry(call: ServiceCall) -> None:
        """Remove a schedule entry for a specific day."""
        day = call.data.get("day")

        for coordinator in coordinators:
            # Get current schedule, remove the day
            current = list(coordinator.device.schedule or [])
            current = [e for e in current if e.get("dayOfWeek") != day]

            await hass.async_add_executor_job(
                coordinator.api.set_schedule,
                coordinator.device.device_sn,
                current,
            )
            await coordinator.async_request_refresh()
            return

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_SCHEDULE_ENTRY,
        handle_remove_schedule_entry,
        schema=SERVICE_REMOVE_ENTRY_SCHEMA,
    )

    # Clear all schedule service
    async def handle_clear_schedule(call: ServiceCall) -> None:
        """Remove all schedule entries."""
        for coordinator in coordinators:
            await hass.async_add_executor_job(
                coordinator.api.set_schedule,
                coordinator.device.device_sn,
                [],  # Empty list clears all
            )
            await coordinator.async_request_refresh()
            return

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_SCHEDULE,
        handle_clear_schedule,
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
