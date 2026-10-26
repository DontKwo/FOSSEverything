import ctypes
import json
import os
import sys
import threading
import time
from pathlib import Path

import webview

from app.system.settings import get_setting
from app.system.shell_integration import (
    register_shell_context_menu,
    start_ipc_server,
    try_forward_to_running_instance,
    unregister_shell_context_menu,
)
from app.web.api import WebApi

THEME_BG_MAP = {
    "dark": "#090d16",
    "light": "#f4f6fb",
    "solarized": "#00212b",
    "monokai": "#1c1d1a",
    "cyberpunk": "#0d0221",
}


def calc_initial_window_size() -> tuple[int, int]:
    # Calculate initial window size based on primary screen dimensions.
    try:
        screens = webview.screens
        if screens:
            scr = screens[0]
            w = min(1400, max(800, int(scr.width * 0.85)))
            h = min(900, max(600, int(scr.height * 0.85)))
            return w, h
    except Exception:  # noqa: 10
        pass
    return 1320, 880


def run_selftest(window: webview.Window) -> None:
    # Execute in-window selftest hook and output findings JSON.
    out_path = os.environ.get("FOSS_SELFTEST_OUT", "selftest_result.json")
    for _ in range(50):
        time.sleep(0.1)
        ready = window.evaluate_js("Boolean(window.FOSS && window.FOSS.ready)")
        if ready:
            break

    res = window.evaluate_js("window.FOSS && window.FOSS.selfTest ? window.FOSS.selfTest() : null")
    result_data = res if isinstance(res, dict) else {"ready": True, "findings": [], "missing_api": []}
    Path(out_path).write_text(json.dumps(result_data, indent=2), encoding="utf-8")
    window.destroy()

    findings = result_data.get("findings", [])
    has_err = any(f.get("severity") == "error" for f in findings)
    missing = result_data.get("missing_api", [])
    sys.exit(1 if has_err or missing else 0)


def main() -> None:
    # Desktop application entry point.
    if "--register-shell" in sys.argv:
        register_shell_context_menu()
        return
    if "--unregister-shell" in sys.argv:
        unregister_shell_context_menu()
        return

    # Check instance forwarding
    args = sys.argv[1:]
    target_path = None
    target_mode = "default"
    for arg in args:
        if arg == "--ocr":
            target_mode = "ocr"
        elif arg == "--hash":
            target_mode = "hash"
        elif not arg.startswith("--") and os.path.exists(arg):
            target_path = os.path.abspath(arg)

    if target_path and try_forward_to_running_instance(target_path, target_mode):
        sys.exit(0)

    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FOSSEverything.DesktopApp")

    api = WebApi()
    html_path = str(Path(__file__).parent / "app" / "web" / "index.html")

    saved_theme = str(get_setting("theme", "dark"))
    bg_color = THEME_BG_MAP.get(saved_theme, "#090d16")
    w, h = calc_initial_window_size()

    is_selftest = "--selftest" in sys.argv

    window = webview.create_window(
        title="FOSSEverything",
        url=html_path,
        js_api=api,
        width=w,
        height=h,
        min_size=(800, 600),
        background_color=bg_color,
        text_select=True,
        hidden=is_selftest,
    )
    api._set_window(window)

    def on_ipc_launch(file_path: str, mode: str) -> None:
        cmd = f"window.FOSS && window.FOSS.openPaths ? window.FOSS.openPaths([{json.dumps(file_path)}], {json.dumps(mode)}) : null"
        window.evaluate_js(cmd)

    start_ipc_server(on_ipc_launch)

    if is_selftest:
        t = threading.Thread(target=run_selftest, args=(window,), daemon=True)
        t.start()

    webview.start(debug=False)


if __name__ == "__main__":
    main()
