"""PyWebView desktop entry point for FOSSEverything."""
from __future__ import annotations

import ctypes
import os
import sys
import webview

from app.web.api import WebApi


def main() -> None:
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FOSSEverything.DesktopApp")

    api = WebApi()
    web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "web")
    html_path = os.path.join(web_dir, "index.html")

    window = webview.create_window(
        title="FOSSEverything",
        url=html_path,
        js_api=api,
        width=1320,
        height=880,
        min_size=(960, 640),
        background_color="#090d16",
    )
    api.set_window(window)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
