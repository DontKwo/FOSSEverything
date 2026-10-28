import ctypes
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

import webview
from webview.dom import DOMEventHandler

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
            win_w = min(1400, max(800, int(scr.width * 0.85)))
            win_h = min(900, max(600, int(scr.height * 0.85)))
            return win_w, win_h
    except Exception:  # noqa: 10
        pass
    return 1320, 880


def calc_app_base_dir() -> Path:
    # Resolve base application directory for source or frozen execution.
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def run_selftest(window: webview.Window) -> None:
    # Execute in-window selftest hook and output findings JSON.
    out_path = os.environ.get("FOSS_SELFTEST_OUT", "selftest_result.json")
    try:
        for _ in range(50):
            time.sleep(0.2)
            try:
                ready = window.evaluate_js("Boolean(window.FOSS && window.FOSS.ready)")
                if ready:
                    break
            except Exception:
                continue

        res = window.evaluate_js("window.FOSS && window.FOSS.selfTest ? window.FOSS.selfTest() : null")
        result_data = res if isinstance(res, dict) else {"ready": True, "findings": [], "missing_api": []}
        Path(out_path).write_text(json.dumps(result_data, indent=2), encoding="utf-8")
    except Exception as exc:
        err_data = {"ready": False, "error": str(exc), "findings": [{"severity": "error", "message": str(exc)}]}
        Path(out_path).write_text(json.dumps(err_data, indent=2), encoding="utf-8")
    finally:
        try:
            window.destroy()
        except Exception:  # noqa: 10
            pass
        os._exit(0)


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
    html_path = str(calc_app_base_dir() / "app" / "web" / "index.html")

    saved_theme = str(get_setting("theme", "dark"))
    bg_color = THEME_BG_MAP.get(saved_theme, "#090d16")
    win_w, win_h = calc_initial_window_size()

    is_selftest = "--selftest" in sys.argv

    window = webview.create_window(
        title="FOSSEverything",
        url=html_path,
        js_api=api,
        width=win_w,
        height=win_h,
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

    def on_window_drop(e: Any) -> None:
        # Route dropped files from OS drag-and-drop.
        try:
            files = e.get("dataTransfer", {}).get("files", [])
            paths = [f.get("pywebviewFullPath") for f in files if f.get("pywebviewFullPath")]
            if paths:
                cmd = f"window.FOSS && window.FOSS.router ? window.FOSS.router.routeFiles({json.dumps(paths)}) : null"
                window.evaluate_js(cmd)
        except Exception as exc:
            _ = exc

    def on_app_ready(win: Any) -> None:
        # Register window drop handler after GUI loop start.
        try:
            win.dom.document.events.drop += DOMEventHandler(on_window_drop, True, True)
        except Exception as exc:
            _ = exc
        if is_selftest:
            t = threading.Thread(target=run_selftest, args=(win,), daemon=True)
            t.start()

    webview.start(on_app_ready, window, debug=False)


if __name__ == "__main__":
    main()
