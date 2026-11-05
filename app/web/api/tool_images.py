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
    delete_rembg_model,
    download_rembg_model,
    extract_gif_frames,
    flip_image,
    frames_to_gif,
    gif_to_video,
    list_rembg_models_status,
    load_image,
    pixelate_region,
    prefetch_background_removal_models,
    remove_background,
    replace_background_color,
    resize_image,
    rotate_image,
    save_ascii_art,
    save_image,
)
from app.features.ocr.ops import ocr_image
from app.web.api.result import api_method, ok, require


def _calc_load_img(file_path: str) -> Image.Image:
    # Open image and force pixel buffer loading to release file locks.
    source_img = load_image(file_path)
    source_img.load()
    return source_img.copy()


def _calc_to_data_url(image_obj: Image.Image, format_name: str = "PNG") -> str:
    # Convert PIL Image object to base64 data URL.
    buffer = io.BytesIO()
    image_obj.save(buffer, format=format_name)
    base64_data = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/{format_name.lower()};base64,{base64_data}"


def _calc_save(image_obj: Image.Image, out_path: str, params: dict[str, Any], default_format: str = "") -> None:
    # Save image in the format given by the output extension with the requested quality.
    ext = Path(out_path).suffix.lstrip(".")
    save_image(image_obj, out_path, format=default_format or ext or "PNG", quality=int(params.get("quality", 85)))


def calc_color_tuple(color_val: Any) -> tuple[int, int, int]:
    # Parse color value to 3-tuple RGB channels.
    if isinstance(color_val, (list, tuple)) and len(color_val) >= 3:
        return (int(color_val[0]), int(color_val[1]), int(color_val[2]))
    clean_hex = str(color_val).strip().lstrip("#")
    if len(clean_hex) == 3:
        clean_hex = "".join(char_code * 2 for char_code in clean_hex)
    if len(clean_hex) == 6:
        return (int(clean_hex[0:2], 16), int(clean_hex[2:4], 16), int(clean_hex[4:6], 16))
    return (255, 255, 255)


class ImagesApiMixin:
    @api_method
    def images_presets(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return presets for aspect ratios, background models, filters, formats, charsets.
        norm = _normalize_model_name("u2net")
        return ok(
            aspect_ratios=ASPECT_RATIO_PRESETS,
            models=BACKGROUND_REMOVAL_MODELS,
            filters=list(FILTER_PRESETS),
            formats=SINGLE_IMAGE_EXPORT_FORMATS,
            supported=SUPPORTED_FORMATS,
            charsets=ASCII_CHARSET_PRESETS,
            default_model=norm,
        )

    @api_method
    def images_models_status(self, params: dict[str, Any]) -> dict[str, Any]:
        # Scan and return download status of all background removal models.
        status_info = list_rembg_models_status()
        return ok(**status_info)

    @api_method
    def images_download_model(self, params: dict[str, Any]) -> dict[str, Any]:
        # Download specified background removal model to unified models directory.
        require(params, "model")
        target_model = str(params["model"])
        status_info = download_rembg_model(target_model)
        return ok(**status_info)

    @api_method
    def images_delete_model(self, params: dict[str, Any]) -> dict[str, Any]:
        # Delete specified background removal model from unified models directory.
        require(params, "model")
        target_model = str(params["model"])
        status_info = delete_rembg_model(target_model)
        return ok(**status_info)

    @api_method
    def images_save_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        # Decode a preview data URL and save it in the format given by the output extension.
        require(params, "data_url", "output_path")
        encoded = str(params["data_url"]).split(",", 1)[-1]
        preview_img = Image.open(io.BytesIO(base64.b64decode(encoded)))
        preview_img.load()
        out_p = str(params["output_path"])
        Path(out_p).parent.mkdir(parents=True, exist_ok=True)
        _calc_save(preview_img, out_p, params)
        return ok(output_path=out_p, width=preview_img.width, height=preview_img.height)

    @api_method
    def images_load_data(self, params: dict[str, Any]) -> dict[str, Any]:
        # Load image file and return base64 data URL with dimensions.
        require(params, "file_path")
        file_path = str(params["file_path"])
        source_img = _calc_load_img(file_path)
        data_url = _calc_to_data_url(source_img, "PNG")
        return ok(data_url=data_url, width=source_img.width, height=source_img.height, file_path=file_path)

    @api_method
    def image_load_data(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for loading image data.
        return self.images_load_data(params)

    @api_method
    def images_load_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        # Load downscaled image preview data URL.
        require(params, "file_path")
        file_path = str(params["file_path"])
        source_img = _calc_load_img(file_path)
        max_size = int(params.get("max_size", 1200))
        source_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        data_url = _calc_to_data_url(source_img, "JPEG")
        return ok(data_url=data_url, width=source_img.width, height=source_img.height)

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
        overwrite = bool(params.get("overwrite", False))
        out_p = str(params["output_path"]) if params.get("output_path") else (file_path if overwrite else "")
        source_img = _calc_load_img(file_path)
        rotated_img = rotate_image(source_img, degrees)
        if out_p:
            _calc_save(rotated_img, out_p, params)
        data_url = _calc_to_data_url(rotated_img, "PNG")
        return ok(output_path=out_p, data_url=data_url, width=rotated_img.width, height=rotated_img.height)

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
        overwrite = bool(params.get("overwrite", False))
        out_p = str(params["output_path"]) if params.get("output_path") else (file_path if overwrite else "")
        source_img = _calc_load_img(file_path)
        flipped_img = flip_image(source_img, horizontal=(direction.lower() != "vertical"))
        if out_p:
            _calc_save(flipped_img, out_p, params)
        data_url = _calc_to_data_url(flipped_img, "PNG")
        return ok(output_path=out_p, data_url=data_url, width=flipped_img.width, height=flipped_img.height)

    @api_method
    def image_flip(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for flipping image.
        return self.images_flip(params)

    @api_method
    def images_resize(self, params: dict[str, Any]) -> dict[str, Any]:
        # Resize image dimensions with optional aspect ratio preservation.
        require(params, "file_path", "width", "height")
        file_path = str(params["file_path"])
        req_width = int(params["width"])
        req_height = int(params["height"])
        keep_aspect = bool(params.get("keep_aspect", True))
        overwrite = bool(params.get("overwrite", False))
        out_p = str(params["output_path"]) if params.get("output_path") else (file_path if overwrite else "")
        source_img = _calc_load_img(file_path)
        resized_img = resize_image(source_img, req_width, req_height, keep_aspect=keep_aspect)
        if out_p:
            _calc_save(resized_img, out_p, params)
        data_url = _calc_to_data_url(resized_img, "PNG")
        return ok(output_path=out_p, data_url=data_url, width=resized_img.width, height=resized_img.height)

    @api_method
    def image_resize(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for resizing image.
        return self.images_resize(params)

    @api_method
    def images_crop(self, params: dict[str, Any]) -> dict[str, Any]:
        # Crop rectangular area from image.
        require(params, "file_path", "x", "y", "width", "height")
        file_path = str(params["file_path"])
        coord_x = int(params["x"])
        coord_y = int(params["y"])
        box = (coord_x, coord_y, coord_x + int(params["width"]), coord_y + int(params["height"]))
        overwrite = bool(params.get("overwrite", False))
        out_p = str(params["output_path"]) if params.get("output_path") else (file_path if overwrite else "")
        source_img = _calc_load_img(file_path)
        cropped_img = crop_image(source_img, box)
        if out_p:
            _calc_save(cropped_img, out_p, params)
        data_url = _calc_to_data_url(cropped_img, "PNG")
        return ok(output_path=out_p, data_url=data_url, width=cropped_img.width, height=cropped_img.height)

    @api_method
    def image_crop(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for cropping image.
        return self.images_crop(params)

    @api_method
    def images_circle_crop(self, params: dict[str, Any]) -> dict[str, Any]:
        # Crop circular avatar from image.
        require(params, "file_path")
        file_path = str(params["file_path"])
        overwrite = bool(params.get("overwrite", False))
        out_p = str(params["output_path"]) if params.get("output_path") else (file_path if overwrite else "")
        source_img = _calc_load_img(file_path)
        cropped_img = circle_crop_image(source_img)
        if out_p:
            save_image(cropped_img, out_p, format="PNG")
        data_url = _calc_to_data_url(cropped_img, "PNG")
        return ok(output_path=out_p, data_url=data_url, width=cropped_img.width, height=cropped_img.height)

    @api_method
    def image_circle_crop(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for circular cropping.
        return self.images_circle_crop(params)

    @api_method
    def images_adjust(self, params: dict[str, Any]) -> dict[str, Any]:
        # Adjust image brightness, contrast, sharpness, and color saturation.
        require(params, "file_path")
        file_path = str(params["file_path"])
        brightness_val = float(params.get("brightness", 1.0))
        contrast_val = float(params.get("contrast", 1.0))
        sharpness_val = float(params.get("sharpness", 1.0))
        sat_val = float(params.get("saturation", params.get("color", 1.0)))
        b_scaled = brightness_val * 100 if brightness_val < 10 else brightness_val
        c_scaled = contrast_val * 100 if contrast_val < 10 else contrast_val
        s_scaled = sharpness_val * 100 if sharpness_val < 10 else sharpness_val
        sat_scaled = sat_val * 100 if sat_val < 10 else sat_val
        overwrite = bool(params.get("overwrite", False))
        out_p = str(params["output_path"]) if params.get("output_path") else (file_path if overwrite else "")
        source_img = _calc_load_img(file_path)
        adjusted_img = adjust_image(
            source_img,
            brightness=b_scaled,
            contrast=c_scaled,
            saturation=sat_scaled,
            sharpness=s_scaled,
        )
        if out_p:
            _calc_save(adjusted_img, out_p, params)
        data_url = _calc_to_data_url(adjusted_img, "PNG")
        return ok(output_path=out_p, data_url=data_url, width=adjusted_img.width, height=adjusted_img.height)

    @api_method
    def image_adjust(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for adjusting image.
        return self.images_adjust(params)

    @api_method
    def images_auto_enhance(self, params: dict[str, Any]) -> dict[str, Any]:
        # Automatically enhance image color balance and contrast.
        require(params, "file_path")
        file_path = str(params["file_path"])
        overwrite = bool(params.get("overwrite", False))
        out_p = str(params["output_path"]) if params.get("output_path") else (file_path if overwrite else "")
        source_img = _calc_load_img(file_path)
        enhanced_img = auto_enhance(source_img)
        if out_p:
            _calc_save(enhanced_img, out_p, params)
        data_url = _calc_to_data_url(enhanced_img, "PNG")
        return ok(output_path=out_p, data_url=data_url, width=enhanced_img.width, height=enhanced_img.height)

    @api_method
    def image_auto_enhance(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for auto enhancing image.
        return self.images_auto_enhance(params)

    @api_method
    def images_apply_filter(self, params: dict[str, Any]) -> dict[str, Any]:
        # Apply artistic or photographic filter preset to image.
        require(params, "file_path", "filter_name")
        file_path = str(params["file_path"])
        filter_name = str(params["filter_name"])
        overwrite = bool(params.get("overwrite", False))
        out_p = str(params["output_path"]) if params.get("output_path") else (file_path if overwrite else "")
        source_img = _calc_load_img(file_path)
        filtered_img = apply_filter_preset(source_img, filter_name)
        if out_p:
            _calc_save(filtered_img, out_p, params)
        data_url = _calc_to_data_url(filtered_img, "PNG")
        return ok(output_path=out_p, data_url=data_url, width=filtered_img.width, height=filtered_img.height)

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
        overwrite = bool(params.get("overwrite", False))
        out_p = str(params["output_path"]) if params.get("output_path") else (file_path if overwrite else "")
        backdrop = str(params.get("backdrop", "transparent")).lower()
        color_tuple = calc_color_tuple(params.get("color", "#ffffff"))
        blur_radius = int(params.get("blur_radius", 25))
        source_img = _calc_load_img(file_path)
        nobg = remove_background(source_img, model_name=model)
        if backdrop == "solid":
            nobg = replace_background_color(nobg, color=(color_tuple[0], color_tuple[1], color_tuple[2], 255))
        elif backdrop == "blur":
            nobg = replace_background_color(nobg, blur_backdrop=True, blur_radius=blur_radius, original_img=source_img)
        if out_p:
            _calc_save(nobg, out_p, params, default_format="PNG" if backdrop == "transparent" else "")
        data_url = _calc_to_data_url(nobg, "PNG")
        return ok(output_path=out_p, data_url=data_url, width=nobg.width, height=nobg.height)

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
        border_size = int(params.get("border_width", params.get("border_size", 10)))
        color_tuple = calc_color_tuple(params.get("color", "#000000"))
        polaroid = bool(params.get("polaroid", False))
        overwrite = bool(params.get("overwrite", False))
        out_p = str(params["output_path"]) if params.get("output_path") else (file_path if overwrite else "")
        source_img = _calc_load_img(file_path)
        bordered_img = add_border(source_img, border_size=border_size, color=color_tuple, polaroid=polaroid)
        if out_p:
            _calc_save(bordered_img, out_p, params)
        data_url = _calc_to_data_url(bordered_img, "PNG")
        return ok(output_path=out_p, data_url=data_url, width=bordered_img.width, height=bordered_img.height)

    @api_method
    def image_add_border(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for adding image border.
        return self.images_add_border(params)

    @api_method
    def images_blur_region(self, params: dict[str, Any]) -> dict[str, Any]:
        # Blur rectangular bounding box within image.
        require(params, "file_path", "box")
        file_path = str(params["file_path"])
        box = tuple(int(coord) for coord in params["box"])
        blur_radius = int(params.get("radius", 15))
        overwrite = bool(params.get("overwrite", False))
        out_p = str(params["output_path"]) if params.get("output_path") else (file_path if overwrite else "")
        source_img = _calc_load_img(file_path)
        blurred_img = blur_region(source_img, box, radius=blur_radius)
        if out_p:
            _calc_save(blurred_img, out_p, params)
        data_url = _calc_to_data_url(blurred_img, "PNG")
        return ok(output_path=out_p, data_url=data_url, width=blurred_img.width, height=blurred_img.height)

    @api_method
    def image_blur_region(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for blurring region.
        return self.images_blur_region(params)

    @api_method
    def images_pixelate_region(self, params: dict[str, Any]) -> dict[str, Any]:
        # Censor image bounding box with pixelation mosaic.
        require(params, "file_path", "box")
        file_path = str(params["file_path"])
        box = tuple(int(coord) for coord in params["box"])
        pixel_size = int(params.get("pixel_size", 10))
        overwrite = bool(params.get("overwrite", False))
        out_p = str(params["output_path"]) if params.get("output_path") else (file_path if overwrite else "")
        source_img = _calc_load_img(file_path)
        pixelated_img = pixelate_region(source_img, box, pixel_size=pixel_size)
        if out_p:
            _calc_save(pixelated_img, out_p, params)
        data_url = _calc_to_data_url(pixelated_img, "PNG")
        return ok(output_path=out_p, data_url=data_url, width=pixelated_img.width, height=pixelated_img.height)

    @api_method
    def image_pixelate_region(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for pixelating region.
        return self.images_pixelate_region(params)

    @api_method
    def images_aspect_box(self, params: dict[str, Any]) -> dict[str, Any]:
        # Calculate aspect ratio centered crop bounding box.
        require(params, "width", "height", "aspect_ratio")
        full_width = int(params["width"])
        full_height = int(params["height"])
        ratio_str = str(params["aspect_ratio"]).replace("/", ":")
        if ":" in ratio_str:
            parts = ratio_str.split(":")
            ratio_w = float(parts[0])
            ratio_h = float(parts[1])
        else:
            ratio_w = float(ratio_str)
            ratio_h = 1.0
        box = aspect_ratio_crop_box(full_width, full_height, ratio_w, ratio_h)
        return ok(box=list(box))

    @api_method
    def images_to_ascii(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert image to ASCII text art.
        require(params, "file_path")
        file_path = str(params["file_path"])
        source_img = _calc_load_img(file_path)
        cols = int(params.get("columns", params.get("width", 80)))
        raw_charset = str(params.get("charset", "standard"))
        resolved_charset = raw_charset
        for preset_name, preset_chars in ASCII_CHARSET_PRESETS.items():
            if preset_name.lower() == raw_charset.lower():
                resolved_charset = preset_chars
                break
        from app.features.image.ops import image_to_ascii
        art = image_to_ascii(source_img, width=cols, charset=resolved_charset)
        out_p = params.get("output_path")
        if out_p:
            save_ascii_art(source_img, str(out_p), width=cols, charset=resolved_charset)
        return ok(ascii=art, output_path=out_p)

    @api_method
    def images_gif_ops(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract frames from GIF or assemble GIF from frame paths.
        action = str(params.get("action", "extract")).lower()
        if action == "extract":
            require(params, "file_path", "output_dir")
            frames = extract_gif_frames(str(params["file_path"]))
            out_dir = Path(str(params["output_dir"]))
            out_dir.mkdir(parents=True, exist_ok=True)
            saved_paths: list[str] = []
            for frame_idx, frame in enumerate(frames):
                frame_path = out_dir / f"frame_{frame_idx + 1:04d}.png"
                frame.save(frame_path, format="PNG")
                saved_paths.append(str(frame_path))
            return ok(frames=saved_paths, count=len(saved_paths))
        elif action == "create":
            require(params, "frame_paths", "output_path")
            fps = float(params.get("fps", 10.0))
            loop = int(params.get("loop", 0))
            duration_ms = max(10, round(1000.0 / max(1.0, fps)))
            pil_frames = [_calc_load_img(str(frame_p)) for frame_p in params["frame_paths"]]
            out_p = frames_to_gif(pil_frames, str(params["output_path"]), duration_ms=duration_ms, loop=loop)
            return ok(output_path=out_p)
        elif action == "video":
            require(params, "file_path", "output_path")
            video_out_path = gif_to_video(str(params["file_path"]), str(params["output_path"]))
            return ok(output_path=video_out_path)
        return ok()

    @api_method
    def images_batch_process(self, params: dict[str, Any]) -> dict[str, Any]:
        # Batch execute pipeline operations across multiple images.
        require(params, "file_paths")
        paths = [str(input_p) for input_p in params["file_paths"]]
        out_dir = str(params.get("output_dir", "."))
        target_fmt = params.get("target_format")
        quality = int(params.get("quality", 85))
        resize_to = None
        if "width" in params and "height" in params:
            resize_to = (int(params["width"]), int(params["height"]))
        keep_aspect = bool(params.get("keep_aspect", True))
        remove_bg = bool(params.get("remove_background", False))
        bg_model = str(params.get("bg_model", "u2net"))
        results = batch_process(
            paths,
            out_dir,
            target_format=str(target_fmt) if target_fmt else None,
            quality=quality,
            resize_to=resize_to,
            keep_aspect=keep_aspect,
            remove_background_enabled=remove_bg,
            bg_model=bg_model,
        )
        return ok(results=results, count=len(results))

    @api_method
    def images_ocr(self, params: dict[str, Any]) -> dict[str, Any]:
        # Recognize text inside image using OCR.
        require(params, "file_path")
        text = ocr_image(str(params["file_path"]), language=str(params.get("language", "eng")))
        return ok(text=text)

    @api_method
    def images_compress(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compress image file with specified quality.
        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        output_path = str(params["output_path"])
        quality = int(params.get("quality", 80))
        source_img = _calc_load_img(file_path)
        save_image(source_img, output_path, quality=quality, compress_well=True)
        return ok(output_path=output_path)

    @api_method
    def image_compress(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for image compression.
        return self.images_compress(params)
