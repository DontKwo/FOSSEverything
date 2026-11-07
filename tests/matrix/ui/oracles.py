import json
import os
from pathlib import Path
import time
from typing import Any

from playwright.sync_api import Page

from tests.ui import pixel_checks


def check_ui_oracles(
    page: Page,
    problems: list[str],
    view: str = "",
    state: str = "",
    check_audit: bool = True,
) -> tuple[bool, str, list[dict[str, Any]]]:
    # Evaluate UI health oracles: console errors, hung spinners, leaked modals, and A1-A22 audit.
    findings: list[dict[str, Any]] = []

    # 1. Console / Page errors
    if problems:
        err_msg = "; ".join(problems)
        return False, f"Page/Console error: {err_msg}", [{"id": "CONSOLE_ERROR", "message": err_msg}]

    # 2. Hung spinner check
    try:
        has_stuck_spinner = page.evaluate("""() => {
            const spinners = document.querySelectorAll('.spinner, .loading, [aria-busy="true"]');
            for (const sp of spinners) {
                const rect = sp.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) return true;
            }
            return false;
        }""")
        if has_stuck_spinner:
            return False, "Hung spinner detected after operation settle", [{"id": "HUNG_SPINNER"}]
    except Exception:  # noqa: 10
        pass

    # 3. Leaked unclosed modal check
    try:
        leaked_modal = page.evaluate("""() => {
            const modals = document.querySelectorAll('.modal-backdrop, .modal-open, dialog[open]');
            return modals.length > 0;
        }""")
        if leaked_modal:
            return False, "Leaked modal backdrop or dialog open", [{"id": "LEAKED_MODAL"}]
    except Exception:  # noqa: 10
        pass

    # 4. Human readable error check in DOM
    try:
        raw_error = page.evaluate("""() => {
            const text = document.body ? document.body.innerText : "";
            if (text.includes("Traceback (most recent call last)") ||
                text.includes("[object Object]") ||
                text.includes("undefined is not a function")) {
                return true;
            }
            return false;
        }""")
        if raw_error:
            return False, "Raw unhandled traceback or [object Object] rendered to user", [{"id": "RAW_ERROR"}]
    except Exception:  # noqa: 10
        pass

    # 5. UI Audit script findings
    if check_audit:
        try:
            audit_res = page.evaluate("() => (window.__audit ? window.__audit() : [])")
            if isinstance(audit_res, list):
                # Filter allowed exceptions from tests/ui/audit_allow.json if needed
                for f in audit_res:
                    if f.get("severity") == "error":
                        findings.append(f)
        except Exception as exc:
            findings.append({"id": "AUDIT_FAILURE", "message": str(exc)})

    # Determine pass/fail
    if findings:
        summary_msg = f"{len(findings)} audit findings ({findings[0].get('id')}: {findings[0].get('message', '')})"
        return False, summary_msg, findings

    return True, "All UI oracles clean", []


def capture_failure_artifacts(
    page: Page,
    out_dir: Path,
    test_id: str,
) -> tuple[str, str]:
    # Capture screenshot and full HTML DOM snapshot upon test case failure.
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / f"{test_id}.png"
    html_path = out_dir / f"{test_id}.html"

    try:
        page.screenshot(path=str(png_path), full_page=False)
    except Exception:  # noqa: 10
        pass

    try:
        dom_content = page.content()
        html_path.write_text(dom_content, encoding="utf-8")
    except Exception:  # noqa: 10
        pass

    return str(png_path), str(html_path)
