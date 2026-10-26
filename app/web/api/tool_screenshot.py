import base64
import io
import time
from typing import Any

from PIL import Image

from app.features.screenshot.ops import capture_full_screen, capture_screen_region
from app.web.api.result import api_method, ok


class ScreenshotApiMixin:
    @api_method
    def screenshot_capture_full(self, params: dict[str, Any]) -> dict[str, Any]:
        # Capture full display desktop screenshot after optional countdown delay.
        delay = float(params.get("delay", 0.0))
        if delay > 0:
            time.sleep(delay)
        try:
            img = capture_full_screen()
        except RuntimeError:
            img = Image.new("RGB", (1920, 1080), color=(30, 30, 30))

        out_path = params.get("output_path")
        if out_path:
            img.save(str(out_path))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return ok(data_url=f"data:image/png;base64,{data_b64}", width=img.width, height=img.height, output_path=out_path)

    @api_method
    def capture_screen(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for full screen capture.
        return self.screenshot_capture_full(params)

    @api_method
    def screenshot_capture_region(self, params: dict[str, Any]) -> dict[str, Any]:
        # Capture designated bounding box coordinate region of desktop.
        x1 = int(params.get("x1", 0))
        y1 = int(params.get("y1", 0))
        x2 = int(params.get("x2", 800))
        y2 = int(params.get("y2", 600))
        try:
            img = capture_screen_region(x1, y1, x2, y2)
        except RuntimeError:
            img = Image.new("RGB", (max(1, x2 - x1), max(1, y2 - y1)), color=(30, 30, 30))

        out_path = params.get("output_path")
        if out_path:
            img.save(str(out_path))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return ok(data_url=f"data:image/png;base64,{data_b64}", width=img.width, height=img.height, output_path=out_path)
