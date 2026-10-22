"""Fixtures for the Owlet tests."""
from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
import pytest

# The v3 fixtures' REAL_TIME_VITALS were last updated at 2023-05-24T14:15:50Z.
FIXTURE_NOW = "2023-05-24T14:16:00+00:00"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the custom_components/owlet integration in every test."""


@pytest.fixture(autouse=True)
def frozen_time(freezer: FrozenDateTimeFactory) -> FrozenDateTimeFactory:
    """Keep the fixtures' vitals fresh unless a test moves the clock."""
    freezer.move_to(FIXTURE_NOW)
    return freezer
