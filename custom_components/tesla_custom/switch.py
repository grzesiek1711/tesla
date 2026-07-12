"""Support for Tesla switches.

Only the local polling switch remains. All other switches (heated steering
wheel, sentry mode, charger and valet mode) sent signed vehicle commands which
require Tesla's vehicle-command signing certificate and have therefore been
removed. Their status is now exposed through read-only binary sensors/sensors.
The polling switch only toggles local polling behaviour and does not send any
command to the vehicle.
"""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .base import TeslaCarEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the Tesla switches by config_entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators = entry_data["coordinators"]
    cars = entry_data["cars"]
    entities = []

    for vin, car in cars.items():
        coordinator = coordinators[vin]
        entities.append(TeslaCarPolling(car, coordinator))

    async_add_entities(entities, update_before_add=True)


class TeslaCarPolling(TeslaCarEntity, SwitchEntity):
    """Representation of a polling switch.

    This is a local-only control that enables or disables polling of the
    vehicle by the integration. It does not send any command to the vehicle.
    """

    type = "polling"
    _attr_icon = "mdi:car-connected"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        """Return True if updates available."""
        controller = self.coordinator.controller
        get_updates = controller.get_updates(vin=self._car.vin)
        if get_updates is None:
            return None
        return bool(get_updates)

    async def async_turn_on(self, **kwargs):
        """Send the on command."""
        _LOGGER.debug("Enable polling: %s %s", self.name, self._car.vin)
        self.coordinator.controller.set_updates(vin=self._car.vin, value=True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Send the off command."""
        _LOGGER.debug("Disable polling: %s %s", self.name, self._car.vin)
        self.coordinator.controller.set_updates(vin=self._car.vin, value=False)
        self.async_write_ha_state()
