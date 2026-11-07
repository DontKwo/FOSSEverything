import json
from pathlib import Path
from typing import Any

import pytest


def calc_load_json(filename: str) -> Any:
    # Load JSON file from tests/parity directory.
    path = Path(__file__).parent / "parity" / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


QT_INV = calc_load_json("qt_inventory.json")


@pytest.mark.parametrize("tool_key", list(QT_INV.keys()))
def test_parity_ui_strings(tool_key: str) -> None:
    # Assert every Qt string exists in rendered tool views or label map.
    categories = QT_INV.get(tool_key, {})
    label_map = calc_load_json("label_map.json")
    missing_labels: list[str] = []

    all_rendered = ""
    tools_dir = Path("app/web/js")
    for p in tools_dir.rglob("*.js"):
        all_rendered += "\n" + p.read_text(encoding="utf-8", errors="replace").lower()

    for cat in ("buttons", "checks", "radios", "groups", "tabs", "combo_items"):
        for label in categories.get(cat, []):
            clean = label.strip().lower()
            if "{" in clean or not clean:
                continue
            if clean in label_map or label in label_map or clean in all_rendered:
                continue
            missing_labels.append(f"{tool_key} [{cat}]: {label}")

    assert not missing_labels, f"Unmapped UI labels ({len(missing_labels)}):\n" + "\n".join(missing_labels[:30])
