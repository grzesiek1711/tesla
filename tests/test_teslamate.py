"""Tests for TeslaMate MQTT support."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.tesla_extended.teslamate import (
    MAP_CHARGE_STATE,
    MAP_DRIVE_STATE,
    MAP_VEHICLE_CONFIG,
    MAP_VEHICLE_STATE,
    TeslaMate,
    cast_int,
    cast_open,
    cast_optional_str,
)

from .mock_data import car as car_mock_data

pytestmark = pytest.mark.asyncio


async def test_get_car_from_id_skips_stale_vin_mapping() -> None:
    """Test stale VIN mappings do not block active TeslaMate car mappings."""
    active_car = SimpleNamespace(vin=car_mock_data.VIN)
    teslamate = object.__new__(TeslaMate)
    teslamate.cars = {car_mock_data.VIN: active_car}
    teslamate._data = {
        "car_map": {
            "stale-vin": "1",
            car_mock_data.VIN: "1",
        }
    }
    teslamate.async_load = AsyncMock()

    assert await teslamate.get_car_from_id("1") is active_car


async def test_center_display_state_mapping_updates_vehicle_state() -> None:
    """Test center_display_state MQTT topic maps into vehicle_state as an int."""
    # The topic is mapped to the vehicle_state sub-path.
    assert "center_display_state" in MAP_VEHICLE_STATE
    attr, cast = MAP_VEHICLE_STATE["center_display_state"]
    assert attr == "center_display_state"
    # TeslaMate publishes the value as a string payload; it must cast to int.
    assert cast("2") == 2

    car = SimpleNamespace(vin=car_mock_data.VIN, _vehicle_data={})
    TeslaMate.update_car_state(car, "vehicle_state", attr, cast("2"))

    assert car._vehicle_data["vehicle_state"]["center_display_state"] == 2


async def test_cast_helpers() -> None:
    """Test the new cast helpers behave as expected."""
    assert cast_open("true") == 1
    assert cast_open("false") == 0
    assert cast_int("-9") == -9
    assert cast_int("3.0") == 3
    assert cast_optional_str("nil") is None
    assert cast_optional_str("2024.44.25") == "2024.44.25"


async def test_expanded_state_mappings_present() -> None:
    """Test the newly added topics are mapped to the correct API attributes."""
    # Doors and windows map to the Tesla API vehicle_state keys.
    assert MAP_VEHICLE_STATE["driver_front_door_open"] == ("df", cast_open)
    assert MAP_VEHICLE_STATE["passenger_rear_door_open"] == ("pr", cast_open)
    assert MAP_VEHICLE_STATE["driver_front_window_open"] == ("fd_window", cast_open)
    assert MAP_VEHICLE_STATE["passenger_rear_window_open"] == ("rp_window", cast_open)
    # Sunroof and software version.
    assert MAP_VEHICLE_STATE["sun_roof_state"][0] == "sun_roof_state"
    assert MAP_VEHICLE_STATE["version"][0] == "car_version"
    # Drive state power.
    assert MAP_DRIVE_STATE["power"] == ("power", cast_int)
    # Charge state additions.
    assert MAP_CHARGE_STATE["charger_phases"][0] == "charger_phases"
    assert (
        MAP_CHARGE_STATE["scheduled_charging_start_time"][0]
        == "scheduled_charging_start_time"
    )
    # Vehicle config.
    assert MAP_VEHICLE_CONFIG["sun_roof_installed"][0] == "sun_roof_installed"


async def test_update_active_route_parses_json() -> None:
    """Test active_route JSON blob populates drive_state route attributes."""
    teslamate = object.__new__(TeslaMate)
    car = SimpleNamespace(vin=car_mock_data.VIN, _vehicle_data={})

    payload = (
        '{"destination": "Home", "energy_at_arrival": 73, '
        '"miles_to_arrival": 6.485299, "minutes_to_arrival": 23.466667, '
        '"traffic_minutes_delay": 0.0, '
        '"location": {"latitude": 35.278131, "longitude": 29.744801}, '
        '"error": null}'
    )
    teslamate.update_active_route(car, payload)

    drive_state = car._vehicle_data["drive_state"]
    assert drive_state["active_route_destination"] == "Home"
    assert drive_state["active_route_energy_at_arrival"] == 73
    assert drive_state["active_route_miles_to_arrival"] == 6.485299
    assert drive_state["active_route_minutes_to_arrival"] == 23.466667
    assert drive_state["active_route_traffic_minutes_delay"] == 0.0
    assert drive_state["active_route_latitude"] == 35.278131
    assert drive_state["active_route_longitude"] == 29.744801


async def test_update_active_route_clears_on_error() -> None:
    """Test active_route error payload clears route attributes."""
    teslamate = object.__new__(TeslaMate)
    car = SimpleNamespace(
        vin=car_mock_data.VIN,
        _vehicle_data={
            "drive_state": {
                "active_route_destination": "Home",
                "active_route_miles_to_arrival": 6.4,
            }
        },
    )

    teslamate.update_active_route(car, '{"error": "No active route available"}')

    drive_state = car._vehicle_data["drive_state"]
    assert drive_state["active_route_destination"] is None
    assert drive_state["active_route_miles_to_arrival"] is None
    assert drive_state["active_route_latitude"] is None
    assert drive_state["active_route_longitude"] is None


async def test_update_software_update_merges_fields() -> None:
    """Test discrete software update topics merge into a single dict."""
    car = SimpleNamespace(vin=car_mock_data.VIN, _vehicle_data={})

    TeslaMate.update_software_update(car, "version", "2024.44.25")
    TeslaMate.update_software_update(car, "install_perc", 42)

    software_update = car._vehicle_data["vehicle_state"]["software_update"]
    assert software_update["version"] == "2024.44.25"
    assert software_update["install_perc"] == 42
