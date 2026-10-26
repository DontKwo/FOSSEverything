import base64
import io
import os
from pathlib import Path
from typing import Any

from PIL import Image

from app.features.collage.ops import (
    CollageConfig,
    LAYOUT_PRESETS,
    make_collage,
)
from app.web.api.result import api_method, ok, require


def _parse_rgb(val: Any) -> tuple[int, int, int]:
    # Parse color string (#rrggbb or rgb) into RGB integer tuple.
    if isinstance(val, (list, tuple)) and len(val) >= 3:
        return (int(val[0]), int(val[1]), int(val[2]))
    if isinstance(val, str) and val.startswith("#") and len(val) >= 7:
        try:
            return (int(val[1:3], 16), int(val[3:5], 16), int(val[5:7], 16))
        except ValueError:
            pass
    return (240, 240, 240)


class CollageApiMixin:
    @api_method
    def collage_presets(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return layout preset names and configurations for collage grids.
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
        bg_col = _parse_rgb(params.get("bg_color", (240, 240, 240)))
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
        res_img.save(out_path)
        return ok(output_path=out_path, width=res_img.width, height=res_img.height)

    @api_method
    def collage_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate low-resolution collage preview data URL for interactive adjustment.
        require(params, "image_paths")
        paths = list(params["image_paths"])
        cols = int(params.get("columns", params.get("cols", 2)))
        bg_col = _parse_rgb(params.get("bg_color", (240, 240, 240)))
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
        res_img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        res_img.save(buf, format="JPEG", quality=80)
        data_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return ok(data_url=f"data:image/jpeg;base64,{data_b64}", width=res_img.width, height=res_img.height)
