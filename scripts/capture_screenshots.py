"""Automated screenshot capture script for FOSSEverything showcase."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time
from typing import Any

from playwright.sync_api import sync_playwright

from app.web.api import WebApi

ROOT_DIR = Path(__file__).resolve().parent.parent


class QuietStaticHandler(SimpleHTTPRequestHandler):
    """Static handler that keeps automated screenshot output quiet."""

    def log_message(self, format: str, *args: Any) -> None:
        return


def _launch_browser(pw: Any) -> Any:
    try:
        return pw.chromium.launch(headless=True)
    except Exception:  # noqa: 10
        return pw.chromium.launch(channel="msedge", headless=True)


def capture_all(out_dir: Path) -> None:
    """Capture application feature screenshots into out_dir."""
    out_resolved = out_dir.expanduser().resolve()
    out_resolved.mkdir(parents=True, exist_ok=True)
    api = WebApi()

    web_root = ROOT_DIR / "app" / "web"
    handler = partial(QuietStaticHandler, directory=str(web_root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with sync_playwright() as pw:
            browser = _launch_browser(pw)
            page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)

            def py_call_handler(name: str, args_json: str) -> str:
                try:
                    args = json.loads(args_json)
                    method = getattr(api, name)
                    res = method(*args)
                    return json.dumps(res, default=str)
                except Exception as exc:
                    return json.dumps({"ok": False, "error": str(exc)})

            page.expose_function("__py_call", py_call_handler)
            bridge_script = """
            window.pywebview = {
                api: new Proxy({}, {
                    get: (t, name) => (...args) => window.__py_call(String(name), JSON.stringify(args)).then(JSON.parse)
                })
            };
            """
            page.add_init_script(bridge_script)
            page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle")
            page.wait_for_selector(".app")
            time.sleep(1.0)

            views = [
                ("01_home_hub.png", None),
                ("02_pdf_studio.png", "window.FOSS.router.open('pdf', 'merge')"),
                ("03_3d_viewer.png", "window.FOSS.router.open('model3d')"),
                ("04_network_monitor.png", "window.FOSS.router.open('network_monitor')"),
                ("05_data_studio.png", "window.FOSS.router.open('data')"),
                ("06_converter.png", "window.FOSS.router.open('converter')"),
                ("07_command_palette.png", "window.FOSS.router.open('home'); window.FOSS.palette.open()"),
            ]
            for filename, js_expr in views:
                if js_expr:
                    page.evaluate(js_expr)
                    time.sleep(0.8)
                target = out_resolved / filename
                page.screenshot(path=str(target), full_page=False)
                sys.stdout.write(f"Captured {filename}\n")

            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture FOSSEverything desktop screenshots.")
    parser.add_argument("--out-dir", type=Path, default=ROOT_DIR / "assets" / "screenshots")
    args = parser.parse_args()
    capture_all(args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
