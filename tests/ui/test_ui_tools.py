import importlib
import json
from pathlib import Path
from typing import Any

import pytest

from tests.ui.harness import QUICK, VIEWPORTS, capture, make_page


def calc_load_allowlist() -> list[dict[str, str]]:
    # Load allowed audit exceptions.
    allow_file = Path("tests/ui/audit_allow.json")
    if allow_file.exists():
        try:
            return json.loads(allow_file.read_text(encoding="utf-8"))
        except Exception:  # noqa: 10
            return []
    return []


def calc_filter_findings(findings: list[dict[str, Any]], view: str, allowlist: list[dict[str, str]]) -> list[dict[str, Any]]:
    # Filter findings against allowlist rules.
    filtered: list[dict[str, Any]] = []
    for f in findings:
        if f.get("severity") != "error":
            continue
        fid = f.get("id")
        sel = f.get("selector", "")
        is_allowed = False
        for a in allowlist:
            if a.get("check") == fid and a.get("view") in (view, "*"):
                if not a.get("selector") or a.get("selector") in sel:
                    is_allowed = True
                    break
        if not is_allowed:
            filtered.append(f)
    return filtered


def calc_get_scenarios() -> list[tuple[str, str, Any]]:
    # Discover available tool scenarios from scenarios directory.
    scenarios: list[tuple[str, str, Any]] = []
    scenarios_dir = Path(__file__).parent / "scenarios"
    if not scenarios_dir.exists():
        return scenarios
    for p in scenarios_dir.glob("*.py"):
        if p.stem.startswith("_"):
            continue
        tool_id = p.stem
        mod = importlib.import_module(f"tests.ui.scenarios.{tool_id}")
        tool_scenarios = getattr(mod, "SCENARIOS", [])
        for name, fn in tool_scenarios:
            scenarios.append((tool_id, name, fn))
    return scenarios


DISCOVERED_SCENARIOS = calc_get_scenarios()


@pytest.mark.parametrize("vp_id", QUICK)
@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("tool_id,sc_name,sc_fn", DISCOVERED_SCENARIOS, ids=[f"{t}-{n}" for t, n, _ in DISCOVERED_SCENARIOS] if DISCOVERED_SCENARIOS else ["none-none"])
def test_tool_scenarios(
    browser: Any,
    api: Any,
    fixtures: dict[str, str],
    run_dir: Path,
    records: list[dict[str, Any]],
    vp_id: str,
    theme: str,
    tool_id: str,
    sc_name: str,
    sc_fn: Any,
) -> None:
    # Execute UI scenario and verify visual and accessibility audit rules.
    if tool_id == "none":
        pytest.skip("No scenarios discovered yet")
    vp = next(v for v in VIEWPORTS if v["id"] == vp_id)
    session = make_page(browser, api, vp, theme=theme, ui_scale=1.0)
    page = session["page"]
    allowlist = calc_load_allowlist()

    sc_fn(page, fixtures, api)
    rec = capture(session, tool_id, sc_name, "0", run_dir.name)
    records.append(rec)

    unallowed = calc_filter_findings(rec["findings"], tool_id, allowlist)
    errors: list[str] = []
    if unallowed:
        for u in unallowed:
            errors.append(f"[{vp_id}/{theme}] {tool_id}:{sc_name} -> [{u.get('id')}] {u.get('selector')}: {u.get('message')}")

    session["context"].close()
    assert not errors, f"UI audit errors in {tool_id}:{sc_name} ({len(errors)}):\n" + "\n".join(errors[:20])
