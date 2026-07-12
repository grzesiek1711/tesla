"""Tests for the Tesla switch.

Only the local polling switch remains; all command switches were removed
because they require Tesla's signed vehicle-command protocol.
"""

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .common import setup_platform
from .mock_data import car as car_mock_data


async def test_registry_entries(hass: HomeAssistant) -> None:
    """Tests devices are registered in the entity registry."""
    await setup_platform(hass, SWITCH_DOMAIN)
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("switch.my_model_s_polling")
    assert entry.unique_id == f"{car_mock_data.VIN.lower()}_polling"


async def test_command_switches_removed(hass: HomeAssistant) -> None:
    """Tests that command switches were removed."""
    await setup_platform(hass, SWITCH_DOMAIN)
    entity_registry = er.async_get(hass)

    for removed in (
        "switch.my_model_s_heated_steering",
        "switch.my_model_s_charger",
        "switch.my_model_s_sentry_mode",
        "switch.my_model_s_valet_mode",
    ):
        assert entity_registry.async_get(removed) is None


async def test_enabled_by_default(hass: HomeAssistant) -> None:
    """Tests the polling switch is enabled by default."""
    await setup_platform(hass, SWITCH_DOMAIN)
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("switch.my_model_s_polling")
    assert not entry.disabled


async def test_polling_switch(hass: HomeAssistant) -> None:
    """Tests the polling switch toggles local polling only."""
    _, mock_controller = await setup_platform(hass, SWITCH_DOMAIN)
    instance = mock_controller.return_value

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.my_model_s_polling"},
        blocking=True,
    )
    assert instance.set_updates.call_args.kwargs["value"] is True

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.my_model_s_polling"},
        blocking=True,
    )
    assert instance.set_updates.call_args.kwargs["value"] is False
