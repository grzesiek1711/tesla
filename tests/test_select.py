"""Tests for the Tesla select."""

from unittest.mock import patch

from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_SELECT_OPTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .common import setup_platform
from .mock_data import car as car_mock_data


async def test_registry_entries(hass: HomeAssistant) -> None:
    """Tests devices are registered in the entity registry."""
    await setup_platform(hass, SELECT_DOMAIN)
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("select.my_model_s_heated_seat_left")
    assert entry.unique_id == f"{car_mock_data.VIN.lower()}_heated_seat_left"

    entry = entity_registry.async_get("select.my_model_s_heated_seat_right")
    assert entry.unique_id == f"{car_mock_data.VIN.lower()}_heated_seat_right"

    entry = entity_registry.async_get("select.my_model_s_cabin_overheat_protection")
    assert entry.unique_id == f"{car_mock_data.VIN.lower()}_cabin_overheat_protection"

    entry = entity_registry.async_get("select.my_model_s_heated_steering_wheel")
    assert entry.unique_id == f"{car_mock_data.VIN.lower()}_heated_steering_wheel"


async def test_skipped_entries(hass: HomeAssistant) -> None:
    """Tests devices are skipped in the entity registry."""

    del car_mock_data.VEHICLE_DATA["climate_state"]["steering_wheel_heat_level"]
    await setup_platform(hass, SELECT_DOMAIN)
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("select.my_model_s_heated_steering_wheel")
    assert entry is None

    # Add it back for further tests
    car_mock_data.VEHICLE_DATA["climate_state"]["steering_wheel_heat_level"] = "1"


async def test_car_heated_seat_select(hass: HomeAssistant) -> None:
    """Tests car heated seat select."""
    await setup_platform(hass, SELECT_DOMAIN)

    # Test cars with heated seats only
    del car_mock_data.VEHICLE_DATA["vehicle_config"]["has_seat_cooling"]
    car_mock_data.VEHICLE_DATA["vehicle_config"]["has_seat_cooling"] = False
    with patch(
        "teslajsonpy.car.TeslaCar.remote_seat_heater_request"
    ) as mock_remote_seat_heater_request:
        # Test selecting "Off"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left", "option": "Off"},
            blocking=True,
        )
        mock_remote_seat_heater_request.assert_awaited_once_with(0, 0)
        # Test selecting "Low"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left", "option": "Low"},
            blocking=True,
        )
        mock_remote_seat_heater_request.assert_awaited_with(1, 0)
        # Test selecting "Medium"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left", "option": "Medium"},
            blocking=True,
        )
        mock_remote_seat_heater_request.assert_awaited_with(2, 0)
        # Test selecting "High"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left", "option": "High"},
            blocking=True,
        )
        mock_remote_seat_heater_request.assert_awaited_with(3, 0)

    with patch(
        "teslajsonpy.car.TeslaCar.remote_auto_seat_climate_request"
    ) as mock_remote_auto_seat_climate_request:
        # Test selecting "Auto"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left", "option": "Auto"},
            blocking=True,
        )
        mock_remote_auto_seat_climate_request.assert_awaited_once_with(1, True)
        # Test from "Auto" selection
        car_mock_data.VEHICLE_DATA["climate_state"]["auto_seat_climate_left"] = True
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left", "option": "Low"},
            blocking=True,
        )
        mock_remote_auto_seat_climate_request.assert_awaited_with(1, False)

    with patch("teslajsonpy.car.TeslaCar.set_hvac_mode") as mock_set_hvac_mode:
        # Test climate_on check
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left", "option": "Low"},
            blocking=True,
        )
        mock_set_hvac_mode.assert_awaited_once_with("on")


async def test_car_cooling_seat_select(hass: HomeAssistant) -> None:
    """Tests car cooling seat select."""
    await setup_platform(hass, SELECT_DOMAIN)

    # Test cars with cooling/heated seats
    del car_mock_data.VEHICLE_DATA["vehicle_config"]["has_seat_cooling"]
    car_mock_data.VEHICLE_DATA["vehicle_config"]["has_seat_cooling"] = True
    # The "Off" assertion below relies on the seat being in auto mode so that
    # turning off issues a heater request. Set it explicitly rather than
    # inheriting the leaked global state from test_car_heated_seat_select, which
    # is not guaranteed to run first under pytest-xdist (-n auto).
    car_mock_data.VEHICLE_DATA["climate_state"]["auto_seat_climate_left"] = True

    with patch(
        "teslajsonpy.car.TeslaCar.remote_seat_heater_request"
    ) as mock_remote_seat_heater_request:
        # Test selecting "Off"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left", "option": "Off"},
            blocking=True,
        )
        mock_remote_seat_heater_request.assert_awaited_once_with(0, 0)
        # Test selecting "Low"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left",
                "option": "Heat Low",
            },
            blocking=True,
        )
        mock_remote_seat_heater_request.assert_awaited_with(1, 0)
        # Test selecting "Medium"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left",
                "option": "Heat Medium",
            },
            blocking=True,
        )
        mock_remote_seat_heater_request.assert_awaited_with(2, 0)
        # Test selecting "High"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left",
                "option": "Heat High",
            },
            blocking=True,
        )
        mock_remote_seat_heater_request.assert_awaited_with(3, 0)

    with patch(
        "teslajsonpy.car.TeslaCar.remote_seat_cooler_request"
    ) as mock_remote_seat_cooler_request:
        # Test selecting "Off"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left", "option": "Off"},
            blocking=True,
        )
        mock_remote_seat_cooler_request.assert_awaited_once_with(1, 1)
        # Test selecting "Low"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left",
                "option": "Cool Low",
            },
            blocking=True,
        )
        mock_remote_seat_cooler_request.assert_awaited_with(2, 1)
        # Test selecting "Medium"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left",
                "option": "Cool Medium",
            },
            blocking=True,
        )
        mock_remote_seat_cooler_request.assert_awaited_with(3, 1)
        # Test selecting "High"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left",
                "option": "Cool High",
            },
            blocking=True,
        )
        mock_remote_seat_cooler_request.assert_awaited_with(4, 1)

    with patch(
        "teslajsonpy.car.TeslaCar.remote_auto_seat_climate_request"
    ) as mock_remote_auto_seat_climate_request:
        # Test selecting "Auto"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left", "option": "Auto"},
            blocking=True,
        )
        mock_remote_auto_seat_climate_request.assert_awaited_once_with(1, True)
        # Test from "Auto" selection
        car_mock_data.VEHICLE_DATA["climate_state"]["auto_seat_climate_left"] = True
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left",
                "option": "Cool Low",
            },
            blocking=True,
        )
        mock_remote_auto_seat_climate_request.assert_awaited_with(1, False)

    with patch("teslajsonpy.car.TeslaCar.set_hvac_mode") as mock_set_hvac_mode:
        # Test climate_on check
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.my_model_s_heated_seat_left",
                "option": "Cool Low",
            },
            blocking=True,
        )
        mock_set_hvac_mode.assert_awaited_once_with("on")


async def test_cabin_overheat_protection(hass: HomeAssistant) -> None:
    """Tests car cabin overheat protection select."""
    await setup_platform(hass, SELECT_DOMAIN)

    with patch(
        "teslajsonpy.car.TeslaCar.set_cabin_overheat_protection"
    ) as mock_set_cabin_overheat_protection:
        # Test selecting "On"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.my_model_s_cabin_overheat_protection",
                "option": "On",
            },
            blocking=True,
        )
        mock_set_cabin_overheat_protection.assert_awaited_once_with("On")
        # Test selecting "Off"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.my_model_s_cabin_overheat_protection",
                "option": "Off",
            },
            blocking=True,
        )
        mock_set_cabin_overheat_protection.assert_awaited_with("Off")
        # Test selecting "No A/C"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.my_model_s_cabin_overheat_protection",
                "option": "No A/C",
            },
            blocking=True,
        )
        mock_set_cabin_overheat_protection.assert_awaited_with("No A/C")


async def test_car_heated_steering_wheel_select(hass: HomeAssistant) -> None:
    """Tests car heated steering wheel select."""
    entity_id = "select.my_model_s_heated_steering_wheel"

    await setup_platform(hass, SELECT_DOMAIN)

    with patch(
        "teslajsonpy.car.TeslaCar.set_heated_steering_wheel_level"
    ) as mock_set_heated_steering_wheel_level:
        # Test selecting "Off"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: entity_id,
                "option": "Off",
            },
            blocking=True,
        )
        mock_set_heated_steering_wheel_level.assert_awaited_once_with(0)
        # Test selecting "Low"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: entity_id,
                "option": "Low",
            },
            blocking=True,
        )
        mock_set_heated_steering_wheel_level.assert_awaited_with(1)
        # Test selecting "High"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: entity_id,
                "option": "High",
            },
            blocking=True,
        )
        mock_set_heated_steering_wheel_level.assert_awaited_with(3)

    with patch(
        "teslajsonpy.car.TeslaCar.remote_auto_steering_wheel_heat_climate_request"
    ) as mock_remote_auto_steering_wheel_heat_climate_request:
        # Test selecting "Auto"
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: entity_id,
                "option": "Auto",
            },
            blocking=True,
        )
        mock_remote_auto_steering_wheel_heat_climate_request.assert_awaited_once_with(
            True
        )
        # Test from "Auto" selection
        car_mock_data.VEHICLE_DATA["climate_state"]["auto_seat_climate_left"] = True
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: entity_id,
                "option": "Low",
            },
            blocking=True,
        )
        mock_remote_auto_steering_wheel_heat_climate_request.assert_awaited_with(False)

    with patch("teslajsonpy.car.TeslaCar.set_hvac_mode") as mock_set_hvac_mode:
        # Test climate_on check
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: entity_id,
                "option": "Low",
            },
            blocking=True,
        )
        mock_set_hvac_mode.assert_awaited_once_with("on")
