"""Support for Tesla number entities."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from teslajsonpy.car import TeslaCar

from . import TeslaDataUpdateCoordinator
from .base import TeslaCarEntity
from .const import DOMAIN
from .teslamate import TeslaMate


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the Tesla number entities by config_entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators = entry_data["coordinators"]
    cars = entry_data["cars"]
    teslamate = entry_data["teslamate"]
    entities = []

    for vin, car in cars.items():
        coordinator = coordinators[vin]
        entities.append(TeslaCarTeslaMateID(car, coordinator, teslamate))

    async_add_entities(entities, update_before_add=True)


class TeslaCarTeslaMateID(TeslaCarEntity, NumberEntity):
    """Representation of the numeric TeslaMate car ID used for MQTT syncing."""

    type = "teslamate id"
    _attr_icon = "mdi:ev-station"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 1
    _attr_native_max_value = 65535
    _attr_native_step = 1
    _enabled_by_default = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        car: TeslaCar,
        coordinator: TeslaDataUpdateCoordinator,
        teslamate: TeslaMate,
    ) -> None:
        """Initialize the TeslaMate ID entity."""
        self.teslamate = teslamate
        self._state = None
        super().__init__(car, coordinator)

    async def async_set_native_value(self, value: float) -> None:
        """Update the TeslaMate car ID."""
        # TeslaMate identifies cars with integer ids that are compared against
        # the MQTT topic segments (strings), so store the id as a plain integer
        # string (e.g. "3" rather than "3.0").
        teslamate_id = str(int(value))

        # Update the cached state before writing so the entity does not revert
        # to the previously stored value on the next coordinator refresh.
        self._state = teslamate_id
        await self.teslamate.set_car_id(self._car.vin, teslamate_id)
        await self.teslamate.watch_cars()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity."""
        # Ignore manual update requests if the entity is disabled
        self._state = await self.teslamate.get_car_id(self._car.vin)

    @property
    def native_value(self) -> float | None:
        """Return the TeslaMate car ID."""
        if self._state is None:
            return None
        try:
            return int(self._state)
        except (TypeError, ValueError):
            return None
