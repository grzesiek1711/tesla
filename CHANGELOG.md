# CHANGELOG



## v1.5.0 (2026-07-12)

### Fix

* fix(polling): actually apply the sentry polling interval. `config_entry.options`
  is a `MappingProxyType`, not a `dict`, so the previous `isinstance(..., dict)`
  guard discarded the real options and treated the sentry interval as equal to
  the normal one — the interval never activated and the "polling interval"
  sensor stayed at the normal value. The options mapping is now read correctly.

### Change

* change(config): lower the minimum polling interval from 10 to 5 seconds for
  both the normal and sentry polling intervals.

* change(events): rename the sentry event from `tesla_extended_sentry_display`
  to `tesla_sentry_triggered`. Update automations that used the old name.


## v1.4.0 (2026-07-12)

### Fix

* fix(polling): honor the sentry polling interval when sentry state arrives over
  TeslaMate MQTT. Sentry detection no longer requires `sentry_mode_available`
  (which TeslaMate does not publish), so the sentry interval now activates and
  the "polling interval" sensor reflects it and the vehicle is refreshed on the
  configured cadence instead of staying at the normal interval.

* fix(number): the TeslaMate ID no longer reverts to its previous value after
  being changed; the entity now caches the new value immediately.

* fix(translations): add the missing `polling_policy` option label to the
  options flow (English and Polish).

### Change

* change(events): the `tesla_extended_sentry_display` event now carries only the
  vehicle `name`.


## v1.3.0 (2026-07-12)

### Feature

* feat(events): fire a `tesla_extended_sentry_display` event on the Home
  Assistant event bus when a vehicle has sentry mode enabled and its center
  display changes to state `7`. The event is edge-triggered and carries `vin`,
  `name`, `sentry_mode` and `center_display_state`. It is evaluated on every
  car-state change (cloud polling and TeslaMate MQTT), so with MQTT enabled it
  fires in near real time.

### Fix

* fix(sensor): the "polling interval" sensor now reflects the sentry polling
  interval as soon as sentry mode activates/deactivates. The interval is applied
  as a per-VIN override so the sensor reports the value currently in effect.

* fix(polling): honor the sentry polling interval accurately. While sentry mode
  is active the coordinator heartbeat is shortened to the configured interval
  and refresh is forced, so a 10s setting refreshes about every 10s instead of
  drifting to roughly 20s. A manual `set_update_interval` service override is
  preserved when sentry mode is not active.


## v1.2.0 (2026-07-12)

### Feature

* feat(number): the TeslaMate ID is now a numeric **number** entity instead of a
  free-text input, so it only accepts a valid numeric TeslaMate car id. The
  `text` platform was replaced by a `number` platform.

* feat(config): add a **Sentry Polling Interval** option (`sentry_scan_interval`,
  default 660 s, min 10 s). When sentry mode is active on any vehicle the
  integration polls at this interval instead of the normal polling interval.
  Leave it equal to the normal interval for unchanged behavior.

### Breaking Change

* The TeslaMate ID entity moves from the `text` domain to the `number` domain
  (`text.*_teslamate_id` → `number.*_teslamate_id`). The entity is disabled by
  default; any automation or dashboard referencing the old text entity id must
  be updated.


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
