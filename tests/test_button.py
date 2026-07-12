"""Tests for the Tesla button.

Only the wake up and force data update buttons remain; all command buttons
were removed because they require Tesla's signed vehicle-command protocol.
"""

from unittest.mock import patch

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .common import setup_platform
from .mock_data import car as car_mock_data


async def test_registry_entries(hass: HomeAssistant) -> None:
    """Tests devices are registered in the entity registry."""
    await setup_platform(hass, BUTTON_DOMAIN)
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("button.my_model_s_wake_up")
    assert entry.unique_id == f"{car_mock_data.VIN.lower()}_wake_up"

    entry = entity_registry.async_get("button.my_model_s_force_data_update")
    assert entry.unique_id == f"{car_mock_data.VIN.lower()}_force_data_update"


async def test_command_buttons_removed(hass: HomeAssistant) -> None:
    """Tests that command buttons were removed."""
    await setup_platform(hass, BUTTON_DOMAIN)
    entity_registry = er.async_get(hass)

    for removed in (
        "button.my_model_s_horn",
        "button.my_model_s_flash_lights",
        "button.my_model_s_homelink",
        "button.my_model_s_remote_start",
        "button.my_model_s_emissions_test",
    ):
        assert entity_registry.async_get(removed) is None


async def test_enabled_by_default(hass: HomeAssistant) -> None:
    """Tests devices are enabled by default."""
    await setup_platform(hass, BUTTON_DOMAIN)
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("button.my_model_s_wake_up")
    assert not entry.disabled

    entry = entity_registry.async_get("button.my_model_s_force_data_update")
    assert not entry.disabled


async def test_wake_up_press(hass: HomeAssistant) -> None:
    """Tests car wake up button press."""
    await setup_platform(hass, BUTTON_DOMAIN)

    with patch("teslajsonpy.car.TeslaCar.wake_up") as mock_wake_up:
        await hass.services.async_call(
            BUTTON_DOMAIN,
            "press",
            {ATTR_ENTITY_ID: "button.my_model_s_wake_up"},
            blocking=True,
        )
        mock_wake_up.assert_awaited_once()


async def test_force_data_update_press(hass: HomeAssistant) -> None:
    """Tests car force data button press."""
    await setup_platform(hass, BUTTON_DOMAIN)

    with patch(
        "custom_components.tesla_extended.base.TeslaCarEntity.update_controller"
    ) as mock_force_data_update:
        await hass.services.async_call(
            BUTTON_DOMAIN,
            "press",
            {ATTR_ENTITY_ID: "button.my_model_s_force_data_update"},
            blocking=True,
        )
        mock_force_data_update.assert_awaited_once_with(wake_if_asleep=True, force=True)
