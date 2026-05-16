"""DataUpdateCoordinator for Cecotec GrassHopper."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GrassHopperAPI, GrassHopperDevice

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)


class GrassHopperCoordinator(DataUpdateCoordinator[GrassHopperDevice]):
    """Coordinator for a single mower device."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: GrassHopperAPI,
        device: GrassHopperDevice,
        entry: ConfigEntry,
    ) -> None:
        self.api = api
        self.device = device
        self.entry = entry

        super().__init__(
            hass,
            _LOGGER,
            name=f"GrassHopper {device.device_sn}",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> GrassHopperDevice:
        """Fetch latest state from the API (runs in executor)."""
        success = await self.hass.async_add_executor_job(
            self.api.update_device, self.device
        )
        if not success:
            raise UpdateFailed(
                f"Failed to fetch state for mower {self.device.device_sn}"
            )
        return self.device
