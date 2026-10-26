"""Local JSON-based application settings manager replacing QSettings."""
from __future__ import annotations

import json
import os
from typing import Any

_SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".fosseverything")
_SETTINGS_FILE = os.path.join(_SETTINGS_DIR, "settings.json")


def _read_settings() -> dict[str, Any]:
    if not os.path.isfile(_SETTINGS_FILE):
        return {}
    try:
        with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_settings(data: dict[str, Any]) -> None:
    os.makedirs(_SETTINGS_DIR, exist_ok=True)
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_setting(key: str, default: Any = None) -> Any:
    """Retrieve setting value by key with fallback default."""
    data = _read_settings()
    return data.get(key, default)


def set_setting(key: str, value: Any) -> None:
    """Persist setting key and value to local settings store."""
    data = _read_settings()
    data[key] = value
    _write_settings(data)

