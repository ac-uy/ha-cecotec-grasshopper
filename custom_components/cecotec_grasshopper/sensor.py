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

DAY_NAMES = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}


def _get_next_schedule(device) -> str | None:
    """Get the next scheduled mowing time as a readable string."""
    from datetime import datetime, timedelta

    if not device.schedule:
        return None

    now = datetime.now()
    current_dow = now.isoweekday()  # 1=Monday, 7=Sunday

    # Find the next scheduled day
    for offset in range(7):
        check_dow = ((current_dow - 1 + offset) % 7) + 1
        for entry in device.schedule:
            if entry.get("dayOfWeek") == check_dow:
                start_time = entry.get("startAt", "00:00:00")
                # Parse start time
                parts = start_time.split(":")
                hour, minute = int(parts[0]), int(parts[1])

                # If it's today, check if the time hasn't passed
                if offset == 0:
                    scheduled = now.replace(hour=hour, minute=minute, second=0)
                    if scheduled <= now:
                        continue

                day_name = DAY_NAMES.get(check_dow, "")
                return f"{day_name} {hour:02d}:{minute:02d}"

    return None


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
    GrassHopperSensorDescription(
        key="rain_delay_duration",
        translation_key="rain_delay_duration",
        icon="mdi:weather-rainy",
        native_unit_of_measurement="min",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.rain_delay_duration,
    ),
    GrassHopperSensorDescription(
        key="border_length",
        translation_key="border_length",
        icon="mdi:tape-measure",
        native_unit_of_measurement="m",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: round(d.border_length / 100, 1) if d.border_length else None,
    ),
    GrassHopperSensorDescription(
        key="next_schedule",
        translation_key="next_schedule",
        icon="mdi:calendar-clock",
        value_fn=lambda d: _get_next_schedule(d),
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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes for schedule sensor."""
        if self.entity_description.key == "next_schedule":
            schedule = self._device.schedule
            if not schedule:
                return {"schedule_entries": 0, "schedule_paused": self._device.schedule_paused}
            attrs = {
                "schedule_entries": len(schedule),
                "schedule_paused": self._device.schedule_paused,
            }
            for entry in schedule:
                day = DAY_NAMES.get(entry.get("dayOfWeek", 0), "Unknown")
                start = entry.get("startAt", "?")[:5]
                end = entry.get("endAt", "?")[:5]
                edge = "✓" if entry.get("trimFlag") else "✗"
                attrs[f"{day.lower()}"] = f"{start}-{end} (edge: {edge})"
            return attrs
        return None
