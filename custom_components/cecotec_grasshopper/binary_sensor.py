"""Binary sensor platform for Cecotec GrassHopper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ROBOTS
from .coordinator import GrassHopperCoordinator
from .entity import GrassHopperEntity


@dataclass(frozen=True)
class GrassHopperBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a GrassHopper binary sensor."""

    value_fn: Any = None
    name_override: str | None = None


BINARY_SENSOR_DESCRIPTIONS: tuple[GrassHopperBinarySensorDescription, ...] = (
    GrassHopperBinarySensorDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: d.online,
    ),
    GrassHopperBinarySensorDescription(
        key="error",
        translation_key="error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: bool(d.error_code),
    ),
    GrassHopperBinarySensorDescription(
        key="rain_detected",
        translation_key="rain_detected",
        device_class=BinarySensorDeviceClass.MOISTURE,
        value_fn=lambda d: d.rain_status != 0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GrassHopper binary sensor entities."""
    coordinators: list[GrassHopperCoordinator] = hass.data[DOMAIN][entry.entry_id][ROBOTS]
    async_add_entities(
        GrassHopperBinarySensor(coordinator, description)
        for coordinator in coordinators
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class GrassHopperBinarySensor(GrassHopperEntity, BinarySensorEntity):
    """A binary sensor entity for the GrassHopper."""

    entity_description: GrassHopperBinarySensorDescription

    def __init__(
        self,
        coordinator: GrassHopperCoordinator,
        description: GrassHopperBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{self._device.device_sn}_{description.key}"
        self._attr_translation_key = description.key

    @property
    def is_on(self) -> bool:
        """Return the binary sensor state."""
        return bool(self.entity_description.value_fn(self._device))
