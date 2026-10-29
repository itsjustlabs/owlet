"""Test Owlet init."""
from __future__ import annotations

from datetime import timedelta
import json

import pytest
from unittest.mock import patch

from custom_components.owlet.pyowletapi.exceptions import (
    OwletAuthenticationError,
    OwletConnectionError,
    OwletDevicesError,
    OwletError,
)

from custom_components.owlet.const import (
    CONF_OWLET_EXPIRY,
    CONF_OWLET_REFRESH,
    DOMAIN,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    CONF_API_TOKEN,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    EntityCategory,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from . import async_init_integration, load_fixture

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]


async def test_async_setup_entry(hass: HomeAssistant) -> None:
    """Test setting up entry."""
    entry = await async_init_integration(hass)

    assert entry.state == ConfigEntryState.LOADED

    device_registry = dr.async_get(hass)

    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "SERIAL_NUMBER")}
    )

    assert device_entry.name == "Owlet Sock SERIAL_NUMBER"

    entity_registry = er.async_get(hass)

    entities = er.async_entries_for_device(entity_registry, device_entry.id)

    assert len(entities) == 25

    await hass.config_entries.async_unload(entry.entry_id)

    assert entry.state == ConfigEntryState.NOT_LOADED


async def test_async_setup_entry_new_tokens(hass: HomeAssistant) -> None:
    """Test setting up entry and getting new tokens."""
    entry = await async_init_integration(
        hass, devices_fixture="get_devices_with_tokens.json"
    )

    assert entry.data == {
        CONF_REGION: "europe",
        CONF_USERNAME: "sample@gmail.com",
        CONF_API_TOKEN: "new_api_token",
        CONF_OWLET_EXPIRY: 200,
        CONF_OWLET_REFRESH: "new_refresh_token",
    }

    assert entry.state == ConfigEntryState.LOADED

    await hass.config_entries.async_unload(entry.entry_id)

    assert entry.state == ConfigEntryState.NOT_LOADED


async def test_async_setup_entry_auth_error(hass: HomeAssistant) -> None:
    """Test setting up entry with auth error."""
    entry = await async_init_integration(hass, skip_setup=True)

    with patch(
        "custom_components.owlet.OwletAPI.authenticate",
        side_effect=OwletAuthenticationError(),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.SETUP_ERROR

        await hass.config_entries.async_unload(entry.entry_id)


async def test_async_setup_entry_connection_error(hass: HomeAssistant) -> None:
    """Test setting up entry with connection error."""
    entry = await async_init_integration(hass, skip_setup=True)

    with patch(
        "custom_components.owlet.OwletAPI.authenticate",
        side_effect=OwletConnectionError(),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.SETUP_RETRY

        await hass.config_entries.async_unload(entry.entry_id)


async def test_async_setup_entry_devices_error(hass: HomeAssistant) -> None:
    """Test no socks found retries setup later instead of giving up."""
    entry = await async_init_integration(hass, skip_setup=True)

    with patch(
        "custom_components.owlet.OwletAPI.authenticate", return_value=None
    ), patch(
        "custom_components.owlet.OwletAPI.get_devices",
        side_effect=OwletDevicesError(),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.SETUP_RETRY
        await hass.config_entries.async_unload(entry.entry_id)


async def test_async_setup_entry_error(hass: HomeAssistant) -> None:
    """Test setting up entry with unknown error."""
    entry = await async_init_integration(hass, skip_setup=True)

    with patch(
        "custom_components.owlet.OwletAPI.authenticate",
        side_effect=OwletError(),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.SETUP_ERROR

        await hass.config_entries.async_unload(entry.entry_id)


async def test_options_update_reloads_entry(hass: HomeAssistant) -> None:
    """Test changing the scan interval applies without restarting HA."""
    entry = await async_init_integration(hass)

    with patch(
        "custom_components.owlet.OwletAPI.get_properties",
        return_value=json.loads(
            load_fixture("update_properties_charging.json", "owlet")
        ),
    ), patch(
        "custom_components.owlet.OwletAPI.authenticate", return_value=None
    ), patch(
        "custom_components.owlet.OwletAPI.get_devices",
        return_value=json.loads(load_fixture("get_devices.json", "owlet")),
    ):
        hass.config_entries.async_update_entry(
            entry, options={CONF_SCAN_INTERVAL: 30}
        )
        await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.LOADED
    coordinator = entry.runtime_data["SERIAL_NUMBER"]
    assert coordinator.update_interval == timedelta(seconds=30)


@pytest.mark.parametrize(
    ("old_title", "new_title"),
    [
        ("sample@gmail.com", "Owlet"),
        ("Sample@Gmail.com", "Owlet"),
        ("Nursery", "Nursery"),
    ],
)
async def test_migrate_email_title(
    hass: HomeAssistant, old_title: str, new_title: str
) -> None:
    """Test 1.1 entries titled with the email are renamed, and custom titles kept."""
    entry = await async_init_integration(hass, title=old_title)

    assert entry.state == ConfigEntryState.LOADED
    assert entry.title == new_title
    assert entry.minor_version == 2


async def test_auth_error_does_not_log_email(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test a failed login doesn't put the account email in the log."""
    entry = await async_init_integration(hass, skip_setup=True)

    with patch(
        "custom_components.owlet.OwletAPI.authenticate",
        side_effect=OwletAuthenticationError(),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.SETUP_ERROR
    assert "sample@gmail.com" not in caplog.text.lower()


@pytest.mark.parametrize(
    ("properties_fixture", "hw_version"),
    [("update_properties_asleep.json", "obl"), ("update_properties_v2.json", "B2_1_0_0_6c36")],
)
async def test_device_info(
    hass: HomeAssistant, properties_fixture: str, hw_version: str
) -> None:
    """Test the device shows the sock's reported hardware version and serial."""
    entry = await async_init_integration(hass, properties_fixture=properties_fixture)

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, "SERIAL_NUMBER")}
    )
    assert device.hw_version == hw_version
    assert device.serial_number == "SERIAL_NUMBER"
    assert device.connections == {(dr.CONNECTION_NETWORK_MAC, "MAC")}

    await hass.config_entries.async_unload(entry.entry_id)


async def test_device_without_mac(hass: HomeAssistant) -> None:
    """Test a sock with no MAC address gets no placeholder connection."""
    devices = json.loads(load_fixture("get_devices.json"))
    devices["response"][0]["device"]["mac"] = ""
    entry = await async_init_integration(hass, skip_setup=True)

    with patch(
        "custom_components.owlet.OwletAPI.get_properties",
        return_value=json.loads(load_fixture("update_properties_asleep.json")),
    ), patch("custom_components.owlet.OwletAPI.authenticate", return_value=None), patch(
        "custom_components.owlet.OwletAPI.get_devices", return_value=devices
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, "SERIAL_NUMBER")}
    )
    assert device.connections == set()


async def test_diagnostic_entities(hass: HomeAssistant) -> None:
    """Test signal strength and readings stale are listed under Diagnostic."""
    await async_init_integration(hass, properties_fixture="update_properties_asleep.json")

    registry = er.async_get(hass)
    for entity_id in (
        "sensor.owlet_sock_serial_number_signal_strength",
        "binary_sensor.owlet_sock_serial_number_readings_stale",
    ):
        assert registry.async_get(entity_id).entity_category == EntityCategory.DIAGNOSTIC
