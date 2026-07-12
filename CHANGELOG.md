# CHANGELOG



## v1.1.0 (2026-07-12)

Expanded TeslaMate MQTT coverage so far more entities update in near real-time
(as often as every ~500 ms while driving) instead of waiting for cloud polling.

### Feature

* feat(teslamate): consume all TeslaMate MQTT topics that map to an existing
  entity and feed them into the same sensors/binary sensors used by polling.
  Newly synced data includes drive power; the individual doors and windows;
  sunroof state and percent open; charger phases and scheduled charging start
  time; the active navigation route (destination, ETA, distance, traffic delay
  and destination coordinates, parsed from the `active_route` JSON blob); and
  the installed/available software version.

* feat(teslamate): convert TeslaMate metric values to the units the Tesla API
  reports (km→miles, km/h→mph) and cast door/window booleans to the open/closed
  integers the entities expect, so Home Assistant unit handling stays
  consistent regardless of the data source.

## v1.0.0 (2026-07-12)

Initial release of **Tesla Extended**, a read-only Home Assistant integration
for monitoring Tesla vehicles (domain `tesla_extended`).

### Feature

* feat: read-only monitoring of Tesla vehicles via sensors, binary sensors,
  device trackers, a software update entity and a TeslaMate ID text input.

* feat: local polling switch plus wake up and force data update buttons (none of
  which require Tesla's signed vehicle-command protocol).

* feat: simple setup flow that only asks for the account email and refresh
  token; vehicles are always included and the default Tesla auth domain
  (`https://auth.tesla.com`) is used.

* feat: all sensors and binary sensors, including the diagnostic ones, are
  enabled by default so everything is visible right after installation.

* feat: localized entity names via translation keys, with bundled English and
  Polish (`pl`) translations.

* feat: optional TeslaMate MQTT synchronization.

### Build

* build(ci): tag-driven release workflow that builds `tesla_extended.zip` and
  publishes it as a GitHub Release asset for HACS.
