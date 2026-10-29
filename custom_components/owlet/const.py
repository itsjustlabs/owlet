"""Constants for the Owlet Smart Sock integration."""

from datetime import timedelta

DOMAIN = "owlet"
# Entry titles show up in Home Assistant's logs, so don't use the email.
DEFAULT_TITLE = "Owlet"

CONF_OWLET_EXPIRY = "expiry"
CONF_OWLET_REFRESH = "refresh"

SUPPORTED_VERSIONS = [2, 3]
POLLING_INTERVAL = 5
# Owlet keeps returning the last readings when the base station stops
# relaying them, so treat vitals older than this as no longer live.
STALE_AFTER = timedelta(minutes=2)
MANUFACTURER = "Owlet Baby Care"
SLEEP_STATES = {0: "unknown", 1: "awake", 8: "light_sleep", 15: "deep_sleep"}
MONITORING_STATES = [
    "monitoring",
    "low_signal",
    "base_station_off",
    "stale",
    "charging",
    "charged",
]
