import json
from pathlib import Path
from typing import Any

import pytest


def calc_load_json(filename: str) -> Any:
    # Load JSON file from tests/parity directory.
    path = Path(__file__).parent / "parity" / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


DOC_FEATURES = calc_load_json("doc_features.json")
SECTIONS = sorted(list({k.split("-")[0] for k in DOC_FEATURES.keys()}))


@pytest.mark.parametrize("section", SECTIONS)
def test_parity_doc_features(section: str) -> None:
    # Assert all documented features for section are mapped to UI controls.
    feature_map = calc_load_json("feature_map.json")
    unmapped: list[str] = []

    for feat_id, feat_info in DOC_FEATURES.items():
        if feat_id.startswith(f"{section}-"):
            mapping = feature_map.get(feat_id)
            if not mapping:
                unmapped.append(f"{feat_id}: {feat_info.get('text', '')[:60]}")

    assert not unmapped, f"Unmapped document features in {section} ({len(unmapped)}):\n" + "\n".join(unmapped[:30])
