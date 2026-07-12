"""Tests for the Tesla number platform.

The only number entity is the numeric TeslaMate ID (converted from the former
text input) used to map a vehicle to its TeslaMate car id for MQTT syncing.
"""

from unittest.mock import AsyncMock, MagicMock

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.number import NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.tesla_extended.const import DOMAIN as TESLA_DOMAIN
from custom_components.tesla_extended.number import TeslaCarTeslaMateID

from .common import setup_platform
from .mock_data import car as car_mock_data


async def _setup_number(hass: HomeAssistant):
    """Set up the number platform and flush real tokens into the entry.

    The TeslaMate ID entity is disabled by default, so no coordinator refresh
    is triggered during setup. Refresh explicitly so the mock ``connect()``
    tokens stored on the config entry are replaced with the real mock-data
    tokens (otherwise a mock would be serialized at teardown).
    """
    mock_entry, mock_controller = await setup_platform(hass, NUMBER_DOMAIN)
    entry_data = hass.data[TESLA_DOMAIN][mock_entry.entry_id]
    for coordinator in entry_data["coordinators"].values():
        await coordinator.async_refresh()
    await hass.async_block_till_done()
    return mock_entry, mock_controller


async def test_registry_entries(hass: HomeAssistant) -> None:
    """The TeslaMate ID is registered as a number entity."""
    await _setup_number(hass)
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("number.my_model_s_teslamate_id")
    assert entry is not None
    assert entry.unique_id == f"{car_mock_data.VIN.lower()}_teslamate_id"
    # The entity lives on the number platform (no longer text).
    assert entry.domain == NUMBER_DOMAIN


async def test_disabled_by_default(hass: HomeAssistant) -> None:
    """The TeslaMate ID entity is disabled by default."""
    await _setup_number(hass)
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("number.my_model_s_teslamate_id")
    assert entry.disabled_by is not None


def _build_entity() -> tuple[TeslaCarTeslaMateID, MagicMock]:
    """Build a TeslaMate ID entity with a stubbed teslamate connector."""
    teslamate = MagicMock()
    teslamate.set_car_id = AsyncMock()
    teslamate.watch_cars = AsyncMock()
    teslamate.get_car_id = AsyncMock()

    car = MagicMock()
    car.vin = car_mock_data.VIN
    coordinator = MagicMock()

    entity = TeslaCarTeslaMateID(car, coordinator, teslamate)
    # Avoid touching Home Assistant state machine in these unit tests.
    entity.async_write_ha_state = MagicMock()
    return entity, teslamate


async def test_entity_is_numeric_box() -> None:
    """The entity exposes a numeric box input with integer stepping."""
    entity, _ = _build_entity()
    assert entity._attr_mode == NumberMode.BOX
    assert entity._attr_native_step == 1
    assert entity._attr_native_min_value == 1


async def test_set_native_value_stores_integer_string() -> None:
    """Setting the value stores a plain integer string (e.g. "3" not "3.0")."""
    entity, teslamate = _build_entity()

    await entity.async_set_native_value(3.0)

    teslamate.set_car_id.assert_awaited_once_with(car_mock_data.VIN, "3")
    teslamate.watch_cars.assert_awaited_once()


async def test_native_value_parsing() -> None:
    """native_value returns the stored id as an int, or None when unset/invalid."""
    entity, _ = _build_entity()

    entity._state = None
    assert entity.native_value is None

    entity._state = "7"
    assert entity.native_value == 7

    entity._state = "not-a-number"
    assert entity.native_value is None
