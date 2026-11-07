import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any

from playwright.sync_api import Browser, Page, sync_playwright

from app.core.tooltips import TOOLTIP_DICTIONARY
from app.web.api import WebApi
from tests.matrix.common.fixture_factory import FixtureFactory
from tests.matrix.ui.crawler import TOOLS, extract_static_controls
from tests.ui.harness import ARGS, VIEWPORTS, launch_browser, make_page

TOOL_FIXTURE_MAP: dict[str, tuple[str, str]] = {
    "archive": ("zip", "typical"),
    "collage": ("png", "typical"),
    "compressor": ("pdf", "typical"),
    "converter": ("docx", "typical"),
    "data": ("json", "typical"),
    "encoding": ("txt", "typical"),
    "images": ("png", "typical"),
    "markdown": ("md", "typical"),
    "media": ("mp4", "typical"),
    "metadata": ("jpg", "typical"),
    "model3d": ("stl", "typical"),
    "network_monitor": ("txt", "typical"),
    "ocr": ("png", "typical"),
    "palette": ("png", "typical"),
    "pdf": ("pdf", "typical"),
    "playlist": ("m3u8", "typical"),
    "qr": ("qr", "typical"),
    "renamer": ("png", "typical"),
    "resume": ("json", "typical"),
    "text_tools": ("txt", "typical"),
    "unit_converter": ("txt", "typical"),
}


def build_inventory_json(output_path: Path | str = "tests/matrix/ui_inventory.json") -> dict[str, Any]:
    # Crawl tools both dynamically and statically to generate ui_inventory.json.
    static_controls = extract_static_controls()
    inventory: dict[str, list[dict[str, Any]]] = {}

    with tempfile.TemporaryDirectory() as td:
        work_dir = Path(td)
        os.environ["FOSS_SETTINGS_DIR"] = str(work_dir / "settings")
        factory = FixtureFactory(work_dir / "fixtures", seed=42)
        fixtures: dict[str, str] = {}
        for tool, (fam, var) in TOOL_FIXTURE_MAP.items():
            fpath = factory.create(fam, var)
            fixtures[tool] = str(fpath.resolve())

        api = WebApi()
        api._dialog_answers = []

        with sync_playwright() as p:
            browser = launch_browser(p)
            session = make_page(browser, api, VIEWPORTS[0], theme="dark", ui_scale=1.0)
            page: Page = session["page"]

            for tool in TOOLS:
                inventory[tool] = []
                seen_in_tool: set[str] = set()

                # Open the tool in pywebview DOM
                try:
                    page.evaluate(f"window.FOSS.router.open('{tool}', 'main')")
                    page.wait_for_timeout(300)
                except Exception:  # noqa: 10
                    pass

                # Scan initial DOM elements
                def record_dom_elements(mode_name: str, state_cond: str) -> None:
                    try:
                        elements = page.query_selector_all(
                            "[data-testid], button, input, select, textarea, [role='switch'], [role='tab'], .tab-btn, .segmented-item"
                        )
                        for el in elements:
                            tid = el.get_attribute("data-testid") or ""
                            tag = el.evaluate("e => e.tagName.toLowerCase()")
                            el_type = el.get_attribute("type") or ""
                            role = el.get_attribute("role") or ""
                            aria_label = el.get_attribute("aria-label") or el.inner_text()[:40].strip()

                            kind = "button"
                            if tag == "input":
                                kind = "switch" if el_type in ("checkbox", "radio") else "slider" if el_type == "range" else "input"
                            elif tag in ("select", "textarea"):
                                kind = "select" if tag == "select" else "input"
                            elif role == "switch":
                                kind = "switch"
                            elif role == "tab" or "tab-btn" in (el.get_attribute("class") or ""):
                                kind = "tab"
                            elif "segmented" in (el.get_attribute("class") or ""):
                                kind = "segmented"

                            final_id = tid if tid else f"{tool}-{kind}-{len(seen_in_tool)}"
                            if final_id in seen_in_tool:
                                continue
                            seen_in_tool.add(final_id)

                            inventory[tool].append({
                                "tool": tool,
                                "mode": mode_name,
                                "testid": final_id,
                                "kind": kind,
                                "tag": tag,
                                "aria_label": aria_label,
                                "preconditions": [state_cond] if state_cond else [],
                                "api_method": "",
                                "expected_effect": f"Trigger {aria_label or final_id}",
                            })
                    except Exception:  # noqa: 10
                        pass

                record_dom_elements("initial", "")

                # Click tabs to discover tab-specific controls
                tabs = page.query_selector_all(".tab-btn, [role='tab']")
                for t in tabs[:6]:
                    try:
                        t_label = t.inner_text().strip().lower()
                        t.click()
                        page.wait_for_timeout(100)
                        record_dom_elements(t_label or "tab", "tab_active")
                    except Exception:  # noqa: 10
                        pass

                # Merge static testids that were not dynamically in the initial empty view
                for stat in static_controls.get(tool, []):
                    stat_id = stat["testid"]
                    if stat_id not in seen_in_tool:
                        seen_in_tool.add(stat_id)
                        inventory[tool].append({
                            "tool": tool,
                            "mode": stat["mode"],
                            "testid": stat_id,
                            "kind": stat["kind"],
                            "tag": "div" if stat["kind"] == "container" else "button",
                            "aria_label": stat_id,
                            "preconditions": stat["preconditions"] or ["file_loaded"],
                            "api_method": stat["api_method"],
                            "expected_effect": stat["expected_effect"],
                        })

            browser.close()

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    return inventory


if __name__ == "__main__":
    inv = build_inventory_json()
    total = sum(len(v) for v in inv.values())
    print(f"Generated UI inventory: {len(inv)} tools, {total} total controls.")
