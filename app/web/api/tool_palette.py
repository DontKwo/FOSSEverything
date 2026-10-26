from pathlib import Path
from typing import Any

from PIL import Image

from app.features.palette.ops import (
    ColorSwatch,
    contrast_ratio,
    extract_palette,
    nearest_named_color,
    sample_pixel_color,
)
from app.web.api.result import api_method, ok, require


def _calc_to_rgb(color_val: Any) -> tuple[int, int, int]:
    # Parse color representation into 3-tuple integer RGB channels.
    if isinstance(color_val, (list, tuple)) and len(color_val) >= 3:
        return (int(color_val[0]), int(color_val[1]), int(color_val[2]))
    val = str(color_val).strip().lstrip("#")
    if len(val) == 3:
        val = "".join(c * 2 for c in val)
    if len(val) == 6:
        return (int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16))
    return (0, 0, 0)


class PaletteApiMixin:
    @api_method
    def palette_extract(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract dominant color swatches from image using median-cut or k-means.
        require(params, "image_path")
        img_path = str(params["image_path"])
        num_colors = int(params.get("num_colors", params.get("n_colors", 8)))
        method = str(params.get("method", "median_cut"))
        with Image.open(img_path) as raw_img:
            img = raw_img.convert("RGB")
        swatches = extract_palette(img, n_colors=num_colors, method=method)
        results = [
            {
                "hex": s.hex_code,
                "rgb": [s.rgb[0], s.rgb[1], s.rgb[2]],
                "percentage": round(s.percentage, 1),
                "name": s.name or nearest_named_color(s.rgb),
            }
            for s in swatches
        ]
        return ok(palette=results, count=len(results), image_path=img_path)

    @api_method
    def palette_sample_pixel(self, params: dict[str, Any]) -> dict[str, Any]:
        # Sample exact pixel RGB color at given image coordinates.
        require(params, "image_path", "x", "y")
        img_path = str(params["image_path"])
        x = int(params["x"])
        y = int(params["y"])
        rgb = sample_pixel_color(img_path, x, y)
        hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        c_white = contrast_ratio(rgb, (255, 255, 255))
        c_black = contrast_ratio(rgb, (0, 0, 0))
        name = nearest_named_color(hex_color)
        return ok(rgb=list(rgb), hex=hex_color, contrast_white=round(c_white, 2), contrast_black=round(c_black, 2), name=name)

    @api_method
    def palette_contrast(self, params: dict[str, Any]) -> dict[str, Any]:
        # Calculate WCAG contrast ratio between two hex colors.
        require(params, "color1", "color2")
        rgb1 = _calc_to_rgb(params["color1"])
        rgb2 = _calc_to_rgb(params["color2"])
        ratio = contrast_ratio(rgb1, rgb2)
        return ok(contrast_ratio=round(ratio, 2))

    @api_method
    def palette_nearest_name(self, params: dict[str, Any]) -> dict[str, Any]:
        # Find nearest standard CSS color name for hex code.
        require(params, "color")
        rgb = _calc_to_rgb(params["color"])
        name = nearest_named_color(rgb)
        return ok(name=name, color=str(params["color"]))

    @api_method
    def palette_export_gpl(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export palette to GIMP Palette (.gpl) format file.
        require(params, "colors", "output_path")
        colors = list(params["colors"])
        palette_name = str(params.get("palette_name", "FOSS Palette"))
        out_path = Path(params["output_path"]).resolve()

        lines = ["GIMP Palette", f"Name: {palette_name}", "Columns: 8", "#"]
        for c in colors:
            hex_val = str(c).lstrip("#")
            if len(hex_val) == 6:
                r_val = int(hex_val[0:2], 16)
                g_val = int(hex_val[2:4], 16)
                b_val = int(hex_val[4:6], 16)
                c_name = nearest_named_color((r_val, g_val, b_val))
                lines.append(f"{r_val:3d} {g_val:3d} {b_val:3d}\t{c_name}")

        out_path.write_text("\n".join(lines), encoding="utf-8")
        return ok(output_path=str(out_path))
