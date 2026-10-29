"""Test Owlet config flow."""
from __future__ import annotations

from unittest.mock import PropertyMock, patch

from custom_components.owlet.pyowletapi.exceptions import (
    OwletConnectionError,
    OwletCredentialsError,
    OwletDevicesError,
)

from homeassistant import config_entries
from custom_components.owlet.const import DOMAIN, POLLING_INTERVAL
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from . import async_init_integration
from .const import AUTH_RETURN, CONF_INPUT


async def test_form(hass: HomeAssistant) -> None:
    """Test that the form is served with no input."""
    # await async_init_integration(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.owlet.config_flow.OwletAPI.authenticate",
        return_value=AUTH_RETURN,
    ), patch(
        "custom_components.owlet.config_flow.OwletAPI.get_devices"
    ), patch(
        "custom_components.owlet.config_flow.OwletAPI.tokens",
        new_callable=PropertyMock,
        return_value=AUTH_RETURN,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONF_INPUT,
        )
        await hass.async_block_till_done()

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Owlet"
        assert result["data"] == {
            "region": "europe",
            "username": "sample@gmail.com",
            "api_token": "api_token",
            "expiry": 100,
            "refresh": "refresh_token",
        }
        assert result["options"] == {"scan_interval": POLLING_INTERVAL}


async def test_flow_connection_error(hass: HomeAssistant) -> None:
    """Test a network failure showing cannot_connect."""
    with patch(
        "custom_components.owlet.config_flow.OwletAPI.authenticate",
        side_effect=OwletConnectionError(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONF_INPUT,
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_flow_credentials_error(hass: HomeAssistant) -> None:
    """Test incorrect login throwing error."""
    with patch(
        "custom_components.owlet.config_flow.OwletAPI.authenticate",
        side_effect=OwletCredentialsError(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONF_INPUT,
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_credentials"}


async def test_flow_unknown_error(hass: HomeAssistant) -> None:
    """Test unknown error throwing error."""
    with patch(
        "custom_components.owlet.config_flow.OwletAPI.authenticate",
        side_effect=Exception(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONF_INPUT,
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


async def test_flow_no_devices(hass: HomeAssistant) -> None:
    """Test unknown error throwing error."""
    with patch(
        "custom_components.owlet.config_flow.OwletAPI.authenticate"
    ), patch(
        "custom_components.owlet.config_flow.OwletAPI.get_devices",
        side_effect=OwletDevicesError(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONF_INPUT,
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "no_devices"}


async def test_reauth_success(hass: HomeAssistant) -> None:
    """Test reauth form."""

    entry = await async_init_integration(hass, skip_setup=True)

    result = await entry.start_reauth_flow(hass)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "custom_components.owlet.config_flow.OwletAPI.authenticate",
        return_value=AUTH_RETURN,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_PASSWORD: "sample"},
        )
        await hass.async_block_till_done()

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"

        await hass.config_entries.async_unload(entry.entry_id)


async def test_reauth_invalid_password(hass: HomeAssistant) -> None:
    """Test reauth with invalid password errir."""
    entry = await async_init_integration(hass, skip_setup=True)

    result = await entry.start_reauth_flow(hass)

    with patch(
        "custom_components.owlet.config_flow.OwletAPI.authenticate",
        side_effect=OwletCredentialsError(),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PASSWORD: "sample"}
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"
        assert result["errors"] == {"password": "invalid_password"}


async def test_reauth_unknown_error(hass: HomeAssistant) -> None:
    """Test reauthing with an unknown error."""

    entry = await async_init_integration(hass, skip_setup=True)

    result = await entry.start_reauth_flow(hass)

    with patch(
        "custom_components.owlet.config_flow.OwletAPI.authenticate",
        side_effect=Exception(),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PASSWORD: "sample"}
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test that the form is served with no input."""
    entry = await async_init_integration(hass, skip_setup=True)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 10},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == ""
    assert result["data"] == {CONF_SCAN_INTERVAL: 10}


async def test_reconfigure_changes_region(hass: HomeAssistant) -> None:
    """Test reconfigure logs in again and saves the new region and tokens."""
    entry = await async_init_integration(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["description_placeholders"] == {"username": "sample@gmail.com"}

    with patch(
        "custom_components.owlet.config_flow.OwletAPI.authenticate"
    ) as authenticate, patch(
        "custom_components.owlet.config_flow.OwletAPI.get_devices"
    ), patch(
        "custom_components.owlet.config_flow.OwletAPI.tokens",
        new_callable=PropertyMock,
        return_value={"api_token": "new", "expiry": 300, "refresh": "new_refresh"},
    ), patch("custom_components.owlet.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"region": "world", CONF_PASSWORD: "pw"}
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert authenticate.call_count == 1
    assert entry.data["region"] == "world"
    assert entry.data["api_token"] == "new"
    assert entry.data["username"] == "sample@gmail.com"


async def test_reconfigure_bad_password(hass: HomeAssistant) -> None:
    """Test reconfigure shows an error and keeps the entry when login fails."""
    entry = await async_init_integration(hass)
    result = await entry.start_reconfigure_flow(hass)

    with patch(
        "custom_components.owlet.config_flow.OwletAPI.authenticate",
        side_effect=OwletCredentialsError(),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"region": "world", CONF_PASSWORD: "bad"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_credentials"}
    assert entry.data["region"] == "europe"
