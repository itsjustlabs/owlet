"""Test icons.json matches the integration's entities."""
from __future__ import annotations

import json
from pathlib import Path

INTEGRATION = Path(__file__).parent.parent / "custom_components" / "owlet"


def test_icons_match_entities() -> None:
    """Every icon is for an entity, and every enum state icon is a real state."""
    icons = json.loads((INTEGRATION / "icons.json").read_text())["entity"]
    strings = json.loads((INTEGRATION / "strings.json").read_text())["entity"]

    for platform, entities in icons.items():
        for key, icon in entities.items():
            assert key in strings[platform], f"{platform}.{key} has no entity"
            assert icon["default"].startswith("mdi:")
            states = strings[platform][key].get("state", {"on": "", "off": ""})
            for state in icon.get("state", {}):
                assert state in states, f"{platform}.{key} has no state {state}"
