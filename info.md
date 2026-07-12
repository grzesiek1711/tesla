# Tesla Extended

A fork of [alandtse/tesla](https://github.com/alandtse/tesla), the previous
official Tesla integration in Home Assistant which was removed due to Tesla
login issues. Do not report issues to Home Assistant.

**Read-only monitoring** for Tesla vehicles: battery and charging, climate,
location, doors/windows/locks, trunk/frunk, sentry/valet mode, software update
status and more. Sending commands is not supported because it requires Tesla's
signed vehicle-command protocol; the only actions are wake up, force data
update and a local polling switch.

To use the integration you need a Tesla refresh token, which you can generate
with one of:

- Android: [Tesla Tokens](https://play.google.com/store/apps/details?id=net.leveugle.teslatokens)
- iOS: [Auth App for Tesla](https://apps.apple.com/us/app/auth-app-for-tesla/id1552058613)
- TeslaFi: [Tesla v3 API Tokens](https://support.teslafi.com/en/communities/1/topics/16979-tesla-v3-api-tokens)
- Chromium/Edge: [Chromium Tesla Token Generator](https://github.com/DoctorMcKay/chromium-tesla-token-generator)

{% if not installed %}

## Installation

1. Click install.
2. Restart Home Assistant.
3. Go to **Settings** → **Devices & Services** → **+ Add Integration** and
   search for **Tesla Extended**.
4. Paste your Tesla refresh token when prompted.

{% endif %}
