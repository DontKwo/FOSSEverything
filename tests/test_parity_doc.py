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
def test_parity_doc_features() -> None:
    # Assert all documented features are mapped to UI controls or scenarios.
    doc_features = calc_load_json("doc_features.json")
    feature_map = calc_load_json("feature_map.json")

    unmapped: list[str] = []
    for feat_id, feat_info in doc_features.items():
        mapping = feature_map.get(feat_id)
        if not mapping:
            unmapped.append(f"{feat_id}: {feat_info.get('text', '')[:60]}")

    assert not unmapped, f"Unmapped document features ({len(unmapped)}):\n" + "\n".join(unmapped[:30])
