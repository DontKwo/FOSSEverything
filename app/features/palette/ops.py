"""Color palette extraction from images. Pure Pillow - no extra deps."""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np
from PIL import Image


CSS_NAMED_COLORS = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0), "green": (0, 128, 0),
    "blue": (0, 0, 255), "yellow": (255, 255, 0), "cyan": (0, 255, 255), "magenta": (255, 0, 255),
    "orange": (255, 165, 0), "purple": (128, 0, 128), "pink": (255, 192, 203), "brown": (165, 42, 42),
    "gray": (128, 128, 128), "silver": (192, 192, 192), "maroon": (128, 0, 0), "navy": (0, 0, 128),
    "teal": (0, 128, 128), "olive": (128, 128, 0), "lime": (0, 255, 0), "aqua": (0, 255, 255),
    "fuchsia": (255, 0, 255), "gold": (255, 215, 0), "indigo": (75, 0, 130), "violet": (238, 130, 238),
    "coral": (255, 127, 80), "tomato": (255, 99, 71), "salmon": (250, 128, 114), "beige": (245, 245, 220),
    "tan": (210, 180, 140), "khaki": (240, 230, 140), "azure": (240, 255, 255), "aliceblue": (240, 248, 255),
    "lavender": (230, 230, 250), "mintcream": (245, 255, 250), "honeydew": (240, 255, 240), "snow": (255, 250, 250),
}


@dataclass
class ColorSwatch:
    hex_code: str
    rgb: tuple[int, int, int]
    percentage: float
    name: str | None = None

    @property
    def rgb_str(self) -> str:
        return f"rgb({self.rgb[0]}, {self.rgb[1]}, {self.rgb[2]})"

    @property
    def css_name(self) -> str:
        return self.name or nearest_named_color(self.rgb)


def nearest_named_color(rgb: tuple[int, int, int]) -> str:
    """Return the nearest CSS-like color name for a given RGB triplet."""
    best_name = "black"
    best_distance = float("inf")
    for name, base in CSS_NAMED_COLORS.items():
        distance = sqrt(sum((a - b) ** 2 for a, b in zip(rgb, base)))
        if distance < best_distance:
            best_distance = distance
            best_name = name
    return best_name


def contrast_ratio(rgb_a: tuple[int, int, int], rgb_b: tuple[int, int, int]) -> float:
    """Calculate WCAG contrast ratio between two RGB colors."""
    def luminance(rgb: tuple[int, int, int]) -> float:
        r, g, b = [c / 255 for c in rgb]
        channels = []
        for c in (r, g, b):
            channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
        r, g, b = channels
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    lum_a = luminance(rgb_a)
    lum_b = luminance(rgb_b)
    lighter = max(lum_a, lum_b)
    darker = min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def kmeans_palette(
    img: Image.Image,
    n_colors: int = 5,
    max_dimension: int = 200,
    max_iterations: int = 20,
    sample_step: int = 2,
) -> list[ColorSwatch]:
    """Extract a palette using a lightweight K-means clustering pass over sampled pixels."""
    thumb = img.copy().convert("RGB")
    if thumb.width > max_dimension or thumb.height > max_dimension:
        thumb.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    pixels = np.asarray(thumb, dtype=np.float64).reshape(-1, 3)
    if len(pixels) == 0:
        return []
    sample = pixels[::sample_step]
    if len(sample) < n_colors:
        n_colors = len(sample)
    centers = sample[np.linspace(0, len(sample) - 1, n_colors, dtype=int)].copy()

    for _ in range(max_iterations):
        distances = ((sample[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = distances.argmin(axis=1)

        new_centers = centers.copy()
        for idx in range(n_colors):
            mask = labels == idx
            if mask.any():
                new_centers[idx] = np.round(sample[mask].mean(axis=0))

        if np.all(np.abs(new_centers - centers).sum(axis=1) <= 1):
            centers = new_centers
            break
        centers = new_centers

    swatches = []
    for center in centers:
        rgb = tuple(max(0, min(255, int(v))) for v in center)
        hex_code = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
        swatches.append(ColorSwatch(hex_code=hex_code, rgb=rgb, percentage=0.0, name=nearest_named_color(rgb)))

    total_pixels = len(sample)
    if total_pixels:
        for swatch in swatches:
            matches = int(np.all(sample == np.array(swatch.rgb, dtype=np.float64), axis=1).sum())
            swatch.percentage = round(matches / total_pixels * 100, 1)
    return swatches


def extract_palette(
    img: Image.Image,
    n_colors: int = 8,
    max_dimension: int = 300,
    method: str = "median-cut",
) -> list[ColorSwatch]:
    """Extract the top *n_colors* dominant colors from *img*.

    Uses Pillow's built-in quantizer (median cut) for speed, and supports a
    lightweight K-means mode for more perceptually balanced palettes.
    """
    if method.lower() == "kmeans":
        return kmeans_palette(img, n_colors=n_colors, max_dimension=max_dimension)

    # Resize for speed
    thumb = img.copy().convert("RGB")
    if thumb.width > max_dimension or thumb.height > max_dimension:
        thumb.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    # Quantize to n_colors + some headroom, then pick top n_colors
    quantized = thumb.quantize(colors=min(n_colors + 16, 256), method=Image.Quantize.MEDIANCUT)
    palette_rgb = quantized.convert("RGB")

    # Count pixels per cluster
    if hasattr(palette_rgb, "get_flattened_data"):
        pixel_data = list(palette_rgb.get_flattened_data())
    else:
        pixel_data = list(palette_rgb.getdata())
    total_pixels = len(pixel_data)
    counts: dict[tuple[int, int, int], int] = {}
    for px in pixel_data:
        counts[px] = counts.get(px, 0) + 1

    # Sort by frequency and pick top n
    sorted_colors = sorted(counts.items(), key=lambda kv: -kv[1])[:n_colors]
    swatches = []
    for rgb, count in sorted_colors:
        r, g, b = rgb
        hex_code = f"#{r:02X}{g:02X}{b:02X}"
        pct = round(count / total_pixels * 100, 1)
        swatches.append(ColorSwatch(hex_code=hex_code, rgb=rgb, percentage=pct, name=nearest_named_color(rgb)))

    return swatches


def generate_palette_strip(swatches: list[ColorSwatch], width: int = 400, height: int = 60) -> Image.Image:
    """Render a horizontal color strip image from *swatches* suitable for display or export."""
    img = Image.new("RGB", (width, height), (30, 30, 30))
    n = len(swatches)
    if n == 0:
        return img
    swatch_w = width // n
    for i, swatch in enumerate(swatches):
        x0 = i * swatch_w
        x1 = x0 + swatch_w if i < n - 1 else width
        block = Image.new("RGB", (x1 - x0, height), swatch.rgb)
        img.paste(block, (x0, 0))
    return img


def sample_pixel_color(img: Image.Image, x: int, y: int) -> ColorSwatch:
    """Sample the exact color of the pixel at coordinates (x, y)."""
    rgb_img = img.convert("RGB")
    clamped_x = max(0, min(rgb_img.width - 1, x))
    clamped_y = max(0, min(rgb_img.height - 1, y))
    r, g, b = rgb_img.getpixel((clamped_x, clamped_y))[:3]
    hex_code = f"#{r:02X}{g:02X}{b:02X}"
    return ColorSwatch(hex_code=hex_code, rgb=(r, g, b), percentage=0.0, name=nearest_named_color((r, g, b)))


