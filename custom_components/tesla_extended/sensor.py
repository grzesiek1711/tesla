"""Support for the Tesla sensors."""

from datetime import datetime, timedelta
from typing import Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.util import dt
from homeassistant.util.unit_conversion import DistanceConverter
from teslajsonpy.car import TeslaCar

from . import TeslaDataUpdateCoordinator
from .base import TeslaCarEntity
from .const import DISTANCE_UNITS_KM_HR, DOMAIN

TPMS_SENSORS = {
    "TPMS front left": "tpms_pressure_fl",
    "TPMS front right": "tpms_pressure_fr",
    "TPMS rear left": "tpms_pressure_rl",
    "TPMS rear right": "tpms_pressure_rr",
}

TPMS_SENSOR_ATTR = {
    "TPMS front left": "tpms_last_seen_pressure_time_fl",
    "TPMS front right": "tpms_last_seen_pressure_time_fr",
    "TPMS rear left": "tpms_last_seen_pressure_time_rl",
    "TPMS rear right": "tpms_last_seen_pressure_time_rr",
}

# Seat name -> seat_id as used by teslajsonpy get_seat_heater_status().
SEAT_ID_MAP = {
    "left": 0,
    "right": 1,
    "rear left": 2,
    "rear center": 4,
    "rear right": 5,
    "third row left": 6,
    "third row right": 7,
}


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the Tesla Sensors by config_entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators = entry_data["coordinators"]
    cars = entry_data["cars"]
    entities = []

    for vin, car in cars.items():
        coordinator = coordinators[vin]
        entities.append(TeslaCarBattery(car, coordinator))
        entities.append(TeslaCarChargerRate(car, coordinator))
        entities.append(TeslaCarChargerEnergy(car, coordinator))
        entities.append(TeslaCarChargerPower(car, coordinator))
        entities.append(TeslaCarOdometer(car, coordinator))
        entities.append(TeslaCarShiftState(car, coordinator))
        entities.append(TeslaCarCenterDisplayState(car, coordinator))
        entities.append(TeslaCarRange(car, coordinator))
        entities.append(TeslaCarTemp(car, coordinator))
        entities.append(TeslaCarTemp(car, coordinator, inside=True))
        entities.append(TeslaCarTimeChargeComplete(car, coordinator))
        for tpms_sensor in TPMS_SENSORS:
            entities.append(TeslaCarTpmsPressureSensor(car, coordinator, tpms_sensor))
        entities.append(TeslaCarArrivalTime(car, coordinator))
        entities.append(TeslaCarDistanceToArrival(car, coordinator))
        entities.append(TeslaCarDataUpdateTime(car, coordinator))
        entities.append(TeslaCarPollingInterval(car, coordinator))
        # Read-only sensors converted from former command entities plus
        # additional data exposed by the teslajsonpy fork. None of these send
        # commands to the vehicle.
        entities.append(TeslaCarChargeLimit(car, coordinator))
        entities.append(TeslaCarChargingAmps(car, coordinator))
        entities.append(TeslaCarChargerCurrent(car, coordinator))
        entities.append(TeslaCarChargerVoltage(car, coordinator))
        entities.append(TeslaCarDriverTempSetting(car, coordinator))
        entities.append(TeslaCarPassengerTempSetting(car, coordinator))
        entities.append(TeslaCarCabinOverheatProtection(car, coordinator))
        entities.append(TeslaCarClimateKeeperMode(car, coordinator))
        entities.append(TeslaCarHeatedSteeringWheelLevel(car, coordinator))
        entities.append(TeslaCarSpeed(car, coordinator))
        entities.append(TeslaCarPower(car, coordinator))
        entities.append(TeslaCarHeading(car, coordinator))
        for seat_name in SEAT_ID_MAP:
            if "rear" in seat_name and not car.rear_seat_heaters:
                continue
            if "third" in seat_name and (
                car.third_row_seats == "None" or car.third_row_seats is None
            ):
                continue
            entities.append(TeslaCarSeatHeater(car, coordinator, seat_name))

    async_add_entities(entities, update_before_add=True)


class TeslaCarBattery(TeslaCarEntity, SensorEntity):
    """Representation of the Tesla car battery sensor."""

    type = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:battery"

    @staticmethod
    def has_battery() -> bool:
        """Return whether the device has a battery."""
        return True

    @property
    def native_value(self) -> int:
        """Return battery level."""
        # usable_battery_level matches the Tesla app and car display
        return self._car.usable_battery_level

    @property
    def icon(self):
        """Return icon for the battery."""
        charging = self._car.charging_state == "Charging"

        return icon_for_battery_level(
            battery_level=self.native_value, charging=charging
        )

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        return {
            "raw_soc": self._car.battery_level,
        }


class TeslaCarChargerEnergy(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car energy added sensor."""

    type = "energy added"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self) -> float:
        """Return the charge energy added."""
        # The car will reset this to 0 automatically when charger
        # goes from disconnected to connected
        return self._car.charge_energy_added

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        if self._car.charge_miles_added_rated:
            added_range = self._car.charge_miles_added_rated
        elif (
            self._car.charge_miles_added_ideal
            and self._car.gui_range_display == "Ideal"
        ):
            added_range = self._car.charge_miles_added_ideal
        else:
            added_range = 0

        if self._car.gui_distance_units == DISTANCE_UNITS_KM_HR:
            added_range = DistanceConverter.convert(
                added_range, UnitOfLength.MILES, UnitOfLength.KILOMETERS
            )

        return {
            "added_range": round(added_range, 2),
        }


class TeslaCarChargerPower(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car charger power."""

    type = "charger power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT

    @property
    def native_value(self) -> float:
        """Return the charger power."""
        return (
            float(self._car.charger_power)
            if self._car.charger_power is not None
            else self._car.charger_power
        )

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        car = self._car
        return {
            "charger_amps_request": car.charge_current_request,
            "charger_amps_actual": car.charger_actual_current,
            "charger_volts": car.charger_voltage,
            "charger_phases": car.charger_phases,
        }


class TeslaCarChargerRate(TeslaCarEntity, SensorEntity):
    """Representation of the Tesla car charging rate."""

    type = "charging rate"
    _attr_device_class = SensorDeviceClass.SPEED
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfSpeed.MILES_PER_HOUR
    _attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> float:
        """Return charge rate."""
        charge_rate = self._car.charge_rate

        if charge_rate is None:
            return charge_rate

        return round(charge_rate, 2)

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        return {
            "time_left": self._car.time_to_full_charge,
        }


class TeslaCarOdometer(TeslaCarEntity, SensorEntity):
    """Representation of the Tesla car odometer sensor."""

    type = "odometer"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfLength.MILES
    _attr_icon = "mdi:counter"

    @property
    def native_value(self) -> float:
        """Return the odometer."""
        odometer_value = self._car.odometer

        if odometer_value is None:
            return None

        return round(odometer_value, 2)


class TeslaCarShiftState(TeslaCarEntity, SensorEntity):
    """Representation of the Tesla car Shift State sensor."""

    type = "shift state"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:car-shift-pattern"

    @property
    def native_value(self) -> float:
        """Return the shift state."""
        value = self._car.shift_state

        # When car is parked and off, Tesla API reports shift_state None
        if value is None or value == "":
            return "P"

        return value

    @property
    def options(self) -> float:
        """Return the values for the ENUM."""
        values = ["P", "D", "R", "N"]

        return values

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""

        return {
            "raw_state": self._car.shift_state,
        }


class TeslaCarCenterDisplayState(TeslaCarEntity, SensorEntity):
    """Representation of the Tesla car center display state sensor."""

    type = "center display state"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:monitor"

    @property
    def native_value(self) -> Optional[int]:
        """Return the center display state."""
        value = self._car.center_display_state
        if value is None:
            return None
        return int(value)


class TeslaCarRange(TeslaCarEntity, SensorEntity):
    """Representation of the Tesla car range sensor."""

    type = "range"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfLength.MILES
    _attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> float:
        """Return range."""
        car = self._car
        range_value = car.battery_range

        if car.gui_range_display == "Ideal":
            range_value = car.ideal_battery_range

        if range_value is None:
            return None

        return round(range_value, 2)

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        # pylint: disable=protected-access
        est_battery_range = self._car._vehicle_data.get("charge_state", {}).get(
            "est_battery_range"
        )
        if est_battery_range is not None:
            est_battery_range_km = DistanceConverter.convert(
                est_battery_range, UnitOfLength.MILES, UnitOfLength.KILOMETERS
            )
        else:
            est_battery_range_km = None

        return {
            "est_battery_range_miles": est_battery_range,
            "est_battery_range_km": est_battery_range_km,
        }


class TeslaCarTemp(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car temp sensor."""

    type = "temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer"

    def __init__(
        self,
        car: TeslaCar,
        coordinator: TeslaDataUpdateCoordinator,
        *,
        inside=False,
    ) -> None:
        """Initialize temp entity."""
        self.inside = inside
        if inside is True:
            self.type += " (inside)"
        else:
            self.type += " (outside)"
        super().__init__(car, coordinator)

    @property
    def native_value(self) -> float:
        """Return car temperature."""
        if self.inside is True:
            return self._car.inside_temp
        return self._car.outside_temp


class TeslaCarTimeChargeComplete(TeslaCarEntity, SensorEntity):
    """Representation of the Tesla car time charge complete."""

    type = "time charge complete"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:timer-plus"
    _value: Optional[datetime] = None
    _last_known_value: Optional[int] = None
    _last_update_time: Optional[datetime] = None

    @property
    def native_value(self) -> Optional[datetime]:
        """Return time charge complete."""
        if self._car.time_to_full_charge is None:
            charge_hours = 0
        else:
            charge_hours = float(self._car.time_to_full_charge)

        if self._last_known_value != charge_hours:
            self._last_known_value = charge_hours
            self._last_update_time = dt.utcnow()

        if self._car.charging_state == "Charging" and charge_hours > 0:
            new_value = (
                dt.utcnow()
                + timedelta(hours=charge_hours)
                - (dt.utcnow() - self._last_update_time)
            )
            if (
                self._value is None
                or abs((new_value - self._value).total_seconds()) >= 60
            ):
                self._value = new_value
        if self._car.charging_state in ["Charging", "Complete"]:
            return self._value
        return None

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        # pylint: disable=protected-access
        minutes_to_full_charge = self._car._vehicle_data.get("charge_state", {}).get(
            "minutes_to_full_charge"
        )

        return {
            "minutes_to_full_charge": minutes_to_full_charge,
        }


class TeslaCarTpmsPressureSensor(TeslaCarEntity, SensorEntity):
    """Representation of the Tesla car TPMS Pressure sensor."""

    _attr_device_class = SensorDeviceClass.PRESSURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPressure.BAR
    _attr_suggested_unit_of_measurement = UnitOfPressure.PSI
    _attr_icon = "mdi:gauge-full"

    def __init__(
        self,
        car: TeslaCar,
        coordinator: TeslaDataUpdateCoordinator,
        tpms_sensor: str,
    ) -> None:
        """Initialize TPMS Pressure sensor."""
        self._tpms_sensor = tpms_sensor
        self.type = tpms_sensor
        super().__init__(car, coordinator)

    @property
    def native_value(self) -> float:
        """Return TPMS Pressure."""
        value = getattr(self._car, TPMS_SENSORS.get(self._tpms_sensor))
        if value is not None:
            value = round(value, 2)
        return value

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        # pylint: disable=protected-access
        timestamp = self._car._vehicle_data.get("vehicle_state", {}).get(
            TPMS_SENSOR_ATTR.get(self._tpms_sensor)
        )

        return {
            "tpms_last_seen_pressure_timestamp": timestamp,
        }


class TeslaCarArrivalTime(TeslaCarEntity, SensorEntity):
    """Representation of the Tesla car route arrival time."""

    type = "arrival time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:timer-sand"
    _datetime_value: Optional[datetime] = None
    _last_known_value: Optional[int] = None
    _last_update_time: Optional[datetime] = None

    @property
    def native_value(self) -> Optional[datetime]:
        """Return route arrival time."""
        if self._car.active_route_minutes_to_arrival is None:
            return self._datetime_value
        min_duration = round(float(self._car.active_route_minutes_to_arrival), 2)

        utcnow = dt.utcnow()
        if self._last_known_value != min_duration:
            self._last_known_value = min_duration
            self._last_update_time = utcnow

        new_value = (
            utcnow + timedelta(minutes=min_duration) - (utcnow - self._last_update_time)
        )
        if (
            self._datetime_value is None
            or abs((new_value - self._datetime_value).total_seconds()) >= 60
        ):
            self._datetime_value = new_value
        return self._datetime_value

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        car = self._car
        if car.active_route_traffic_minutes_delay is None:
            minutes = None
        else:
            minutes = round(car.active_route_traffic_minutes_delay, 1)

        return {
            "Energy at arrival": car.active_route_energy_at_arrival,
            "Minutes traffic delay": minutes,
            "Destination": car.active_route_destination,
            "Minutes to arrival": (
                None
                if car.active_route_minutes_to_arrival is None
                else round(float(car.active_route_minutes_to_arrival), 2)
            ),
        }


class TeslaCarDistanceToArrival(TeslaCarEntity, SensorEntity):
    """Representation of the Tesla distance to arrival."""

    type = "distance to arrival"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfLength.MILES
    _attr_icon = "mdi:map-marker-distance"

    @property
    def native_value(self) -> float:
        """Return the distance to arrival."""
        if self._car.active_route_miles_to_arrival is None:
            return None
        return round(self._car.active_route_miles_to_arrival, 2)


class TeslaCarDataUpdateTime(TeslaCarEntity, SensorEntity):
    """Representation of the TeslajsonPy Last Data Update time."""

    type = "data last update time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:timer"

    @property
    def native_value(self) -> datetime:
        """Return the last data update time."""
        last_time = self.coordinator.controller.get_last_update_time(vin=self._car.vin)
        if not isinstance(last_time, datetime):
            date_obj = datetime.fromtimestamp(last_time, dt.UTC)
        else:
            date_obj = last_time.replace(tzinfo=dt.UTC)
        return date_obj


class TeslaCarPollingInterval(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car polling interval."""

    type = "polling interval"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:timer-sync"

    @property
    def native_value(self) -> int:
        """Return the update time interval."""
        return self.coordinator.controller.get_update_interval_vin(vin=self._car.vin)


class TeslaCarChargeLimit(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car charge limit sensor.

    Read-only replacement for the removed charge limit number entity.
    """

    type = "charge limit"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:ev-station"

    @property
    def native_value(self) -> int:
        """Return charge limit."""
        return self._car.charge_limit_soc


class TeslaCarChargingAmps(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car charging amps sensor.

    Read-only replacement for the removed charging amps number entity.
    """

    type = "charging amps"
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_icon = "mdi:ev-station"

    @property
    def native_value(self) -> int:
        """Return requested charging amps."""
        return self._car.charge_current_request


class TeslaCarChargerCurrent(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car actual charger current sensor."""

    type = "charger current"
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:current-ac"

    @property
    def native_value(self) -> int:
        """Return actual charger current."""
        return self._car.charger_actual_current


class TeslaCarChargerVoltage(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car charger voltage sensor."""

    type = "charger voltage"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:sine-wave"

    @property
    def native_value(self) -> int:
        """Return charger voltage."""
        return self._car.charger_voltage


class TeslaCarDriverTempSetting(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car driver temperature setting sensor.

    Read-only replacement for the target temperature of the removed climate
    entity.
    """

    type = "driver temperature setting"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermostat"

    @property
    def native_value(self) -> float:
        """Return driver temperature setting."""
        return self._car.driver_temp_setting


class TeslaCarPassengerTempSetting(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car passenger temperature setting sensor."""

    type = "passenger temperature setting"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermostat"

    @property
    def native_value(self) -> float:
        """Return passenger temperature setting."""
        return self._car.passenger_temp_setting


class TeslaCarCabinOverheatProtection(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car cabin overheat protection sensor.

    Read-only replacement for the removed cabin overheat protection select.
    """

    type = "cabin overheat protection"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["Off", "No A/C", "On"]
    _attr_icon = "mdi:sun-thermometer"

    @property
    def native_value(self) -> Optional[str]:
        """Return cabin overheat protection setting."""
        return self._car.cabin_overheat_protection


class TeslaCarClimateKeeperMode(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car climate keeper mode sensor."""

    type = "climate keeper mode"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["off", "on", "dog", "camp"]
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:fan"

    @property
    def native_value(self) -> Optional[str]:
        """Return climate keeper mode."""
        return self._car.climate_keeper_mode


class TeslaCarHeatedSteeringWheelLevel(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car heated steering wheel level sensor.

    Read-only replacement for the removed heated steering wheel select.
    """

    type = "heated steering wheel level"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:steering"

    @property
    def native_value(self) -> Optional[int]:
        """Return heated steering wheel level."""
        return self._car.get_heated_steering_wheel_level()

    @property
    def available(self) -> bool:
        """Return True if the car has a heated steering wheel."""
        return super().available and self._car.steering_wheel_heater


class TeslaCarSpeed(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car speed sensor."""

    type = "speed"
    _attr_device_class = SensorDeviceClass.SPEED
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfSpeed.MILES_PER_HOUR
    _attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> Optional[float]:
        """Return current speed."""
        return self._car.speed


class TeslaCarPower(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car power sensor."""

    type = "power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_icon = "mdi:flash"

    @property
    def native_value(self) -> Optional[float]:
        """Return current power usage."""
        power = self._car.power
        if power is None:
            return None
        return float(power)


class TeslaCarHeading(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car heading sensor."""

    type = "heading"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = DEGREE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:compass"

    @property
    def native_value(self) -> Optional[int]:
        """Return heading."""
        return self._car.heading


class TeslaCarSeatHeater(TeslaCarEntity, SensorEntity):
    """Representation of a Tesla car seat heater level sensor.

    Read-only replacement for the removed heated seat selects.
    """

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:car-seat-heater"

    def __init__(
        self,
        car: TeslaCar,
        coordinator: TeslaDataUpdateCoordinator,
        seat_name: str,
    ) -> None:
        """Initialize seat heater sensor."""
        self._seat_name = seat_name
        self.type = f"heated seat {seat_name}"
        super().__init__(car, coordinator)

    @property
    def native_value(self) -> Optional[int]:
        """Return seat heater level."""
        return self._car.get_seat_heater_status(SEAT_ID_MAP[self._seat_name])
