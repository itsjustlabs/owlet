"""Test the bundled Owlet API client."""
from __future__ import annotations

from http import HTTPStatus
import time

from aiohttp import ClientConnectionError
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)

from custom_components.owlet.pyowletapi.api import OwletAPI
from custom_components.owlet.pyowletapi.const import REGION_INFO
from custom_components.owlet.pyowletapi.exceptions import (
    OwletAuthenticationError,
    OwletConnectionError,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

REGION = REGION_INFO["europe"]
BASE = REGION["url_base"]
ACTIVATE_URL = f"{BASE}/dsns/SERIAL/properties/APP_ACTIVE/datapoints.json"
PROPERTIES_URL = f"{BASE}/dsns/SERIAL/properties.json"
PROPERTIES_BODY = [{"property": {"name": "CHARGE_STATUS", "value": 1}}]


def _api(hass: HomeAssistant, expiry: float) -> OwletAPI:
    return OwletAPI(
        region="europe",
        token="old_token",
        expiry=expiry,
        refresh="refresh_token",
        session=async_get_clientsession(hass),
    )


def _mock_refresh(aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.post(
        "https://securetoken.googleapis.com/v1/token",
        json={"refresh_token": "refresh_token", "id_token": "id_token"},
    )
    aioclient_mock.get(REGION["url_mini"], json={"mini_token": "mini_token"})
    aioclient_mock.post(
        REGION["url_signin"], json={"access_token": "new_token", "expires_in": 86400}
    )


async def test_valid_token_makes_no_extra_requests(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A poll with a valid token is just activate + read, with no login probe."""
    aioclient_mock.post(ACTIVATE_URL, json={})
    aioclient_mock.get(PROPERTIES_URL, json=PROPERTIES_BODY)

    response = await _api(hass, time.time() + 3600).get_properties("SERIAL")

    assert response == {"response": {"CHARGE_STATUS": PROPERTIES_BODY[0]["property"]}}
    assert [call[1].path for call in aioclient_mock.mock_calls] == [
        "/apiv1/dsns/SERIAL/properties/APP_ACTIVE/datapoints.json",
        "/apiv1/dsns/SERIAL/properties.json",
    ]


async def test_expired_token_refreshes_and_returns_tokens(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """An expired token is refreshed once and the new tokens reach the caller."""
    _mock_refresh(aioclient_mock)
    aioclient_mock.post(ACTIVATE_URL, json={})
    aioclient_mock.get(PROPERTIES_URL, json=PROPERTIES_BODY)
    api = _api(hass, time.time() - 1)

    response = await api.get_properties("SERIAL")

    assert response["tokens"]["api_token"] == "new_token"
    assert aioclient_mock.call_count == 5
    # The next poll does not report the same tokens again.
    assert "tokens" not in await api.get_properties("SERIAL")


async def test_rejected_token_refreshes_and_retries(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 401 from Owlet triggers one refresh and a retry of the same request."""
    statuses = iter([HTTPStatus.UNAUTHORIZED, HTTPStatus.OK])

    async def activate(method, url, data):
        return AiohttpClientMockResponse(method, url, status=next(statuses), json={})

    _mock_refresh(aioclient_mock)
    aioclient_mock.post(ACTIVATE_URL, side_effect=activate)

    api = _api(hass, time.time() + 3600)
    await api.activate("SERIAL")

    assert api.tokens["api_token"] == "new_token"
    assert api.headers["Authorization"] == "auth_token new_token"
    paths = [call[1].path for call in aioclient_mock.mock_calls]
    assert paths.count("/apiv1/dsns/SERIAL/properties/APP_ACTIVE/datapoints.json") == 2
    assert paths.count("/api/v1/token_sign_in") == 1


async def test_rejected_after_refresh_is_auth_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """If Owlet still rejects the refreshed token, report an auth failure."""
    _mock_refresh(aioclient_mock)
    aioclient_mock.post(ACTIVATE_URL, status=HTTPStatus.UNAUTHORIZED)

    with pytest.raises(OwletAuthenticationError):
        await _api(hass, time.time() + 3600).activate("SERIAL")


@pytest.mark.parametrize("exc", [TimeoutError(), ClientConnectionError()])
async def test_network_errors_are_connection_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, exc: Exception
) -> None:
    """Timeouts and client errors surface as OwletConnectionError."""
    aioclient_mock.post(ACTIVATE_URL, exc=exc)

    with pytest.raises(OwletConnectionError):
        await _api(hass, time.time() + 3600).activate("SERIAL")


async def test_network_error_during_login_is_connection_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A timeout while logging in is a connection problem, not bad credentials."""
    aioclient_mock.post(
        "https://securetoken.googleapis.com/v1/token", exc=TimeoutError()
    )

    with pytest.raises(OwletConnectionError):
        await _api(hass, time.time() - 1).authenticate()
