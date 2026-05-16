"""Base entity for Cecotec GrassHopper."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GrassHopperCoordinator


class GrassHopperEntity(CoordinatorEntity[GrassHopperCoordinator]):
    """Base class for all GrassHopper entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GrassHopperCoordinator) -> None:
        super().__init__(coordinator)
        self._device = coordinator.device

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.device_sn)},
            name=self._device.name,
            manufacturer="Cecotec",
            model=self._device.model,
            sw_version=self._device.firmware,
        )
