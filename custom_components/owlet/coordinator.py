"""Owlet integration coordinator class."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr, issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STALE_AFTER, STALE_ISSUE_AFTER
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
            raise ConfigEntryAuthFailed("Owlet login expired") from err
        except (OwletError, OwletConnectionError) as err:
            raise UpdateFailed(err) from err

        self._async_update_stale_issue()

    @property
    def stale_issue_id(self) -> str:
        """Return the Repairs issue ID for this sock's stale readings."""
        return f"stale_data_{self.sock.serial}"

    @callback
    def _async_update_stale_issue(self) -> None:
        """Warn in Repairs when readings have been stale for a long time."""
        last_updated = self.sock.properties.get("last_updated")
        base_station_on = self.sock.properties.get("base_station_on")
        if (
            not self.vitals_stale
            or last_updated is None
            # With the base station off the sock isn't expected to send readings.
            or (base_station_on is not None and not base_station_on)
            or dt_util.utcnow() - last_updated < STALE_ISSUE_AFTER
        ):
            ir.async_delete_issue(self.hass, DOMAIN, self.stale_issue_id)
            return

        device = dr.async_get(self.hass).async_get_device(
            identifiers={(DOMAIN, self.sock.serial)}
        )
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self.stale_issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="stale_data",
            translation_placeholders={
                "name": (device and (device.name_by_user or device.name))
                or f"Owlet Sock {self.sock.serial}",
                "last_updated": dt_util.as_local(last_updated).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            },
        )
