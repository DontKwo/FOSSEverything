"""Image operations: compress, convert, resize, crop, batch processing, and photo tools.

Kept free of Qt imports so it can be reused headlessly (CLI, batch script,
tests) without needing a GUI event loop.
"""
import io
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from app.core.file_formats import extension_for_format, normalized_format

SUPPORTED_FORMATS = ["JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF"]
SINGLE_IMAGE_EXPORT_FORMATS = [*SUPPORTED_FORMATS, "PDF"]
RAW_EXTENSIONS = {".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw"}
HEIF_EXTENSIONS = {".heic", ".heif", ".avif"}
_heif_registered = False


def _ensure_heif_registered() -> None:
    """Lazily register Pillow's HEIC/HEIF/AVIF opener. pillow_heif is a heavy
    optional import that most opened images (JPEG/PNG/etc.) never need."""
    global _heif_registered
    if not _heif_registered:
        import pillow_heif  # noqa: 13 (heavy optional dep, only needed for HEIC/HEIF/AVIF files)
        pillow_heif.register_heif_opener()
        _heif_registered = True

FILTER_PRESETS = [
    "Auto Enhance",
    "Vivid",
    "Warm Tone",
    "Cool Tone",
    "Grayscale",
    "High Contrast B&W",
    "Sepia",
    "Vintage / Fade",
    "Invert",
]

ASPECT_RATIO_PRESETS = {
    "1:1 Square (Avatar / Post)": (1, 1),
    "4:5 Portrait (Instagram)": (4, 5),
    "16:9 Landscape (YouTube / Desktop)": (16, 9),
    "9:16 Story (Reels / Mobile)": (9, 16),
    "4:3 Standard Photo": (4, 3),
    "3:2 Classic 35mm": (3, 2),
    "5:7 Portrait Print": (5, 7),
}

# These are intentionally local models. ``withoutbg`` is excluded because it
# is a remote/API-backed provider rather than an offline FOSSEverything feature.
BACKGROUND_REMOVAL_MODELS = {
    "bria-rmbg": ("Default", "Official rembg model; reliable default for local cutouts."),
    "u2net": ("Balanced", "General-purpose default; good quality and speed."),
    "u2netp": ("Fast", "Lightweight general model; fastest choice."),
    "isnet-general-use": ("Detailed", "Better general cutouts; slower than Balanced."),
    "birefnet-general": ("Best quality", "High-quality general cutouts; slowest option."),
    "birefnet-portrait": ("Portrait", "Best for people and portrait photos."),
}


def _normalize_model_name(model_name: Optional[str]) -> str:
    if model_name is None:
        return "bria-rmbg"
    value = str(model_name).strip().replace("\x00", "")
    aliases = {
        "bria_rmbg": "bria-rmbg",
        "bria-rmbg": "bria-rmbg",
        "default": "bria-rmbg",
        "balanced": "bria-rmbg",
        "fast": "u2netp",
        "detailed": "isnet-general-use",
        "best quality": "birefnet-general",
        "portrait": "birefnet-portrait",
    }
    return aliases.get(value.lower(), value)


def remove_background(img: Image.Image, model_name: str = "bria-rmbg") -> Image.Image:
    """Return an RGBA copy of *img* with its background made transparent.

    ``rembg`` runs inference on-device. Its model is downloaded once by the
    library on first use and reused locally after that; FOSSEverything never uploads
    the image. The inference engine is a required FOSSEverything dependency.
    """
    from rembg import new_session, remove  # noqa: 13 (deferred: multi-second import, only needed for this feature)

    model_name = _normalize_model_name(model_name)
    fallback_candidates = [model_name]
    if model_name not in BACKGROUND_REMOVAL_MODELS:
        fallback_candidates = ["bria-rmbg", "u2net", "u2netp", "isnet-general-use"]
    else:
        fallback_candidates.extend(["bria-rmbg", "u2net", "u2netp", "isnet-general-use"])

    last_error = None
    for candidate in fallback_candidates:
        candidate = _normalize_model_name(candidate)
        if candidate not in BACKGROUND_REMOVAL_MODELS:
            continue
        try:
            session = None
            try:
                session = new_session(candidate, providers=["CPUExecutionProvider"])
            except TypeError:
                session = new_session(candidate)
            except Exception as exc:
                last_error = exc
                session = new_session(candidate)
            return remove(img.convert("RGBA"), session=session)
        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError(f"Background removal failed for all local models. Last error: {last_error}")


def prefetch_background_removal_models(model_names: List[str], progress_cb: Optional[Callable[[int, int, str], None]] = None) -> List[str]:
    """Download and cache the given local background-removal models without processing an image."""
    from rembg import new_session  # noqa: 13 (deferred: multi-second import, only needed for this feature)

    fetched = []
    total = len(model_names)
    for i, raw_name in enumerate(model_names, 1):
        name = _normalize_model_name(raw_name)
        if progress_cb:
            progress_cb(i, total, name)
        new_session(name)
        fetched.append(name)
    return fetched


def _render_batch_output_name(source_path: str, template: str = "{stem}_bg_removed{ext}") -> str:
    """Render a unique output name for batch background-removal jobs."""
    source_name = os.path.basename(source_path)
    stem, ext = os.path.splitext(source_name)
    mapping = {"stem": stem, "name": stem, "filename": source_name, "ext": ext.lower(), "extension": ext.lower()}
    rendered = template
    for key, value in mapping.items():
        rendered = rendered.replace(f"{{{key}}}", str(value))
    return rendered


def batch_remove_background(file_paths: List[str], output_dir: Optional[str] = None, model_name: str = "bria-rmbg", filename_template: str = "{stem}_bg_removed{ext}", overwrite: bool = False, progress_cb: Optional[Callable[[int, int, str], None]] = None) -> List[str]:
    """Remove backgrounds from multiple local images and return the created file paths.

    progress_cb(index, total, filename), if given, is called after each file
    so a caller (e.g. a worker thread) can report progress to the UI.
    """
    output_paths = []
    total = len(file_paths)
    for i, file_path in enumerate(file_paths, start=1):
        img = Image.open(file_path)
        cleaned = remove_background(img, model_name=model_name)
        target_dir = output_dir or os.path.dirname(file_path)
        os.makedirs(target_dir, exist_ok=True)
        target_name = _render_batch_output_name(file_path, filename_template)
        target_path = os.path.join(target_dir, target_name)
        counter = 1
        while os.path.exists(target_path) and not overwrite:
            stem, ext = os.path.splitext(target_path)
            target_path = f"{stem}_{counter}{ext}"
            counter += 1
        save_image(cleaned, target_path, format=os.path.splitext(target_path)[1].lstrip("."), quality=95)
        output_paths.append(target_path)
        if progress_cb:
            progress_cb(i, total, os.path.basename(file_path))
    return output_paths


def load_image(path: Union[str, Path]) -> Image.Image:
    """Open an image, including HEIC/HEIF/AVIF, RAW camera formats, PSD, and SVG."""
    ext = os.path.splitext(str(path))[1].lower()
    if ext == ".svg":
        import cairosvg  # noqa: 13 (heavy optional dep, only needed for SVG files)
        png_bytes = cairosvg.svg2png(url=str(path))
        return Image.open(io.BytesIO(png_bytes))
    if ext == ".psd":
        from psd_tools import PSDImage  # noqa: 13 (heavy optional dep, only needed for PSD files)
        return PSDImage.open(path).composite()
    if ext in RAW_EXTENSIONS:
        import rawpy  # noqa: 13 (heavy optional dep, only needed for RAW camera files)
        with rawpy.imread(str(path)) as raw:
            rgb = raw.postprocess()
        return Image.fromarray(rgb)
    if ext in HEIF_EXTENSIONS:
        _ensure_heif_registered()
    return Image.open(path)


def save_image(img: Image.Image, output_path: Union[str, Path], format: Optional[str] = None, quality: int = 85, compress_well: bool = True, **extra_options: Union[int, bool, str]) -> None:
    fmt = normalized_format(format or img.format or "PNG")
    save_kwargs = {}
    if fmt in ("JPEG", "WEBP", "PDF"):
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if fmt != "PDF":
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = compress_well  # noqa: 4 (Pillow's real save() parameter name)
    elif fmt == "PNG":
        save_kwargs["optimize"] = compress_well  # noqa: 4 (Pillow's real save() parameter name)
    save_kwargs.update(extra_options)
    img.save(output_path, format=fmt, **save_kwargs)


def resize_image(img: Image.Image, width: int, height: int, keep_aspect: bool = True) -> Image.Image:
    if keep_aspect:
        img = img.copy()
        img.thumbnail((width, height), Image.LANCZOS)
        return img
    return img.resize((width, height), Image.LANCZOS)


def crop_image(img: Image.Image, box: Tuple[int, int, int, int]) -> Image.Image:
    """box: (left, top, right, bottom) in pixel coordinates."""
    return img.crop(box)


def circle_crop_image(img: Image.Image) -> Image.Image:
    """Crop to the largest centered square and make outside the circle transparent."""
    size = min(img.width, img.height)
    left = (img.width - size) // 2
    top = (img.height - size) // 2
    result = img.convert("RGBA").crop((left, top, left + size, top + size))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    result.putalpha(mask)
    return result


def build_rectangle_mask(size: Union[int, Tuple[int, int]], box: Optional[Tuple[int, int, int, int]] = None, feather: int = 0, invert: bool = False) -> Image.Image:
    """Create a local rectangular alpha mask for non-destructive compositing workflows."""
    if isinstance(size, (tuple, list)):
        width, height = size
    else:
        width = height = int(size)
    mask = Image.new("L", (width, height), 0 if not invert else 255)
    bounds = box or (0, 0, width, height)
    draw = ImageDraw.Draw(mask)
    draw.rectangle(bounds, fill=255 if not invert else 0)
    if feather:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    if invert:
        mask = ImageOps.invert(mask)
    return mask


def build_ellipse_mask(size: Union[int, Tuple[int, int]], box: Optional[Tuple[int, int, int, int]] = None, feather: int = 0, invert: bool = False) -> Image.Image:
    """Create a local elliptical alpha mask for non-destructive compositing workflows."""
    if isinstance(size, (tuple, list)):
        width, height = size
    else:
        width = height = int(size)
    mask = Image.new("L", (width, height), 0 if not invert else 255)
    draw = ImageDraw.Draw(mask)
    bounds = box or (0, 0, width, height)
    draw.ellipse(bounds, fill=255 if not invert else 0)
    if feather:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    if invert:
        mask = ImageOps.invert(mask)
    return mask


def build_circle_mask(size: Union[int, Tuple[int, int]], radius: int = 0, feather: int = 0, invert: bool = False) -> Image.Image:
    """Create a local circular alpha mask for non-destructive compositing workflows."""
    if isinstance(size, (tuple, list)):
        width, height = size
    else:
        width = height = int(size)
    mask = Image.new("L", (width, height), 0 if not invert else 255)
    cx = width // 2
    cy = height // 2
    r = max(1, min(width, height) // 2 if radius <= 0 else radius)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255 if not invert else 0)
    if feather:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    if invert:
        mask = ImageOps.invert(mask)
    return mask


def apply_non_destructive_mask(img: Image.Image, mask: Union[Image.Image, object], invert: bool = False, feather: int = 0, background: Tuple[int, int, int, int] = (0, 0, 0, 0)) -> Image.Image:
    """Apply an editable alpha mask while preserving the source pixels beneath the mask."""
    rgba = img.convert("RGBA")
    mask_img = mask.convert("L") if hasattr(mask, "convert") else Image.new("L", rgba.size, 255)
    if feather:
        mask_img = mask_img.filter(ImageFilter.GaussianBlur(feather))
    if invert:
        mask_img = ImageOps.invert(mask_img)

    if mask_img.size != rgba.size:
        mask_img = mask_img.resize(rgba.size, Image.Resampling.LANCZOS)

    base = Image.new("RGBA", rgba.size, background)
    base.putalpha(mask_img)
    result = Image.composite(rgba, base, mask_img)
    return result


def perspective_crop_image(img: Image.Image, corners: Union[List[Tuple[int, int]], Tuple[Tuple[int, int], ...]], output_size: Optional[Tuple[int, int]] = None, fill_color: Tuple[int, int, int, int] = (0, 0, 0, 0)) -> Image.Image:
    """Perspective-crop a quadrilateral region using OpenCV.

    corners: a 4-tuple/list of (x, y) points in clockwise order around the
    target region. output_size optionally specifies (width, height); when omitted,
    a tight bounding box is created from the supplied corners.
    """
    import cv2  # noqa: 13 (deferred: only needed for perspective crop)
    import numpy as np  # noqa: 13 (deferred: keeps numpy out of every image tab's cold-start import)

    if len(corners) != 4:
        raise ValueError("perspective_crop_image requires exactly four corner points.")

    pts_src = np.array(corners, dtype=np.float32)
    min_x = int(np.min(pts_src[:, 0]))
    max_x = int(np.max(pts_src[:, 0]))
    min_y = int(np.min(pts_src[:, 1]))
    max_y = int(np.max(pts_src[:, 1]))
    if output_size is None:
        width = max(1, max_x - min_x)
        height = max(1, max_y - min_y)
    else:
        width, height = output_size

    pts_dst = np.array([
        [0, 0],
        [width - 1, 0],
        [width - 1, height - 1],
        [0, height - 1],
    ], dtype=np.float32)

    matrix = cv2.getPerspectiveTransform(pts_src, pts_dst)
    rgba = np.array(img.convert("RGBA"), dtype=np.uint8)
    warped = cv2.warpPerspective(rgba, matrix, (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=fill_color)
    return Image.fromarray(warped, "RGBA")


def aspect_ratio_crop_box(width: int, height: int, ratio_w: Union[int, float], ratio_h: Union[int, float]) -> Tuple[int, int, int, int]:
    """Calculate centered (left, top, right, bottom) bounding box for target aspect ratio."""
    target_aspect = ratio_w / ratio_h
    current_aspect = width / height
    if current_aspect > target_aspect:
        new_width = int(round(height * target_aspect))
        new_height = height
        left = (width - new_width) // 2
        top = 0
    else:
        new_width = width
        new_height = int(round(width / target_aspect))
        left = 0
        top = (height - new_height) // 2
    return (left, top, left + new_width, top + new_height)


def rotate_image(img: Image.Image, degrees: Union[int, float]) -> Image.Image:
    return img.rotate(-degrees, expand=True)


def flip_image(img: Image.Image, horizontal: bool = True) -> Image.Image:
    """Flip an image left-to-right or top-to-bottom."""
    direction = Image.Transpose.FLIP_LEFT_RIGHT if horizontal else Image.Transpose.FLIP_TOP_BOTTOM
    return img.transpose(direction)


def adjust_image(img: Image.Image, brightness: Union[int, float] = 100, contrast: Union[int, float] = 100, saturation: Union[int, float] = 100, sharpness: Union[int, float] = 100,
                 blur_radius: Union[int, float] = 0, grayscale: bool = False, warmth: Union[int, float] = 0) -> Image.Image:
    """Apply comprehensive per-image visual adjustments using percentage/offset controls."""
    result = img.convert("RGBA")
    if brightness != 100:
        result = ImageEnhance.Brightness(result).enhance(brightness / 100)
    if contrast != 100:
        result = ImageEnhance.Contrast(result).enhance(contrast / 100)
    if saturation != 100:
        result = ImageEnhance.Color(result).enhance(saturation / 100)
    if sharpness != 100:
        result = ImageEnhance.Sharpness(result).enhance(sharpness / 100)

    if warmth != 0:
        r, g, b, a = result.split()
        shift = int(round(warmth * 0.4))
        r = r.point(lambda p: min(255, max(0, p + shift)))
        b = b.point(lambda p: min(255, max(0, p - shift)))
        result = Image.merge("RGBA", (r, g, b, a))

    if blur_radius > 0:
        alpha = result.getchannel("A")
        result = result.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        result.putalpha(alpha)

    if grayscale:
        alpha = result.getchannel("A")
        result = ImageOps.grayscale(result).convert("RGBA")
        result.putalpha(alpha)

    return result


def auto_enhance(img: Image.Image) -> Image.Image:
    """Automatically enhance contrast and balance histogram levels."""
    has_alpha = img.mode == "RGBA"
    alpha = img.getchannel("A") if has_alpha else None
    rgb = img.convert("RGB")
    enhanced = ImageOps.autocontrast(rgb, cutoff=0.5)
    enhanced = ImageEnhance.Color(enhanced).enhance(1.1)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.15)
    result = enhanced.convert("RGBA") if has_alpha else enhanced
    if alpha is not None:
        result.putalpha(alpha)
    return result


def apply_color_balance(img: Image.Image, red_shift: int = 0, green_shift: int = 0, blue_shift: int = 0) -> Image.Image:
    """Shift each RGB channel by a small amount for white-balance and tint adjustments."""
    result = img.convert("RGB")
    r, g, b = result.split()
    r = r.point(lambda v: max(0, min(255, v + red_shift)))
    g = g.point(lambda v: max(0, min(255, v + green_shift)))
    b = b.point(lambda v: max(0, min(255, v + blue_shift)))
    return Image.merge("RGB", (r, g, b))


def _interpolate_curve(value: int, points: list[tuple[int, int]]) -> int:
    """Map one channel value through a piecewise tonal curve."""
    if not points:
        return value
    if value <= points[0][0]:
        return points[0][1]
    for idx in range(len(points) - 1):
        x1, y1 = points[idx]
        x2, y2 = points[idx + 1]
        if x1 <= value <= x2:
            if x2 == x1:
                return y2
            ratio = (value - x1) / (x2 - x1)
            return int(round(y1 + (y2 - y1) * ratio))
    return points[-1][1]


def apply_curves(img: Image.Image, red_points: Optional[List[Tuple[int, int]]] = None, green_points: Optional[List[Tuple[int, int]]] = None, blue_points: Optional[List[Tuple[int, int]]] = None) -> Image.Image:
    """Apply simple tonal curves to the red, green, and blue channels."""
    rgb = img.convert("RGB")
    r, g, b = rgb.split()
    if red_points is None:
        red_points = [(0, 0), (128, 128), (255, 255)]
    if green_points is None:
        green_points = [(0, 0), (128, 128), (255, 255)]
    if blue_points is None:
        blue_points = [(0, 0), (128, 128), (255, 255)]

    def adjust_channel(channel: Image.Image, points: List[Tuple[int, int]]) -> Image.Image:
        return channel.point(lambda v: max(0, min(255, _interpolate_curve(v, points))))

    return Image.merge("RGB", (
        adjust_channel(r, red_points),
        adjust_channel(g, green_points),
        adjust_channel(b, blue_points),
    ))


ANNOTATION_PRESETS = {
    "callout-badge": {
        "name": "callout badge",
        "style": "highlight",
        "fill": (255, 237, 121),
        "stroke": (40, 40, 40),
        "border_radius": 12,
    },
    "magnifier-inset": {
        "name": "magnifier inset",
        "style": "zoom-box",
        "zoom": 2.0,
        "stroke": (255, 255, 255),
    },
    "numbered-step": {
        "name": "numbered step",
        "style": "step-marker",
        "fill": (66, 153, 225),
        "stroke": (255, 255, 255),
    },
}


def build_annotation_preset(name: str, **kwargs: Union[str, int, float, Tuple[int, int, int], float]) -> Dict[str, Union[str, int, float, Tuple[int, int, int], float]]:
    """Build a reusable annotation preset matching the future-work document naming."""
    if name not in ANNOTATION_PRESETS:
        raise ValueError(f"Unsupported annotation preset: {name}")
    preset = dict(ANNOTATION_PRESETS[name])
    preset.update(kwargs)
    return preset


def apply_filter_preset(img: Image.Image, preset_name: str) -> Image.Image:
    """Apply a named photographic filter look."""
    if preset_name == "Auto Enhance":
        return auto_enhance(img)
    if preset_name == "Grayscale":
        return adjust_image(img, grayscale=True)
    if preset_name == "High Contrast B&W":
        return adjust_image(img, contrast=140, grayscale=True, sharpness=120)
    if preset_name == "Sepia":
        gray = ImageOps.grayscale(img.convert("RGB"))
        sepia = ImageOps.colorize(gray, black=(35, 20, 10), white=(255, 240, 200))
        if img.mode == "RGBA":
            sepia = sepia.convert("RGBA")
            sepia.putalpha(img.getchannel("A"))
        return sepia
    if preset_name == "Warm Tone":
        return adjust_image(img, warmth=40, saturation=115, contrast=105)
    if preset_name == "Cool Tone":
        return adjust_image(img, warmth=-40, saturation=105, contrast=105)
    if preset_name == "Vivid":
        return adjust_image(img, contrast=125, saturation=135, sharpness=130)
    if preset_name == "Vintage / Fade":
        return adjust_image(img, contrast=85, brightness=110, saturation=85, warmth=20)
    if preset_name == "Invert":
        has_alpha = img.mode == "RGBA"
        alpha = img.getchannel("A") if has_alpha else None
        inverted = ImageOps.invert(img.convert("RGB"))
        if has_alpha:
            inverted = inverted.convert("RGBA")
            inverted.putalpha(alpha)
        return inverted
    return img.copy()


def add_border(img: Image.Image, border_size: int = 20, color: Tuple[int, int, int] = (255, 255, 255), polaroid: bool = False) -> Image.Image:
    """Add a solid or Polaroid-style frame around an image."""
    result = img.convert("RGBA")
    bottom_pad = border_size * 4 if polaroid else border_size
    new_width = result.width + border_size * 2
    new_height = result.height + border_size + bottom_pad
    bg = Image.new("RGBA", (new_width, new_height), (*color[:3], 255))
    bg.paste(result, (border_size, border_size), result)
    return bg


def blur_region(img: Image.Image, box: Tuple[int, int, int, int], radius: int = 15) -> Image.Image:
    """Apply Gaussian blur to a specific region (left, top, right, bottom)."""
    result = img.copy()
    left, top, right, bottom = [int(v) for v in box]
    left = max(0, min(result.width, left))
    top = max(0, min(result.height, top))
    right = max(left, min(result.width, right))
    bottom = max(top, min(result.height, bottom))
    if right - left < 1 or bottom - top < 1:
        return result
    region = result.crop((left, top, right, bottom))
    blurred = region.filter(ImageFilter.GaussianBlur(radius=radius))
    result.paste(blurred, (left, top))
    return result


def pixelate_region(img: Image.Image, box: Tuple[int, int, int, int], pixel_size: int = 12) -> Image.Image:
    """Apply mosaic pixelation redaction to a specific region (left, top, right, bottom)."""
    result = img.copy()
    left, top, right, bottom = [int(v) for v in box]
    left = max(0, min(result.width, left))
    top = max(0, min(result.height, top))
    right = max(left, min(result.width, right))
    bottom = max(top, min(result.height, bottom))
    width, height = right - left, bottom - top
    if width < 1 or height < 1:
        return result
    region = result.crop((left, top, right, bottom))
    small_w = max(1, width // pixel_size)
    small_h = max(1, height // pixel_size)
    small = region.resize((small_w, small_h), Image.Resampling.NEAREST)
    pixelated = small.resize((width, height), Image.Resampling.NEAREST)
    result.paste(pixelated, (left, top))
    return result


def replace_background_color(img: Image.Image, color: Tuple[int, int, int, int] = (255, 255, 255, 255), blur_backdrop: bool = False, blur_radius: int = 25) -> Image.Image:
    """Composite a transparent cutout onto a solid color or blurred backdrop."""
    cutout = img.convert("RGBA")
    if blur_backdrop:
        bg = cutout.convert("RGB").filter(ImageFilter.GaussianBlur(radius=blur_radius)).convert("RGBA")
    else:
        bg = Image.new("RGBA", cutout.size, color)
    bg.paste(cutout, (0, 0), cutout)
    return bg


def batch_process(paths: List[str], output_dir: str, target_format: Optional[str] = None, quality: int = 85,
                   resize_to: Optional[Tuple[int, int]] = None, keep_aspect: bool = True,
                   remove_background_enabled: bool = False, bg_model: str = "bria-rmbg",
                   progress_cb: Optional[Callable[[int, int, str], None]] = None) -> List[str]:
    """Apply the same pipeline (remove background -> resize -> convert -> compress) to many images.

    progress_cb(index, total, filename), if given, is called after each file
    so a caller (e.g. a worker thread) can report progress to the UI.
    Returns the list of output paths written.
    """
    os.makedirs(output_dir, exist_ok=True)
    outputs = []
    total = len(paths)
    for i, path in enumerate(paths, start=1):
        img = Image.open(path)
        if remove_background_enabled:
            img = remove_background(img, model_name=bg_model)
        if resize_to:
            img = resize_image(img, resize_to[0], resize_to[1], keep_aspect)
        base = os.path.splitext(os.path.basename(path))[0]
        default_format = "PNG" if remove_background_enabled else (img.format or "JPEG")
        fmt = normalized_format(target_format or default_format)
        ext = extension_for_format(fmt)
        out_path = os.path.join(output_dir, f"{base}{ext}")
        save_image(img, out_path, format=fmt, quality=quality)
        outputs.append(out_path)
        if progress_cb:
            progress_cb(i, total, os.path.basename(path))
    return outputs


# ─── ASCII Art ────────────────────────────────────────────────────────────────
ASCII_CHARSET = "@%#*+=-:. "

ASCII_CHARSET_PRESETS: Dict[str, str] = {
    "Standard": "@%#*+=-:. ",
    "Detailed": "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. ",
    "Blocks": "█▓▒░ ",
    "Minimal": "#. ",
}


def image_to_ascii(img: Image.Image, width: int = 100, charset: str = ASCII_CHARSET, contrast: float = 100.0) -> str:
    """Render an image as ASCII art text using a brightness-ramp character set."""
    import numpy as np  # noqa: 13 (deferred: keeps numpy out of every image tab's cold-start import)
    aspect_correction = 0.55
    src_w, src_h = img.size
    height = max(1, int(width * (src_h / src_w) * aspect_correction))
    source = adjust_image(img, contrast=contrast) if contrast != 100.0 else img
    small = source.convert("L").resize((max(1, width), height))
    pixels = np.array(small)
    ramp_len = len(charset) - 1
    indices = (pixels.astype(np.float32) / 255.0 * ramp_len).astype(np.int32)
    return "\n".join("".join(charset[i] for i in row) for row in indices)


def save_ascii_art(img: Image.Image, output_path: str, width: int = 100, charset: str = ASCII_CHARSET, contrast: float = 100.0) -> str:
    """Write ASCII art rendered from an image to a local text file."""
    text = image_to_ascii(img, width=width, charset=charset, contrast=contrast)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    return output_path


# ─── Animated GIF Frames ──────────────────────────────────────────────────────
def extract_gif_frames(path: Union[str, Path]) -> List[Image.Image]:
    """Return every frame of an animated GIF as separate RGBA images."""
    img = Image.open(path)
    frames = []
    try:
        while True:
            frames.append(img.convert("RGBA").copy())
            img.seek(img.tell() + 1)
    except EOFError:  # noqa: 10
        pass
    return frames


def frames_to_gif(frames: List[Image.Image], output_path: Union[str, Path], duration_ms: int = 100, loop: int = 0) -> str:
    """Build an animated GIF from a sequence of images."""
    if not frames:
        raise ValueError("At least one frame is required to build a GIF.")
    converted = [f.convert("P", palette=Image.ADAPTIVE) for f in frames]
    converted[0].save(output_path, format="GIF", save_all=True, append_images=converted[1:], duration=duration_ms, loop=loop)
    return str(output_path)


def _local_ffmpeg_path() -> str:
    """Resolve the local FFmpeg binary without importing app.features.media.ops (which itself imports this module)."""
    import imageio_ffmpeg  # noqa: 13 (heavy optional dep, only needed for gif/video conversion)
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    if exe and os.path.exists(exe):
        return exe
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    raise RuntimeError("FFmpeg executable not found. Please install imageio-ffmpeg or add ffmpeg to PATH.")


def gif_to_video(input_path: Union[str, Path], output_path: Union[str, Path], fps: Optional[int] = None) -> str:
    """Convert an animated GIF into an MP4 video using the local FFmpeg binary."""
    img = Image.open(input_path)
    durations_ms: List[int] = []
    frames: List[Image.Image] = []
    try:
        while True:
            durations_ms.append(img.info.get("duration", 100))
            frames.append(img.convert("RGB").copy())
            img.seek(img.tell() + 1)
    except EOFError:  # noqa: 10
        pass
    if not frames:
        raise ValueError("GIF has no frames to convert.")

    avg_duration_ms = sum(durations_ms) / len(durations_ms)
    resolved_fps = fps if fps else max(1, round(1000.0 / avg_duration_ms))

    with tempfile.TemporaryDirectory() as tmp_dir:
        for index, frame in enumerate(frames):
            frame.save(os.path.join(tmp_dir, f"frame_{index:05d}.png"))
        cmd = [
            _local_ffmpeg_path(), "-y", "-framerate", str(resolved_fps),
            "-i", os.path.join(tmp_dir, "frame_%05d.png"),
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-pix_fmt", "yuv420p",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
    return str(output_path)

