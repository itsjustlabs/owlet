"""Test Owlet Sensor."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from . import async_init_integration


async def test_sensors_asleep(hass: HomeAssistant) -> None:
    """Test sensor values."""
    await async_init_integration(
        hass, properties_fixture="update_properties_asleep.json"
    )

    assert len(hass.states.async_all("binary_sensor")) == 14

    assert hass.states.get("binary_sensor.owlet_sock_serial_number_charging").state == "off"
    assert (
        hass.states.get(
            "binary_sensor.owlet_sock_serial_number_high_heart_rate_alert"
        ).state
        == "off"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_low_heart_rate_alert").state
        == "off"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_high_oxygen_alert").state
        == "off"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_low_oxygen_alert").state
        == "off"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_low_battery_alert").state
        == "off"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_lost_power_alert").state
        == "off"
    )
    assert (
        hass.states.get(
            "binary_sensor.owlet_sock_serial_number_sock_disconnected_alert"
        ).state
        == "off"
    )
    assert hass.states.get("binary_sensor.owlet_sock_serial_number_sock_off").state == "off"
    assert hass.states.get("binary_sensor.owlet_sock_serial_number_awake").state == "off"


async def test_sensors_awake(hass: HomeAssistant) -> None:
    """Test sensor values."""
    await async_init_integration(
        hass, properties_fixture="update_properties_awake.json"
    )

    assert len(hass.states.async_all("binary_sensor")) == 14

    assert hass.states.get("binary_sensor.owlet_sock_serial_number_charging").state == "off"
    assert (
        hass.states.get(
            "binary_sensor.owlet_sock_serial_number_high_heart_rate_alert"
        ).state
        == "on"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_low_heart_rate_alert").state
        == "on"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_high_oxygen_alert").state
        == "on"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_low_oxygen_alert").state
        == "on"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_low_battery_alert").state
        == "on"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_lost_power_alert").state
        == "on"
    )
    assert (
        hass.states.get(
            "binary_sensor.owlet_sock_serial_number_sock_disconnected_alert"
        ).state
        == "off"
    )
    assert hass.states.get("binary_sensor.owlet_sock_serial_number_sock_off").state == "off"
    assert hass.states.get("binary_sensor.owlet_sock_serial_number_awake").state == "on"


async def test_sensors_charging(hass: HomeAssistant) -> None:
    """Test sensor values."""
    await async_init_integration(
        hass, properties_fixture="update_properties_charging.json"
    )

    assert len(hass.states.async_all("binary_sensor")) == 14

    assert hass.states.get("binary_sensor.owlet_sock_serial_number_charging").state == "on"
    assert (
        hass.states.get(
            "binary_sensor.owlet_sock_serial_number_high_heart_rate_alert"
        ).state
        == "off"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_low_heart_rate_alert").state
        == "off"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_high_oxygen_alert").state
        == "off"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_low_oxygen_alert").state
        == "off"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_low_battery_alert").state
        == "off"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_lost_power_alert").state
        == "off"
    )
    assert (
        hass.states.get(
            "binary_sensor.owlet_sock_serial_number_sock_disconnected_alert"
        ).state
        == "off"
    )
    assert hass.states.get("binary_sensor.owlet_sock_serial_number_sock_off").state == "off"
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_awake").state == "unavailable"
    )


async def test_sensors_v2(hass: HomeAssistant) -> None:
    """Test sensor values."""
    await async_init_integration(hass, properties_fixture="update_properties_v2.json")
    assert len(hass.states.async_all("binary_sensor")) == 11

    assert hass.states.get("binary_sensor.owlet_sock_serial_number_charging").state == "off"
    assert (
        hass.states.get(
            "binary_sensor.owlet_sock_serial_number_high_heart_rate_alert"
        ).state
        == "off"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_low_heart_rate_alert").state
        == "off"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_low_oxygen_alert").state
        == "off"
    )
    assert (
        hass.states.get("binary_sensor.owlet_sock_serial_number_low_battery_alert").state
        == "off"
    )
    assert (
        hass.states.get(
            "binary_sensor.owlet_sock_serial_number_critical_battery_alert"
        ).state
        == "off"
    )
    assert (
        hass.states.get(
            "binary_sensor.owlet_sock_serial_number_critical_oxygen_alert"
        ).state
        == "off"
    )
    assert (
        hass.states.get(
            "binary_sensor.owlet_sock_serial_number_sock_disconnected_alert"
        ).state
        == "off"
    )
    assert hass.states.get("binary_sensor.owlet_sock_serial_number_sock_off").state == "off"
