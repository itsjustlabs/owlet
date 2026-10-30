"""Validate the bundled dashboard (adapted from LucasVollebergh/owlet)."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import re
from typing import Any

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.template import Template
from homeassistant.util.yaml import load_yaml_dict

from . import async_init_integration

DASHBOARD = Path(__file__).parent.parent / "dashboards" / "owlet.yaml"
ENTITY_ID = re.compile(r"^(sensor|binary_sensor|switch)\.[a-z0-9_]+$")
TEMPLATE_ENTITY_ID = re.compile(r"'((?:sensor|binary_sensor|switch)\.[a-z0-9_]+)'")
# The prefix users replace; it matches the test sock's entity IDs.
PLACEHOLDER = "owlet_sock_serial_number"
# Only created on socks that report them; their cards stay hidden otherwise.
OPTIONAL = {
    f"binary_sensor.{PLACEHOLDER}_critical_oxygen_alert",
    f"binary_sensor.{PLACEHOLDER}_critical_battery_alert",
}


def _entity_ids(node: Any) -> Iterator[str]:
    """Yield every entity ID used anywhere in the dashboard."""
    if isinstance(node, dict):
        for value in node.values():
            yield from _entity_ids(value)
    elif isinstance(node, list):
        for value in node:
            yield from _entity_ids(value)
    elif isinstance(node, str) and ENTITY_ID.match(node):
        yield node


def _referenced() -> set[str]:
    """Return every entity ID in the dashboard, including inside templates."""
    return set(_entity_ids(load_yaml_dict(DASHBOARD))) | set(
        TEMPLATE_ENTITY_ID.findall(DASHBOARD.read_text())
    )


def test_dashboard_uses_placeholder() -> None:
    """Every entity ID starts with the prefix the README says to replace."""
    referenced = _referenced()
    assert referenced
    for entity_id in referenced:
        assert entity_id.split(".", 1)[1].startswith(f"{PLACEHOLDER}_"), entity_id


@pytest.mark.parametrize(
    ("properties_fixture", "expected"),
    [("update_properties_asleep.json", None), ("update_properties_v2.json", OPTIONAL)],
    ids=["sock_3", "sock_2_optional"],
)
async def test_dashboard_entities_exist(
    hass: HomeAssistant, properties_fixture: str, expected: set[str] | None
) -> None:
    """Every entity in the dashboard exists and is enabled by default."""
    await async_init_integration(hass, properties_fixture=properties_fixture)
    registry = er.async_get(hass)

    for entity_id in expected or _referenced() - OPTIONAL:
        entry = registry.async_get(entity_id)
        assert entry is not None, f"{entity_id} does not exist"
        assert not entry.disabled, f"{entity_id} is disabled by default"


def _markdown(node: Any) -> Iterator[str]:
    """Yield the content of every markdown card."""
    if isinstance(node, dict):
        if node.get("type") == "markdown":
            yield node["content"]
        for value in node.values():
            yield from _markdown(value)
    elif isinstance(node, list):
        for value in node:
            yield from _markdown(value)


@pytest.mark.parametrize(
    "properties_fixture",
    [
        "update_properties_asleep.json",
        "update_properties_awake.json",
        "update_properties_charging.json",
        "update_properties_v2.json",
    ],
)
async def test_dashboard_templates_render(
    hass: HomeAssistant, properties_fixture: str
) -> None:
    """Every markdown template renders, with or without a session."""
    await async_init_integration(hass, properties_fixture=properties_fixture)

    for content in _markdown(load_yaml_dict(DASHBOARD)):
        rendered = Template(content, hass).async_render(parse_result=False)
        assert "unknown" not in rendered.lower() or "unknown" in content, rendered
