"""Sensor platform for Cecotec GrassHopper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ROBOTS
from .coordinator import GrassHopperCoordinator
from .entity import GrassHopperEntity


@dataclass(frozen=True)
class GrassHopperSensorDescription(SensorEntityDescription):
    """Describes a GrassHopper sensor."""

    value_fn: Any = None
    name_override: str | None = None


SENSOR_DESCRIPTIONS: tuple[GrassHopperSensorDescription, ...] = (
    GrassHopperSensorDescription(
        key="battery",
        translation_key="battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.battery,
    ),
    GrassHopperSensorDescription(
        key="wifi_level",
        translation_key="wifi_level",
        native_unit_of_measurement=None,
        icon="mdi:wifi",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.wifi_level,
    ),
    GrassHopperSensorDescription(
        key="error_code",
        translation_key="error_code",
        icon="mdi:alert-circle-outline",
        value_fn=lambda d: d.error_code if d.error_code and d.error_code != 0 else None,
    ),
    GrassHopperSensorDescription(
        key="error_text",
        translation_key="error_text",
        icon="mdi:alert-circle",
        value_fn=lambda d: d.error_text if d.error_text and d.error_text.lower() not in ("normal", "ok", "none", "") else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GrassHopper sensor entities."""
    coordinators: list[GrassHopperCoordinator] = hass.data[DOMAIN][entry.entry_id][ROBOTS]
    async_add_entities(
        GrassHopperSensor(coordinator, description)
        for coordinator in coordinators
        for description in SENSOR_DESCRIPTIONS
    )


class GrassHopperSensor(GrassHopperEntity, SensorEntity):
    """A sensor entity for the GrassHopper."""

    entity_description: GrassHopperSensorDescription

    def __init__(
        self,
        coordinator: GrassHopperCoordinator,
        description: GrassHopperSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{self._device.device_sn}_{description.key}"
        # Use translation key for name (Home Assistant will translate it)
        if description.name_override:
            self._attr_name = description.name_override

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self._device)
