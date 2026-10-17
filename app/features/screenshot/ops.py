"""Screenshot and screen capture operations.

Provides both pure PIL fallbacks (ImageGrab) and Qt-native high-DPI screen grab.
"""
from __future__ import annotations

import io
from PIL import Image
from PyQt6.QtGui import QGuiApplication


def capture_full_screen(screen_index: int = 0) -> Image.Image:
    """Capture the full display into a PIL Image."""
    try:
        app = QGuiApplication.instance()
        if app:
            screens = app.screens()
            if screens:
                screen = screens[min(screen_index, len(screens) - 1)]
                pixmap = screen.grabWindow(0)
                qimage = pixmap.toImage().convertToFormat(pixmap.toImage().Format.Format_RGBA8888)
                ptr = qimage.bits()
                ptr.setsize(qimage.sizeInBytes())
                raw_bytes = bytes(ptr)
                return Image.frombuffer("RGBA", (qimage.width(), qimage.height()), raw_bytes, "raw", "RGBA", 0, 1).convert("RGB")
    except Exception:  # noqa: 10 (fall through to ImageGrab fallback below)
        pass

    # Fallback to PIL ImageGrab
    try:
        from PIL import ImageGrab  # noqa: 22
        return ImageGrab.grab().convert("RGB")
    except Exception as exc:
        raise RuntimeError(f"Screen capture is not supported on this platform: {exc}") from exc


def capture_screen_region(x: int, y: int, width: int, height: int, screen_index: int = 0) -> Image.Image:
    """Capture a rectangular region (x, y, w, h) of the screen into a PIL Image."""
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive.")

    try:
        app = QGuiApplication.instance()
        if app:
            screens = app.screens()
            if screens:
                screen = screens[min(screen_index, len(screens) - 1)]
                pixmap = screen.grabWindow(0, x, y, width, height)
                qimage = pixmap.toImage().convertToFormat(pixmap.toImage().Format.Format_RGBA8888)
                ptr = qimage.bits()
                ptr.setsize(qimage.sizeInBytes())
                raw_bytes = bytes(ptr)
                return Image.frombuffer("RGBA", (qimage.width(), qimage.height()), raw_bytes, "raw", "RGBA", 0, 1).convert("RGB")
    except Exception:  # noqa: 10 (fall through to ImageGrab fallback below)
        pass

    try:
        from PIL import ImageGrab  # noqa: 22
        bbox = (x, y, x + width, y + height)
        return ImageGrab.grab(bbox=bbox).convert("RGB")
    except Exception as exc:
        raise RuntimeError(f"Region capture failed: {exc}") from exc


def save_screenshot(img: Image.Image, output_path: str, format: str = "PNG") -> str:
    """Save screenshot image to disk."""
    img.save(output_path, format=format)
    return output_path
