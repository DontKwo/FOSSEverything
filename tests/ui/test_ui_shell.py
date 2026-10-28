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
        for allowed_entry in allowlist:
            if allowed_entry.get("check") == fid and a.get("view") in (view, "*"):
                if not a.get("selector") or a.get("selector") in sel:
                    is_allowed = True
                    break
        if not is_allowed:
            filtered.append(f)
    return filtered


@pytest.mark.parametrize("vp_id", QUICK)
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_shell_states(browser: Any, api: Any, run_dir: Path, records: list[dict[str, Any]], vp_id: str, theme: str) -> None:
    # Test shell views and states against automated visual and DOM audit.
    vp = next(v for v in VIEWPORTS if v["id"] == vp_id)
    session = make_page(browser, api, vp, theme=theme, ui_scale=1.0)
    page = session["page"]
    allowlist = calc_load_allowlist()

    shell_states = [
        ("home", "default"),
        ("home", "empty-search"),
        ("palette", "open"),
        ("settings", "appearance"),
        ("settings", "privacy"),
        ("modal", "confirm"),
        ("sidebar", "rail"),
    ]

    errors: list[str] = []
    for view, state in shell_states:
        page.evaluate(f"window.FOSS.openState('{view}', '{state}')")
        rec = capture(session, view, state, "0", run_dir.name)
        records.append(rec)

        unallowed = calc_filter_findings(rec["findings"], view, allowlist)
        if unallowed:
            for err_item in unallowed:
                errors.append(f"[{vp_id}/{theme}] {view}:{state} -> [{err_item.get('id')}] {err_item.get('selector')}: {err_item.get('message')}")

    session["context"].close()
    assert not errors, f"Shell audit errors ({len(errors)}):\n" + "\n".join(errors[:20])


FULL_VIEWPORTS = [v["id"] for v in VIEWPORTS]


@pytest.mark.ui_full
@pytest.mark.parametrize("vp_id", FULL_VIEWPORTS)
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_shell_states_full(
    browser: Any,
    api: Any,
    run_dir: Path,
    records: list[dict[str, Any]],
    vp_id: str,
    theme: str,
) -> None:
    # Test shell views and states across full viewport matrix.
    test_shell_states(browser, api, run_dir, records, vp_id, theme)


