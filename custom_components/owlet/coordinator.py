"""Owlet integration coordinator class."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STALE_AFTER
from .pyowletapi.exceptions import (
    OwletAuthenticationError,
    OwletConnectionError,
    OwletError,
)
from .pyowletapi.sock import Sock

_LOGGER = logging.getLogger(__name__)

type OwletConfigEntry = ConfigEntry[dict[str, OwletCoordinator]]


class OwletCoordinator(DataUpdateCoordinator[None]):
    """Coordinator is responsible for querying the device at a specified route."""

    config_entry: OwletConfigEntry

    def __init__(
        self, hass: HomeAssistant, sock: Sock, interval: int, entry: OwletConfigEntry
    ) -> None:
        """Initialise a custom coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.sock = sock

    @property
    def vitals_stale(self) -> bool:
        """Return True when the sock's live readings have stopped updating."""
        if self.sock.properties.get("charging"):
            return False
        last_updated = self.sock.properties.get("last_updated")
        return (
            last_updated is not None and dt_util.utcnow() - last_updated > STALE_AFTER
        )

    async def _async_update_data(self) -> None:
        """Fetch the data from the device."""
        try:
            properties = await self.sock.update_properties()
            if "tokens" in properties:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, **properties["tokens"]},
                )
        except OwletAuthenticationError as err:
            raise ConfigEntryAuthFailed(
                f"Authentication failed for {self.config_entry.data[CONF_USERNAME]}"
            ) from err
        except (OwletError, OwletConnectionError) as err:
            raise UpdateFailed(err) from err
