"""Test detection of vitals that have stopped updating."""
from __future__ import annotations

from datetime import timedelta
import json
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from custom_components.owlet.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from . import async_init_integration, load_fixture

PREFIX = "owlet_sock_serial_number"
VITALS = [
    f"sensor.{PREFIX}_heart_rate",
    f"sensor.{PREFIX}_o2_saturation",
    f"sensor.{PREFIX}_sleep_state",
    f"binary_sensor.{PREFIX}_awake",
]


async def test_fresh_readings(hass: HomeAssistant) -> None:
    """Readings updated within the window are shown and not flagged."""
    await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )

    assert hass.states.get(f"binary_sensor.{PREFIX}_readings_stale").state == "off"
    assert (
        hass.states.get(f"sensor.{PREFIX}_last_updated").state
        == "2023-05-24T14:15:50+00:00"
    )
    for entity_id in VITALS:
        assert hass.states.get(entity_id).state != "unavailable", entity_id


async def test_stale_readings(
    hass: HomeAssistant, frozen_time: FrozenDateTimeFactory
) -> None:
    """Frozen readings go unavailable and the stale sensor turns on."""
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )
    coordinator = entry.runtime_data["SERIAL_NUMBER"]

    # Owlet keeps returning the same readings, so last_updated never moves.
    frozen_time.tick(timedelta(minutes=3))
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    assert hass.states.get(f"binary_sensor.{PREFIX}_readings_stale").state == "on"
    for entity_id in VITALS:
        assert hass.states.get(entity_id).state == "unavailable", entity_id
    # Alerts and battery are not live vitals and stay visible.
    assert hass.states.get(f"binary_sensor.{PREFIX}_low_oxygen_alert").state == "off"
    assert hass.states.get(f"sensor.{PREFIX}_battery_percentage").state == "50.0"


async def test_charging_is_not_stale(
    hass: HomeAssistant, frozen_time: FrozenDateTimeFactory
) -> None:
    """A sock on the charger stops sending vitals; that is not a fault."""
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_charging.json"
    )
    coordinator = entry.runtime_data["SERIAL_NUMBER"]

    frozen_time.tick(timedelta(minutes=30))
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    assert hass.states.get(f"binary_sensor.{PREFIX}_readings_stale").state == "off"


@pytest.mark.parametrize(
    ("now", "stale"),
    [("2023-11-20T14:06:00+00:00", "off"), ("2023-11-20T14:10:00+00:00", "on")],
)
async def test_v2_sock_staleness(
    hass: HomeAssistant, frozen_time: FrozenDateTimeFactory, now: str, stale: str
) -> None:
    """v2 socks are live while heart rate or oxygen is still updating."""
    frozen_time.move_to(now)
    await async_init_integration(hass, properties_fixture="update_properties_v2.json")

    # Oxygen was last stored at 12:22 (Owlet only stores changes); heart rate at 14:05.
    assert (
        hass.states.get(f"sensor.{PREFIX}_last_updated").state
        == "2023-11-20T14:05:01+00:00"
    )
    assert hass.states.get(f"binary_sensor.{PREFIX}_readings_stale").state == stale
    o2 = hass.states.get(f"sensor.{PREFIX}_o2_saturation").state
    assert (o2 == "unavailable") == (stale == "on")


@pytest.mark.parametrize(
    ("threshold", "stale"), [(0, "off"), (10, "off"), (3, "on")]
)
async def test_stale_threshold_option(
    hass: HomeAssistant,
    frozen_time: FrozenDateTimeFactory,
    threshold: int,
    stale: str,
) -> None:
    """The threshold comes from the options, and 0 turns detection off."""
    entry = await async_init_integration(
        hass,
        properties_fixture="update_properties_asleep.json",
        options={"stale_threshold": threshold},
    )
    coordinator = entry.runtime_data["SERIAL_NUMBER"]

    frozen_time.tick(timedelta(minutes=5))
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    assert hass.states.get(f"binary_sensor.{PREFIX}_readings_stale").state == stale


async def _poll_after(
    hass: HomeAssistant,
    frozen_time: FrozenDateTimeFactory,
    elapsed: timedelta,
    base_station_on: int = 1,
):
    """Set up a v3 sock, move the clock, and poll the same frozen readings again."""
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )
    coordinator = entry.runtime_data["SERIAL_NUMBER"]
    properties = json.loads(load_fixture("update_properties_asleep.json"))
    vitals = properties["response"]["REAL_TIME_VITALS"]
    vitals["value"] = vitals["value"].replace('"bso":1', f'"bso":{base_station_on}')
    assert f'"bso":{base_station_on}' in vitals["value"]

    frozen_time.tick(elapsed)
    with patch(
        "custom_components.owlet.OwletAPI.get_properties", return_value=properties
    ):
        await coordinator.async_refresh()
    await hass.async_block_till_done()
    return entry, coordinator


async def test_stale_for_an_hour_raises_repair(
    hass: HomeAssistant,
    frozen_time: FrozenDateTimeFactory,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Readings stuck for over an hour with the base station on raise a warning."""
    _, coordinator = await _poll_after(hass, frozen_time, timedelta(minutes=61))

    issue = issue_registry.async_get_issue(DOMAIN, "stale_data_SERIAL_NUMBER")
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING
    assert issue.translation_placeholders["name"] == "Owlet Sock SERIAL_NUMBER"
    assert issue.translation_placeholders["last_updated"].startswith("2023-05-24")

    # Fresh readings clear it again.
    frozen_time.move_to("2023-05-24T14:16:00+00:00")
    coordinator._async_update_stale_issue()
    assert issue_registry.async_get_issue(DOMAIN, "stale_data_SERIAL_NUMBER") is None


@pytest.mark.parametrize(
    ("elapsed", "base_station_on"),
    [(timedelta(minutes=30), 1), (timedelta(hours=2), 0)],
    ids=["stale_under_an_hour", "base_station_off"],
)
async def test_no_repair(
    hass: HomeAssistant,
    frozen_time: FrozenDateTimeFactory,
    issue_registry: ir.IssueRegistry,
    elapsed: timedelta,
    base_station_on: int,
) -> None:
    """No warning before an hour, or while the base station is off."""
    await _poll_after(hass, frozen_time, elapsed, base_station_on)

    assert issue_registry.async_get_issue(DOMAIN, "stale_data_SERIAL_NUMBER") is None


async def test_removing_entry_clears_repair(
    hass: HomeAssistant,
    frozen_time: FrozenDateTimeFactory,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Removing the integration doesn't leave a stale warning behind."""
    entry, _ = await _poll_after(hass, frozen_time, timedelta(minutes=61))
    assert issue_registry.async_get_issue(DOMAIN, "stale_data_SERIAL_NUMBER")

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert issue_registry.async_get_issue(DOMAIN, "stale_data_SERIAL_NUMBER") is None
