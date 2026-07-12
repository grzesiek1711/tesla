# Tesla Extended

[![GitHub Release][releases-shield]][releases]
![GitHub all releases][download-all]
![GitHub release (latest by SemVer)][download-latest]
[![GitHub Activity][commits-shield]][commits]

[![License][license-shield]][license]

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

A fork of [alandtse/tesla](https://github.com/alandtse/tesla), the previous official Tesla integration in Home Assistant which has been removed due to Tesla login issues. Do not report issues to Home Assistant.

---

## What This Integration Does

This integration provides read-only Home Assistant monitoring for Tesla vehicles:

**For Tesla Vehicles**:

- Real-time state monitoring (battery, temperature, location, charging)
- Climate status (HVAC on/off, target/current temperature, preconditioning)
- Vehicle status (locks, doors, windows, trunk/frunk, charge port, sentry/valet mode)
- Charging status and energy tracking (charge limit, amps, voltage, power, rate)
- Software update status

> **Read-only integration.** Sending commands to the vehicle (lock/unlock,
> climate control, opening the trunk/frunk/windows, charge start/stop, etc.)
> requires Tesla's signed vehicle-command protocol and a signing certificate,
> which this integration does not use. Where the corresponding state is
> readable it is exposed as a read-only sensor/binary sensor. The only actions
> available are **wake up** and **force data update** (which do not require
> signing) and a local **polling** switch.

> **Note**: This is a vehicles-only fork (no Tesla Energy Site / Powerwall /
> solar support). If you need Powerwall support, use the upstream
> [alandtse/tesla](https://github.com/alandtse/tesla) integration.

---

## Before You Start: Get a Tesla Refresh Token

To use this integration, you need a Tesla refresh token (from your Tesla account, not your car).

**Token Generator Apps**:

- Android: [Tesla Tokens](https://play.google.com/store/apps/details?id=net.leveugle.teslatokens)
- iOS: [Auth App for Tesla](https://apps.apple.com/us/app/auth-app-for-tesla/id1552058613)
- TeslaFi: [Tesla v3 API Tokens](https://support.teslafi.com/en/communities/1/topics/16979-tesla-v3-api-tokens)
- Chromium/Edge: [Chromium Tesla Token Generator](https://github.com/DoctorMcKay/chromium-tesla-token-generator)

**Note**: Never share your refresh token with anyone.

---

## Installation

### Method 1: HACS (Easiest)

1. Open HACS in Home Assistant
2. Go to **Integrations** → **Explore & Add Repositories**
3. Search for "Tesla Extended"
4. Add repository: `https://github.com/alandtse/tesla`
5. Click **Install**
6. Restart Home Assistant
7. Go to **Settings** → **Devices & Services** → **+** and search for "Tesla Extended"
8. Add your Tesla refresh token when prompted

### Method 2: Manual Installation

1. Download all files from `custom_components/tesla_extended/` in the repository
2. In your Home Assistant config directory, create folder: `custom_components/tesla_extended/`
3. Place downloaded files in that folder
4. Restart Home Assistant
5. Add integration as above

---

## Quick Setup

1. **Add Integration**: Settings → Devices & Services → + → Tesla Extended
2. **Enter Token**: Paste your Tesla refresh token
3. **Configure Options**: Set polling interval and wake behavior (or use defaults)
4. **Done!**: Your vehicles appear automatically

> **Note**: Setup only asks for your account email and refresh token. The
> integration always includes your vehicles and uses the default Tesla auth
> domain (`https://auth.tesla.com`), so the former "Include Vehicles" and "Auth
> Domain" fields are no longer shown.

---

## Configuration Options

After adding the integration, open its options dialog:

| Option                      | Default | Range                              | Purpose                                                          |
| --------------------------- | ------- | ---------------------------------- | ---------------------------------------------------------------- |
| **Polling Interval**        | 660 sec | 10-3600                            | How often to check for updates                                   |
| **Sentry Polling Interval** | 660 sec | 10-3600                            | Polling interval used while sentry mode is active on any vehicle |
| **Wake on Start**           | Off     | On/Off                             | Wake sleeping cars when HA starts                                |
| **Polling Policy**          | Always  | Always / Connected Only / Conserve | Sleep optimization strategy                                      |
| **TeslaMate MQTT**          | Off     | On/Off                             | Sync data from TeslaMate (requires MQTT)                         |

> **Sentry polling interval.** While sentry mode is active on a vehicle the
> integration polls that vehicle at this interval instead of the normal polling
> interval, so you can refresh more frequently (or less) while the car is
> guarding itself. It is applied per vehicle and the "polling interval" sensor
> reflects the value currently in effect. Leave it equal to the normal polling
> interval for unchanged behavior. The minimum is 10 seconds; note that more
> frequent polling keeps the car awake and increases battery drain.

> **TeslaMate MQTT sync (near real-time).** TeslaMate talks to Tesla over a
> streaming/websocket connection and publishes vehicle data to MQTT far more
> frequently than cloud polling (as often as every ~500 ms while driving). When
> enabled, this integration consumes **all** TeslaMate topics that map to an
> existing entity and feeds them into the same sensors/binary sensors used by
> polling, so those entities update almost instantly. Covered data includes:
> location, speed, heading, power, shift state; inside/outside temperature,
> climate on and preconditioning; battery level, ranges, and the full set of
> charging values (state, limit, amps, voltage, power, phases, energy added,
> time to full, scheduled start); doors, windows, trunk/frunk, locks, sentry,
> sunroof, TPMS pressures, odometer, user-present and center-display state;
> the active navigation route (destination, ETA, distance, traffic delay,
> destination coordinates); and the installed/available software version.
> Values TeslaMate reports in metric (km, km/h, °C) are converted to match the
> Tesla API so Home Assistant unit handling stays consistent.

---

## Available Entities

### Vehicle Entities

All vehicle entities are read-only (status monitoring), except the wake up and
force data update buttons and the local polling switch.

**Sensors**:

- Battery level, charge rate, estimated range, power, speed, heading
- Inside/outside temperature, driver/passenger temperature setting
- Odometer, TPMS tire pressure
- Charge limit %, charging amps, charger current, charger voltage, charger power
- Energy added in charging session, time to charge complete
- Cabin overheat protection, climate keeper mode, heated steering wheel level
- Per-seat heater levels (diagnostic, enabled by default)
- Active route destination, arrival time and distance to arrival
- Shift state, center display state, polling interval, last data update time

**Binary Sensors**:

- Charging status, online status, asleep status, user present
- Door open/closed, window open/closed, parking brake, charger connection
- Doors lock, charge port latch, charge port door
- Frunk, trunk, sunroof (open/closed)
- Sentry mode, valet mode, climate on, preconditioning
- Battery heater, front/rear defroster (diagnostic, enabled by default)
- Scheduled charging, scheduled departure

**Switches**:

- Polling enable/disable (local only, does not command the vehicle)

**Buttons**:

- Wake up (does not require signing)
- Force data update (refreshes cached data only)

**Device Tracker**:

- Current location (latitude/longitude)
- Active route destination

**Updates**:

- Software update status (read-only; installing requires a signing certificate)

**Number**:

- TeslaMate ID (numeric car id used for TeslaMate MQTT syncing)

> **Note**: all diagnostic sensors and binary sensors (per-seat heater levels,
> passenger temperature setting, battery heater and front/rear defroster) are
> enabled by default, so every sensor is visible right after installation.

---

## Events

The integration fires a Home Assistant event you can use as an automation
trigger:

| Event                            | Fired when                                                                                             |
| -------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `tesla_extended_sentry_display`  | A vehicle has **sentry mode enabled** and its **center display** changes to state `7` (the alert view) |

The event is edge-triggered (fired once when the condition becomes true and
re-armed after it clears) and carries this data:

| Field                  | Description                             |
| ---------------------- | --------------------------------------- |
| `vin`                  | Vehicle VIN                             |
| `name`                 | Vehicle display name                    |
| `sentry_mode`          | `true` while sentry mode is active      |
| `center_display_state` | The center display state (`7`)          |

When TeslaMate MQTT sync is enabled the event fires in near real time; with
cloud polling only it fires on the next poll.

**Example Automation**:

```yaml
automation:
  - alias: "Tesla - Sentry display alert"
    trigger:
      platform: event
      event_type: tesla_extended_sentry_display
    action:
      - service: notify.mobile_app
        data:
          message: "Sentry alert on {{ trigger.event.data.name }}"
```

---

## Localization

Entity names are localized through Home Assistant's translation system. English
and **Polish (`pl`)** translations are bundled for all entity names and the
configuration flow. Home Assistant automatically uses the translation matching
your configured language and falls back to English otherwise. Contributions of
additional languages are welcome in `custom_components/tesla_extended/translations/`.

---

## Battery Impact & Sleep Optimization

Tesla vehicles have a battery drain concern. This integration minimizes impact:

**How Polling Works**:

- Default polling interval: 660 seconds (11 minutes)
- **Does NOT wake sleeping cars** during polling
- Only wakes cars when you send commands (lock, climate, etc.)
- After waking, fetches data based on polling interval

**Your Battery Management**:

- **Polling Interval**: Higher = fewer updates = less battery drain. Experiment with 660-1800 seconds.
- **Wake on Start**: Disable to let cars sleep. Vehicles wake naturally on user actions.
- **Polling Policy**: Use "Conserve" to skip polling for offline/sleeping vehicles.
- **Polling Switch**: Disable polling completely via automations for extended idle periods.

**Example Automation** - Ensure data is fresh every morning:

```yaml
automation:
  - alias: "Tesla - Get fresh data in morning"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      - service: tesla_extended.set_update_interval
        data:
          interval: 60 # Poll frequently for 1 minute
      - delay: "00:01:00"
      - service: tesla_extended.set_update_interval
        data:
          interval: 660 # Back to normal
```

---

## Tips & Troubleshooting

### Data not updating

- **Cause**: Polling interval too high or car offline
- **Fix**: Check polling interval setting, ensure car is online

### Token expired

- **Cause**: Refresh token too old or credentials changed
- **Fix**: Restart Home Assistant to trigger reauthentication

### High battery drain

- **Cause**: Polling interval too low
- **Fix**: Increase polling interval to 1200-1800 seconds

---

## For Developers

### Architecture Documentation

For AI agents and developers working on this codebase:

- **AGENTS.md** - AI agent quick reference and codebase navigation
- **docs/index.md** - Documentation index and navigation guide
- **docs/architecture.md** - System design and integration patterns
- **docs/components.md** - Component breakdown and responsibilities
- **docs/interfaces.md** - APIs and contracts
- **docs/workflows.md** - Key processes and workflows

### Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Code style requirements (black formatting)
- Testing procedures (pytest)
- Pull request process
- Bug reporting guidelines

### Development Setup

Quick start with Docker dev container:

1. Install "Remote - Containers" extension in VS Code
2. Reopen folder in container
3. Home Assistant instance runs at `localhost:8123`

---

## Community & Support

- **Issues**: Report bugs at [GitHub Issues](https://github.com/alandtse/tesla/issues)
- **Discord**: [Join our Discord community](https://discord.gg/Qa5fW2R)
- **Forum**: [Home Assistant Community Forum](https://community.home-assistant.io/)
- **Wiki**: [Project Wiki](https://github.com/alandtse/tesla/wiki)

---

## License

Apache License 2.0 - See [LICENSE](LICENSE) file

---

## Credits

- Forked from the official Home Assistant Tesla integration
- Maintained by the community for continued Tesla integration support
- Built with [integration_blueprint](https://github.com/custom-components/integration_blueprint)

---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[buymecoffee]: https://www.buymeacoffee.com/alandtse
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/w/alandtse/tesla?style=for-the-badge
[commits]: https://github.com/alandtse/tesla/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license]: LICENSE
[license-shield]: https://img.shields.io/github/license/alandtse/tesla.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Alan%20Tse%20%40alandtse-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/alandtse/tesla.svg?style=for-the-badge
[releases]: https://github.com/alandtse/tesla/releases
[download-all]: https://img.shields.io/github/downloads/alandtse/tesla/total?style=for-the-badge
[download-latest]: https://img.shields.io/github/downloads/alandtse/tesla/latest/total?style=for-the-badge
[add-integration]: https://my.home-assistant.io/redirect/config_flow_start?domain=tesla_extended
[add-integration-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
