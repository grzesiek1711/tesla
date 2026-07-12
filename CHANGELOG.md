# CHANGELOG



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
