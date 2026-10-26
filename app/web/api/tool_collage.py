import base64
import io
from pathlib import Path
from typing import Any

from PIL import Image

from app.features.collage.ops import (
    CollageConfig,
    LAYOUT_PRESETS,
    make_collage,
)
from app.web.api.result import api_method, ok, require


class CollageApiMixin:
    @api_method
    def collage_presets(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return layout preset names and configurations for collage grids.
        return ok(presets=dict(LAYOUT_PRESETS))

    @api_method
    def collage_create(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate composite image collage from multiple source pictures.
        require(params, "image_paths", "output_path")
        paths = list(params["image_paths"])
        out_path = str(params["output_path"])
        preset_name = params.get("preset")

        cols = int(params.get("columns", params.get("cols", 3)))
        cfg = CollageConfig(
            cols=cols,
            thumb_width=int(params.get("cell_width", 400)),
            thumb_height=int(params.get("cell_height", 400)),
            padding=int(params.get("padding", 12)),
            fit_mode=str(params.get("fit_mode", "cover")),
        )

        res_img = make_collage(paths, cfg)
        res_img.save(out_path)
        return ok(output_path=out_path, width=res_img.width, height=res_img.height)

    @api_method
    def collage_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate low-resolution collage preview data URL for interactive adjustment.
        require(params, "image_paths")
        paths = list(params["image_paths"])
        cols = int(params.get("columns", params.get("cols", 3)))
        cfg = CollageConfig(
            cols=cols,
            thumb_width=int(params.get("cell_width", 200)),
            thumb_height=int(params.get("cell_height", 200)),
            padding=int(params.get("padding", 6)),
            fit_mode=str(params.get("fit_mode", "cover")),
        )
        res_img = make_collage(paths, cfg)
        res_img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        res_img.save(buf, format="JPEG", quality=80)
        data_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return ok(data_url=f"data:image/jpeg;base64,{data_b64}", width=res_img.width, height=res_img.height)
