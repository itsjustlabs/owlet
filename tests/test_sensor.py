"""Test Owlet Sensor."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from . import async_init_integration


async def test_sensors_asleep(hass: HomeAssistant) -> None:
    """Test sensor values."""
    await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )

    assert len(hass.states.async_all("sensor")) == 11

    assert (
        hass.states.get("sensor.owlet_sock_serial_number_battery_percentage").state
        == "50.0"
    )
    assert (
        hass.states.get("sensor.owlet_sock_serial_number_battery_remaining").state
        == "400.0"
    )
    assert hass.states.get("sensor.owlet_sock_serial_number_heart_rate").state == "97.0"
    assert hass.states.get("sensor.owlet_sock_serial_number_o2_saturation").state == "99.0"
    assert (
        hass.states.get(
            "sensor.owlet_sock_serial_number_o2_saturation_10_minute_average"
        ).state
        == "97.0"
    )

    assert (
        hass.states.get("sensor.owlet_sock_serial_number_signal_strength").state == "30.0"
    )
    assert hass.states.get("sensor.owlet_sock_serial_number_skin_temperature").state == "34"
    assert (
        hass.states.get("sensor.owlet_sock_serial_number_sleep_state").state
        == "light_sleep"
    )


async def test_sensors_awake(hass: HomeAssistant) -> None:
    """Test sensor values."""
    await async_init_integration(
        hass, properties_fixture="update_properties_awake.json"
    )

    assert len(hass.states.async_all("sensor")) == 11

    assert (
        hass.states.get("sensor.owlet_sock_serial_number_battery_percentage").state
        == "80.0"
    )
    assert (
        hass.states.get("sensor.owlet_sock_serial_number_battery_remaining").state
        == "600.0"
    )
    assert hass.states.get("sensor.owlet_sock_serial_number_heart_rate").state == "110.0"
    assert hass.states.get("sensor.owlet_sock_serial_number_o2_saturation").state == "98.0"
    assert (
        hass.states.get(
            "sensor.owlet_sock_serial_number_o2_saturation_10_minute_average"
        ).state
        == "98.0"
    )
    assert (
        hass.states.get("sensor.owlet_sock_serial_number_signal_strength").state == "34.0"
    )
    assert hass.states.get("sensor.owlet_sock_serial_number_skin_temperature").state == "35"
    assert hass.states.get("sensor.owlet_sock_serial_number_sleep_state").state == "awake"


async def test_sensors_charging(hass: HomeAssistant) -> None:
    """Test sensor values."""
    await async_init_integration(
        hass, properties_fixture="update_properties_charging.json"
    )

    assert len(hass.states.async_all("sensor")) == 11

    assert (
        hass.states.get("sensor.owlet_sock_serial_number_battery_percentage").state
        == "100.0"
    )
    assert (
        hass.states.get("sensor.owlet_sock_serial_number_battery_remaining").state
        == "unavailable"
    )
    assert hass.states.get("sensor.owlet_sock_serial_number_heart_rate").state == "unavailable"
    assert (
        hass.states.get("sensor.owlet_sock_serial_number_o2_saturation").state == "unavailable"
    )
    assert (
        hass.states.get(
            "sensor.owlet_sock_serial_number_o2_saturation_10_minute_average"
        ).state
        == "unavailable"
    )

    assert (
        hass.states.get("sensor.owlet_sock_serial_number_signal_strength").state == "34.0"
    )
    assert (
        hass.states.get("sensor.owlet_sock_serial_number_skin_temperature").state
        == "unavailable"
    )
    assert hass.states.get("sensor.owlet_sock_serial_number_sleep_state").state == "unavailable"


async def test_sensors_v2(hass: HomeAssistant) -> None:
    """Test sensor values."""
    await async_init_integration(hass, properties_fixture="update_properties_v2.json")
    assert len(hass.states.async_all("sensor")) == 5

    assert (
        hass.states.get("sensor.owlet_sock_serial_number_battery_percentage").state == "29"
    )
    assert hass.states.get("sensor.owlet_sock_serial_number_heart_rate").state == "145"
    assert hass.states.get("sensor.owlet_sock_serial_number_o2_saturation").state == "99"

    assert (
        hass.states.get("sensor.owlet_sock_serial_number_signal_strength").state == "98.0"
    )

