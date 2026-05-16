"""Lawn mower platform for Cecotec GrassHopper."""

from __future__ import annotations

import logging

from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ROBOTS,
    STATE_CHARGING,
    STATE_CHARGING_FULL,
    STATE_ERROR,
    STATE_GOING_HOME,
    STATE_MOWING,
    STATE_OFFLINE,
    STATE_PAUSE,
    STATE_STANDBY,
)
from .coordinator import GrassHopperCoordinator
from .entity import GrassHopperEntity

_LOGGER = logging.getLogger(__name__)

# Map raw mode integers → HA LawnMowerActivity
# Based on the sk-robot OEM platform (same as Sunseeker/Adano)
_MODE_TO_ACTIVITY: dict[int, LawnMowerActivity] = {
    0: LawnMowerActivity.DOCKED,      # standby / idle
    1: LawnMowerActivity.MOWING,      # mowing
    2: LawnMowerActivity.RETURNING,   # going home
    3: LawnMowerActivity.DOCKED,      # charging
    6: LawnMowerActivity.ERROR,       # error
    7: LawnMowerActivity.MOWING,      # border mowing
    8: LawnMowerActivity.PAUSED,      # return paused
    9: LawnMowerActivity.DOCKED,      # charging
    10: LawnMowerActivity.DOCKED,     # fully charged
    13: LawnMowerActivity.ERROR,      # offline
    14: LawnMowerActivity.MOWING,     # continue mowing
    18: LawnMowerActivity.PAUSED,     # stopped
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GrassHopper lawn mower entities."""
    coordinators: list[GrassHopperCoordinator] = hass.data[DOMAIN][entry.entry_id][ROBOTS]
    async_add_entities(
        GrassHopperLawnMower(coordinator) for coordinator in coordinators
    )


class GrassHopperLawnMower(GrassHopperEntity, LawnMowerEntity):
    """Representation of the GrassHopper as a lawn_mower entity."""

    _attr_supported_features = (
        LawnMowerEntityFeature.START_MOWING
        | LawnMowerEntityFeature.PAUSE
        | LawnMowerEntityFeature.DOCK
    )

    def __init__(self, coordinator: GrassHopperCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{self._device.device_sn}_mower"
        self._attr_name = None  # use device name as entity name

    @property
    def activity(self) -> LawnMowerActivity:
        """Return the current mowing activity."""
        if not self._device.online:
            return LawnMowerActivity.ERROR
        if self._device.error_code:
            return LawnMowerActivity.ERROR
        return _MODE_TO_ACTIVITY.get(self._device.mode, LawnMowerActivity.ERROR)

    async def async_start_mowing(self) -> None:
        """Start or resume mowing."""
        mowing_mode_entity = f"select.{self._device.device_sn}_mowing_mode"
        mowing_mode_state = self.hass.states.get(mowing_mode_entity)
        
        if mowing_mode_state and mowing_mode_state.state == "edge":
            await self.hass.async_add_executor_job(
                self.coordinator.api.start_border, self._device.device_sn
            )
        else:
            await self.hass.async_add_executor_job(
                self.coordinator.api.start_mowing, self._device.device_sn
            )
        await self.coordinator.async_request_refresh()

    async def async_pause(self) -> None:
        """Pause the mower."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.pause, self._device.device_sn
        )
        await self.coordinator.async_request_refresh()

    async def async_dock(self) -> None:
        """Send the mower back to the dock."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.dock, self._device.device_sn
        )
        await self.coordinator.async_request_refresh()
