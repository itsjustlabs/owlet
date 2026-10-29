"""Test the one-glance monitoring state sensor."""
from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.core import HomeAssistant

from . import async_init_integration
from .test_parsing import _asleep_with, _poll

ENTITY_ID = "sensor.owlet_sock_serial_number_monitoring_state"


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("update_properties_asleep.json", "monitoring"),
        ("update_properties_charging.json", "charged"),
        ("update_properties_v2.json", "monitoring"),
    ],
)
async def test_state_from_fixtures(
    hass: HomeAssistant, fixture: str, expected: str
) -> None:
    """Each fixture maps to the expected state."""
    await async_init_integration(hass, properties_fixture=fixture)
    assert hass.states.get(ENTITY_ID).state == expected


@pytest.mark.parametrize(
    ("vitals", "raw", "expected"),
    [
        ({"chg": 1}, {}, "charging"),
        ({}, {"LOW_INTEG_READ": 1}, "low_signal"),
        # No reading and no low-reading alert: no signal, even without the flag.
        ({"hr": 0, "ox": 0}, {}, "low_signal"),
        # A real low-oxygen alert is not a signal problem.
        ({"hr": 0, "ox": 0}, {"LOW_OX_ALRT": 1}, "monitoring"),
        ({"hr": 0, "ox": 0, "bso": 0}, {}, "base_station_off"),
        # Base station off but readings still arriving: trust the readings.
        ({"bso": 0}, {}, "monitoring"),
    ],
)
async def test_state_transitions(
    hass: HomeAssistant, vitals: dict, raw: dict, expected: str
) -> None:
    """Combinations of charge, signal and base-station state."""
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )

    await _poll(hass, entry, _asleep_with(vitals, **raw))

    assert hass.states.get(ENTITY_ID).state == expected


async def test_stale_state(
    hass: HomeAssistant, frozen_time: FrozenDateTimeFactory
) -> None:
    """Frozen readings show as stale instead of monitoring."""
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )

    frozen_time.tick(timedelta(minutes=3))
    entry.runtime_data["SERIAL_NUMBER"].async_update_listeners()
    await hass.async_block_till_done()

    assert hass.states.get(ENTITY_ID).state == "stale"
