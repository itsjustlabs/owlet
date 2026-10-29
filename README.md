# Owlet Custom Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]

[![License][license-shield]][license]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

A custom component for the Owlet smart sock.

This is a maintained continuation of [ryanbdclark/owlet](https://github.com/ryanbdclark/owlet), which was archived in 2025. It bundles [pyowletapi](https://github.com/ryanbdclark/pyowletapi) (MIT) under `custom_components/owlet/pyowletapi`. Existing installs of the original integration keep their entities when switched to this repository, because the domain and entity IDs are unchanged.

> **Not a medical device.** This reads Owlet's cloud API, which is unofficial and can change without notice. Keep using the Owlet app and base station for alarms.

## Installation

1. In [HACS](https://hacs.xyz/), open the menu, choose "Custom repositories", and add `https://github.com/itsjustlabs/owlet` as an Integration. Then download "Owlet".
2. Restart Home Assistant.
3. [![Add Integration][add-integration-badge]][add-integration] or in the HA UI go to "Settings" -> "Devices & Services" then click "+" and search for "Owlet Smart Sock".


<!---->

## Usage

The `Owlet` integration offers integration with the Owlet Smart Sock cloud service. This provides sensors such as heart rate, oxygen saturation, charge percentage.

This integration provides the following entities:

- Binary sensors - charging status, awake, sock off, high heart rate alert, low heart rate alert, high oxygen alert, low oxygen alert, critical oxygen alert, low battery alert, critical battery alert, lost power alert, and sock disconnected alert.
- Sensors - battery level, oxygen saturation, oxygen saturation 10 minute average, heart rate, battery time remaining, signal strength, skin temperature, sleep state, last updated, and movement and movement bucket (disabled by default).
- Readings stale - turns on when the sock's live readings are more than 2 minutes old while it is off the charger. The time is a setting (see Options). On a Smart Sock 2, the sock counts as live while either heart rate or oxygen is still updating. Heart rate, oxygen and the other live readings show as unavailable while this is on, instead of repeating the last value. If readings stay stale for over an hour while the base station is on, a warning also appears under Settings → System → Repairs; it clears itself when readings return.
- Switch - base station on/off.
- Monitoring state - one of monitoring, low signal, base station off, readings stale, charging, or charged. Handy for a dashboard tile or a single automation trigger.
- Low signal and discomfort alert binary sensors, plus Owlet's high/medium/low priority alarm flags (disabled by default).
- Firmware update status (diagnostic).

## Blueprints

Ready-made automations that notify a phone with the Home Assistant Companion app. Adapted from [LucasVollebergh/owlet](https://github.com/LucasVollebergh/owlet).

| Blueprint | What it does | Import |
| --- | --- | --- |
| Owlet alert notification | Notifies when any of the Owlet alerts you pick turns on. Optionally sends it as a critical notification, which sounds even on silent or do not disturb. | [![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fitsjustlabs%2Fowlet%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fowlet%2Fowlet_alert_notification.yaml) |
| Owlet readings stale notification | Notifies when a sock's Readings stale sensor turns on, after an optional extra delay, and optionally again when readings come back. | [![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fitsjustlabs%2Fowlet%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fowlet%2Fowlet_stale_data_notification.yaml) |

Like the integration, these depend on polling Owlet's cloud and can be late. Keep the Owlet base station and app as your alarm.

## Development

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv -r requirements_test.txt
.venv/bin/python -m pytest
```

Changes reach `main` only through pull requests. To release, bump `version` in `custom_components/owlet/manifest.json` and add a matching `## <version>` section to `CHANGELOG.md` in the same pull request. When it merges, the Release workflow runs the tests, tags the version, and publishes `owlet.zip` with that changelog section as the notes. Merges that don't change the version publish nothing.

## Reconfigure

To change the region or log in again without removing the integration, open Settings → Devices & services → Owlet → ⋮ → **Reconfigure**.

## Options

- Seconds between polling - Number of seconds between each call for data from the owlet cloud service, default is 5 seconds.
- Minutes before readings count as stale - how long the sock can go without a new reading before live readings show as unavailable and Readings stale turns on. Default 2; 0 turns stale detection off.

---

[commits-shield]: https://img.shields.io/github/commit-activity/w/itsjustlabs/owlet?style=for-the-badge
[commits]: https://github.com/itsjustlabs/owlet/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license]: LICENSE
[license-shield]: https://img.shields.io/github/license/itsjustlabs/owlet.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-itsjustlabs-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/itsjustlabs/owlet.svg?style=for-the-badge
[releases]: https://github.com/itsjustlabs/owlet/releases
[user_profile]: https://github.com/itsjustlabs
[add-integration]: https://my.home-assistant.io/redirect/config_flow_start?domain=owlet
[add-integration-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
