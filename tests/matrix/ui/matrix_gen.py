import json
from pathlib import Path
import random
from typing import Any

from tests.matrix.common.fixture_factory import ALL_FAMILIES, ALL_VARIANTS, FixtureFactory

TOOL_ACCEPT_FAMILIES: dict[str, list[str]] = {
    "archive": ["zip", "tar", "gz", "7z"],
    "collage": ["png", "jpg", "webp"],
    "compressor": ["pdf", "mp4", "png", "mp3"],
    "converter": ["docx", "pdf", "xlsx", "pptx", "png", "jpg"],
    "data": ["json", "yaml", "xml", "csv", "toml"],
    "encoding": ["txt", "json", "png"],
    "images": ["png", "jpg", "webp", "bmp", "tiff"],
    "markdown": ["md", "txt"],
    "media": ["mp4", "mov", "mkv", "mp3", "wav"],
    "metadata": ["jpg", "png", "mp4", "pdf", "docx"],
    "model3d": ["stl", "obj", "ply", "gltf"],
    "network_monitor": ["txt"],
    "ocr": ["png", "jpg", "pdf"],
    "palette": ["png", "jpg", "webp"],
    "pdf": ["pdf"],
    "playlist": ["m3u8", "m3u"],
    "qr": ["qr", "png"],
    "renamer": ["png", "jpg", "txt", "pdf"],
    "resume": ["json", "txt"],
    "text_tools": ["txt", "md"],
    "unit_converter": ["txt"],
}

WRONG_FAMILIES = ["stl", "mp4", "h5", "7z", "ics"]


def build_ui_cases(
    inventory: dict[str, list[dict[str, Any]]],
    factory: FixtureFactory,
    tool_filter: str | None = None,
    control_filter: str | None = None,
    fixture_kind_filter: str | None = None,
    smoke: bool = False,
    seed: int = 42,
) -> list[dict[str, Any]]:
    # Generate test matrix cases: Tool x Mode x Control x Fixture variants + Sequences + Chaos.
    rng = random.Random(seed)
    cases: list[dict[str, Any]] = []

    tools_to_run = [tool_filter] if tool_filter and tool_filter in inventory else sorted(list(inventory.keys()))

    for tool in tools_to_run:
        ctrls = inventory[tool]
        if control_filter:
            ctrls = [c for c in ctrls if control_filter in c.get("testid", "")]

        acc_fams = TOOL_ACCEPT_FAMILIES.get(tool, ["txt"])

        # 1. Standard Control x Fixture cases
        target_ctrls = ctrls if not smoke else ctrls[:4]
        for ctrl in target_ctrls:
            # Pair with valid fixture
            fam = acc_fams[0]
            var = "typical"
            if fixture_kind_filter and fixture_kind_filter not in var:
                continue

            cases.append({
                "type": "control_click",
                "tool": tool,
                "mode": ctrl.get("mode", "main"),
                "control": ctrl,
                "fixture_family": fam,
                "fixture_variant": var,
                "description": f"Click {ctrl.get('testid')} with {fam}_{var}",
            })

            # Add wrong-typed / chaos variant for non-smoke or sampled
            if not smoke and rng.random() < 0.2:
                wrong_fam = WRONG_FAMILIES[rng.randint(0, len(WRONG_FAMILIES) - 1)]
                cases.append({
                    "type": "control_click",
                    "tool": tool,
                    "mode": ctrl.get("mode", "main"),
                    "control": ctrl,
                    "fixture_family": wrong_fam,
                    "fixture_variant": "minimal_valid",
                    "description": f"Click {ctrl.get('testid')} with mismatched fixture {wrong_fam}",
                })

        # 2. Multi-step Sequences
        seq_steps: list[dict[str, Any]] = []
        actionable = [c for c in ctrls if c.get("kind") in ("button", "tab", "switch", "segmented")]
        num_steps = 3 if smoke else rng.randint(4, 7)
        sampled = rng.sample(actionable, min(num_steps, len(actionable))) if actionable else []
        for s in sampled:
            seq_steps.append({
                "testid": s.get("testid"),
                "kind": s.get("kind"),
            })

        cases.append({
            "type": "sequence",
            "tool": tool,
            "steps": seq_steps,
            "fixture_family": acc_fams[0],
            "fixture_variant": "typical",
            "description": f"Random walk sequence of {len(seq_steps)} steps in {tool}",
        })

        # 3. Chaos test per tool
        cases.append({
            "type": "chaos",
            "tool": tool,
            "actions": ["rapid_click", "keys_esc_tab_enter", "large_paste", "theme_toggle"],
            "fixture_family": acc_fams[0],
            "fixture_variant": "corrupt_header" if not smoke else "typical",
            "description": f"Chaos stress testing for {tool}",
        })

    return cases
