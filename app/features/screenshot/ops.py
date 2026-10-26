"""Screenshot and screen capture operations using PIL."""
from __future__ import annotations

from PIL import Image, ImageGrab


def capture_full_screen(screen_index: int = 0) -> Image.Image:
    """Capture the full display into a PIL Image."""
    try:
        return ImageGrab.grab().convert("RGB")
    except Exception as exc:
        raise RuntimeError(f"Screen capture is not supported on this platform: {exc}") from exc


def capture_screen_region(x: int, y: int, width: int, height: int, screen_index: int = 0) -> Image.Image:
    """Capture a rectangular region (x, y, w, h) of the screen into a PIL Image."""
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive.")

    try:
        bbox = (x, y, x + width, y + height)
        return ImageGrab.grab(bbox=bbox).convert("RGB")
    except Exception as exc:
        raise RuntimeError(f"Region capture failed: {exc}") from exc


def save_screenshot(img: Image.Image, output_path: str, format: str = "PNG") -> str:
    """Save screenshot image to disk."""
    img.save(output_path, format=format)
    return output_path
