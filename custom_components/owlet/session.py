"""Track sleep sessions from the sock's sleep state.

Owlet works out sleep sessions in its own backend, and the API this
integration uses doesn't return them. So a session here starts when the sock
begins reporting a sleep state, and ends when the sock goes on the charger or
stops sending live readings for SESSION_GAP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

AWAKE = 1
SLEEP_STATE_KEYS = {AWAKE: "awake", 8: "light_sleep", 15: "deep_sleep"}

# Live readings missing for longer than this end the session.
SESSION_GAP = timedelta(minutes=30)
# A longer gap between two polls isn't counted towards any sleep state,
# because the readings in between were missed.
MAX_CREDIT = timedelta(minutes=5)
# Brief awake readings are noise, so a waking counts once it lasts this long.
WAKING_AFTER = timedelta(minutes=2)

STORAGE_VERSION = 1
SAVE_DELAY = 60


def _empty_seconds() -> dict[str, float]:
    return dict.fromkeys(SLEEP_STATE_KEYS.values(), 0.0)


def _to_datetime(value: str | None) -> datetime | None:
    return dt_util.parse_datetime(value) if value else None


def _to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@dataclass
class SleepSession:
    """The current or most recent sleep session of one sock."""

    started: datetime | None = None
    ended: datetime | None = None
    # The last poll that had a sleep state, and that state.
    last_seen: datetime | None = None
    last_state: int | None = None
    seconds: dict[str, float] = field(default_factory=_empty_seconds)
    wakings: int = 0
    has_slept: bool = False
    awake_since: datetime | None = None
    waking_counted: bool = False

    @property
    def active(self) -> bool:
        """Return True while a session is in progress."""
        return self.started is not None and self.ended is None

    def minutes(self, *states: str) -> int | None:
        """Return whole minutes spent in the given sleep states."""
        if self.started is None:
            return None
        return int(sum(self.seconds[state] for state in states) // 60)

    def update(
        self, now: datetime, sleep_state: int | None, live: bool, charging: bool
    ) -> bool:
        """Add one poll to the session. Return True if anything changed."""
        if charging or not live or sleep_state not in SLEEP_STATE_KEYS:
            if self.active and (charging or now - self.last_seen > SESSION_GAP):
                self.ended = self.last_seen
                return True
            return False

        if not self.active or now - self.last_seen > SESSION_GAP:
            self._start(now)
        elif now - self.last_seen <= MAX_CREDIT:
            self.seconds[SLEEP_STATE_KEYS[self.last_state]] += (
                now - self.last_seen
            ).total_seconds()

        if sleep_state == AWAKE:
            if self.last_state != AWAKE:
                self.awake_since = now
                self.waking_counted = False
            if (
                self.has_slept
                and not self.waking_counted
                and now - self.awake_since >= WAKING_AFTER
            ):
                self.wakings += 1
                self.waking_counted = True
        else:
            self.has_slept = True

        self.last_seen = now
        self.last_state = sleep_state
        return True

    def _start(self, now: datetime) -> None:
        self.started = now
        self.ended = None
        self.last_state = None
        self.seconds = _empty_seconds()
        self.wakings = 0
        self.has_slept = False
        self.awake_since = None
        self.waking_counted = False

    def as_dict(self) -> dict[str, Any]:
        """Return the session for storage."""
        return {
            "started": _to_iso(self.started),
            "ended": _to_iso(self.ended),
            "last_seen": _to_iso(self.last_seen),
            "last_state": self.last_state,
            "seconds": self.seconds,
            "wakings": self.wakings,
            "has_slept": self.has_slept,
            "awake_since": _to_iso(self.awake_since),
            "waking_counted": self.waking_counted,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SleepSession:
        """Restore a stored session."""
        return cls(
            started=_to_datetime(data.get("started")),
            ended=_to_datetime(data.get("ended")),
            last_seen=_to_datetime(data.get("last_seen")),
            last_state=data.get("last_state"),
            seconds={**_empty_seconds(), **data.get("seconds", {})},
            wakings=data.get("wakings", 0),
            has_slept=data.get("has_slept", False),
            awake_since=_to_datetime(data.get("awake_since")),
            waking_counted=data.get("waking_counted", False),
        )


class SessionStore:
    """Keep each sock's session across Home Assistant restarts."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialise the store for one config entry."""
        self._store: Store[dict[str, dict[str, Any]]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}"
        )
        self._sessions: dict[str, SleepSession] = {}
        self._save_scheduled = False

    async def async_load(self) -> None:
        """Load the stored sessions."""
        data = await self._store.async_load() or {}
        self._sessions = {
            serial: SleepSession.from_dict(session) for serial, session in data.items()
        }

    def get(self, serial: str) -> SleepSession:
        """Return the session for a sock, creating an empty one."""
        return self._sessions.setdefault(serial, SleepSession())

    @callback
    def async_schedule_save(self) -> None:
        """Save within SAVE_DELAY seconds, and when Home Assistant stops."""
        # Store.async_delay_save restarts its timer on every call, so with
        # polls every few seconds it would never write until shutdown.
        if self._save_scheduled:
            return
        self._save_scheduled = True
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)

    @callback
    def _data_to_save(self) -> dict[str, dict[str, Any]]:
        self._save_scheduled = False
        return {
            serial: session.as_dict() for serial, session in self._sessions.items()
        }

    async def async_save(self) -> None:
        """Save now, such as before the entry reloads."""
        await self._store.async_save(self._data_to_save())

    async def async_remove(self) -> None:
        """Delete the stored sessions."""
        await self._store.async_remove()
