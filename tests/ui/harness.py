import json
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, Playwright

from tests.ui import contact_sheet, pixel_checks

ARGS = [
    "--allow-file-access-from-files",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--force-color-profile=srgb",
    "--font-render-hinting=none",
]

VIEWPORTS: list[dict[str, Any]] = [
    {"id": "min", "w": 800, "h": 600, "dpr": 1},
    {"id": "s960", "w": 960, "h": 640, "dpr": 1},
    {"id": "xga", "w": 1024, "h": 768, "dpr": 1},
    {"id": "hd720", "w": 1280, "h": 720, "dpr": 1},
    {"id": "wxga", "w": 1366, "h": 768, "dpr": 1},
    {"id": "hd900", "w": 1440, "h": 900, "dpr": 1},
    {"id": "d125", "w": 1536, "h": 864, "dpr": 1.25},
    {"id": "fhd", "w": 1920, "h": 1080, "dpr": 1},
    {"id": "hidpi", "w": 1920, "h": 1080, "dpr": 2},
    {"id": "qhd", "w": 2560, "h": 1440, "dpr": 1},
    {"id": "ultra", "w": 3440, "h": 1440, "dpr": 1},
    {"id": "uhd", "w": 3840, "h": 2160, "dpr": 1},
    {"id": "tall", "w": 820, "h": 1180, "dpr": 1},
]

QUICK: list[str] = ["min", "hd720", "fhd"]


def launch_browser(playwright: Playwright) -> Browser:
    # Launch browser using Edge channel if possible, falling back to bundled Chromium.
    try:
        return playwright.chromium.launch(channel="msedge", args=ARGS)
    except Exception:  # noqa: 10
        return playwright.chromium.launch(args=ARGS)


def make_page(
    browser: Browser,
    api: Any,
    viewport: dict[str, Any],
    theme: str = "dark",
    ui_scale: float = 1.0,
    page_url: str | None = None,
) -> dict[str, Any]:
    # Create browser page with pywebview bridge and injected settings.
    w = int(viewport["w"])
    h = int(viewport["h"])
    dpr = float(viewport["dpr"])

    context = browser.new_context(
        viewport={"width": w, "height": h},
        device_scale_factor=dpr,
        reduced_motion="reduce",
        locale="en-US",
    )

    def py_call_handler(name: str, args_json: str) -> str:
        try:
            args = json.loads(args_json)
            method = getattr(api, name)
            res = method(*args)
            return json.dumps(res, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)})

    context.expose_function("__py_call", py_call_handler)

    bridge_script = """
    window.pywebview = {
        api: new Proxy({}, {
            get: (t, name) => (...args) => window.__py_call(String(name), JSON.stringify(args)).then(JSON.parse)
        })
    };
    document.addEventListener("DOMContentLoaded", () => {
        window.dispatchEvent(new Event("pywebviewready"));
    });
    """
    context.add_init_script(bridge_script)

    settings_script = f"""
    (() => {{
        const applySettings = () => {{
            if (document.documentElement) {{
                document.documentElement.setAttribute('data-theme', '{theme}');
                document.documentElement.style.setProperty('--ui-scale', '{ui_scale}');
            }}
        }};
        if (document.documentElement) {{
            applySettings();
        }} else {{
            document.addEventListener('DOMContentLoaded', applySettings);
        }}
    }})();
    """
    context.add_init_script(settings_script)

    audit_code = (Path(__file__).parent / "audit.js").read_text(encoding="utf-8")
    context.add_init_script(audit_code)

    page = context.new_page()
    page_problems: list[str] = []

    def on_console(msg: Any) -> None:
        if msg.type == "error":
            page_problems.append(f"Console error: {msg.text}")

    page.on("console", on_console)
    page.on("pageerror", lambda exc: page_problems.append(f"Page error: {exc}"))
    page.on("requestfailed", lambda req: page_problems.append(f"Failed request: {req.url}"))

    url = page_url if page_url else Path("app/web/index.html").resolve().as_uri()
    page.goto(url)

    # Wait for app readiness if app.js is present
    try:
        page.wait_for_function("() => window.FOSS && window.FOSS.ready === true", timeout=4000)
    except Exception:  # noqa: 10
        pass

    session = {
        "page": page,
        "context": context,
        "viewport": viewport,
        "theme": theme,
        "scale": ui_scale,
        "problems": page_problems,
    }
    return session


def capture(session: dict[str, Any], view: str, state: str, tag: str, run_id: str) -> dict[str, Any]:
    # Capture screenshot, run audit, and analyze pixels for view state.
    page: Page = session["page"]
    try:
        page.wait_for_load_state("networkidle", timeout=3000)
    except Exception:  # noqa: 10
        pass
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")

    vp_id = session["viewport"]["id"]
    theme = session["theme"]
    scale = session["scale"]

    out_dir = Path("tests/ui/_out") / run_id / vp_id / f"{theme}-{scale}"
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / f"{view}__{state}__{tag}.png"

    page.screenshot(path=str(png_path), full_page=False)

    findings: list[dict[str, Any]] = []
    # Collect browser problems
    for prob in session.get("problems", []):
        findings.append({"id": "A14", "severity": "error", "selector": "window", "message": prob})
    session["problems"].clear()

    # Run audit.js
    try:
        audit_res = page.evaluate("() => (window.__audit ? window.__audit() : [])")
        if isinstance(audit_res, list):
            findings.extend(audit_res)
    except Exception as exc:
        findings.append({"id": "A14", "severity": "error", "selector": "audit", "message": str(exc)})

    # Pixel checks
    pix_res = pixel_checks.analyze(str(png_path))
    findings.extend(pix_res)

    record = {
        "view": view,
        "state": state,
        "tag": tag,
        "viewport": vp_id,
        "theme": theme,
        "scale": scale,
        "png": str(png_path.resolve()),
        "findings": findings,
    }
    return record


def write_report(run_dir: Path, records: list[dict[str, Any]]) -> None:
    # Write report.json, findings.txt, and build contact sheets.
    run_dir.mkdir(parents=True, exist_ok=True)
    report_file = run_dir / "report.json"
    report_file.write_text(json.dumps(records, indent=2), encoding="utf-8")

    findings_file = run_dir / "findings.txt"
    by_id: dict[str, list[str]] = {}
    for r in records:
        vp = r.get("viewport", "")
        vw = r.get("view", "")
        st = r.get("state", "")
        for f in r.get("findings", []):
            fid = f.get("id", "UNKNOWN")
            sel = f.get("selector", "")
            msg = f.get("message", "")
            by_id.setdefault(fid, []).append(f"{vw}/{st} @ {vp}: {sel}: {msg}")

    lines: list[str] = ["Findings Summary:", ""]
    for fid, items in sorted(by_id.items()):
        lines.append(f"Check {fid} ({len(items)} occurrences):")
        for ex in items[:5]:
            lines.append(f"  {ex}")
        lines.append("")

    sheets = contact_sheet.build(str(run_dir))
    for s in sheets:
        lines.append(f"Contact sheet: {s}")

    findings_file.write_text("\n".join(lines), encoding="utf-8")

    latest_file = Path("tests/ui/_out/latest.txt")
    latest_file.parent.mkdir(parents=True, exist_ok=True)
    latest_file.write_text(str(run_dir.resolve()), encoding="utf-8")
