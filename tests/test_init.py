"""Tests for the Tesla integration setup and device removal."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
import pytest
from pytest_homeassistant_custom_component.common import async_capture_events
from teslajsonpy.car import TeslaCar

from custom_components.tesla_extended import (
    TeslaDataUpdateCoordinator,
    async_remove_config_entry_device,
)
from custom_components.tesla_extended.base import device_identifier
from custom_components.tesla_extended.const import (
    CONF_SENTRY_SCAN_INTERVAL,
    DOMAIN,
    EVENT_SENTRY_DISPLAY,
    MIN_SCAN_INTERVAL,
)

from .common import setup_platform
from .const import TEST_USERNAME
from .mock_data import car as car_mock_data

# Mock data ids used across the helpers below.
CAR_ID = 12345678901234567  # car_mock_data.VEHICLE["id"]


def _make_car() -> TeslaCar:
    """Return a TeslaCar built from the shared mock data."""
    return TeslaCar(
        car_mock_data.VEHICLE,
        MagicMock(),
        car_mock_data.VEHICLE_DATA,
    )


def _device_entry(*identifiers) -> dr.DeviceEntry:
    """Build a minimal DeviceEntry-like object exposing only identifiers."""
    entry = MagicMock(spec=dr.DeviceEntry)
    entry.identifiers = set(identifiers)
    return entry


def _config_entry(entry_id: str = "test_entry") -> ConfigEntry:
    """Build a minimal ConfigEntry-like object exposing only entry_id."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = entry_id
    entry.options = {}
    return entry


def test_device_identifier_discriminates_by_type() -> None:
    """device_identifier uses car.id for cars."""
    car = _make_car()

    assert device_identifier(car) == (DOMAIN, car.id)


def _entry_data():
    """Return an entry_data dict shaped like hass.data[DOMAIN][entry_id]."""
    return {
        "cars": {car_mock_data.VIN: _make_car()},
    }


def _hass_with_entry(entry_id: str = "test_entry"):
    """Return a MagicMock hass whose data holds a loaded entry."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {entry_id: _entry_data()}}
    return hass


async def test_remove_protects_live_car() -> None:
    """A device matching a live car must not be removable."""
    hass = _hass_with_entry()
    device = _device_entry((DOMAIN, CAR_ID))
    assert (
        await async_remove_config_entry_device(hass, _config_entry(), device) is False
    )


async def test_remove_allows_orphan_device() -> None:
    """A device no longer provided by the integration is removable."""
    hass = _hass_with_entry()
    device = _device_entry((DOMAIN, 99999999999))
    assert await async_remove_config_entry_device(hass, _config_entry(), device) is True


async def test_remove_refuses_when_entry_not_loaded() -> None:
    """Removal must be refused while the config entry is not loaded."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    device = _device_entry((DOMAIN, 99999999999))
    assert (
        await async_remove_config_entry_device(hass, _config_entry(), device) is False
    )

    # Also when DOMAIN itself is absent from hass.data.
    hass.data = {}
    assert (
        await async_remove_config_entry_device(hass, _config_entry(), device) is False
    )


async def test_remove_handles_id_coercion() -> None:
    """Identifier comparison is exact: a string id does not match an int id.

    The integration registers integer ids, so a device entry holding the
    string form is treated as an orphan (removable) rather than silently
    matching a live device.
    """
    hass = _hass_with_entry()
    device = _device_entry((DOMAIN, str(CAR_ID)))
    assert await async_remove_config_entry_device(hass, _config_entry(), device) is True


async def test_remove_protects_device_merged_with_foreign_domain() -> None:
    """A device with our live id plus a foreign-domain id stays protected.

    Device entries can carry identifiers from multiple integrations. As long
    as one of our live identifiers is present, the device must not be removed.
    """
    hass = _hass_with_entry()
    device = _device_entry((DOMAIN, CAR_ID), ("other_domain", "abc123"))
    assert (
        await async_remove_config_entry_device(hass, _config_entry(), device) is False
    )


async def test_remove_orphan_with_only_foreign_domain() -> None:
    """A device carrying only foreign-domain identifiers is removable."""
    hass = _hass_with_entry()
    device = _device_entry(("other_domain", "abc123"))
    assert await async_remove_config_entry_device(hass, _config_entry(), device) is True


@pytest.mark.parametrize("platform", ["binary_sensor"])
async def test_remove_with_real_loaded_entry(
    hass: HomeAssistant, platform: str
) -> None:
    """Integration test using the real setup fixture and device registry.

    Verifies the live car device created by setup is protected, while an
    orphaned device under the same entry is removable.
    """
    mock_entry, _ = await setup_platform(hass, platform)

    device_registry = dr.async_get(hass)

    # The car must be registered and protected.
    car_device = device_registry.async_get_device(identifiers={(DOMAIN, CAR_ID)})
    assert car_device is not None
    assert await async_remove_config_entry_device(hass, mock_entry, car_device) is False

    # Every device the platform actually registered for this entry is live and
    # must be protected. Enumerate the registry rather than assuming a fixed set.
    entry_devices = dr.async_entries_for_config_entry(
        device_registry, mock_entry.entry_id
    )
    assert entry_devices
    for device in entry_devices:
        assert await async_remove_config_entry_device(hass, mock_entry, device) is False

    # A stale device under the same entry (e.g. a car removed from the
    # account) is no longer provided and must be removable.
    orphan = device_registry.async_get_or_create(
        config_entry_id=mock_entry.entry_id,
        identifiers={(DOMAIN, 99999999999)},
    )
    assert await async_remove_config_entry_device(hass, mock_entry, orphan) is True


def test_config_entry_title_is_username() -> None:
    """Sanity check that the shared fixture username constant is wired."""
    assert TEST_USERNAME == "test-username"


def _controller_with_update_error(error: Exception):
    """Return a minimal controller for coordinator update tests."""
    controller = MagicMock()
    controller.is_token_refreshed.return_value = False
    controller.update = AsyncMock(side_effect=error)
    controller.get_last_update_time.return_value = datetime.now().timestamp()
    controller.get_last_wake_up_time.return_value = 0
    controller.is_car_online.return_value = True
    controller.update_interval = 660
    return controller


async def test_update_vehicles_key_error_reloads_entry(hass: HomeAssistant) -> None:
    """A new vehicle appearing during product refresh reloads the entry."""
    config_entry = _config_entry()
    controller = _controller_with_update_error(KeyError("VIN2"))
    hass.config_entries.async_reload = AsyncMock()
    coordinator = TeslaDataUpdateCoordinator(
        hass,
        config_entry=config_entry,
        controller=controller,
        reload_lock=asyncio.Lock(),
        update_vehicles=True,
    )

    assert await coordinator._async_update_data() is None

    controller.update.assert_awaited_once_with(
        vins=set(), update_vehicles=True, force=False
    )
    hass.config_entries.async_reload.assert_awaited_once_with("test_entry")


async def test_vehicle_key_error_is_not_swallowed(hass: HomeAssistant) -> None:
    """Vehicle-specific KeyErrors still surface as programming/data errors."""
    config_entry = _config_entry()
    controller = _controller_with_update_error(KeyError("VIN2"))
    hass.config_entries.async_reload = AsyncMock()
    coordinator = TeslaDataUpdateCoordinator(
        hass,
        config_entry=config_entry,
        controller=controller,
        reload_lock=asyncio.Lock(),
        vin=car_mock_data.VIN,
    )

    with pytest.raises(KeyError):
        await coordinator._async_update_data()

    hass.config_entries.async_reload.assert_not_awaited()


# --- Sentry polling interval + sentry-display event ---------------------------


def _sentry_car(*, sentry: bool, display, available: bool = True) -> MagicMock:
    """Return a lightweight car stub for coordinator tests."""
    car = MagicMock()
    car.vin = car_mock_data.VIN
    car.display_name = "My Model S"
    car.sentry_mode_available = available
    car.sentry_mode = sentry
    car.center_display_state = display
    return car


def _interval_controller() -> MagicMock:
    """Return a controller mock that tracks per-VIN interval overrides."""
    controller = MagicMock()
    controller.is_token_refreshed.return_value = False
    controller.update = AsyncMock(return_value={})
    controller.get_last_update_time.return_value = datetime.now().timestamp()
    controller.get_last_wake_up_time.return_value = 0
    controller.is_car_online.return_value = True
    controller.update_interval = 660
    vin_intervals: dict = {}

    def _get(vin=None, car_id=None):
        return vin_intervals.get(vin, controller.update_interval)

    def _set(vin=None, car_id=None, value=None):
        if value is None:
            vin_intervals.pop(vin, None)
        else:
            vin_intervals[vin] = value

    controller.get_update_interval_vin.side_effect = _get
    controller.set_update_interval_vin.side_effect = _set
    return controller


def _make_coordinator(hass, car, controller, options):
    entry = _config_entry()
    entry.options = options
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"cars": {car.vin: car}}
    return TeslaDataUpdateCoordinator(
        hass,
        config_entry=entry,
        controller=controller,
        reload_lock=asyncio.Lock(),
        vin=car.vin,
    )


async def test_sentry_interval_applied_and_cleared(hass: HomeAssistant) -> None:
    """Sentry mode applies a per-VIN interval + short heartbeat, then clears it."""
    car = _sentry_car(sentry=True, display=0)
    controller = _interval_controller()
    options = {CONF_SCAN_INTERVAL: 660, CONF_SENTRY_SCAN_INTERVAL: 10}
    coordinator = _make_coordinator(hass, car, controller, options)

    # Sentry active: per-VIN override reflects the sentry interval (so the
    # polling-interval sensor updates) and the heartbeat shortens; caller forces.
    assert coordinator._async_apply_scan_interval() is True
    assert controller.get_update_interval_vin(vin=car.vin) == 10
    assert coordinator.update_interval == timedelta(seconds=10)

    # Sentry cleared: override we set is removed and heartbeat returns to normal.
    car.sentry_mode = False
    assert coordinator._async_apply_scan_interval() is False
    assert controller.get_update_interval_vin(vin=car.vin) == 660
    assert coordinator.update_interval == timedelta(seconds=MIN_SCAN_INTERVAL)


async def test_manual_interval_override_preserved(hass: HomeAssistant) -> None:
    """A manual set_update_interval override is not clobbered when sentry is off."""
    car = _sentry_car(sentry=False, display=0)
    controller = _interval_controller()
    options = {CONF_SCAN_INTERVAL: 660, CONF_SENTRY_SCAN_INTERVAL: 10}
    coordinator = _make_coordinator(hass, car, controller, options)

    controller.set_update_interval_vin(vin=car.vin, value=120)
    assert coordinator._async_apply_scan_interval() is False
    assert controller.get_update_interval_vin(vin=car.vin) == 120


async def test_sentry_interval_noop_when_equal(hass: HomeAssistant) -> None:
    """No sentry override when the sentry interval equals the normal interval."""
    car = _sentry_car(sentry=True, display=0)
    controller = _interval_controller()
    options = {CONF_SCAN_INTERVAL: 660, CONF_SENTRY_SCAN_INTERVAL: 660}
    coordinator = _make_coordinator(hass, car, controller, options)

    assert coordinator._async_apply_scan_interval() is False
    assert controller.get_update_interval_vin(vin=car.vin) == 660


async def test_sentry_display_event_fires_once_and_rearms(
    hass: HomeAssistant,
) -> None:
    """Event fires once on entering sentry+display==7 and re-arms after clearing."""
    car = _sentry_car(sentry=True, display=7)
    controller = _interval_controller()
    coordinator = _make_coordinator(hass, car, controller, {})
    events = async_capture_events(hass, EVENT_SENTRY_DISPLAY)

    coordinator._fire_sentry_display_event()
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data == {"name": car.display_name}

    # Condition still holds -> no re-fire.
    coordinator._fire_sentry_display_event()
    await hass.async_block_till_done()
    assert len(events) == 1

    # Condition clears then holds again -> fires a second time.
    car.center_display_state = 0
    coordinator._fire_sentry_display_event()
    car.center_display_state = 7
    coordinator._fire_sentry_display_event()
    await hass.async_block_till_done()
    assert len(events) == 2


async def test_sentry_interval_active_without_sentry_available(
    hass: HomeAssistant,
) -> None:
    """Sentry interval activates on sentry_mode alone (TeslaMate MQTT case).

    TeslaMate MQTT publishes ``sentry_mode`` but not ``sentry_mode_available``,
    so detection must not require the latter.
    """
    car = _sentry_car(sentry=True, display=0, available=False)
    controller = _interval_controller()
    options = {CONF_SCAN_INTERVAL: 660, CONF_SENTRY_SCAN_INTERVAL: 10}
    coordinator = _make_coordinator(hass, car, controller, options)

    assert coordinator._async_apply_scan_interval() is True
    assert controller.get_update_interval_vin(vin=car.vin) == 10


async def test_sentry_display_event_requires_sentry_on(hass: HomeAssistant) -> None:
    """The event does not fire when the display is 7 but sentry mode is off."""
    car = _sentry_car(sentry=False, display=7)
    controller = _interval_controller()
    coordinator = _make_coordinator(hass, car, controller, {})
    events = async_capture_events(hass, EVENT_SENTRY_DISPLAY)

    coordinator._fire_sentry_display_event()
    await hass.async_block_till_done()
    assert len(events) == 0
