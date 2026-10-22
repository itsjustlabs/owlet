"""Test detection of vitals that have stopped updating."""
from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory

from homeassistant.core import HomeAssistant

from . import async_init_integration

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


async def test_v2_sock_has_no_stale_sensor(hass: HomeAssistant) -> None:
    """v2 socks report no update time, so no stale sensor is created."""
    await async_init_integration(hass, properties_fixture="update_properties_v2.json")

    assert hass.states.get(f"binary_sensor.{PREFIX}_readings_stale") is None
    assert hass.states.get(f"sensor.{PREFIX}_last_updated") is None
