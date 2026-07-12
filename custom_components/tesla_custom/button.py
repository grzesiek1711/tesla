"""Support for Tesla buttons.

Only the wake up and force data update buttons remain. All other buttons
(horn, flash lights, HomeLink, remote start and boombox/emissions test) sent
signed vehicle commands which require Tesla's vehicle-command signing
certificate and have therefore been removed. Wake up and force data update do
not require signing: wake up uses the account-level wake endpoint and force
data update only refreshes cached data.
"""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .base import TeslaCarEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the Tesla buttons by config_entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators = entry_data["coordinators"]
    cars = entry_data["cars"]
    entities = []

    for vin, car in cars.items():
        coordinator = coordinators[vin]
        entities.append(TeslaCarWakeUp(car, coordinator))
        entities.append(TeslaCarForceDataUpdate(car, coordinator))

    async_add_entities(entities, update_before_add=True)


class TeslaCarWakeUp(TeslaCarEntity, ButtonEntity):
    """Representation of a Tesla car wake up button."""

    type = "wake up"
    _attr_icon = "mdi:moon-waning-crescent"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._car.wake_up()

    @property
    def available(self) -> bool:
        """Return True."""
        return True


class TeslaCarForceDataUpdate(TeslaCarEntity, ButtonEntity):
    """Representation of a Tesla car force data update button."""

    type = "force data update"
    _attr_icon = "mdi:database-sync"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.update_controller(wake_if_asleep=True, force=True)

    @property
    def available(self) -> bool:
        """Return True."""
        return True
