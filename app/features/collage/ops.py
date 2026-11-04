"""Image collage and layer composition engine.

Supports grid collages, freeform multi-layer canvases, Z-order adjustments,
and layered exports in PSD, OpenRaster (ORA), ZIP, and TIFF formats.
"""
from __future__ import annotations

import io
import json
import logging
import math
import os
import zipfile
from dataclasses import dataclass
from typing import Any, Sequence
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

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
    # Return a reordered copy of an image list using sequence indices.
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
    # Apply a text watermark overlay to an image.
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
    cols: int = 2
    thumb_width: int = 400
    thumb_height: int = 400
    padding: int = 12
    bg_color: tuple = (240, 240, 240)
    fit_mode: str = "cover"
    cell_backgrounds: list[tuple[int, int, int] | None] | None = None
    corner_radius: int = 0


def _fit_cell(img: Image.Image, cell_w: int, cell_h: int, mode: str, bg_color: tuple = (240, 240, 240)) -> Image.Image:
    # Resize image to fill or fit inside a cell.
    if mode == "stretch":
        return img.resize((cell_w, cell_h), Image.Resampling.LANCZOS)

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
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        fill = (*bg_color, 255) if len(bg_color) == 3 else tuple(bg_color)
        canvas = Image.new("RGBA", (cell_w, cell_h), fill)
        x_off = (cell_w - new_w) // 2
        y_off = (cell_h - new_h) // 2
        canvas.paste(resized.convert("RGBA"), (x_off, y_off))
        return canvas

    if img_aspect > cell_aspect:
        new_h = cell_h
        new_w = max(1, int(cell_h * img_aspect))
    else:
        new_w = cell_w
        new_h = max(1, int(cell_w / img_aspect))
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
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
    # Arrange images in a padded grid and return a composited image.
    from app.features.image.ops import load_image

    if config is None:
        config = CollageConfig()
    if layout_name:
        preset = LAYOUT_PRESETS.get(layout_name)
        if not preset:
            raise ValueError(f"Unsupported collage layout: {layout_name}")
        if preset.get("cols") is not None:
            config.cols = preset["cols"]
        elif preset.get("rows") is not None and preset.get("cols") is None:
            config.cols = max(1, len(image_paths))
    if not image_paths:
        raise ValueError("No images provided for collage.")

    cols = max(1, config.cols)
    total_items = len(image_paths)
    rows = math.ceil(total_items / cols)

    cell_w = config.thumb_width
    cell_h = config.thumb_height
    caption_height = 28 if captions else 0
    pad = config.padding

    canvas_w = cols * cell_w + (cols + 1) * pad
    canvas_h = rows * (cell_h + caption_height) + (rows + 1) * pad

    bg_fill = (*config.bg_color, 255) if len(config.bg_color) == 3 else tuple(config.bg_color)
    canvas = Image.new("RGBA", (canvas_w, canvas_h), bg_fill)
    draw = ImageDraw.Draw(canvas)

    for idx, path in enumerate(image_paths):
        col = idx % cols
        row = idx // cols

        x = pad + col * (cell_w + pad)
        y = pad + row * (cell_h + caption_height + pad)

        try:
            raw = load_image(path)
            img = raw.convert("RGBA")
            cell = _fit_cell(img, cell_w, cell_h, config.fit_mode, config.bg_color)
        except Exception as exc:
            logger.debug("Failed fitting collage cell for %s: %s", path, exc)
            cell = Image.new("RGBA", (cell_w, cell_h), (200, 200, 200, 255))

        if config.corner_radius > 0:
            round_mask = Image.new("L", (cell_w, cell_h), 0)
            round_draw = ImageDraw.Draw(round_mask)
            round_draw.rounded_rectangle((0, 0, cell_w - 1, cell_h - 1), radius=max(0, config.corner_radius), fill=255)
            rounded = Image.new("RGBA", (cell_w, cell_h), (0, 0, 0, 0))
            rounded.paste(cell, (0, 0), round_mask)
            cell = rounded

        if config.cell_backgrounds:
            cbg = config.cell_backgrounds[idx] if idx < len(config.cell_backgrounds) and config.cell_backgrounds[idx] else config.bg_color
            if len(cbg) == 3:
                cbg = (*cbg, 255)
            background = Image.new("RGBA", (cell_w, cell_h), cbg)
            if config.corner_radius > 0:
                mask = Image.new("L", (cell_w, cell_h), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle((0, 0, cell_w - 1, cell_h - 1), radius=max(0, config.corner_radius), fill=255)
                background.paste(cell, (0, 0), mask)
            else:
                background.paste(cell, (0, 0))
            cell = background

        canvas.paste(cell, (x, y), mask=cell)

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

    if len(config.bg_color) == 4 and config.bg_color[3] < 255:
        return canvas
    return canvas.convert("RGB")


# Freeform Layers Compositor & Exporters

@dataclass
class CollageLayer:
    layer_id: str
    name: str
    source_path: str
    x: float
    y: float
    width: float
    height: float
    rotation_deg: float = 0.0
    opacity: float = 1.0
    visible: bool = True
    locked: bool = False


def transform_layer_bitmap(layer: CollageLayer) -> tuple[Image.Image, int, int]:
    # Transform layer source into resized, rotated, and opacity-adjusted bitmap.
    from app.features.image.ops import load_image

    img = load_image(layer.source_path).convert("RGBA")
    target_w = max(1, round(layer.width))
    target_h = max(1, round(layer.height))
    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    if abs(layer.rotation_deg) > 1e-3:
        rotated = img.rotate(-layer.rotation_deg, expand=True, resample=Image.Resampling.BICUBIC)
        orig_cx = layer.x + layer.width / 2.0
        orig_cy = layer.y + layer.height / 2.0
        top_left_x = round(orig_cx - rotated.width / 2.0)
        top_left_y = round(orig_cy - rotated.height / 2.0)
        img = rotated
    else:
        top_left_x = round(layer.x)
        top_left_y = round(layer.y)

    clamped_opacity = max(0.0, min(1.0, layer.opacity))
    if clamped_opacity < 1.0:
        alpha = img.split()[3]
        alpha = alpha.point(lambda p: round(p * clamped_opacity))
        img.putalpha(alpha)

    return img, top_left_x, top_left_y


def render_freeform_composite(
    canvas_width: int,
    canvas_height: int,
    layers: Sequence[CollageLayer],
    bg_rgba: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> Image.Image:
    # Composite all visible freeform layers in bottom-to-top Z-order.
    canvas = Image.new("RGBA", (canvas_width, canvas_height), bg_rgba)
    for layer in layers:
        if not layer.visible:
            continue
        bmp, tx, ty = transform_layer_bitmap(layer)
        ix0 = max(0, tx)
        iy0 = max(0, ty)
        ix1 = min(canvas_width, tx + bmp.width)
        iy1 = min(canvas_height, ty + bmp.height)
        if ix1 > ix0 and iy1 > iy0:
            crop_box = (ix0 - tx, iy0 - ty, ix1 - tx, iy1 - ty)
            cropped_bmp = bmp.crop(crop_box)
            canvas.alpha_composite(cropped_bmp, dest=(ix0, iy0))
    return canvas


def export_collage_layers(
    canvas_width: int,
    canvas_height: int,
    layers: Sequence[CollageLayer],
    output_path: str,
    export_format: str = "psd",
    bg_rgba: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> dict[str, Any]:
    # Export multi-layer collage in PSD, ORA, ZIP, or TIFF formats.
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fmt = export_format.lower().strip()

    if fmt == "psd":
        from psd_tools import PSDImage
        from psd_tools.api.layers import PixelLayer

        psd = PSDImage.new("RGBA", (canvas_width, canvas_height))
        if bg_rgba[3] > 0:
            bg_bmp = Image.new("RGBA", (canvas_width, canvas_height), bg_rgba)
            bg_layer = PixelLayer.frompil(bg_bmp, psd, "Background", top=0, left=0)
            psd.append(bg_layer)

        for layer in layers:
            bmp, tx, ty = transform_layer_bitmap(layer)
            px_layer = PixelLayer.frompil(bmp, psd, layer.name, top=ty, left=tx)
            px_layer.visible = layer.visible
            psd.append(px_layer)

        psd.save(output_path)
        return {"output_path": output_path, "layer_count": len(layers), "format": "psd"}

    if fmt == "ora":
        composite = render_freeform_composite(canvas_width, canvas_height, layers, bg_rgba=bg_rgba)
        with zipfile.ZipFile(output_path, "w") as zf:
            zf.writestr("mimetype", b"image/openraster", compress_type=zipfile.ZIP_STORED)

            comp_buf = io.BytesIO()
            composite.save(comp_buf, format="PNG")
            zf.writestr("mergedimage.png", comp_buf.getvalue())

            thumb = composite.resize((min(256, canvas_width), min(256, canvas_height)), Image.Resampling.LANCZOS)
            thumb_buf = io.BytesIO()
            thumb.save(thumb_buf, format="PNG")
            zf.writestr("Thumbnails/thumbnail.png", thumb_buf.getvalue())

            layer_xml_tags: list[str] = []
            for idx, layer in enumerate(reversed(layers)):
                bmp, tx, ty = transform_layer_bitmap(layer)
                l_buf = io.BytesIO()
                bmp.save(l_buf, format="PNG")
                entry_name = f"data/layer_{idx:03d}.png"
                zf.writestr(entry_name, l_buf.getvalue())
                vis_str = "visible" if layer.visible else "hidden"
                safe_name = layer.name.replace('"', '&quot;')
                layer_xml_tags.append(
                    f'    <layer name="{safe_name}" src="{entry_name}" x="{tx}" y="{ty}" opacity="{layer.opacity:.2f}" visibility="{vis_str}"/>'
                )

            stack_content = "\n".join(layer_xml_tags)
            stack_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<image version="0.0.1" w="{canvas_width}" h="{canvas_height}">\n  <stack>\n{stack_content}\n  </stack>\n</image>'
            zf.writestr("stack.xml", stack_xml)

        return {"output_path": output_path, "layer_count": len(layers), "format": "ora"}

    if fmt == "zip":
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            if bg_rgba[3] > 0:
                bg_full = Image.new("RGBA", (canvas_width, canvas_height), bg_rgba)
                b_buf = io.BytesIO()
                bg_full.save(b_buf, format="PNG")
                zf.writestr("00_background.png", b_buf.getvalue())

            manifest_layers: list[dict[str, Any]] = []
            for idx, layer in enumerate(layers):
                full_canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
                bmp, tx, ty = transform_layer_bitmap(layer)
                ix0 = max(0, tx)
                iy0 = max(0, ty)
                ix1 = min(canvas_width, tx + bmp.width)
                iy1 = min(canvas_height, ty + bmp.height)
                if ix1 > ix0 and iy1 > iy0:
                    crop_box = (ix0 - tx, iy0 - ty, ix1 - tx, iy1 - ty)
                    full_canvas.alpha_composite(bmp.crop(crop_box), dest=(ix0, iy0))

                l_buf = io.BytesIO()
                full_canvas.save(l_buf, format="PNG")
                clean_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in layer.name)
                fname = f"{idx + 1:02d}_{clean_name}.png"
                zf.writestr(fname, l_buf.getvalue())
                manifest_layers.append({
                    "layer_id": layer.layer_id,
                    "name": layer.name,
                    "filename": fname,
                    "x": layer.x,
                    "y": layer.y,
                    "width": layer.width,
                    "height": layer.height,
                    "rotation": layer.rotation_deg,
                    "opacity": layer.opacity,
                    "visible": layer.visible,
                })

            composite = render_freeform_composite(canvas_width, canvas_height, layers, bg_rgba=bg_rgba)
            comp_buf = io.BytesIO()
            composite.save(comp_buf, format="PNG")
            zf.writestr("composite.png", comp_buf.getvalue())

            manifest = {
                "canvas_width": canvas_width,
                "canvas_height": canvas_height,
                "layer_count": len(layers),
                "layers": manifest_layers,
            }
            zf.writestr("layers.json", json.dumps(manifest, indent=2))

        return {"output_path": output_path, "layer_count": len(layers), "format": "zip"}

    if fmt == "tiff":
        frames: list[Image.Image] = []
        if bg_rgba[3] > 0:
            frames.append(Image.new("RGBA", (canvas_width, canvas_height), bg_rgba))

        for layer in layers:
            full_frame = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
            bmp, tx, ty = transform_layer_bitmap(layer)
            ix0 = max(0, tx)
            iy0 = max(0, ty)
            ix1 = min(canvas_width, tx + bmp.width)
            iy1 = min(canvas_height, ty + bmp.height)
            if ix1 > ix0 and iy1 > iy0:
                crop_box = (ix0 - tx, iy0 - ty, ix1 - tx, iy1 - ty)
                full_frame.alpha_composite(bmp.crop(crop_box), dest=(ix0, iy0))
            frames.append(full_frame)

        if not frames:
            frames.append(Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0)))

        frames[0].save(
            output_path,
            format="TIFF",
            save_all=True,
            append_images=frames[1:],
            compression="tiff_deflate",
        )
        return {"output_path": output_path, "layer_count": len(layers), "format": "tiff"}

    raise ValueError(f"Unsupported layer export format: {export_format}")
