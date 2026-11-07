import json
from pathlib import Path
import re
from typing import Any

from app.core.tooltips import TOOLTIP_DICTIONARY
from tests.matrix.common.fixture_factory import FixtureFactory

TOOLS = [
    "archive", "collage", "compressor", "converter", "data", "encoding",
    "images", "markdown", "media", "metadata", "model3d", "network_monitor",
    "ocr", "palette", "pdf", "playlist", "qr", "renamer", "resume",
    "text_tools", "unit_converter"
]


def extract_static_controls() -> dict[str, list[dict[str, Any]]]:
    # Parse app/web/js/tools/*.js for all registered testids, handlers, and labels.
    controls_by_tool: dict[str, list[dict[str, Any]]] = {}
    tools_dir = Path("app/web/js/tools")

    for tool in TOOLS:
        js_file = tools_dir / f"{tool}.js"
        if not js_file.exists():
            continue
        text = js_file.read_text(encoding="utf-8")
        controls_by_tool[tool] = []

        pattern = re.compile(
            r'(?:data-testid[\'"]?\s*[:=]\s*[\'"]|testid[\'"]?\s*[:=]\s*[\'"])([a-zA-Z0-9_-]+)[\'"]'
        )
        seen_testids: set[str] = set()

        for match in pattern.finditer(text):
            tid = match.group(1)
            if tid in seen_testids:
                continue
            seen_testids.add(tid)

            # Determine kind from testid naming conventions or context
            kind = "button"
            lower_tid = tid.lower()
            if "input" in lower_tid or "field" in lower_tid or "path" in lower_tid or "search" in lower_tid:
                kind = "input"
            elif "select" in lower_tid or "format" in lower_tid or "mode" in lower_tid or "type" in lower_tid or "dropdown" in lower_tid:
                kind = "select"
            elif "check" in lower_tid or "switch" in lower_tid or "toggle" in lower_tid:
                kind = "switch"
            elif "slider" in lower_tid or "quality" in lower_tid or "scale" in lower_tid:
                kind = "slider"
            elif "tab" in lower_tid:
                kind = "tab"
            elif "zone" in lower_tid or "drop" in lower_tid or "picker" in lower_tid:
                kind = "dropzone"
            elif "card" in lower_tid or "view" in lower_tid or "list" in lower_tid or "editor" in lower_tid or "panel" in lower_tid:
                kind = "container"
            elif "btn" in lower_tid or "button" in lower_tid or "action" in lower_tid or "add" in lower_tid or "remove" in lower_tid or "clear" in lower_tid or "apply" in lower_tid:
                kind = "button"

            # Search nearby API calls
            idx = match.start()
            surrounding = text[max(0, idx - 400):min(len(text), idx + 600)]
            api_match = re.search(r'window\.FOSS\.api\([\'"]([a-zA-Z0-9_]+)[\'"]', surrounding)
            api_method = api_match.group(1) if api_match else ""

            # Check tooltip text dictionary
            expected_effect = ""
            for tk, tv in TOOLTIP_DICTIONARY.items():
                if tk.lower() in tid.lower().replace("-", " ") or tk.lower() in surrounding.lower():
                    expected_effect = tv.description
                    break
            if not expected_effect:
                expected_effect = f"Interact with control {tid} in {tool}"

            # Determine tab/mode if identifiable
            mode = "main"
            mode_match = re.search(r'(?:tab|mode|section)[\'"]?\s*[:=]\s*[\'"]([a-zA-Z0-9_-]+)[\'"]', text[max(0, idx - 200):idx])
            if mode_match:
                mode = mode_match.group(1)

            controls_by_tool[tool].append({
                "tool": tool,
                "mode": mode,
                "testid": tid,
                "kind": kind,
                "preconditions": [] if kind != "container" else ["tool_active"],
                "api_method": api_method,
                "expected_effect": expected_effect,
            })

    return controls_by_tool
