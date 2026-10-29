"""Test that unexpected values from Owlet don't fail the whole poll."""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import async_init_integration, load_fixture

PREFIX = "owlet_sock_serial_number"


def _asleep_with(vitals: dict[str, Any] | None = None, **raw: Any) -> dict[str, Any]:
    """Return the asleep fixture with some vitals or raw property values replaced."""
    fixture = json.loads(load_fixture("update_properties_asleep.json"))
    response = fixture["response"]
    if vitals:
        current = json.loads(response["REAL_TIME_VITALS"]["value"])
        response["REAL_TIME_VITALS"]["value"] = json.dumps({**current, **vitals})
    for name, value in raw.items():
        response[name]["value"] = value
    return fixture


async def _poll(hass: HomeAssistant, entry, properties: dict[str, Any]) -> None:
    with patch(
        "custom_components.owlet.OwletAPI.get_properties", return_value=properties
    ):
        await entry.runtime_data["SERIAL_NUMBER"].async_refresh()
        await hass.async_block_till_done()


async def test_bad_vital_only_affects_its_own_entity(hass: HomeAssistant) -> None:
    """A null or non-numeric reading leaves the other readings updating."""
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )

    await _poll(hass, entry, _asleep_with({"hr": 120, "rsi": "bad", "mv": None}))

    assert entry.runtime_data["SERIAL_NUMBER"].last_update_success
    assert hass.states.get(f"sensor.{PREFIX}_heart_rate").state == "120.0"
    assert hass.states.get(f"sensor.{PREFIX}_signal_strength").state == "unknown"


async def test_null_alert_is_unknown(hass: HomeAssistant) -> None:
    """A null alert value shows as unknown rather than off."""
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )

    await _poll(hass, entry, _asleep_with(LOW_OX_ALRT=None))

    assert (
        hass.states.get(f"binary_sensor.{PREFIX}_low_oxygen_alert").state == "unknown"
    )
    assert hass.states.get(f"sensor.{PREFIX}_heart_rate").state == "97.0"


async def test_unreadable_vitals_blob(hass: HomeAssistant) -> None:
    """Corrupt REAL_TIME_VITALS keeps the poll alive; the alerts still update."""
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )

    await _poll(hass, entry, _asleep_with(REAL_TIME_VITALS="not json", LOW_OX_ALRT=1))

    assert entry.runtime_data["SERIAL_NUMBER"].last_update_success
    assert hass.states.get(f"binary_sensor.{PREFIX}_low_oxygen_alert").state == "on"
    assert hass.states.get(f"sensor.{PREFIX}_heart_rate").state == "unknown"


async def test_firmware_update_status(hass: HomeAssistant) -> None:
    """The firmware status reports Owlet's state instead of always 'available'."""
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )
    assert hass.states.get(f"sensor.{PREFIX}_firmware_update_status").state == "idle"

    await _poll(
        hass, entry, _asleep_with(FW_UPDATE_STATUS='{"primary":"DOWNLOADING"}')
    )
    assert (
        hass.states.get(f"sensor.{PREFIX}_firmware_update_status").state
        == "downloading"
    )


async def test_low_signal_and_discomfort(hass: HomeAssistant) -> None:
    """LOW_INTEG_READ and DISCOMFORT_ALRT have their own binary sensors."""
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )
    assert hass.states.get(f"binary_sensor.{PREFIX}_low_signal").state == "off"
    assert hass.states.get(f"binary_sensor.{PREFIX}_discomfort_alert").state == "off"

    await _poll(hass, entry, _asleep_with(LOW_INTEG_READ=1, DISCOMFORT_ALRT=1))

    assert hass.states.get(f"binary_sensor.{PREFIX}_low_signal").state == "on"
    assert hass.states.get(f"binary_sensor.{PREFIX}_discomfort_alert").state == "on"


async def test_priority_alarms_start_disabled(hass: HomeAssistant) -> None:
    """Owlet's alarm priority flags are registered but disabled by default."""
    await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )
    registry = er.async_get(hass)

    for level in ("high", "medium", "low"):
        entity_id = f"binary_sensor.{PREFIX}_{level}_priority_alarm"
        assert hass.states.get(entity_id) is None
        entity = registry.async_get(entity_id)
        assert entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION
