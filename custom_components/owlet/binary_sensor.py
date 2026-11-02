"""Support for Owlet binary sensors."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import OwletConfigEntry, OwletCoordinator
from .entity import OwletBaseEntity


@dataclass(kw_only=True)
class OwletBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Represent the owlet binary sensor entity description."""

    available_during_charging: bool


SENSORS: tuple[OwletBinarySensorEntityDescription, ...] = (
    OwletBinarySensorEntityDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="high_heart_rate_alert",
        translation_key="high_hr_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="low_heart_rate_alert",
        translation_key="low_hr_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="high_oxygen_alert",
        translation_key="high_ox_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="low_oxygen_alert",
        translation_key="low_ox_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="critical_oxygen_alert",
        translation_key="crit_ox_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="low_battery_alert",
        translation_key="low_batt_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="critical_battery_alert",
        translation_key="crit_batt_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="lost_power_alert",
        translation_key="lost_pwr_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="sock_disconnected",
        translation_key="sock_discon_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="discomfort_alert",
        translation_key="discomfort_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    # On when the sock is on but can't get a reading (the app's yellow
    # "low signal" notification), so heart rate and oxygen read 0.
    OwletBinarySensorEntityDescription(
        key="low_integrity_read",
        translation_key="low_signal",
        device_class=BinarySensorDeviceClass.PROBLEM,
        available_during_charging=False,
    ),
    # Owlet's own alarm priority flags. What each level covers isn't
    # documented, so they start disabled.
    OwletBinarySensorEntityDescription(
        key="high_priority_alarm",
        translation_key="high_priority_alarm",
        device_class=BinarySensorDeviceClass.SOUND,
        entity_registry_enabled_default=False,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="medium_priority_alarm",
        translation_key="medium_priority_alarm",
        device_class=BinarySensorDeviceClass.SOUND,
        entity_registry_enabled_default=False,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="low_priority_alarm",
        translation_key="low_priority_alarm",
        device_class=BinarySensorDeviceClass.SOUND,
        entity_registry_enabled_default=False,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="sock_off",
        translation_key="sock_off",
        device_class=BinarySensorDeviceClass.POWER,
        available_during_charging=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: OwletConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the owlet sensors from config entry."""

    coordinators = config_entry.runtime_data.values()

    sensors = []
    for coordinator in coordinators:
        sensors.extend([
            OwletBinarySensor(coordinator, sensor)
            for sensor in SENSORS
            if sensor.key in coordinator.sock.properties
        ])

        if OwletAwakeSensor.entity_description.key in coordinator.sock.properties:
            sensors.append(OwletAwakeSensor(coordinator))
        if "last_updated" in coordinator.sock.properties:
            sensors.append(OwletStaleDataSensor(coordinator))
        if "sleep_state" in coordinator.sock.properties:
            sensors.append(OwletSleepSessionSensor(coordinator))

    async_add_entities(sensors)


class OwletBinarySensor(OwletBaseEntity, BinarySensorEntity):
    """Representation of an Owlet binary sensor."""

    def __init__(
        self,
        coordinator: OwletCoordinator,
        description: OwletBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self.sock.serial}-{description.key}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and (
            not self.sock.properties.get("charging")
            or self.entity_description.available_during_charging
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""

        return self.sock.properties.get(self.entity_description.key)


class OwletAwakeSensor(OwletBinarySensor):
    """Representation of an Owlet sleep sensor."""

    entity_description = OwletBinarySensorEntityDescription(
        key="sleep_state",
        translation_key="awake",
        available_during_charging=False,
    )

    def __init__(
        self,
        coordinator: OwletCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, self.entity_description)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and not self.coordinator.vitals_stale

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        sleep_state = self.sock.properties.get(self.entity_description.key)
        if sleep_state is None:
            return None
        return sleep_state not in [8, 15]


class OwletStaleDataSensor(OwletBinarySensor):
    """On when Owlet has stopped updating the sock's live readings."""

    entity_description = OwletBinarySensorEntityDescription(
        key="stale_data",
        translation_key="stale_data",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        available_during_charging=True,
    )

    def __init__(
        self,
        coordinator: OwletCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, self.entity_description)

    @property
    def is_on(self) -> bool:
        """Return true if the readings are stale."""
        return self.coordinator.vitals_stale


class OwletSleepSessionSensor(OwletBaseEntity, BinarySensorEntity):
    """On while a sleep session is in progress."""

    _attr_translation_key = "sleep_session"

    def __init__(self, coordinator: OwletCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.sock.serial}-sleep_session"

    @property
    def is_on(self) -> bool:
        """Return true while a session is in progress."""
        return self.coordinator.session.active
