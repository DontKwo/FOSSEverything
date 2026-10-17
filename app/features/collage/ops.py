"""Image collage / grid composer. Pure Pillow - no extra dependencies."""
from __future__ import annotations

import math
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont


LAYOUT_PRESETS = {
    "2-column grid": {"cols": 2, "rows": None},
    "3-column grid": {"cols": 3, "rows": None},
    "2x2 quad": {"cols": 2, "rows": 2},
    "3x3 grid": {"cols": 3, "rows": 3},
    "Side-by-side (1 row)": {"cols": None, "rows": 1},
    "Stacked (1 column)": {"cols": 1, "rows": None},
    "Side-by-side 2-up": {"cols": 2, "rows": 1},
    "Triptych": {"cols": 3, "rows": 1},
    "Instagram grid": {"cols": 3, "rows": 3},
}


def reorder_image_paths(image_paths: list[str], order: list[int]) -> list[str]:
    """Return a reordered copy of an image list using the exact drag/drop sequence."""
    if not order:
        return list(image_paths)
    if sorted(order) != list(range(len(image_paths))):
        raise ValueError("Image reorder order must be a permutation of 0..n-1.")
    return [image_paths[i] for i in order]


def add_watermark_to_image(
    image: Image.Image,
    text: str,
    opacity: float = 0.30,
    color: tuple[int, int, int] = (255, 255, 255),
    position: str = "diagonal",
    font_size: int = 28,
    rotation: int = 45,
) -> Image.Image:
    """Apply a subtle text watermark to a collage or image export."""
    result = image.convert("RGBA")
    overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    if position == "center":
        anchor = ((result.width - text_w) // 2, (result.height - text_h) // 2)
    elif position == "bottom-right":
        anchor = (result.width - text_w - 20, result.height - text_h - 20)
    elif position == "top-left":
        anchor = (20, 20)
    else:
        anchor = (max(10, result.width // 6), max(10, result.height // 6))

    watermark = Image.new("RGBA", result.size, (0, 0, 0, 0))
    watermark_draw = ImageDraw.Draw(watermark)
    watermark_draw.text(anchor, text, font=font, fill=(*color, int(255 * opacity)))

    if rotation:
        rotated = watermark.rotate(rotation, expand=True, fillcolor=(0, 0, 0, 0))
        watermark = rotated
    if watermark.size != result.size:
        watermark = watermark.resize(result.size, Image.Resampling.LANCZOS)

    return Image.alpha_composite(result, watermark).convert("RGBA")


@dataclass
class CollageConfig:
    cols: int = 2                           # number of columns
    thumb_width: int = 400                  # width of each thumbnail cell
    thumb_height: int = 400                 # height of each thumbnail cell
    padding: int = 12                       # gap between cells
    bg_color: tuple = (240, 240, 240)       # canvas background color
    fit_mode: str = "cover"                 # "cover", "contain", or "stretch"
    cell_backgrounds: list[tuple[int, int, int] | None] | None = None
    corner_radius: int = 0                   # optional rounded corners in pixels


def _fit_cell(img: Image.Image, cell_w: int, cell_h: int, mode: str, bg_color: tuple = (240, 240, 240)) -> Image.Image:
    """Resize *img* to fill (cover) or fit inside (contain) a cell."""
    if mode == "stretch":
        return img.resize((cell_w, cell_h), Image.LANCZOS)

    img_w, img_h = img.size
    img_aspect = img_w / img_h
    cell_aspect = cell_w / cell_h

    if mode == "contain":
        if img_aspect > cell_aspect:
            new_w = cell_w
            new_h = max(1, int(cell_w / img_aspect))
        else:
            new_h = cell_h
            new_w = max(1, int(cell_h * img_aspect))
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        fill = (*bg_color, 255) if len(bg_color) == 3 else tuple(bg_color)
        canvas = Image.new("RGBA", (cell_w, cell_h), fill)
        x_off = (cell_w - new_w) // 2
        y_off = (cell_h - new_h) // 2
        canvas.paste(resized.convert("RGBA"), (x_off, y_off))
        return canvas

    # cover: fill cell, center-crop excess
    if img_aspect > cell_aspect:
        new_h = cell_h
        new_w = max(1, int(cell_h * img_aspect))
    else:
        new_w = cell_w
        new_h = max(1, int(cell_w / img_aspect))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    x_off = (new_w - cell_w) // 2
    y_off = (new_h - cell_h) // 2
    return resized.crop((x_off, y_off, x_off + cell_w, y_off + cell_h))


def make_collage(
    image_paths: list[str],
    config: CollageConfig | None = None,
    captions: list[str] | None = None,
    layout_name: str | None = None,
    watermark_text: str | None = None,
    watermark_color: tuple[int, int, int] = (255, 255, 255),
    watermark_opacity: float = 0.30,
) -> Image.Image:
    """Arrange images in a padded grid and return a composited PIL image.

    Supports cover, contain, and stretch fit modes and optional captions.
    """
    if config is None:
        config = CollageConfig()
    if layout_name:
        preset = LAYOUT_PRESETS.get(layout_name)
        if not preset:
            raise ValueError(f"Unsupported collage layout: {layout_name}")
        if preset.get("cols") is not None:
            config.cols = preset["cols"]
        if preset.get("rows") is not None:
            config.cols = max(1, preset["cols"] or config.cols)
    if not image_paths:
        raise ValueError("No images provided for collage.")

    cols = config.cols
    n = len(image_paths)
    rows = math.ceil(n / cols)

    cell_w = config.thumb_width
    cell_h = config.thumb_height
    caption_height = 28 if captions else 0
    p = config.padding

    canvas_w = cols * cell_w + (cols + 1) * p
    canvas_h = rows * (cell_h + caption_height) + (rows + 1) * p

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (*config.bg_color, 255))
    draw = ImageDraw.Draw(canvas)

    for idx, path in enumerate(image_paths):
        col = idx % cols
        row = idx // cols

        x = p + col * (cell_w + p)
        y = p + row * (cell_h + caption_height + p)

        try:
            with Image.open(path) as raw:
                img = raw.convert("RGBA")
            cell = _fit_cell(img, cell_w, cell_h, config.fit_mode, config.bg_color)
        except Exception:
            cell = Image.new("RGBA", (cell_w, cell_h), (200, 200, 200, 255))

        if config.corner_radius > 0:
            round_mask = Image.new("L", (cell_w, cell_h), 0)
            round_draw = ImageDraw.Draw(round_mask)
            round_draw.rounded_rectangle((0, 0, cell_w - 1, cell_h - 1), radius=max(0, config.corner_radius), fill=255)
            rounded = Image.new("RGBA", (cell_w, cell_h), (0, 0, 0, 0))
            rounded.paste(cell, (0, 0), round_mask)
            cell = rounded

        if config.cell_backgrounds:
            bg_color = config.cell_backgrounds[idx] if idx < len(config.cell_backgrounds) and config.cell_backgrounds[idx] else config.bg_color
            if len(bg_color) == 3:
                bg_color = (*bg_color, 255)
            background = Image.new("RGBA", (cell_w, cell_h), bg_color)
            if config.corner_radius > 0:
                mask = Image.new("L", (cell_w, cell_h), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle((0, 0, cell_w - 1, cell_h - 1), radius=max(0, config.corner_radius), fill=255)
                background.paste(cell, (0, 0), mask)
                cell = background
            else:
                background.paste(cell, (0, 0))
                cell = background

        canvas.paste(cell, (x, y))

        if captions and idx < len(captions) and captions[idx]:
            caption_y = y + cell_h + 4
            draw.rectangle([x, caption_y, x + cell_w, caption_y + caption_height - 4], fill=(50, 50, 50, 200))
            try:
                font = ImageFont.load_default(size=13)
            except TypeError:
                font = ImageFont.load_default()
            draw.text((x + 6, caption_y + 4), captions[idx], fill=(255, 255, 255), font=font)

    if watermark_text:
        canvas = add_watermark_to_image(
            canvas,
            watermark_text,
            opacity=watermark_opacity,
            color=watermark_color,
            position="diagonal",
            font_size=max(18, min(canvas.width // 20, 54)),
        )

    return canvas.convert("RGB")
