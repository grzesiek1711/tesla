"""Const file for Tesla cars."""

VERSION = "5.0.0"
CONF_EXPIRATION = "expiration"
CONF_INCLUDE_VEHICLES = "include_vehicles"
CONF_POLLING_POLICY = "polling_policy"
CONF_WAKE_ON_START = "enable_wake_on_start"
CONF_ENABLE_TESLAMATE = "enable_teslamate"
DOMAIN = "tesla_custom"
ATTRIBUTION = "Data provided by Tesla"
DATA_LISTENER = "listener"
DEFAULT_SCAN_INTERVAL = 660
DEFAULT_WAKE_ON_START = False
DEFAULT_ENABLE_TESLAMATE = False
ERROR_URL_NOT_DETECTED = "url_not_detected"
MIN_SCAN_INTERVAL = 10

# Command platforms that require Tesla's signed vehicle-command protocol
# (lock, climate, cover, select, number) have been removed. This integration
# is read-only apart from the local polling controls, the wake up command and
# force data update, which do not require a signing certificate.
PLATFORMS = [
    "sensor",
    "binary_sensor",
    "device_tracker",
    "switch",
    "button",
    "update",
    "text",
]


ATTR_PARAMETERS = "parameters"
ATTR_PATH_VARS = "path_vars"
ATTR_POLLING_POLICY_NORMAL = "normal"
ATTR_POLLING_POLICY_CONNECTED = "connected"
ATTR_POLLING_POLICY_ALWAYS = "always"
ATTR_VIN = "vin"
DEFAULT_POLLING_POLICY = ATTR_POLLING_POLICY_NORMAL
DISTANCE_UNITS_KM_HR = "km/hr"
SERVICE_API = "api"
SERVICE_SCAN_INTERVAL = "polling_interval"

TESLAMATE_STORAGE_VERSION = 1
TESLAMATE_STORAGE_KEY = f"{DOMAIN}_teslamate"
