import base64
import io
from pathlib import Path
from typing import Any

from PIL import Image

from app.features.image.ops import (
    ASCII_CHARSET_PRESETS,
    ASPECT_RATIO_PRESETS,
    BACKGROUND_REMOVAL_MODELS,
    FILTER_PRESETS,
    SINGLE_IMAGE_EXPORT_FORMATS,
    SUPPORTED_FORMATS,
    _normalize_model_name,
    add_border,
    adjust_image,
    apply_filter_preset,
    aspect_ratio_crop_box,
    auto_enhance,
    batch_process,
    blur_region,
    circle_crop_image,
    crop_image,
    extract_gif_frames,
    flip_image,
    frames_to_gif,
    gif_to_video,
    load_image,
    pixelate_region,
    prefetch_background_removal_models,
    remove_background,
    resize_image,
    rotate_image,
    save_ascii_art,
    save_image,
)
from app.features.ocr.ops import ocr_image
from app.web.api.result import api_method, ok, require


def _calc_load_img(file_path: str) -> Image.Image:
    # Open image and force pixel buffer loading to release file locks.
    img = load_image(file_path)
    img.load()
    return img.copy()


def calc_color_tuple(color_val: Any) -> tuple[int, int, int]:
    # Parse color value to 3-tuple RGB channels.
    if isinstance(color_val, (list, tuple)) and len(color_val) >= 3:
        return (int(color_val[0]), int(color_val[1]), int(color_val[2]))
    val = str(color_val).strip().lstrip("#")
    if len(val) == 3:
        val = "".join(c * 2 for c in val)
    if len(val) == 6:
        return (int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16))
    return (255, 255, 255)


class ImagesApiMixin:
    @api_method
    def images_presets(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return presets for aspect ratios, background models, filters, formats, charsets.
        norm = _normalize_model_name("u2net")
        return ok(
            aspect_ratios=ASPECT_RATIO_PRESETS,
            models=BACKGROUND_REMOVAL_MODELS,
            filters=list(FILTER_PRESETS.keys()),
            formats=SINGLE_IMAGE_EXPORT_FORMATS,
            supported=SUPPORTED_FORMATS,
            charsets=ASCII_CHARSET_PRESETS,
            default_model=norm,
        )

    @api_method
    def images_load_data(self, params: dict[str, Any]) -> dict[str, Any]:
        # Load image file and return base64 data URL with dimensions.
        require(params, "file_path")
        file_path = str(params["file_path"])
        img = _calc_load_img(file_path)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return ok(data_url=f"data:image/png;base64,{b64}", width=img.width, height=img.height, file_path=file_path)

    @api_method
    def image_load_data(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for loading image data.
        return self.images_load_data(params)

    @api_method
    def images_load_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        # Load downscaled image preview data URL.
        require(params, "file_path")
        file_path = str(params["file_path"])
        img = _calc_load_img(file_path)
        max_size = int(params.get("max_size", 1200))
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return ok(data_url=f"data:image/jpeg;base64,{b64}", width=img.width, height=img.height)

    @api_method
    def image_load_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for loading image preview.
        return self.images_load_preview(params)

    @api_method
    def images_rotate(self, params: dict[str, Any]) -> dict[str, Any]:
        # Rotate image clockwise by specified degrees.
        require(params, "file_path")
        file_path = str(params["file_path"])
        degrees = int(params.get("degrees", 90))
        out_p = str(params.get("output_path", file_path))
        img = _calc_load_img(file_path)
        rot = rotate_image(img, degrees)
        save_image(rot, out_p)
        return ok(output_path=out_p, width=rot.width, height=rot.height)

    @api_method
    def image_rotate(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for rotating image.
        return self.images_rotate(params)

    @api_method
    def images_flip(self, params: dict[str, Any]) -> dict[str, Any]:
        # Flip image horizontally or vertically.
        require(params, "file_path")
        file_path = str(params["file_path"])
        direction = str(params.get("direction", "horizontal"))
        out_p = str(params.get("output_path", file_path))
        img = _calc_load_img(file_path)
        flipped = flip_image(img, direction)
        save_image(flipped, out_p)
        return ok(output_path=out_p)

    @api_method
    def image_flip(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for flipping image.
        return self.images_flip(params)

    @api_method
    def images_resize(self, params: dict[str, Any]) -> dict[str, Any]:
        # Resize image dimensions with optional aspect ratio preservation.
        require(params, "file_path", "width", "height")
        file_path = str(params["file_path"])
        w = int(params["width"])
        h = int(params["height"])
        keep_aspect = bool(params.get("keep_aspect", True))
        out_p = str(params.get("output_path", file_path))
        img = _calc_load_img(file_path)
        resized = resize_image(img, w, h, keep_aspect=keep_aspect)
        save_image(resized, out_p)
        return ok(output_path=out_p, width=resized.width, height=resized.height)

    @api_method
    def image_resize(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for resizing image.
        return self.images_resize(params)

    @api_method
    def images_crop(self, params: dict[str, Any]) -> dict[str, Any]:
        # Crop rectangular area from image.
        require(params, "file_path", "x", "y", "width", "height")
        file_path = str(params["file_path"])
        box = (int(params["x"]), int(params["y"]), int(params["x"]) + int(params["width"]), int(params["y"]) + int(params["height"]))
        out_p = str(params.get("output_path", file_path))
        img = _calc_load_img(file_path)
        cropped = crop_image(img, box)
        save_image(cropped, out_p)
        return ok(output_path=out_p, width=cropped.width, height=cropped.height)

    @api_method
    def image_crop(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for cropping image.
        return self.images_crop(params)

    @api_method
    def images_circle_crop(self, params: dict[str, Any]) -> dict[str, Any]:
        # Crop circular avatar from image.
        require(params, "file_path")
        file_path = str(params["file_path"])
        out_p = str(params.get("output_path", file_path))
        img = _calc_load_img(file_path)
        cropped = circle_crop_image(img)
        save_image(cropped, out_p, format="PNG")
        return ok(output_path=out_p)

    @api_method
    def image_circle_crop(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for circular cropping.
        return self.images_circle_crop(params)

    @api_method
    def images_adjust(self, params: dict[str, Any]) -> dict[str, Any]:
        # Adjust image brightness, contrast, sharpness, and color saturation.
        require(params, "file_path")
        file_path = str(params["file_path"])
        b = float(params.get("brightness", 1.0))
        c = float(params.get("contrast", 1.0))
        s = float(params.get("sharpness", 1.0))
        sat = float(params.get("saturation", params.get("color", 1.0)))
        b_val = b * 100 if b < 10 else b
        c_val = c * 100 if c < 10 else c
        s_val = s * 100 if s < 10 else s
        sat_val = sat * 100 if sat < 10 else sat
        out_p = str(params.get("output_path", file_path))
        img = _calc_load_img(file_path)
        adj = adjust_image(img, brightness=b_val, contrast=c_val, saturation=sat_val, sharpness=s_val)
        save_image(adj, out_p)
        return ok(output_path=out_p)

    @api_method
    def image_adjust(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for adjusting image.
        return self.images_adjust(params)

    @api_method
    def images_auto_enhance(self, params: dict[str, Any]) -> dict[str, Any]:
        # Automatically enhance image color balance and contrast.
        require(params, "file_path")
        file_path = str(params["file_path"])
        out_p = str(params.get("output_path", file_path))
        img = _calc_load_img(file_path)
        enh = auto_enhance(img)
        save_image(enh, out_p)
        return ok(output_path=out_p)

    @api_method
    def image_auto_enhance(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for auto enhancing image.
        return self.images_auto_enhance(params)

    @api_method
    def images_apply_filter(self, params: dict[str, Any]) -> dict[str, Any]:
        # Apply artistic or photographic filter preset to image.
        require(params, "file_path", "filter_name")
        file_path = str(params["file_path"])
        flt = str(params["filter_name"])
        out_p = str(params.get("output_path", file_path))
        img = _calc_load_img(file_path)
        res = apply_filter_preset(img, flt)
        save_image(res, out_p)
        return ok(output_path=out_p)

    @api_method
    def image_apply_filter_preset(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for applying filter preset.
        return self.images_apply_filter(params)

    @api_method
    def images_remove_background(self, params: dict[str, Any]) -> dict[str, Any]:
        # Remove background using machine learning segmentation models.
        require(params, "file_path")
        file_path = str(params["file_path"])
        model = str(params.get("model", "u2net"))
        out_p = str(params.get("output_path", file_path))
        img = _calc_load_img(file_path)
        nobg = remove_background(img, model_name=model)
        save_image(nobg, out_p, format="PNG")
        return ok(output_path=out_p)

    @api_method
    def image_remove_background(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for background removal.
        return self.images_remove_background(params)

    @api_method
    def images_prefetch_models(self, params: dict[str, Any]) -> dict[str, Any]:
        # Prefetch background removal model weights to cache.
        models = list(params.get("models", ["u2netp"]))
        prefetch_background_removal_models(models)
        return ok(prefetched=models)

    @api_method
    def images_add_border(self, params: dict[str, Any]) -> dict[str, Any]:
        # Add decorative border frame around image.
        require(params, "file_path")
        file_path = str(params["file_path"])
        width = int(params.get("border_width", params.get("border_size", 10)))
        color_tuple = calc_color_tuple(params.get("color", "#000000"))
        polaroid = bool(params.get("polaroid", False))
        out_p = str(params.get("output_path", file_path))
        img = _calc_load_img(file_path)
        bordered = add_border(img, border_size=width, color=color_tuple, polaroid=polaroid)
        save_image(bordered, out_p)
        return ok(output_path=out_p)

    @api_method
    def image_add_border(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for adding image border.
        return self.images_add_border(params)

    @api_method
    def images_blur_region(self, params: dict[str, Any]) -> dict[str, Any]:
        # Apply Gaussian blur to specified image bounding box.
        require(params, "file_path", "box")
        file_path = str(params["file_path"])
        box = tuple(int(v) for v in params["box"])
        radius = int(params.get("radius", 15))
        out_p = str(params.get("output_path", file_path))
        img = _calc_load_img(file_path)
        res = blur_region(img, box, radius=radius)
        save_image(res, out_p)
        return ok(output_path=out_p)

    @api_method
    def image_blur_region(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for blurring region.
        return self.images_blur_region(params)

    @api_method
    def images_pixelate_region(self, params: dict[str, Any]) -> dict[str, Any]:
        # Censor image bounding box with pixelation mosaic.
        require(params, "file_path", "box")
        file_path = str(params["file_path"])
        box = tuple(int(v) for v in params["box"])
        pixel_size = int(params.get("pixel_size", 10))
        out_p = str(params.get("output_path", file_path))
        img = _calc_load_img(file_path)
        res = pixelate_region(img, box, pixel_size=pixel_size)
        save_image(res, out_p)
        return ok(output_path=out_p)

    @api_method
    def image_pixelate_region(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for pixelating region.
        return self.images_pixelate_region(params)

    @api_method
    def images_aspect_box(self, params: dict[str, Any]) -> dict[str, Any]:
        # Calculate aspect ratio centered crop bounding box.
        require(params, "width", "height", "aspect_ratio")
        w = int(params["width"])
        h = int(params["height"])
        ratio_str = str(params["aspect_ratio"]).replace("/", ":")
        if ":" in ratio_str:
            parts = ratio_str.split(":")
            rw = float(parts[0])
            rh = float(parts[1])
        else:
            rw = float(ratio_str)
            rh = 1.0
        box = aspect_ratio_crop_box(w, h, rw, rh)
        return ok(box=list(box))

    @api_method
    def images_to_ascii(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert image to ASCII text art.
        require(params, "file_path")
        file_path = str(params["file_path"])
        img = _calc_load_img(file_path)
        cols = int(params.get("columns", params.get("width", 80)))
        charset = str(params.get("charset", "standard"))
        from app.features.image.ops import image_to_ascii
        art = image_to_ascii(img, width=cols, charset=charset)
        out_p = params.get("output_path")
        if out_p:
            save_ascii_art(img, str(out_p), width=cols, charset=charset)
        return ok(ascii=art, output_path=out_p)

    @api_method
    def images_gif_ops(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract frames from GIF or assemble GIF from frame paths.
        action = str(params.get("action", "extract")).lower()
        if action == "extract":
            require(params, "file_path", "output_dir")
            frames = extract_gif_frames(str(params["file_path"]), str(params["output_dir"]))
            return ok(frames=frames)
        elif action == "create":
            require(params, "frame_paths", "output_path")
            fps = float(params.get("fps", 10.0))
            loop = int(params.get("loop", 0))
            out_p = frames_to_gif(list(params["frame_paths"]), str(params["output_path"]), fps=fps, loop=loop)
            return ok(output_path=out_p)
        elif action == "video":
            require(params, "file_path", "output_path")
            vid_p = gif_to_video(str(params["file_path"]), str(params["output_path"]))
            return ok(output_path=vid_p)
        return ok()

    @api_method
    def images_batch_process(self, params: dict[str, Any]) -> dict[str, Any]:
        # Batch execute pipeline operations across multiple images.
        require(params, "file_paths")
        paths = [str(p) for p in params["file_paths"]]
        out_dir = str(params.get("output_dir", "."))
        target_fmt = params.get("target_format")
        quality = int(params.get("quality", 85))
        resize_to = None
        if "width" in params and "height" in params:
            resize_to = (int(params["width"]), int(params["height"]))
        keep_aspect = bool(params.get("keep_aspect", True))
        rm_bg = bool(params.get("remove_background", False))
        bg_model = str(params.get("bg_model", "u2net"))
        results = batch_process(
            paths,
            out_dir,
            target_format=str(target_fmt) if target_fmt else None,
            quality=quality,
            resize_to=resize_to,
            keep_aspect=keep_aspect,
            remove_background_enabled=rm_bg,
            bg_model=bg_model,
        )
        return ok(results=results, count=len(results))

    @api_method
    def images_ocr(self, params: dict[str, Any]) -> dict[str, Any]:
        # Recognize text inside image using OCR.
        require(params, "file_path")
        text = ocr_image(str(params["file_path"]), language=str(params.get("language", "eng")))
        return ok(text=text)
