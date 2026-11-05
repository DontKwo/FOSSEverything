import base64
import io
import os
from typing import Any

from PIL import Image

from app.features.collage.ops import (
    CollageConfig,
    CollageLayer,
    LAYOUT_PRESETS,
    export_collage_layers,
    make_collage,
    render_freeform_composite,
)
from app.features.image.ops import load_image
from app.web.api.result import api_method, ok, require


def _parse_rgba(val: Any, default_alpha: int = 255) -> tuple[int, int, int, int]:
    # Parse color representation into RGBA integer tuple.
    if isinstance(val, (list, tuple)):
        if len(val) == 4:
            return (int(val[0]), int(val[1]), int(val[2]), int(val[3]))
        if len(val) >= 3:
            return (int(val[0]), int(val[1]), int(val[2]), default_alpha)
    if isinstance(val, str) and val.startswith("#") and len(val) >= 7:
        try:
            r = int(val[1:3], 16)
            g = int(val[3:5], 16)
            b = int(val[5:7], 16)
            a = int(val[7:9], 16) if len(val) >= 9 else default_alpha
            return (r, g, b, a)
        except ValueError:
            return (240, 240, 240, default_alpha)
    return (240, 240, 240, default_alpha)


def _calc_save_flat(image_obj: Image.Image, out_path: str) -> None:
    # Save a flattened collage by extension, compositing transparency onto white for JPEG.
    ext = os.path.splitext(out_path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        backdrop = Image.new("RGBA", image_obj.size, (255, 255, 255, 255))
        backdrop.alpha_composite(image_obj.convert("RGBA"))
        backdrop.convert("RGB").save(out_path, quality=92)
    elif ext == ".webp":
        image_obj.save(out_path, quality=90)
    else:
        image_obj.save(out_path, format="PNG")


class CollageApiMixin:
    @api_method
    def collage_presets(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return layout preset configurations for grid collages.
        return ok(presets=dict(LAYOUT_PRESETS))

    @api_method
    def collage_create(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate composite image collage from multiple source pictures.
        require(params, "image_paths")
        paths = list(params["image_paths"])
        out_path = str(params.get("output_path", "")).strip()
        if not out_path and paths:
            base_dir = os.path.dirname(paths[0])
            out_path = os.path.join(base_dir, "collage.png")

        cols = int(params.get("columns", params.get("cols", 2)))
        transparent = bool(params.get("transparent_bg", False))
        if transparent:
            bg_col: tuple = (0, 0, 0, 0)
        else:
            rgba = _parse_rgba(params.get("bg_color", (240, 240, 240, 255)))
            bg_col = (rgba[0], rgba[1], rgba[2])

        cfg = CollageConfig(
            cols=cols,
            thumb_width=int(params.get("cell_width", 400)),
            thumb_height=int(params.get("cell_height", 400)),
            padding=int(params.get("padding", 12)),
            bg_color=bg_col,
            fit_mode=str(params.get("fit_mode", "cover")),
            corner_radius=int(params.get("corner_radius", 0)),
        )

        captions = params.get("captions")
        if captions is True or params.get("add_captions"):
            captions = [os.path.basename(p) for p in paths]
        elif not isinstance(captions, list):
            captions = None

        wm_text = params.get("watermark_text")
        layout_name = params.get("layout_name") or params.get("preset")

        res_img = make_collage(
            paths,
            config=cfg,
            captions=captions,
            layout_name=str(layout_name) if layout_name else None,
            watermark_text=str(wm_text) if wm_text else None,
        )
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        _calc_save_flat(res_img, out_path)
        return ok(output_path=out_path, width=res_img.width, height=res_img.height)

    @api_method
    def collage_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate low-resolution collage preview data URL.
        require(params, "image_paths")
        paths = list(params["image_paths"])
        cols = int(params.get("columns", params.get("cols", 2)))
        transparent = bool(params.get("transparent_bg", False))
        if transparent:
            bg_col: tuple = (0, 0, 0, 0)
        else:
            rgba = _parse_rgba(params.get("bg_color", (240, 240, 240, 255)))
            bg_col = (rgba[0], rgba[1], rgba[2])

        cfg = CollageConfig(
            cols=cols,
            thumb_width=int(params.get("cell_width", 200)),
            thumb_height=int(params.get("cell_height", 200)),
            padding=int(params.get("padding", 6)),
            bg_color=bg_col,
            fit_mode=str(params.get("fit_mode", "cover")),
            corner_radius=int(params.get("corner_radius", 0)),
        )
        captions = params.get("captions")
        if captions is True or params.get("add_captions"):
            captions = [os.path.basename(p) for p in paths]
        elif not isinstance(captions, list):
            captions = None

        wm_text = params.get("watermark_text")
        layout_name = params.get("layout_name") or params.get("preset")

        res_img = make_collage(
            paths,
            config=cfg,
            captions=captions,
            layout_name=str(layout_name) if layout_name else None,
            watermark_text=str(wm_text) if wm_text else None,
        )
        buf = io.BytesIO()
        res_img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return ok(data_url=f"data:image/png;base64,{b64}", width=res_img.width, height=res_img.height)

    @api_method
    def collage_load_layer_asset(self, params: dict[str, Any]) -> dict[str, Any]:
        # Load image asset preserving RGBA transparency and return dimensions and data URL.
        require(params, "file_path")
        file_path = str(params["file_path"])
        img = load_image(file_path).convert("RGBA")

        # Create web-ready preview scaled to max 800px dimension
        max_dim = 800
        preview_img = img
        if max(img.width, img.height) > max_dim:
            scale = max_dim / max(img.width, img.height)
            preview_img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        preview_img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return ok(
            width=img.width,
            height=img.height,
            data_url=f"data:image/png;base64,{b64}",
            file_path=file_path,
        )

    @api_method
    def collage_export_freeform(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export freeform collage in flattened or layered format.
        require(params, "layers", "output_path", "canvas_width", "canvas_height")
        canvas_w = int(params["canvas_width"])
        canvas_h = int(params["canvas_height"])
        out_p = str(params["output_path"])
        mode = str(params.get("mode", "flattened")).lower()

        transparent = bool(params.get("transparent_bg", False))
        if transparent:
            bg_rgba = (0, 0, 0, 0)
        else:
            bg_rgba = _parse_rgba(params.get("bg_color", (240, 240, 240, 255)))

        layers: list[CollageLayer] = []
        for idx, layer_item in enumerate(params.get("layers", [])):
            layers.append(CollageLayer(
                layer_id=str(layer_item.get("layer_id", f"l_{idx}")),
                name=str(layer_item.get("name", f"Layer {idx + 1}")),
                source_path=str(layer_item.get("source_path", "")),
                x=float(layer_item.get("x", 0.0)),
                y=float(layer_item.get("y", 0.0)),
                width=float(layer_item.get("width", 100.0)),
                height=float(layer_item.get("height", 100.0)),
                rotation_deg=float(layer_item.get("rotation_deg", 0.0)),
                opacity=float(layer_item.get("opacity", 1.0)),
                visible=bool(layer_item.get("visible", True)),
                locked=bool(layer_item.get("locked", False)),
            ))

        if mode == "layered":
            export_fmt = str(params.get("format", "psd")).lower()
            res = export_collage_layers(canvas_w, canvas_h, layers, out_p, export_format=export_fmt, bg_rgba=bg_rgba)
            return ok(**res)

        # Flattened mode
        composite = render_freeform_composite(canvas_w, canvas_h, layers, bg_rgba=bg_rgba)
        os.makedirs(os.path.dirname(os.path.abspath(out_p)), exist_ok=True)
        _calc_save_flat(composite, out_p)
        return ok(output_path=out_p, width=composite.width, height=composite.height)
