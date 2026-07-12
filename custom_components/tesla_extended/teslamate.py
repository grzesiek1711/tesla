"""TelsmaMate Module.

This listens to Teslamate MQTT topics, and updates their entites
with the latest data.
"""

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING

from homeassistant.components.mqtt import mqtt_config_entry_enabled
from homeassistant.components.mqtt.models import ReceiveMessage
from homeassistant.components.mqtt.subscription import (
    async_prepare_subscribe_topics,
    async_subscribe_topics,
    async_unsubscribe_topics,
)
from homeassistant.const import UnitOfLength, UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util.unit_conversion import DistanceConverter, SpeedConverter
from teslajsonpy.car import TeslaCar

from .const import TESLAMATE_STORAGE_KEY, TESLAMATE_STORAGE_VERSION

if TYPE_CHECKING:
    from . import TeslaDataUpdateCoordinator

logger = logging.getLogger(__name__)


def is_car_state_charging(car_state: str) -> bool:
    """Check if car_state is charging."""
    return car_state == "charging"


def cast_km_to_miles(km_to_convert: float) -> float:
    """Convert KM to Miles.

    The Tesla API natively returns properties in Miles.
    TeslaMate returns some properties in KMs.
    We need to convert to Miles so the home assistant sensor calculates
    properly.
    """
    km = float(km_to_convert)
    miles = DistanceConverter.convert(km, UnitOfLength.KILOMETERS, UnitOfLength.MILES)

    return miles


def cast_bool(val: str) -> bool:
    """Convert bool string to actual bool."""
    return val.lower() in ["true", "True"]


def cast_trunk_open(val: str) -> int:
    """Convert bool string to trunk/frunk open/close value."""
    return 255 if cast_bool(val) else 0


def cast_speed(speed: int) -> int:
    """Convert KM to Miles.

    The Tesla API natively returns the Speed in Miles M/H.
    TeslaMate returns the Speed in km/h.
    We need to convert to Miles so the speed calculates
    properly.
    """
    speed_km = int(speed)
    speed_miles = SpeedConverter.convert(
        speed_km, UnitOfSpeed.KILOMETERS_PER_HOUR, UnitOfSpeed.MILES_PER_HOUR
    )

    return int(speed_miles)


def cast_open(val: str) -> int:
    """Convert a bool string to an open/closed int (1 open, 0 closed).

    The Tesla API represents door and window states as integers where a
    non-zero value means open. TeslaMate publishes them as bool strings.
    """
    return 1 if cast_bool(val) else 0


def cast_int(val) -> int:
    """Convert a numeric string to an int, tolerating float payloads.

    TeslaMate can publish values such as ``"-9"`` or ``"3.0"``; ``int()``
    alone raises on the latter, so route through ``float`` first.
    """
    return int(float(val))


def cast_optional_float(val) -> float | None:
    """Convert a payload to a float, mapping TeslaMate's "nil"/"None" to None."""
    if val is None:
        return None
    if isinstance(val, str) and val.strip().lower() in ("", "nil", "none", "null"):
        return None
    return float(val)


def cast_optional_str(val) -> str | None:
    """Convert a payload to a str, mapping TeslaMate's "nil"/"None" to None."""
    if val is None:
        return None
    if isinstance(val, str) and val.strip().lower() in ("nil", "none", "null"):
        return None
    return str(val)


MAP_DRIVE_STATE = {
    "latitude": ("latitude", float),
    "longitude": ("longitude", float),
    "shift_state": ("shift_state", str),
    "speed": ("speed", cast_speed),
    "heading": ("heading", int),
    "power": ("power", cast_int),
}

MAP_CLIMATE_STATE = {
    "is_climate_on": ("is_climate_on", cast_bool),
    "inside_temp": ("inside_temp", float),
    "outside_temp": ("outside_temp", float),
    "is_preconditioning": ("is_preconditioning", cast_bool),
}

MAP_VEHICLE_STATE = {
    "tpms_pressure_fl": ("tpms_pressure_fl", float),
    "tpms_pressure_fr": ("tpms_pressure_fr", float),
    "tpms_pressure_rl": ("tpms_pressure_rl", float),
    "tpms_pressure_rr": ("tpms_pressure_rr", float),
    "locked": ("locked", cast_bool),
    "sentry_mode": ("sentry_mode", cast_bool),
    "odometer": ("odometer", cast_km_to_miles),
    "trunk_open": ("rt", cast_trunk_open),
    "frunk_open": ("ft", cast_trunk_open),
    "is_user_present": ("is_user_present", cast_bool),
    "center_display_state": ("center_display_state", int),
    # Individual doors (Tesla API keys: df/dr/pf/pr).
    "driver_front_door_open": ("df", cast_open),
    "driver_rear_door_open": ("dr", cast_open),
    "passenger_front_door_open": ("pf", cast_open),
    "passenger_rear_door_open": ("pr", cast_open),
    # Individual windows (Tesla API keys: *_window).
    "driver_front_window_open": ("fd_window", cast_open),
    "driver_rear_window_open": ("rd_window", cast_open),
    "passenger_front_window_open": ("fp_window", cast_open),
    "passenger_rear_window_open": ("rp_window", cast_open),
    # Sunroof (only present on vehicles with a sunroof).
    "sun_roof_state": ("sun_roof_state", str),
    "sun_roof_percent_open": ("sun_roof_percent_open", cast_int),
    # Software version reported by TeslaMate maps to the API's car_version.
    "version": ("car_version", str),
}

MAP_CHARGE_STATE = {
    "battery_level": ("battery_level", float),
    "rated_battery_range_km": ("battery_range", cast_km_to_miles),
    "est_battery_range_km": ("est_battery_range", cast_km_to_miles),
    "ideal_battery_range_km": ("ideal_battery_range", cast_km_to_miles),
    "usable_battery_level": ("usable_battery_level", float),
    "charge_energy_added": ("charge_energy_added", float),
    "charger_actual_current": ("charger_actual_current", int),
    "charger_power": ("charger_power", int),
    "charger_voltage": ("charger_voltage", int),
    "charger_phases": ("charger_phases", cast_int),
    "time_to_full_charge": ("time_to_full_charge", float),
    "charge_limit_soc": ("charge_limit_soc", int),
    "charge_port_door_open": ("charge_port_door_open", cast_bool),
    "charge_current_request": ("charge_current_request", int),
    "charge_current_request_max": ("charge_current_request_max", int),
    "charging_state": ("charging_state", str),
    "scheduled_charging_start_time": (
        "scheduled_charging_start_time",
        cast_optional_str,
    ),
}

MAP_VEHICLE_CONFIG = {
    "sun_roof_installed": ("sun_roof_installed", cast_bool),
}

# Keys published inside the ``active_route`` JSON blob mapped to the Tesla API
# ``drive_state`` attributes consumed by the arrival/route entities.
MAP_ACTIVE_ROUTE = {
    "destination": "active_route_destination",
    "energy_at_arrival": "active_route_energy_at_arrival",
    "miles_to_arrival": "active_route_miles_to_arrival",
    "minutes_to_arrival": "active_route_minutes_to_arrival",
    "traffic_minutes_delay": "active_route_traffic_minutes_delay",
}

# Keys published inside the ``software_update`` state mapped from the discrete
# TeslaMate topics.
MAP_SOFTWARE_UPDATE = {
    "update_version": ("version", cast_optional_str),
    "download_perc": ("download_perc", cast_int),
    "install_perc": ("install_perc", cast_int),
}


class TeslaMate:
    """TeslaMate Connector.

    Manages connections to MQTT topics exposed by TeslaMate.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        coordinators: dict[str, "TeslaDataUpdateCoordinator"],
        cars: dict[str, TeslaCar],
    ) -> None:
        """Init Class."""
        self.cars = cars
        self.hass = hass
        self.coordinators = coordinators
        self._enabled = False
        self._data: dict = None

        self.watchers = []

        self._sub_state = None
        self._store = Store[dict[str, str]](
            hass, TESLAMATE_STORAGE_VERSION, TESLAMATE_STORAGE_KEY
        )

    async def unload(self):
        """Unload any MQTT watchers."""
        self._enabled = False

        if mqtt_config_entry_enabled(self.hass):
            await self._unsub_mqtt()
        else:
            logger.info("Cannot unsub from TeslaMate as MQTT has not been configured.")

        return True

    async def _unsub_mqtt(self):
        """Unsub from MQTT topics."""
        logger.info("Un-subbing from all MQTT Topics.")
        self._sub_state = async_unsubscribe_topics(self.hass, self._sub_state)
        logger.info("Un-subbed from all MQTT Topics.")

    async def async_load(self) -> None:
        """Load config."""
        if self._data is None:
            if stored := await self._store.async_load():
                self._data = stored

        # If still None, initialise it.
        if self._data is None:
            self._data = {}

    async def _async_save(self) -> None:
        """Save config."""
        await self._store.async_save(self._data)

    async def set_car_id(self, vin, teslamate_id):
        """Set the TeslaMate Car ID."""
        logger.debug("Setting car ID. VIN:%s TeslamateID: %s", vin, teslamate_id)
        await self.async_load()

        if "car_map" not in self._data:
            self._data["car_map"] = {}

        self._data["car_map"][vin] = teslamate_id

        await self._async_save()
        logger.debug("Successfully set car ID. Latest Car data")
        logger.debug(self._data)

    async def get_car_id(self, vin) -> str | None:
        """Get the TeslaMate Car ID."""
        await self.async_load()

        if "car_map" not in self._data:
            self._data["car_map"] = {}

        result = self._data["car_map"].get(vin)

        logger.debug("Got car ID. VIN:%s TeslamateID: %s", vin, result)

        return result

    async def get_car_from_id(self, teslamate_id: str) -> TeslaCar | None:
        """Get the TeslaCar from the TeslaMateID."""
        logger.debug("Getting TeslaCar for teslaMateID:%s", teslamate_id)

        await self.async_load()

        car_map = self._data.get("car_map", {})
        for vin, tm_id in car_map.items():
            if tm_id != teslamate_id:
                continue

            if car := self.cars.get(vin):
                return car

            logger.debug(
                "TeslaMate_id %s is mapped to stale VIN %s that is not loaded",
                teslamate_id,
                vin,
            )

        return None

    async def enable(self, enable=True):
        """Start Listening to MQTT topics."""

        if enable is False:
            return await self.unload()

        self._enabled = True
        return await self.watch_cars()

    async def watch_cars(self):
        """Start listening to MQTT for updates."""

        # Do nothing if TeslaMate or MQTT is not enabled
        if self._enabled is False:
            logger.info("Can't watch cars. TeslaMate is not enabled.")
            return None
        if not mqtt_config_entry_enabled(self.hass):
            logger.warning("Cannot enable TeslaMate as MQTT has not been configured.")
            return None

        logger.info("Setting up MQTT subs for TeslaMate")

        # Unsubscribe from all topics before creating new ones
        await self._unsub_mqtt()

        topics = {}

        # Generate topics for each car
        for vin in self.cars:
            car = self.cars[vin]
            teslamate_id = await self.get_car_id(vin=vin)

            if teslamate_id is not None:
                await self._get_car_topic(
                    car=car, teslamate_id=teslamate_id, topics=topics
                )

        # Subscribe to all topics
        self._sub_state = async_prepare_subscribe_topics(
            self.hass, self._sub_state, topics
        )
        await async_subscribe_topics(self.hass, self._sub_state)
        logger.debug("Subscribed to MQTT Topics")

        logger.debug("Completed watch_cars")

    async def _get_car_topic(self, car: TeslaCar, teslamate_id: str, topics: dict):
        """Create topics for MQTT subscription and add them to the topics dictionary."""
        logger.debug(
            "Setting up MQTT Sub for VIN:%s TelsaMateID:%s", car.vin, teslamate_id
        )

        def msg_recieved(msg: ReceiveMessage):
            return asyncio.run_coroutine_threadsafe(
                self.async_handle_new_data(msg), self.hass.loop
            ).result()

        sub_id = f"teslamate_{teslamate_id}"
        mqtt_topic = f"teslamate/cars/{teslamate_id}/#"
        logger.debug("MQTT Topic: %s", mqtt_topic)

        topics[sub_id] = {
            "topic": mqtt_topic,
            "msg_callback": msg_recieved,
            "qos": 0,
        }

        logger.info("Created mqtt Topic for: %s", mqtt_topic)

    async def async_handle_new_data(self, msg: ReceiveMessage):
        """Update Car Data from MQTT msg."""
        logger.debug("MQTT Topic Recieved: %s", msg.topic)

        mqtt_attr = msg.topic.split("/")[-1]
        teslamate_id = msg.topic.split("/")[2]
        car = await self.get_car_from_id(teslamate_id)

        if car is None:
            logger.debug("TeslaMate_id %s not found in config", teslamate_id)
            return

        coordinator = self.coordinators[car.vin]

        logger.debug(
            "Got %s from MQTT for VIN:%s | TeslsMateID:%s",
            mqtt_attr,
            car.vin,
            teslamate_id,
        )

        if mqtt_attr in MAP_DRIVE_STATE:
            attr, cast = MAP_DRIVE_STATE[mqtt_attr]
            self.update_car_state(car, "drive_state", attr, cast(msg.payload))

        elif mqtt_attr in MAP_VEHICLE_STATE:
            attr, cast = MAP_VEHICLE_STATE[mqtt_attr]
            self.update_car_state(car, "vehicle_state", attr, cast(msg.payload))

        elif mqtt_attr in MAP_CLIMATE_STATE:
            attr, cast = MAP_CLIMATE_STATE[mqtt_attr]
            self.update_car_state(car, "climate_state", attr, cast(msg.payload))

        elif mqtt_attr in MAP_CHARGE_STATE:
            attr, cast = MAP_CHARGE_STATE[mqtt_attr]
            self.update_car_state(car, "charge_state", attr, cast(msg.payload))

        elif mqtt_attr in MAP_VEHICLE_CONFIG:
            attr, cast = MAP_VEHICLE_CONFIG[mqtt_attr]
            self.update_car_state(car, "vehicle_config", attr, cast(msg.payload))

        elif mqtt_attr in MAP_SOFTWARE_UPDATE:
            attr, cast = MAP_SOFTWARE_UPDATE[mqtt_attr]
            self.update_software_update(car, attr, cast(msg.payload))

        elif mqtt_attr == "active_route":
            self.update_active_route(car, msg.payload)

        elif mqtt_attr == "state":
            state = msg.payload
            self.update_car_state(car, None, "state", state)

        else:
            # Nothing matched. Return without updating listeners.
            return

        coordinator.last_update_time = round(time.time())
        coordinator.assumed_state = False
        coordinator.async_update_listeners_debounced()

    def update_charging_state(self, car: TeslaCar, val: str):
        """Update charging state."""
        self.update_car_state(car, "charge_state", "charging_state", val)

    @staticmethod
    def update_software_update(car: TeslaCar, attr: str, value) -> None:
        """Merge a value into the nested ``software_update`` dict.

        TeslaMate publishes update details across several topics
        (``update_version``, ``download_perc``, ``install_perc``) while the
        Tesla API groups them into a single ``software_update`` object inside
        ``vehicle_state``. Merge rather than overwrite so partial updates from
        individual topics don't clobber previously received fields.
        """
        # pylint: disable=protected-access
        vehicle_state = car._vehicle_data.setdefault("vehicle_state", {})
        software_update = vehicle_state.setdefault("software_update", {})
        software_update[attr] = value
        logger.debug(
            "Updating software_update '%s' to '%s' for VIN:%s", attr, value, car.vin
        )

    def update_active_route(self, car: TeslaCar, payload: str) -> None:
        """Parse the ``active_route`` JSON blob into drive_state attributes.

        The blob contains navigation details (destination, distance, ETA and
        destination coordinates). When no route is active TeslaMate publishes
        ``{"error": "No active route available"}``; in that case all route
        attributes are cleared to ``None``.
        """
        try:
            data = json.loads(payload)
        except (ValueError, TypeError):
            logger.debug("Could not parse active_route payload for VIN:%s", car.vin)
            return

        if not isinstance(data, dict):
            return

        if data.get("error"):
            # No active route: clear all route attributes.
            for attr in MAP_ACTIVE_ROUTE.values():
                self.update_car_state(car, "drive_state", attr, None)
            self.update_car_state(car, "drive_state", "active_route_latitude", None)
            self.update_car_state(car, "drive_state", "active_route_longitude", None)
            return

        for key, attr in MAP_ACTIVE_ROUTE.items():
            if key in data:
                self.update_car_state(car, "drive_state", attr, data[key])

        location = data.get("location") or {}
        if "latitude" in location:
            self.update_car_state(
                car, "drive_state", "active_route_latitude", location["latitude"]
            )
        if "longitude" in location:
            self.update_car_state(
                car, "drive_state", "active_route_longitude", location["longitude"]
            )

    @staticmethod
    def update_car_state(car: TeslaCar, sub_path: str, attr: str, value):
        """Update state safely."""
        # pylint: disable=protected-access

        if sub_path is not None:
            logger.debug(
                "Updating state '%s' to value '%s' in sub_path '%s' for VIN:%s",
                attr,
                value,
                sub_path,
                car.vin,
            )

            if sub_path not in car._vehicle_data:
                car._vehicle_data[sub_path] = {}

            state = car._vehicle_data[sub_path]
            state[attr] = value
        else:
            logger.debug(
                "Updating state '%s' to value '%s' in root for VIN:%s",
                attr,
                value,
                car.vin,
            )
            state = car._car
            state[attr] = value
