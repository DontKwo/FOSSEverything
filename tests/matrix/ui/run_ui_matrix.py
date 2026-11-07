import argparse
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import time
from typing import Any

from playwright.sync_api import Browser, Page, sync_playwright

from app.web.api import WebApi
from tests.matrix.common.fixture_factory import FixtureFactory
from tests.matrix.oracles import patch_network_blocking, unpatch_network_blocking
from tests.matrix.ui.matrix_gen import build_ui_cases
from tests.matrix.ui.oracles import capture_failure_artifacts, check_ui_oracles
from tests.ui.harness import VIEWPORTS, launch_browser, make_page


def execute_ui_case(
    page: Page,
    api: Any,
    case: dict[str, Any],
    fixture_path: str,
    problems: list[str],
) -> tuple[bool, str, list[dict[str, Any]]]:
    # Execute a single UI matrix case and verify health oracles.
    tool = case["tool"]
    case_type = case["type"]
    problems.clear()

    # Navigate to tool
    try:
        page.evaluate(f"window.FOSS.router.open('{tool}', 'main')")
        page.wait_for_timeout(150)
    except Exception as exc:
        return False, f"Navigation failure to {tool}: {exc}", []

    # Feed dialog answers if any dialog is expected
    if hasattr(api, "_dialog_answers"):
        api._dialog_answers.clear()
        api._dialog_answers.extend([fixture_path, fixture_path])

    # Case 1: Control interaction
    if case_type == "control_click":
        ctrl = case["control"]
        testid = ctrl.get("testid")
        kind = ctrl.get("kind")
        sel = f"[data-testid='{testid}']"

        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                if kind in ("button", "tab", "segmented", "dropzone"):
                    loc.click(timeout=1000)
                elif kind == "switch":
                    loc.click(timeout=1000)
                elif kind == "input":
                    loc.fill("sample input text", timeout=1000)
                page.wait_for_timeout(200)
        except Exception:  # noqa: 10
            # Settle and let oracles check if control was disabled or not visible
            pass

    # Case 2: Multi-step Sequence
    elif case_type == "sequence":
        for step in case.get("steps", []):
            tid = step.get("testid")
            try:
                loc = page.locator(f"[data-testid='{tid}']").first
                if loc.count() > 0 and loc.is_visible():
                    loc.click(timeout=800)
                    page.wait_for_timeout(100)
            except Exception:  # noqa: 10
                pass

    # Case 3: Chaos Actions
    elif case_type == "chaos":
        try:
            # Rapid clicks on first visible button
            btn = page.locator("button:visible").first
            if btn.count() > 0:
                for _ in range(3):
                    btn.click(timeout=500)
            # Keys
            page.keyboard.press("Escape")
            page.keyboard.press("Tab")
            page.keyboard.press("Enter")
            # Theme toggle mid-op
            page.evaluate("""() => {
                const cur = document.documentElement.getAttribute('data-theme');
                document.documentElement.setAttribute('data-theme', cur === 'dark' ? 'light' : 'dark');
            }""")
            page.wait_for_timeout(150)
        except Exception:  # noqa: 10
            pass

    # Wait for settle
    try:
        page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    except Exception:  # noqa: 10
        pass

    # Check Oracles
    ok, msg, findings = check_ui_oracles(page, problems, view=tool, check_audit=False)
    return ok, msg, findings


def run_ui_matrix(
    tool_filter: str | None = None,
    control_filter: str | None = None,
    fixture_kind_filter: str | None = None,
    seed: int = 42,
    shard_str: str | None = None,
    smoke: bool = False,
    failed_only: bool = False,
    resume: bool = False,
    max_seconds: float = 300.0,
    out_dir: Path | str = "tests/matrix/ui/results",
) -> dict[str, Any]:
    # Main test runner for automated GUI matrix.
    patch_network_blocking()
    start_time = time.time()
    out_p = Path(out_dir)
    out_p.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_p / "ui_results.jsonl"
    summary_path = out_p / "ui_summary.md"

    inv_path = Path("tests/matrix/ui_inventory.json")
    if not inv_path.exists():
        unpatch_network_blocking()
        raise FileNotFoundError("tests/matrix/ui_inventory.json not found")

    with open(inv_path, "r", encoding="utf-8") as f:
        inventory = json.load(f)

    shard_idx, shard_total = 1, 1
    if shard_str and "/" in shard_str:
        p1, p2 = shard_str.split("/", 1)
        shard_idx, shard_total = int(p1), int(p2)

    total_cases = 0
    passed_cases = 0
    failed_cases = 0
    skipped_cases = 0
    failures_by_root_cause: dict[str, list[dict[str, Any]]] = {}

    with tempfile.TemporaryDirectory() as td:
        work_dir = Path(td)
        os.environ["FOSS_SETTINGS_DIR"] = str(work_dir / "settings")
        factory = FixtureFactory(work_dir / "fixtures", seed=seed)

        all_cases = build_ui_cases(
            inventory,
            factory,
            tool_filter=tool_filter,
            control_filter=control_filter,
            fixture_kind_filter=fixture_kind_filter,
            smoke=smoke,
            seed=seed,
        )

        cases_for_shard = [c for i, c in enumerate(all_cases) if (i % shard_total) == (shard_idx - 1)]

        api = WebApi()
        api._dialog_answers = []

        with sync_playwright() as p:
            browser = launch_browser(p)
            session = make_page(browser, api, VIEWPORTS[0], theme="dark", ui_scale=1.0)
            page = session["page"]
            problems = session["problems"]

            mode_flag = "a" if resume and jsonl_path.exists() else "w"
            with open(jsonl_path, mode_flag, encoding="utf-8") as jsonl_file:
                for idx, case in enumerate(cases_for_shard):
                    if (time.time() - start_time) > max_seconds:
                        break

                    total_cases += 1
                    tool = case["tool"]
                    fam = case.get("fixture_family", "txt")
                    var = case.get("fixture_variant", "typical")
                    fpath = str(factory.create(fam, var).resolve())

                    t0 = time.time()
                    ok, msg, findings = execute_ui_case(page, api, case, fpath, problems)
                    dur = round(time.time() - t0, 3)

                    # Flake check: if failed, re-run up to 3 times
                    if not ok:
                        flake_retries = 0
                        while flake_retries < 2 and not ok:
                            flake_retries += 1
                            ok, msg, findings = execute_ui_case(page, api, case, fpath, problems)

                    status = "pass" if ok else "fail"
                    if not ok:
                        failed_cases += 1
                        root_cause = findings[0].get("id", "UNKNOWN_ERROR") if findings else "UNKNOWN_ERROR"
                        sig = f"{tool}::{root_cause}"
                        if sig not in failures_by_root_cause:
                            failures_by_root_cause[sig] = []
                        replay_cmd = f"uv run --no-project --python .venv/bin/python python tests/matrix/ui/run_ui_matrix.py --tool {tool} --seed {seed}"
                        png_f, html_f = capture_failure_artifacts(page, out_p / "artifacts", f"fail_{tool}_{idx}")
                        failures_by_root_cause[sig].append({
                            "case": case,
                            "msg": msg,
                            "replay": replay_cmd,
                            "screenshot": png_f,
                            "dom": html_f,
                        })
                    else:
                        passed_cases += 1

                    record = {
                        "tool": tool,
                        "type": case.get("type"),
                        "description": case.get("description"),
                        "status": status,
                        "duration": dur,
                        "message": msg,
                    }
                    jsonl_file.write(json.dumps(record) + "\n")
                    jsonl_file.flush()

            browser.close()

    unpatch_network_blocking()
    total_time = round(time.time() - start_time, 2)

    summary_lines = [
        "# UI Matrix Run Summary",
        f"- **Total Cases**: {total_cases}",
        f"- **Passed**: {passed_cases}",
        f"- **Failed**: {failed_cases}",
        f"- **Skipped**: {skipped_cases}",
        f"- **Time**: {total_time}s",
        "",
        "## Root Causes & Failures",
    ]
    if not failures_by_root_cause:
        summary_lines.append("No UI matrix failures detected.")
    else:
        for sig, items in failures_by_root_cause.items():
            summary_lines.append(f"### {sig} ({len(items)} cases)")
            first = items[0]
            summary_lines.append(f"- Message: `{first['msg']}`")
            summary_lines.append(f"- Replay: `{first['replay']}`")
            summary_lines.append(f"- Screenshot: `{first['screenshot']}`")
            summary_lines.append("")

    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    return {
        "total": total_cases,
        "passed": passed_cases,
        "failed": failed_cases,
        "skipped": skipped_cases,
        "time": total_time,
        "summary": str(summary_path),
        "failures": failures_by_root_cause,
    }


def main() -> None:
    # CLI entry point for UI matrix testing runner.
    parser = argparse.ArgumentParser(description="Run UI Automated Matrix Tests")
    parser.add_argument("--tool", type=str, default=None, help="Filter by tool name")
    parser.add_argument("--control", type=str, default=None, help="Filter by control testid")
    parser.add_argument("--fixture-kind", type=str, default=None, help="Filter by fixture kind")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--shard", type=str, default=None, help="Shard string e.g. 1/4")
    parser.add_argument("--smoke", action="store_true", help="Run fast smoke subset")
    parser.add_argument("--failed-only", action="store_true", help="Run only previously failed cases")
    parser.add_argument("--resume", action="store_true", help="Resume from previous JSONL results")
    parser.add_argument("--max-seconds", type=float, default=120.0, help="Max run duration")
    args = parser.parse_args()

    res = run_ui_matrix(
        tool_filter=args.tool,
        control_filter=args.control,
        fixture_kind_filter=args.fixture_kind,
        seed=args.seed,
        shard_str=args.shard,
        smoke=args.smoke,
        failed_only=args.failed_only,
        resume=args.resume,
        max_seconds=args.max_seconds,
    )
    print(f"UI Matrix run complete in {res['time']}s: {res['passed']} passed, {res['failed']} failed.")
    if res["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
