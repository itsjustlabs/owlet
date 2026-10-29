"""Test Owlet diagnostics."""
from __future__ import annotations

import json

from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from . import async_init_integration


async def test_diagnostics_redacts_secrets(
    hass: HomeAssistant, hass_client: ClientSessionGenerator
) -> None:
    """Diagnostics carry readings but no credentials, serials or addresses."""
    assert await async_setup_component(hass, "diagnostics", {})
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert diagnostics["entry"]["data"] == {
        "region": "europe",
        "username": "**REDACTED**",
        "api_token": "**REDACTED**",
        "expiry": 100,
        "refresh": "**REDACTED**",
    }
    sock = diagnostics["socks"][0]
    assert sock["version"] == 3
    assert sock["properties"]["heart_rate"] == 97.0
    assert sock["raw_properties"]["CONFIG_STATUS"] == "**REDACTED**"
    assert "PPG_LOG_FILE" not in sock["raw_properties"]

    dumped = json.dumps(diagnostics)
    for secret in ("sample@gmail.com", "api_token\": \"api_token", "refresh_token"):
        assert secret not in dumped
    for identifier in ("SERIAL_NUMBER", "D0ECE231F766", "F832C96E47EF", "1234567"):
        assert identifier not in dumped


async def test_diagnostics_redacts_v2_personal_data(
    hass: HomeAssistant, hass_client: ClientSessionGenerator
) -> None:
    """v2 socks can carry the baby's name and birthdate; never export them."""
    assert await async_setup_component(hass, "diagnostics", {})
    entry = await async_init_integration(
        hass, properties_fixture="update_properties_v2.json"
    )

    raw_properties = entry.runtime_data["SERIAL_NUMBER"].sock.raw_properties
    raw_properties["BABY_NAME"]["value"] = "Ada"
    raw_properties["BIRTHDATE"]["value"] = "2023-01-02"

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    raw = diagnostics["socks"][0]["raw_properties"]

    for name in ("BABY_NAME", "BIRTHDATE", "BLE_MAC_ID", "LOCAL_BLE_MAC_ID"):
        assert raw[name] == "**REDACTED**"
    dumped = json.dumps(diagnostics)
    for value in ("Ada", "2023-01-02", "EEFE7E17F87A", "C1AC7A823D26"):
        assert value not in dumped
