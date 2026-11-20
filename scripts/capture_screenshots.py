"""Automated screenshot capture script for FOSSEverything showcase."""
import json
import os
import time
from playwright.sync_api import sync_playwright

from app.web.api import WebApi

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOTS_DIR = os.path.join(ROOT_DIR, "assets", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

api = WebApi()


def capture_all() -> None:
    # Capture application feature screenshots.
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 820}, device_scale_factor=1)

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

        html_path = "file:///" + os.path.join(ROOT_DIR, "app", "web", "index.html").replace("\\", "/")
        page.goto(html_path)
        page.wait_for_selector(".app")
        time.sleep(1.0)

        # 1. Home Hub
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_home_hub.png"))
        print("Captured 01_home_hub.png")

        # 2. PDF Studio
        page.evaluate("window.FOSS.router.open('pdf', 'merge')")
        time.sleep(0.8)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_pdf_studio.png"))
        print("Captured 02_pdf_studio.png")

        # 3. 3D Model Viewer
        page.evaluate("window.FOSS.router.open('model3d')")
        time.sleep(0.8)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_3d_viewer.png"))
        print("Captured 03_3d_viewer.png")

        # 4. Network Monitor
        page.evaluate("window.FOSS.router.open('network_monitor')")
        time.sleep(0.8)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_network_monitor.png"))
        print("Captured 04_network_monitor.png")

        # 5. Data Studio
        page.evaluate("window.FOSS.router.open('data')")
        time.sleep(0.8)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_data_studio.png"))
        print("Captured 05_data_studio.png")

        # 6. Converter & Compressor
        page.evaluate("window.FOSS.router.open('converter')")
        time.sleep(0.8)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "06_converter.png"))
        print("Captured 06_converter.png")

        # 7. Command Palette Search
        page.evaluate("window.FOSS.router.open('home'); window.FOSS.palette.open()")
        time.sleep(0.8)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "07_command_palette.png"))
        print("Captured 07_command_palette.png")

        browser.close()


if __name__ == "__main__":
    capture_all()
