"""Diagnostics support for Owlet."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_TOKEN, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_OWLET_REFRESH
from .coordinator import OwletConfigEntry

TO_REDACT_ENTRY = {CONF_USERNAME, CONF_API_TOKEN, CONF_OWLET_REFRESH}

# Raw properties that identify the device, its network or the baby.
TO_REDACT_RAW = {
    "BABY_NAME",
    "BIRTHDATE",
    "BLE_MAC_ID",
    "CONFIG_STATUS",
    "GENDER",
    "LATITUDE",
    "LOCAL_BLE_MAC_ID",
    "LONGITUDE",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: OwletConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    socks = []
    for index, coordinator in enumerate(entry.runtime_data.values(), start=1):
        sock = coordinator.sock
        socks.append(
            {
                # The serial is in every API URL, so number the socks instead.
                "sock": index,
                "version": sock.version,
                "revision": sock.revision,
                "model": sock.model,
                "oem_model": sock.oem_model,
                "sw_version": sock.sw_version,
                "connection_status": sock.connection_status,
                "last_update_success": coordinator.last_update_success,
                "vitals_stale": coordinator.vitals_stale,
                "properties": sock.properties,
                # Values only: the metadata carries device keys and file links
                # are signed URLs to Owlet's logs.
                "raw_properties": async_redact_data(
                    {
                        name: prop.get("value")
                        for name, prop in sock.raw_properties.items()
                        if prop.get("base_type") != "file"
                    },
                    TO_REDACT_RAW,
                ),
            }
        )

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT_ENTRY),
            "options": dict(entry.options),
        },
        "socks": socks,
    }
