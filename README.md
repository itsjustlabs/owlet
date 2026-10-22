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

- Binary sensors - charging status, high heart rate alert, low heart rate alert, high oxygen alert, low oxygen alert, low battery alert, lost power alert, sock diconnected alert, and sock status.
- Sensors - battery level, oxygen saturation, oxygen saturation 10 minute average, heart rate, battery time remaining, signal strength, skin temperature, sleep state, and last updated.
- Readings stale - turns on when the sock's live readings are more than 2 minutes old while it is off the charger. Heart rate, oxygen and the other live readings show as unavailable while this is on, instead of repeating the last value.
- Switch - base station on/off.
- Monitoring state - one of monitoring, low signal, base station off, readings stale, charging, or charged. Handy for a dashboard tile or a single automation trigger.
- Low signal and discomfort alert binary sensors, plus Owlet's high/medium/low priority alarm flags (disabled by default).
- Firmware update status (diagnostic).

## Development

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv -r requirements_test.txt
.venv/bin/python -m pytest
```

## Options

- Seconds between polling - Number of seconds between each call for data from the owlet cloud service, default is 5 seconds.

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
