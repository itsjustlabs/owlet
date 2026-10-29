"""Test the Owlet base station switch."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from custom_components.owlet.pyowletapi.exceptions import OwletConnectionError
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN, SERVICE_TURN_OFF
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import async_init_integration

ENTITY_ID = "switch.owlet_sock_serial_number_base_station_on"


@pytest.mark.parametrize(
    "result",
    [{"return_value": False}, {"side_effect": OwletConnectionError("down")}],
    ids=["rejected", "connection_error"],
)
async def test_failed_command_raises(hass: HomeAssistant, result: dict) -> None:
    """Test a command Owlet doesn't accept shows an error instead of passing silently."""
    await async_init_integration(hass, properties_fixture="update_properties_asleep.json")

    with patch(
        "custom_components.owlet.pyowletapi.sock.Sock.control_base_station", **result
    ), pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
        )
    assert err.value.translation_key == "command_failed"
