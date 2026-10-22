"""The Owlet Smart Sock integration."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_TOKEN,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_OWLET_EXPIRY,
    CONF_OWLET_REFRESH,
    POLLING_INTERVAL,
    SUPPORTED_VERSIONS,
)
from .coordinator import OwletConfigEntry, OwletCoordinator
from .pyowletapi.api import OwletAPI
from .pyowletapi.exceptions import (
    OwletAuthenticationError,
    OwletConnectionError,
    OwletCredentialsError,
    OwletDevicesError,
)
from .pyowletapi.sock import Sock

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: OwletConfigEntry) -> bool:
    """Set up Owlet Smart Sock from a config entry."""
    owlet_api = OwletAPI(
        region=entry.data[CONF_REGION],
        token=entry.data[CONF_API_TOKEN],
        expiry=entry.data[CONF_OWLET_EXPIRY],
        refresh=entry.data[CONF_OWLET_REFRESH],
        session=async_get_clientsession(hass),
    )

    try:
        if token := await owlet_api.authenticate():
            hass.config_entries.async_update_entry(entry, data={**entry.data, **token})

        devices = await owlet_api.get_devices(SUPPORTED_VERSIONS)

    except (OwletAuthenticationError, OwletCredentialsError) as err:
        raise ConfigEntryAuthFailed(
            f"Credentials expired for {entry.data[CONF_USERNAME]}"
        ) from err

    except OwletConnectionError as err:
        raise ConfigEntryNotReady(
            f"Error connecting to {entry.data[CONF_USERNAME]}"
        ) from err

    except OwletDevicesError:
        _LOGGER.error("No owlet devices found to set up")
        return False

    if "tokens" in devices:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, **devices["tokens"]}
        )

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, POLLING_INTERVAL)
    coordinators = {
        device["device"]["dsn"]: OwletCoordinator(
            hass, Sock(owlet_api, device["device"]), scan_interval, entry
        )
        for device in devices["response"]
    }

    await asyncio.gather(
        *(
            coordinator.async_config_entry_first_refresh()
            for coordinator in coordinators.values()
        )
    )

    entry.runtime_data = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options such as the scan interval change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: OwletConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
