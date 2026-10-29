"""Config flow for Owlet Smart Sock integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_STALE_THRESHOLD,
    DEFAULT_TITLE,
    DOMAIN,
    POLLING_INTERVAL,
    STALE_AFTER,
)
from .pyowletapi.api import OwletAPI
from .pyowletapi.exceptions import (
    OwletConnectionError,
    OwletCredentialsError,
    OwletDevicesError,
)

_LOGGER = logging.getLogger(__name__)

REGION_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=["europe", "world"],
        translation_key="region",
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REGION): REGION_SELECTOR,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def _async_login(
    hass: HomeAssistant, region: str, username: str, password: str
) -> tuple[OwletAPI, dict[str, str]]:
    """Log in and check the account has socks; return the API and any form errors."""
    owlet_api = OwletAPI(
        region=region,
        user=username,
        password=password,
        session=async_get_clientsession(hass),
    )
    errors: dict[str, str] = {}
    try:
        await owlet_api.authenticate()
        await owlet_api.get_devices()
    except OwletDevicesError:
        errors["base"] = "no_devices"
    except OwletCredentialsError:
        errors["base"] = "invalid_credentials"
    except OwletConnectionError:
        errors["base"] = "cannot_connect"
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception")
        errors["base"] = "unknown"
    return owlet_api, errors


class OwletConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Owlet Smart Sock."""

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()

            owlet_api, errors = await _async_login(
                self.hass,
                user_input[CONF_REGION],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            if not errors:
                return self.async_create_entry(
                    title=DEFAULT_TITLE,
                    data={
                        CONF_REGION: user_input[CONF_REGION],
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        **owlet_api.tokens,
                    },
                    options={CONF_SCAN_INTERVAL: POLLING_INTERVAL},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the region or log in again without removing the entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            owlet_api, errors = await _async_login(
                self.hass,
                user_input[CONF_REGION],
                entry.data[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_REGION: user_input[CONF_REGION],
                        **owlet_api.tokens,
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_REGION, default=entry.data[CONF_REGION]
                    ): REGION_SELECTOR,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            description_placeholders={CONF_USERNAME: entry.data[CONF_USERNAME]},
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Dialog that informs the user that reauth is required."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            owlet_api = OwletAPI(
                region=reauth_entry.data[CONF_REGION],
                user=reauth_entry.data[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                session=async_get_clientsession(self.hass),
            )
            try:
                await owlet_api.authenticate()
            except OwletCredentialsError:
                errors[CONF_PASSWORD] = "invalid_password"
            except OwletConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Error reauthenticating")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry, data_updates=owlet_api.tokens
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={CONF_USERNAME: reauth_entry.data[CONF_USERNAME]},
            errors=errors,
        )


class OptionsFlowHandler(OptionsFlow):
    """Handle a options flow for owlet."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, POLLING_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=5)),
                vol.Required(
                    CONF_STALE_THRESHOLD,
                    default=self.config_entry.options.get(
                        CONF_STALE_THRESHOLD, int(STALE_AFTER.total_seconds() // 60)
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=120)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
