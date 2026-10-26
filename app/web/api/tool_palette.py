import base64
import io
import json
from pathlib import Path
import struct
from typing import Any

from PIL import Image

from app.features.palette.ops import (
    ColorSwatch,
    contrast_ratio,
    extract_palette,
    generate_palette_strip,
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


def calc_rgb_dist_sq(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> float:
    # Compute squared Euclidean distance between two RGB triplets.
    term_r = float(rgb1[0] - rgb2[0]) ** 2
    term_g = float(rgb1[1] - rgb2[1]) ** 2
    term_b = float(rgb1[2] - rgb2[2]) ** 2
    return term_r + term_g + term_b


class PaletteApiMixin:
    @api_method
    def palette_load_image(self, params: dict[str, Any]) -> dict[str, Any]:
        # Load image and return thumbnail data URL and dimensions.
        require(params, "image_path")
        img_path = str(params["image_path"])
        with Image.open(img_path) as raw_img:
            img = raw_img.convert("RGB")
            width, height = img.size
            thumb = img.copy()
            thumb.thumbnail((800, 600))
            buf = io.BytesIO()
            thumb.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            data_url = f"data:image/png;base64,{b64}"
        return ok(data_url=data_url, width=width, height=height, image_path=img_path)

    @api_method
    def palette_extract(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract dominant color swatches from image using median-cut or k-means.
        require(params, "image_path")
        img_path = str(params["image_path"])
        num_colors = int(params.get("num_colors", params.get("n_colors", 8)))
        method = str(params.get("method", "median-cut"))
        if method == "median_cut":
            method = "median-cut"
        with Image.open(img_path) as raw_img:
            img = raw_img.convert("RGB")
            width, height = img.size
            swatches = extract_palette(img, n_colors=num_colors, method=method)
            thumb = img.copy()
            thumb.thumbnail((800, 600))
            buf = io.BytesIO()
            thumb.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            data_url = f"data:image/png;base64,{b64}"
        results = [
            {
                "hex": s.hex_code.upper(),
                "rgb": [s.rgb[0], s.rgb[1], s.rgb[2]],
                "percentage": round(s.percentage, 1),
                "name": s.name or nearest_named_color(s.rgb),
            }
            for s in swatches
        ]
        return ok(palette=results, count=len(results), image_path=img_path, data_url=data_url, width=width, height=height)

    @api_method
    def palette_sample_pixel(self, params: dict[str, Any]) -> dict[str, Any]:
        # Sample exact pixel RGB color at given image coordinates.
        require(params, "image_path", "x", "y")
        img_path = str(params["image_path"])
        x = int(params["x"])
        y = int(params["y"])
        with Image.open(img_path) as raw_img:
            img = raw_img.convert("RGB")
            swatch = sample_pixel_color(img, x, y)
        r_val, g_val, b_val = swatch.rgb
        hex_color = swatch.hex_code.upper()
        c_white = contrast_ratio((r_val, g_val, b_val), (255, 255, 255))
        c_black = contrast_ratio((r_val, g_val, b_val), (0, 0, 0))
        name = swatch.css_name
        return ok(rgb=[r_val, g_val, b_val], hex=hex_color, contrast_white=round(c_white, 2), contrast_black=round(c_black, 2), name=name)

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
            rgb = _calc_to_rgb(c)
            r_val, g_val, b_val = rgb
            c_name = nearest_named_color(rgb)
            lines.append(f"{r_val:3d} {g_val:3d} {b_val:3d}\t{c_name}")

        out_path.write_text("\n".join(lines), encoding="utf-8")
        return ok(output_path=str(out_path))

    @api_method
    def palette_export_strip(self, params: dict[str, Any]) -> dict[str, Any]:
        # Render and save palette swatches as strip image.
        require(params, "colors", "output_path")
        colors = list(params["colors"])
        out_path = Path(params["output_path"]).resolve()
        width = int(params.get("width", 400))
        height = int(params.get("height", 60))
        swatches = []
        for c in colors:
            rgb = _calc_to_rgb(c)
            hex_c = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
            swatches.append(ColorSwatch(hex_code=hex_c, rgb=rgb, percentage=0.0))
        img = generate_palette_strip(swatches, width=width, height=height)
        img.save(str(out_path))
        return ok(output_path=str(out_path))

    @api_method
    def palette_export_css(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export palette colors as CSS custom properties.
        require(params, "colors", "output_path")
        colors = list(params["colors"])
        out_path = Path(params["output_path"]).resolve()
        prefix = str(params.get("prefix", "color-"))
        lines = [":root {"]
        for idx, c in enumerate(colors, start=1):
            rgb = _calc_to_rgb(c)
            hex_c = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
            lines.append(f"  --{prefix}{idx}: {hex_c};")
        lines.append("}")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return ok(output_path=str(out_path))

    @api_method
    def palette_export_json(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export palette data to JSON format file.
        require(params, "colors", "output_path")
        colors = list(params["colors"])
        out_path = Path(params["output_path"]).resolve()
        records = []
        for c in colors:
            rgb = _calc_to_rgb(c)
            hex_c = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
            records.append({
                "hex": hex_c,
                "rgb": [rgb[0], rgb[1], rgb[2]],
                "name": nearest_named_color(rgb),
            })
        out_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return ok(output_path=str(out_path))

    @api_method
    def palette_export_aco(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export palette to Adobe Color Swatch binary format.
        require(params, "colors", "output_path")
        colors = list(params["colors"])
        out_path = Path(params["output_path"]).resolve()
        buf = bytearray()
        buf.extend(struct.pack(">HH", 1, len(colors)))
        for c in colors:
            rgb = _calc_to_rgb(c)
            buf.extend(struct.pack(">HHHHH", 0, rgb[0] * 257, rgb[1] * 257, rgb[2] * 257, 0))
        out_path.write_bytes(bytes(buf))
        return ok(output_path=str(out_path))

    @api_method
    def palette_aggregate(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract and aggregate dominant colors across multiple images with deduplication.
        require(params, "image_paths")
        paths = [str(p) for p in params["image_paths"]]
        num_colors = int(params.get("num_colors", 8))
        method = str(params.get("method", "median-cut"))
        if method == "median_cut":
            method = "median-cut"
        dist_threshold_sq = float(params.get("threshold", 25.0)) ** 2

        all_swatches: list[ColorSwatch] = []
        for p in paths:
            if not Path(p).exists():
                continue
            with Image.open(p) as raw_img:
                img = raw_img.convert("RGB")
                all_swatches.extend(extract_palette(img, n_colors=num_colors, method=method))

        deduped: list[dict[str, Any]] = []
        for s in all_swatches:
            r1, g1, b1 = s.rgb
            found = False
            for d in deduped:
                r2, g2, b2 = d["rgb"]
                dist_sq = calc_rgb_dist_sq((r1, g1, b1), (r2, g2, b2))
                if dist_sq <= dist_threshold_sq:
                    d["count"] += 1
                    found = True
                    break
            if not found:
                deduped.append({
                    "hex": s.hex_code.upper(),
                    "rgb": [r1, g1, b1],
                    "name": s.name or nearest_named_color(s.rgb),
                    "count": 1,
                })

        deduped.sort(key=lambda x: int(x["count"]), reverse=True)
        top = deduped[:num_colors]
        total_counts = sum(item["count"] for item in top) or 1
        for item in top:
            item["percentage"] = round((item["count"] / total_counts) * 100.0, 1)
        return ok(palette=top, count=len(top))
