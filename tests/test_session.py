"""Test sleep session tracking."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from typing import Any
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from custom_components.owlet.const import DOMAIN
from custom_components.owlet.session import SAVE_DELAY, SleepSession
from homeassistant.core import HomeAssistant

from . import async_init_integration, load_fixture

from pytest_homeassistant_custom_component.common import async_fire_time_changed

PREFIX = "owlet_sock_serial_number"
START = datetime(2026, 10, 29, 19, 0, tzinfo=timezone.utc)
AWAKE, LIGHT, DEEP = 1, 8, 15


def _run(session: SleepSession, states: list[int], step: int = 5) -> datetime:
    """Feed one live poll per state, `step` seconds apart; return the last time."""
    now = START
    for index, state in enumerate(states):
        now = START + timedelta(seconds=step * index)
        session.update(now, state, live=True, charging=False)
    return now


def test_session_totals() -> None:
    """Time between polls counts towards the state of the earlier poll."""
    session = SleepSession()
    # 10 minutes awake, then 20 light, then 30 deep, polled every minute.
    _run(session, [AWAKE] * 10 + [LIGHT] * 20 + [DEEP] * 31, step=60)

    assert session.active
    assert session.started == START
    assert session.minutes("awake") == 10
    assert session.minutes("light_sleep") == 20
    assert session.minutes("deep_sleep") == 30
    assert session.minutes("light_sleep", "deep_sleep") == 50
    # Awake before falling asleep is not a waking.
    assert session.wakings == 0


def test_no_session_yet() -> None:
    """Before any session the totals are unknown, not zero."""
    session = SleepSession()
    assert not session.active
    assert session.minutes("awake") is None


@pytest.mark.parametrize(
    ("awake_minutes", "wakings"), [(1, 0), (2, 1), (10, 1)]
)
def test_wakings(awake_minutes: int, wakings: int) -> None:
    """A waking counts once, and only when awake lasts two minutes."""
    session = SleepSession()
    _run(session, [LIGHT] * 5 + [AWAKE] * (awake_minutes + 1) + [DEEP] * 5, step=60)
    assert session.wakings == wakings


def test_missed_readings_are_not_counted() -> None:
    """A gap between polls longer than five minutes adds no time."""
    session = SleepSession()
    session.update(START, LIGHT, live=True, charging=False)
    session.update(START + timedelta(minutes=20), LIGHT, live=True, charging=False)
    assert session.active
    assert session.minutes("light_sleep") == 0


def test_charging_ends_session() -> None:
    """Putting the sock on the charger ends the session right away."""
    session = SleepSession()
    last = _run(session, [LIGHT] * 10, step=60)

    assert session.update(last + timedelta(minutes=1), 0, live=True, charging=True)
    assert not session.active
    assert session.ended == last
    # The finished session's totals stay until the next one starts.
    assert session.minutes("light_sleep") == 9

    session.update(last + timedelta(hours=2), AWAKE, live=True, charging=False)
    assert session.active
    assert session.started == last + timedelta(hours=2)
    assert session.minutes("light_sleep") == 0


def test_long_gap_ends_session() -> None:
    """Thirty minutes without live readings ends the session."""
    session = SleepSession()
    last = _run(session, [LIGHT] * 10, step=60)

    assert not session.update(
        last + timedelta(minutes=29), LIGHT, live=False, charging=False
    )
    assert session.active
    assert session.update(
        last + timedelta(minutes=31), LIGHT, live=False, charging=False
    )
    assert session.ended == last


def test_returning_after_long_gap_starts_new_session() -> None:
    """Live readings after a long gap, such as a restart, start a new session."""
    session = SleepSession()
    last = _run(session, [LIGHT] * 10, step=60)

    session.update(last + timedelta(hours=1), DEEP, live=True, charging=False)
    assert session.started == last + timedelta(hours=1)


def test_storage_round_trip() -> None:
    """A stored session restores exactly."""
    session = SleepSession()
    _run(session, [LIGHT] * 5 + [AWAKE] * 4, step=60)
    assert SleepSession.from_dict(json.loads(json.dumps(session.as_dict()))) == session


async def _poll(
    hass: HomeAssistant, entry: Any, fixture: str, freezer: FrozenDateTimeFactory
) -> None:
    """Advance a minute and poll with the given properties fixture."""
    coordinator = entry.runtime_data["SERIAL_NUMBER"]
    raw = json.loads(load_fixture(fixture))
    # Keep the readings fresh so they don't count as stale.
    for prop in raw["response"].values():
        if "data_updated_at" in prop:
            prop["data_updated_at"] = (
                datetime.now(timezone.utc) + timedelta(minutes=1)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
    freezer.tick(timedelta(minutes=1))
    with patch(
        "custom_components.owlet.OwletAPI.get_properties", return_value=raw
    ):
        await coordinator.async_refresh()
    await hass.async_block_till_done()


async def test_session_sensors(
    hass: HomeAssistant, frozen_time: FrozenDateTimeFactory
) -> None:
    """The session entities follow the sock and survive the charger."""
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )

    assert hass.states.get(f"binary_sensor.{PREFIX}_sleep_session").state == "on"
    assert (
        hass.states.get(f"sensor.{PREFIX}_session_started").state
        == "2023-05-24T14:16:00+00:00"
    )
    assert hass.states.get(f"sensor.{PREFIX}_session_ended").state == "unknown"

    for _ in range(3):
        await _poll(hass, entry, "update_properties_asleep.json", frozen_time)
    for _ in range(3):
        await _poll(hass, entry, "update_properties_awake.json", frozen_time)

    assert hass.states.get(f"sensor.{PREFIX}_time_asleep").state == "4"
    assert hass.states.get(f"sensor.{PREFIX}_light_sleep_time").state == "4"
    assert hass.states.get(f"sensor.{PREFIX}_deep_sleep_time").state == "0"
    assert hass.states.get(f"sensor.{PREFIX}_time_awake").state == "2"
    assert hass.states.get(f"sensor.{PREFIX}_wakings").state == "1"

    await _poll(hass, entry, "update_properties_charging.json", frozen_time)

    assert hass.states.get(f"binary_sensor.{PREFIX}_sleep_session").state == "off"
    assert (
        hass.states.get(f"sensor.{PREFIX}_session_ended").state
        == "2023-05-24T14:22:00+00:00"
    )
    # Totals stay visible while the sock charges.
    assert hass.states.get(f"sensor.{PREFIX}_time_asleep").state == "4"


async def test_no_session_before_first_use(hass: HomeAssistant) -> None:
    """A sock that has only been charging has no session yet."""
    await async_init_integration(
        hass, properties_fixture="update_properties_charging.json"
    )

    assert hass.states.get(f"binary_sensor.{PREFIX}_sleep_session").state == "off"
    for key in ("session_started", "time_asleep", "wakings"):
        assert hass.states.get(f"sensor.{PREFIX}_{key}").state == "unknown", key


async def test_v2_has_no_session(hass: HomeAssistant) -> None:
    """The Smart Sock 2 doesn't report sleep state, so it has no sessions."""
    await async_init_integration(
        hass, properties_fixture="update_properties_v2.json"
    )
    assert hass.states.get(f"sensor.{PREFIX}_time_asleep") is None
    assert hass.states.get(f"binary_sensor.{PREFIX}_sleep_session") is None


async def test_session_restored_after_restart(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """A session in progress carries on after Home Assistant restarts."""
    session = SleepSession()
    session.update(
        datetime(2023, 5, 24, 13, 0, tzinfo=timezone.utc),
        DEEP,
        live=True,
        charging=False,
    )
    session.seconds["deep_sleep"] = 75 * 60
    session.last_seen = datetime(2023, 5, 24, 14, 15, tzinfo=timezone.utc)
    hass_storage[f"{DOMAIN}.mock_entry"] = {
        "version": 1,
        "key": f"{DOMAIN}.mock_entry",
        "data": {"SERIAL_NUMBER": session.as_dict()},
    }

    # The first poll is a minute after the stored one, so it adds a minute.
    await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json", entry_id="mock_entry"
    )

    assert (
        hass.states.get(f"sensor.{PREFIX}_session_started").state
        == "2023-05-24T13:00:00+00:00"
    )
    assert hass.states.get(f"sensor.{PREFIX}_deep_sleep_time").state == "76"
    assert hass.states.get(f"sensor.{PREFIX}_time_asleep").state == "76"


async def test_session_saved_and_removed(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    frozen_time: FrozenDateTimeFactory,
) -> None:
    """Sessions are saved shortly after they change and deleted with the entry."""
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )
    key = f"{DOMAIN}.{entry.entry_id}"
    assert key not in hass_storage

    frozen_time.tick(timedelta(seconds=SAVE_DELAY + 1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    stored = hass_storage[key]["data"]["SERIAL_NUMBER"]
    assert stored["started"] == "2023-05-24T14:16:00+00:00"
    assert stored["last_state"] == LIGHT

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert key not in hass_storage
