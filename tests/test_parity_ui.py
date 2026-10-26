import json
from pathlib import Path
from typing import Any

import pytest


def calc_load_json(filename: str) -> Any:
    # Load JSON file from tests/parity directory.
    path = Path(__file__).parent / "parity" / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.skip(reason="Awaiting Phase 2 UI test harness")
def test_parity_ui_strings() -> None:
    # Assert every Qt string exists in rendered tool views or label map.
    qt_inv = calc_load_json("qt_inventory.json")
    label_map = calc_load_json("label_map.json")
    missing_labels: list[str] = []

    for file_path, categories in qt_inv.items():
        for cat in ("buttons", "checks", "radios", "groups", "tabs", "combo_items"):
            for label in categories.get(cat, []):
                if "{" in label:
                    continue
                if label not in label_map:
                    missing_labels.append(f"{file_path} [{cat}]: {label}")

    assert not missing_labels, f"Unmapped UI labels ({len(missing_labels)}):\n" + "\n".join(missing_labels[:30])
