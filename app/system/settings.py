import json
import os
from pathlib import Path
import sys
from typing import Any


def calc_app_base_dir() -> Path:
    # Resolve root base directory for application assets.
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def calc_settings_dir() -> str:
    # Resolve settings directory path respecting environment override.
    env_dir = os.environ.get("FOSS_SETTINGS_DIR")
    if env_dir:
        return env_dir
    return os.path.join(os.path.expanduser("~"), ".fosseverything")


def calc_settings_file() -> str:
    # Resolve settings JSON file path.
    return os.path.join(calc_settings_dir(), "settings.json")


def calc_read_settings() -> dict[str, Any]:
    # Read settings dictionary from JSON storage file.
    file_path = calc_settings_file()
    if not os.path.isfile(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def calc_write_settings(data: dict[str, Any]) -> None:
    # Write settings dictionary to JSON storage file.
    os.makedirs(calc_settings_dir(), exist_ok=True)
    with open(calc_settings_file(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_setting(key: str, default: Any = None) -> Any:
    # Retrieve setting value by key with fallback default.
    data = calc_read_settings()
    return data.get(key, default)


def set_setting(key: str, value: Any) -> None:
    # Persist setting key and value to local settings store.
    data = calc_read_settings()
    data[key] = value
    calc_write_settings(data)


def get_all_settings() -> dict[str, Any]:
    # Return full dictionary of stored settings.
    return calc_read_settings()


def reset_all_settings() -> None:
    # Reset all stored settings by removing the settings file.
    file_path = calc_settings_file()
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError as err:
            _ = err
