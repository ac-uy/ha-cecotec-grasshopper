"""Select platform for Cecotec GrassHopper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ROBOTS
from .coordinator import GrassHopperCoordinator
from .entity import GrassHopperEntity


@dataclass(frozen=True)
class GrassHopperSelectDescription(SelectEntityDescription):
    """Describes a GrassHopper select entity."""

    options_fn: Any = None


SELECT_DESCRIPTIONS: tuple[GrassHopperSelectDescription, ...] = (
    GrassHopperSelectDescription(
        key="mowing_mode",
        translation_key="mowing_mode",
        icon="mdi:scissors-cutting",
        options=["normal", "edge"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GrassHopper select entities."""
    coordinators: list[GrassHopperCoordinator] = hass.data[DOMAIN][entry.entry_id][ROBOTS]
    async_add_entities(
        GrassHopperSelect(coordinator, description)
        for coordinator in coordinators
        for description in SELECT_DESCRIPTIONS
    )


class GrassHopperSelect(GrassHopperEntity, SelectEntity):
    """A select entity for the GrassHopper."""

    entity_description: GrassHopperSelectDescription

    def __init__(
        self,
        coordinator: GrassHopperCoordinator,
        description: GrassHopperSelectDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{self._device.device_sn}_{description.key}"
        self._attr_current_option = "normal"  # Default to normal mowing

    @property
    def options(self) -> list[str]:
        """Return the list of available options."""
        return self.entity_description.options

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self._attr_current_option

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self._attr_current_option = option
        self.async_write_ha_state()
