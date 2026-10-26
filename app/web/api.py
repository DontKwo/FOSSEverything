"""Python bridge exposing local FOSSEverything engines to the web frontend."""
from __future__ import annotations

import base64
import difflib
import io
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any

import numpy as np
import psutil
import pymupdf
from PIL import Image
import webview

from app.core.home_apps import HOME_APPS
from app.core.tool_registry import ToolDefinition, ToolRegistry
from app.core.theme import (
    THEME_PRESET_ORDER,
    THEME_PRESET_LABELS,
    default_palette,
    resolved_palette,
)
from app.system.settings import get_setting, set_setting
from app.system.shell_integration import (
    FILE_FAMILIES,
    manual_association_instructions,
    register_shell_context_menu,
    set_default_for_extensions,
    unregister_shell_context_menu,
)
from app.features.archive.ops import create_archive, extract_archive, list_archive_contents, test_archive
from app.features.collage.ops import CollageConfig, make_collage
from app.features.converter.ops import (
    BatchConversionItem,
    available_targets,
    batch_convert_files,
    convert_file,
)
from app.features.data.ops import (
    convert_data_format as ops_convert_data,
    format_css,
    format_javascript,
    format_sql,
    format_xml,
    format_yaml,
    infer_json_schema as ops_infer_schema,
    minify_json as ops_minify_json,
    query_jsonpath as ops_query_jsonpath,
)
from app.features.encoding.ops import (
    base64_decode_text,
    base64_encode_text,
    binary_decode_to_bytes,
    binary_encode_bytes,
    hex_decode_text,
    hex_encode_text,
    html_decode,
    html_encode,
    url_decode,
    url_encode,
)
from app.features.hash.ops import (
    generate_checksum_manifest,
    hash_file,
    hash_text,
    infer_algorithm_from_digest_length,
    verify_checksum_manifest,
    verify_hash,
)
from app.features.image.ops import (
    add_border,
    adjust_image,
    apply_filter_preset,
    auto_enhance,
    blur_region,
    circle_crop_image,
    crop_image,
    flip_image,
    load_image,
    pixelate_region,
    remove_background,
    replace_background_color,
    resize_image,
    rotate_image,
    save_image,
)
from app.features.markdown.ops import render_markdown_to_html
from app.features.media.ops import (
    compress_media,
    extract_audio,
    extract_frame,
    get_media_info,
    mute_video,
    trim_media,
)
from app.features.metadata.ops import export_metadata, inspect_metadata, strip_metadata
from app.features.model3d import ops as model_ops
from app.features.ocr.ops import (
    create_searchable_pdf as ops_create_searchable_pdf,
    get_supported_languages,
    ocr_file,
)
from app.features.office.ops import (
    docx_to_markdown,
    docx_to_pdf,
    extract_text_from_office,
    pptx_to_markdown,
    xlsx_to_csv,
)
from app.features.palette.ops import extract_palette
from app.features.pdf.ops import (
    add_page_numbers,
    add_pdf_watermark,
    compress_pdf,
    convert_pdf_to_docx,
    extract_pdf_text,
    merge_pdfs,
    protect_pdf,
    reorganize_pdf_pages,
    split_pdf,
    unlock_pdf,
)
from app.features.playlist.ops import clean_music_title
from app.features.qr.ops import (
    decode_qr_and_barcodes,
    generate_barcode,
    generate_qr_code,
    generate_qr_svg,
)
from app.features.renamer.ops import (
    RenamePlan,
    execute_renames,
    preview_renames,
    undo_renames,
)
from app.features.resume.ops import (
    MasterResume,
    analyze_ats_match,
    create_sample_master_resume,
    export_docx as resume_export_docx,
    export_html as resume_export_html,
    export_markdown as resume_export_markdown,
    export_pdf as resume_export_pdf,
    load_resume_file,
    resume_from_dict,
    resume_to_dict,
    save_resume_file,
)
from app.features.screenshot.ops import capture_full_screen
from app.features.text_tools.ops import (
    dedupe_lines,
    reverse_lines,
    sort_lines,
    to_camel_case,
    to_constant_case,
    to_kebab_case,
    to_lowercase,
    to_sentence_case,
    to_snake_case,
    to_title_case,
    to_uppercase,
)
from app.features.word_counter.ops import analyze_text, extract_text_from_file, generate_report


def _hex_to_rgb_float(hex_str: str) -> tuple[float, float, float]:
    clean = hex_str.lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    if len(clean) != 6:
        return (0.0, 0.0, 0.0)
    try:
        r = int(clean[0:2], 16) / 255.0
        g = int(clean[2:4], 16) / 255.0
        b = int(clean[4:6], 16) / 255.0
        return (r, g, b)
    except ValueError:
        return (0.0, 0.0, 0.0)


def _hex_to_rgb_int(hex_str: str) -> tuple[int, int, int]:
    clean = hex_str.lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    if len(clean) != 6:
        return (0, 0, 0)
    try:
        r = int(clean[0:2], 16)
        g = int(clean[2:4], 16)
        b = int(clean[4:6], 16)
        return (r, g, b)
    except ValueError:
        return (0, 0, 0)


def _img_to_data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    fmt = "PNG" if img.mode in ("RGBA", "LA") else "JPEG"
    img.save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def _parse_page_ranges(range_str: str, max_pages: int = 999999) -> list[tuple[int, int]]:
    result = []
    for part in range_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            s_str, e_str = part.split("-", 1)
            try:
                start = max(1, int(s_str.strip()))
                end = min(max_pages, int(e_str.strip()))
                if start <= end:
                    result.append((start, end))
            except ValueError:
                pass
        else:
            try:
                page = max(1, min(max_pages, int(part)))
                result.append((page, page))
            except ValueError:
                pass
    return result if result else [(1, max_pages)]


def _clean_dialog_filter(raw_filter: str) -> str:
    m = re.search(r"\(([^)]+)\)", raw_filter)
    if m:
        exts = m.group(1).strip()
        label = raw_filter[: m.start()].strip()
    else:
        exts = raw_filter.strip()
        label = "Files"
    clean_label = re.sub(r"[^\w ]", " ", label).strip()
    if not clean_label:
        clean_label = "Files"
    return f"{clean_label} ({exts})"


def _clean_dialog_filters(file_types: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if not file_types:
        return ()
    return tuple(_clean_dialog_filter(str(f)) for f in file_types if f)


class WebApi:
    """Bridge API exposed to pywebview JavaScript environment."""

    def __init__(self) -> None:
        self._window: Any = None
        self.registry = ToolRegistry()
        self._last_renames: list[dict[str, str]] = []
        self._last_undo_pairs: list[dict[str, str]] = []
        for app in HOME_APPS:
            self.registry.register(
                ToolDefinition(
                    id=app.id,
                    title=app.name,
                    category=app.category,
                    keywords=app.keywords,
                    activate=lambda: None,
                    description=app.description,
                )
            )

    def set_window(self, window: Any) -> None:
        self._window = window

    def _get_window(self) -> Any:
        if self._window is not None:
            return self._window
        win = webview.active_window()
        if win:
            return win
        if len(webview.windows) > 0:
            return webview.windows[0]
        return None

    def get_apps(self) -> list[dict[str, Any]]:
        return [
            {
                "id": app.id,
                "name": app.name,
                "category": app.category,
                "description": app.description,
                "keywords": list(app.keywords),
                "available": app.available,
            }
            for app in HOME_APPS
        ]

    def get_theme_presets(self) -> dict[str, Any]:
        return {
            "order": list(THEME_PRESET_ORDER),
            "labels": dict(THEME_PRESET_LABELS),
        }

    def get_theme_palette(self, theme_name: str = "dark") -> dict[str, str]:
        return resolved_palette()

    def get_setting(self, key: str, default: Any = None) -> Any:
        return get_setting(key, default)

    def set_setting(self, key: str, value: Any) -> bool:
        set_setting(key, value)
        return True

    def search_tools(self, query: str) -> list[dict[str, Any]]:
        matches = self.registry.search(query, limit=30)
        return [
            {
                "id": m.tool.id,
                "title": m.tool.title,
                "category": m.tool.category,
                "description": m.tool.description,
                "score": m.score,
            }
            for m in matches
        ]

    def select_file(self, file_types: list[str] | None = None, multiple: bool = False) -> list[str]:
        win = self._get_window()
        cleaned_types = _clean_dialog_filters(file_types)
        if win:
            try:
                result = win.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=multiple, file_types=cleaned_types)
                if result is not None:
                    return list(result)
            except Exception:  # noqa: 23
                pass
        if "PYTEST_CURRENT_TEST" in os.environ or "CI" in os.environ:
            return []
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            if multiple:
                paths = filedialog.askopenfilenames(parent=root)
                root.destroy()
                return list(paths) if paths else []
            single = filedialog.askopenfilename(parent=root)
            root.destroy()
            return [single] if single else []
        except Exception:  # noqa: 23
            return []

    def select_folder(self) -> str:
        win = self._get_window()
        if win:
            try:
                result = win.create_file_dialog(webview.FileDialog.FOLDER)
                if result and len(result) > 0:
                    return result[0]
            except Exception:  # noqa: 23
                pass
        if "PYTEST_CURRENT_TEST" in os.environ or "CI" in os.environ:
            return ""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder = filedialog.askdirectory(parent=root)
            root.destroy()
            return folder if folder else ""
        except Exception:  # noqa: 23
            return ""

    def select_directory(self) -> str:
        return self.select_folder()

    def select_save_file(self, file_types: Any = None, save_filename: Any = "") -> str:
        win = self._get_window()
        if isinstance(file_types, str) and (isinstance(save_filename, (list, tuple)) or not save_filename):
            save_name = file_types
            types_list = list(save_filename) if save_filename else []
        elif isinstance(file_types, (list, tuple)):
            types_list = list(file_types)
            save_name = str(save_filename) if save_filename else ""
        else:
            save_name = str(file_types) if file_types else ""
            types_list = []
        cleaned_types = _clean_dialog_filters(types_list)
        if win:
            try:
                result = win.create_file_dialog(webview.FileDialog.SAVE, save_filename=save_name, file_types=cleaned_types)
                if result and len(result) > 0:
                    return result[0]
            except Exception:  # noqa: 23
                pass
        if "PYTEST_CURRENT_TEST" in os.environ or "CI" in os.environ:
            return ""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            saved = filedialog.asksaveasfilename(parent=root, initialfile=save_name)
            root.destroy()
            return saved if saved else ""
        except Exception:  # noqa: 23
            return ""

    def save_file(self, content: str, file_path: str) -> dict[str, Any]:
        try:
            if os.path.isabs(content) and not os.path.isabs(file_path):
                content, file_path = file_path, content
            target_dir = os.path.dirname(os.path.abspath(file_path))
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "output_path": file_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def read_file(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:  # noqa: 23
            return ""

    def read_file_text(self, file_path: str) -> dict[str, Any]:
        try:
            text = extract_text_from_file(file_path)
            return {"success": True, "text": text, "file_path": file_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc), "text": ""}

    def open_folder(self, folder_path: str) -> bool:
        if not os.path.isdir(folder_path):
            folder_path = os.path.dirname(folder_path)
        if not os.path.exists(folder_path):
            return False
        if sys.platform == "win32":
            os.startfile(folder_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder_path], check=False)
        else:
            subprocess.run(["xdg-open", folder_path], check=False)
        return True

    # Shell Integration
    def shell_register_context_menu(self) -> dict[str, Any]:
        ok, msg = register_shell_context_menu()
        return {"success": ok, "message": msg}

    def shell_unregister_context_menu(self) -> dict[str, Any]:
        ok, msg = unregister_shell_context_menu()
        return {"success": ok, "message": msg}

    def shell_get_file_associations(self) -> dict[str, Any]:
        families = []
        for name, exts in FILE_FAMILIES:
            families.append({"name": name, "extensions": sorted(exts)})
        return {"families": families}

    def shell_set_file_associations(self, extensions: list[str]) -> dict[str, Any]:
        ok, msg = set_default_for_extensions(extensions)
        return {"success": ok, "message": msg}

    def shell_get_manual_instructions(self, extensions: list[str]) -> str:
        return manual_association_instructions(extensions)

    # PDF Visual Viewer and Annotation Operations
    def pdf_open_doc(self, file_path: str) -> dict[str, Any]:
        if not os.path.isfile(file_path):
            return {"error": f"File not found: {file_path}"}
        try:
            doc = pymupdf.open(file_path)
            meta = doc.metadata or {}
            return {
                "success": True,
                "page_count": len(doc),
                "title": meta.get("title", os.path.basename(file_path)),
                "author": meta.get("author", ""),
                "is_encrypted": doc.is_encrypted,
            }
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_render_page(self, file_path: str, page_number: int, dpi: int = 150) -> dict[str, Any]:
        if not os.path.isfile(file_path):
            return {"error": f"File not found: {file_path}"}
        try:
            doc = pymupdf.open(file_path)
            idx = max(0, min(page_number, len(doc) - 1))
            page = doc[idx]
            pix = page.get_pixmap(dpi=dpi)
            data_bytes = pix.tobytes("png")
            b64 = base64.b64encode(data_bytes).decode("ascii")
            return {
                "success": True,
                "page": idx,
                "page_count": len(doc),
                "width": pix.width,
                "height": pix.height,
                "data_url": f"data:image/png;base64,{b64}",
            }
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_save_annotated_page(self, file_path: str, arg2: Any, arg3: Any, arg4: Any = None, dpi: int = 150) -> dict[str, Any]:
        try:
            # Handle both (file_path, output_path, page_number, annotations) and (file_path, page_number, annotations, output_path)
            if isinstance(arg2, str):
                output_path = arg2
                page_number = int(arg3)
                annotations = arg4 if isinstance(arg4, list) else []
            else:
                page_number = int(arg2)
                annotations = arg3 if isinstance(arg3, list) else []
                output_path = str(arg4)
            doc = pymupdf.open(file_path)
            idx = max(0, min(page_number, len(doc) - 1))
            page = doc[idx]
            scale = 72.0 / float(dpi)

            for item in annotations:
                kind = item.get("type")
                color_val = item.get("color", "#ef4444")
                rgb = _hex_to_rgb_float(color_val) if isinstance(color_val, str) else color_val
                width = float(item.get("width", 2)) * scale

                if kind == "rect":
                    x0 = float(item["x"]) * scale
                    y0 = float(item["y"]) * scale
                    x1 = x0 + float(item["w"]) * scale
                    y1 = y0 + float(item["h"]) * scale
                    page.draw_rect(pymupdf.Rect(x0, y0, x1, y1), color=rgb, width=width)
                elif kind == "highlight":
                    x0 = float(item["x"]) * scale
                    y0 = float(item["y"]) * scale
                    x1 = x0 + float(item["w"]) * scale
                    y1 = y0 + float(item["h"]) * scale
                    page.draw_rect(pymupdf.Rect(x0, y0, x1, y1), fill=rgb, fill_opacity=float(item.get("opacity", 0.35)), width=0)
                elif kind == "redact":
                    x0 = float(item["x"]) * scale
                    y0 = float(item["y"]) * scale
                    x1 = x0 + float(item["w"]) * scale
                    y1 = y0 + float(item["h"]) * scale
                    r = pymupdf.Rect(x0, y0, x1, y1)
                    page.add_redact_annot(r)
                    page.apply_redactions()
                elif kind == "text":
                    p = pymupdf.Point(float(item["x"]) * scale, float(item["y"]) * scale)
                    f_size = float(item.get("font_size", 14)) * scale
                    page.insert_text(p, str(item.get("text", "")), fontsize=f_size, color=rgb)
                elif kind == "line":
                    points = item.get("points")
                    if points and len(points) >= 2:
                        for i in range(len(points) - 1):
                            p1 = pymupdf.Point(float(points[i]["x"]) * scale, float(points[i]["y"]) * scale)
                            p2 = pymupdf.Point(float(points[i + 1]["x"]) * scale, float(points[i + 1]["y"]) * scale)
                            page.draw_line(p1, p2, color=rgb, width=width)
                    else:
                        p1 = pymupdf.Point(float(item["x1"]) * scale, float(item["y1"]) * scale)
                        p2 = pymupdf.Point(float(item["x2"]) * scale, float(item["y2"]) * scale)
                        page.draw_line(p1, p2, color=rgb, width=width)
                elif kind == "arrow":
                    p1 = pymupdf.Point(float(item["x1"]) * scale, float(item["y1"]) * scale)
                    p2 = pymupdf.Point(float(item["x2"]) * scale, float(item["y2"]) * scale)
                    page.draw_line(p1, p2, color=rgb, width=width)

            doc.save(output_path)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_rotate_page(self, file_path: str, page_number: int, degrees: int, output_path: str = "") -> dict[str, Any]:
        try:
            doc = pymupdf.open(file_path)
            idx = max(0, min(page_number, len(doc) - 1))
            page = doc[idx]
            page.set_rotation((page.rotation + degrees) % 360)
            target_out = output_path if output_path else file_path + ".tmp.pdf"
            doc.save(target_out)
            doc.close()
            if not output_path:
                shutil.move(target_out, file_path)
                target_out = file_path
            return {"success": True, "output_path": target_out}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_delete_page(self, file_path: str, page_number: int, output_path: str = "") -> dict[str, Any]:
        try:
            doc = pymupdf.open(file_path)
            idx = max(0, min(page_number, len(doc) - 1))
            doc.delete_page(idx)
            target_out = output_path if output_path else file_path + ".tmp.pdf"
            doc.save(target_out)
            doc.close()
            if not output_path:
                shutil.move(target_out, file_path)
                target_out = file_path
            return {"success": True, "output_path": target_out}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_extract_single_page(self, file_path: str, page_number: int, output_path: str) -> dict[str, Any]:
        return self.pdf_extract_page(file_path, page_number, output_path)

    def pdf_reorder_pages(self, file_path: str, arg2: Any, arg3: Any) -> dict[str, Any]:
        try:
            # Handle both (file_path, output_path, order) and (file_path, order, output_path)
            if isinstance(arg2, list):
                order = arg2
                output_path = str(arg3)
            else:
                output_path = str(arg2)
                order = arg3 if isinstance(arg3, list) else []
            ops = [{"source_page": p, "rotation": 0} for p in order]
            reorganize_pdf_pages(file_path, output_path, ops)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_merge(self, file_paths: list[str], output_path: str) -> dict[str, Any]:
        try:
            merge_pdfs(file_paths, output_path)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_split(self, file_path: str, arg2: str = "", arg3: str = "") -> dict[str, Any]:
        try:
            # Handle both (file_path, output_dir, ranges) and (file_path, ranges, output_dir)
            if os.path.isdir(arg2) or not os.path.isdir(arg3) and not ("," in arg2 or "-" in arg2):
                output_dir = arg2
                ranges = arg3
            else:
                ranges = arg2
                output_dir = arg3
            doc = pymupdf.open(file_path)
            total = len(doc)
            parsed_ranges = _parse_page_ranges(ranges, total) if ranges else [(1, total)]
            outputs = split_pdf(file_path, parsed_ranges, output_dir)
            return {"success": True, "output_files": outputs, "files": outputs}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_compress(self, file_path: str, arg2: str = "", arg3: str = "medium") -> dict[str, Any]:
        try:
            # Handle both (file_path, output_path, level) and (file_path, level, output_path)
            if arg2.lower() in ("low", "medium", "high") or not arg3.lower() in ("low", "medium", "high") and arg3:
                level = arg2
                output_path = arg3
            else:
                output_path = arg2
                level = arg3
            quality_map = {"low": "screen", "medium": "ebook", "high": "printer"}
            q = quality_map.get(level.lower(), "ebook")
            compress_pdf(file_path, output_path, quality=q)
            new_sz = os.path.getsize(output_path) if os.path.isfile(output_path) else 0
            return {"success": True, "output_path": output_path, "new_size": new_sz}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_extract_text(self, file_path: str) -> dict[str, Any]:
        try:
            text = extract_pdf_text(file_path)
            return {"success": True, "text": text}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_extract_page(self, file_path: str, page_number: int, output_path: str) -> dict[str, Any]:
        try:
            doc = pymupdf.open(file_path)
            idx = max(0, min(page_number, len(doc) - 1))
            new_doc = pymupdf.open()
            new_doc.insert_pdf(doc, from_page=idx, to_page=idx)
            new_doc.save(output_path)
            new_doc.close()
            doc.close()
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_watermark(self, file_path: str, arg2: str, arg3: str, font_size: int = 48, opacity: float = 0.25) -> dict[str, Any]:
        try:
            # Handle both (file_path, output_path, text) and (file_path, text, output_path)
            if "/" in arg2 or "\\" in arg2 or arg2.endswith(".pdf"):
                output_path = arg2
                text = arg3
            else:
                text = arg2
                output_path = arg3
            add_pdf_watermark(file_path, output_path, text=text, font_size=font_size, opacity=opacity)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_protect(self, file_path: str, arg2: str, arg3: str) -> dict[str, Any]:
        try:
            # Handle both (file_path, output_path, password) and (file_path, password, output_path)
            if "/" in arg2 or "\\" in arg2 or arg2.endswith(".pdf"):
                output_path = arg2
                password = arg3
            else:
                password = arg2
                output_path = arg3
            protect_pdf(file_path, output_path, password)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_unlock(self, file_path: str, arg2: str, arg3: str = "") -> dict[str, Any]:
        try:
            # Handle both (file_path, output_path, password) and (file_path, password, output_path)
            if "/" in arg2 or "\\" in arg2 or arg2.endswith(".pdf"):
                output_path = arg2
                password = arg3
            else:
                password = arg2
                output_path = arg3
            unlock_pdf(file_path, output_path, password)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_add_page_numbers(self, file_path: str, arg2: str, arg3: str = "Page {n} of {total}", arg4: str = "bottom_center") -> dict[str, Any]:
        try:
            # Handle both (file_path, output_path, fmt, pos) and (file_path, fmt, pos, output_path)
            if "/" in arg2 or "\\" in arg2 or arg2.endswith(".pdf"):
                output_path = arg2
                fmt = arg3
                pos = arg4
            else:
                fmt = arg2
                pos = arg3
                output_path = arg4
            add_page_numbers(file_path, output_path, format_str=fmt, position=pos)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_page_numbers(self, file_path: str, arg2: str, arg3: str = "Page {n} of {total}", arg4: str = "bottom_center") -> dict[str, Any]:
        return self.pdf_add_page_numbers(file_path, arg2, arg3, arg4)

    def pdf_to_docx(self, file_path: str, output_path: str) -> dict[str, Any]:
        try:
            convert_pdf_to_docx(file_path, output_path)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_create_searchable_pdf(self, file_path: str, output_path: str, language: str = "eng", dpi: int = 150) -> dict[str, Any]:
        try:
            ops_create_searchable_pdf(file_path, output_path, language=language, dpi=dpi)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def pdf_reorganize(self, file_path: str, output_path: str, order: list[int]) -> dict[str, Any]:
        return self.pdf_reorder_pages(file_path, output_path, order)

    # Image Studio Visual Canvas Operations
    def image_load_data(self, file_path: str) -> dict[str, Any]:
        if not os.path.isfile(file_path):
            return {"error": f"File not found: {file_path}"}
        try:
            img = Image.open(file_path)
            return {
                "success": True,
                "width": img.width,
                "height": img.height,
                "format": img.format or "PNG",
                "mode": img.mode,
                "data_url": _img_to_data_url(img),
            }
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_load_preview(self, file_path: str) -> dict[str, Any]:
        return self.image_load_data(file_path)

    def image_save_canvas_data(self, data_url: str, output_path: str, target_format: str = "PNG", quality: int = 90) -> dict[str, Any]:
        try:
            header, encoded = data_url.split(",", 1) if "," in data_url else ("", data_url)
            data = base64.b64decode(encoded)
            img = Image.open(io.BytesIO(data))
            fmt = target_format.upper().replace("JPG", "JPEG")
            if fmt == "JPEG" and img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            img.save(output_path, format=fmt, quality=quality)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_save_canvas(self, data_url: str, output_path: str, target_format: str = "PNG", quality: int = 90) -> dict[str, Any]:
        return self.image_save_canvas_data(data_url, output_path, target_format=target_format, quality=quality)

    def image_resize(self, file_path: str, output_path: str = "", width: int = 800, height: int = 600, keep_aspect: bool = True) -> dict[str, Any]:
        try:
            img = load_image(file_path)
            res = resize_image(img, width, height, keep_aspect=keep_aspect)
            if output_path:
                save_image(res, output_path)
            return {"success": True, "output_path": output_path, "size": [res.width, res.height], "data_url": _img_to_data_url(res)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_crop(self, file_path: str, arg2: Any, arg3: Any = 0, arg4: Any = 0, arg5: Any = 0, arg6: Any = 0) -> dict[str, Any]:
        try:
            img = load_image(file_path)
            if isinstance(arg2, (list, tuple)) and len(arg2) >= 4:
                # [x1, y1, x2, y2]
                x1, y1, x2, y2 = int(arg2[0]), int(arg2[1]), int(arg2[2]), int(arg2[3])
                x = min(x1, x2)
                y = min(y1, y2)
                w = abs(x2 - x1)
                h = abs(y2 - y1)
                output_path = str(arg3) if isinstance(arg3, str) and arg3 else ""
            else:
                output_path = str(arg2)
                x = int(arg3)
                y = int(arg4)
                w = int(arg5)
                h = int(arg6)
            res = crop_image(img, x, y, w, h)
            if output_path:
                save_image(res, output_path)
            return {"success": True, "output_path": output_path, "data_url": _img_to_data_url(res)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_circle_crop(self, file_path: str, output_path: str = "") -> dict[str, Any]:
        try:
            img = load_image(file_path)
            res = circle_crop_image(img)
            if output_path:
                save_image(res, output_path)
            return {"success": True, "output_path": output_path, "data_url": _img_to_data_url(res)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_rotate(self, file_path: str, arg2: Any = 90, arg3: Any = "") -> dict[str, Any]:
        try:
            img = load_image(file_path)
            if isinstance(arg2, (int, float)) or (isinstance(arg2, str) and arg2.lstrip("-").isdigit()):
                degrees = int(arg2)
                output_path = str(arg3) if arg3 else ""
            else:
                output_path = str(arg2)
                degrees = int(arg3)
            res = rotate_image(img, degrees)
            if output_path:
                save_image(res, output_path)
            return {"success": True, "output_path": output_path, "data_url": _img_to_data_url(res)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_flip(self, file_path: str, arg2: Any = "horizontal", arg3: bool = True, arg4: bool = False) -> dict[str, Any]:
        try:
            img = load_image(file_path)
            if isinstance(arg2, str) and arg2.lower() in ("horizontal", "vertical", "both"):
                mode = arg2.lower()
                horizontal = mode in ("horizontal", "both")
                vertical = mode in ("vertical", "both")
                output_path = ""
            else:
                output_path = str(arg2)
                horizontal = bool(arg3)
                vertical = bool(arg4)
            res = flip_image(img, horizontal=horizontal, vertical=vertical)
            if output_path:
                save_image(res, output_path)
            return {"success": True, "output_path": output_path, "data_url": _img_to_data_url(res)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_convert(self, file_path: str, output_path: str, target_format: str, quality: int = 90) -> dict[str, Any]:
        try:
            img = load_image(file_path)
            save_image(img, output_path, format=target_format, quality=quality)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_adjust(self, file_path: str, output_path: str = "", brightness: float = 1.0, contrast: float = 1.0, sharpness: float = 1.0, warmth: float = 0.0) -> dict[str, Any]:
        try:
            img = load_image(file_path)
            res = adjust_image(img, brightness=brightness, contrast=contrast, sharpness=sharpness, warmth=warmth)
            if output_path:
                save_image(res, output_path)
            return {"success": True, "output_path": output_path, "data_url": _img_to_data_url(res)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_apply_filter_preset(self, file_path: str, output_path: str = "", preset_name: str = "vivid") -> dict[str, Any]:
        try:
            # Handle both (file_path, output_path, preset) and (file_path, preset)
            if not ("/" in output_path or "\\" in output_path or "." in output_path) and output_path:
                preset_name = output_path
                output_path = ""
            img = load_image(file_path)
            res = apply_filter_preset(img, preset_name)
            if output_path:
                save_image(res, output_path)
            return {"success": True, "output_path": output_path, "data_url": _img_to_data_url(res)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_auto_enhance(self, file_path: str, output_path: str = "") -> dict[str, Any]:
        try:
            img = load_image(file_path)
            res = auto_enhance(img)
            if output_path:
                save_image(res, output_path)
            return {"success": True, "output_path": output_path, "data_url": _img_to_data_url(res)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_remove_background(self, file_path: str, arg2: str = "", arg3: str = "bria-rmbg") -> dict[str, Any]:
        try:
            # Handle both (file_path, output_path, model) and (file_path, model)
            if not ("/" in arg2 or "\\" in arg2 or "." in arg2) and arg2:
                model_name = arg2
                output_path = ""
            else:
                output_path = arg2
                model_name = arg3 or "bria-rmbg"
            img = load_image(file_path)
            res = remove_background(img, model_name=model_name)
            if output_path:
                save_image(res, output_path)
            return {"success": True, "output_path": output_path, "data_url": _img_to_data_url(res)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_replace_background_color(self, file_path: str, arg2: str = "", arg3: str = "#ffffff") -> dict[str, Any]:
        try:
            # Handle both (file_path, output_path, color) and (file_path, color)
            if arg2.startswith("#") or arg2.startswith("rgb"):
                color = arg2
                output_path = ""
            else:
                output_path = arg2
                color = arg3 or "#ffffff"
            img = load_image(file_path)
            rgb = _hex_to_rgb_int(color) + (255,)
            res = replace_background_color(img, color=rgb)
            if output_path:
                save_image(res, output_path)
            return {"success": True, "output_path": output_path, "data_url": _img_to_data_url(res)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_add_border(self, file_path: str, arg2: Any = 20, arg3: Any = "#ffffff", arg4: Any = False, arg5: Any = False) -> dict[str, Any]:
        try:
            if isinstance(arg2, (int, float)) or (isinstance(arg2, str) and arg2.isdigit()):
                border_size = int(arg2)
                color = str(arg3)
                polaroid = bool(arg4)
                output_path = ""
            else:
                output_path = str(arg2)
                border_size = int(arg3)
                color = str(arg4)
                polaroid = bool(arg5)
            img = load_image(file_path)
            rgb = _hex_to_rgb_int(color)
            res = add_border(img, border_size=border_size, color=rgb, polaroid=polaroid)
            if output_path:
                save_image(res, output_path)
            return {"success": True, "output_path": output_path, "data_url": _img_to_data_url(res)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_blur_region(self, file_path: str, output_path: str = "", box: list[int] | None = None, radius: int = 15) -> dict[str, Any]:
        try:
            img = load_image(file_path)
            b = tuple(box) if box else (0, 0, img.width, img.height)
            res = blur_region(img, b, radius=radius)
            if output_path:
                save_image(res, output_path)
            return {"success": True, "output_path": output_path, "data_url": _img_to_data_url(res)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def image_pixelate_region(self, file_path: str, output_path: str = "", box: list[int] | None = None, pixel_size: int = 12) -> dict[str, Any]:
        try:
            img = load_image(file_path)
            b = tuple(box) if box else (0, 0, img.width, img.height)
            res = pixelate_region(img, b, pixel_size=pixel_size)
            if output_path:
                save_image(res, output_path)
            return {"success": True, "output_path": output_path, "data_url": _img_to_data_url(res)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # Media Studio Audio/Video Operations
    def media_get_file_url(self, file_path: str) -> dict[str, Any]:
        if not os.path.isfile(file_path):
            return {"error": f"File not found: {file_path}"}
        url = "file:///" + os.path.abspath(file_path).replace("\\", "/")
        return {"url": url, "path": file_path}

    def media_save_frame_data(self, data_url: str, output_path: str) -> dict[str, Any]:
        try:
            header, encoded = data_url.split(",", 1) if "," in data_url else ("", data_url)
            data = base64.b64decode(encoded)
            with open(output_path, "wb") as f:
                f.write(data)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def media_get_info(self, file_path: str) -> dict[str, Any]:
        try:
            info = get_media_info(file_path)
            res = dict(info)
            res["codec"] = info.get("video_codec") or info.get("audio_codec") or "Unknown"
            if "width" in info and "height" in info and info["width"]:
                res["resolution"] = f"{info['width']}x{info['height']}"
            else:
                res["resolution"] = "Audio"
            res["duration"] = info.get("duration_sec", 0.0)
            res["bitrate"] = f"{info.get('bitrate_kbps', 0)} kbps" if info.get("bitrate_kbps") else "N/A"
            return res
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def media_info(self, file_path: str) -> dict[str, Any]:
        return self.media_get_info(file_path)

    def media_trim(self, file_path: str, arg2: Any, arg3: Any, arg4: Any = "", arg5: bool = False) -> dict[str, Any]:
        try:
            # Handle both (file_path, output_path, start, end, fast) and (file_path, start, end, output_path, fast)
            if isinstance(arg2, (int, float)) or (isinstance(arg2, str) and arg2.replace(".", "", 1).isdigit()):
                start_time = float(arg2)
                end_time = float(arg3)
                output_path = str(arg4)
                fast_copy = bool(arg5)
            else:
                output_path = str(arg2)
                start_time = float(arg3)
                end_time = float(arg4)
                fast_copy = bool(arg5)
            trim_media(file_path, output_path, start_time_sec=start_time, end_time_sec=end_time, fast_copy=fast_copy)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def media_extract_audio(self, file_path: str, output_path: str, audio_format: str = "mp3", bitrate: str = "192k") -> dict[str, Any]:
        try:
            extract_audio(file_path, output_path, audio_format=audio_format, bitrate=bitrate)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def media_compress(self, file_path: str, output_path: str, crf: int = 28) -> dict[str, Any]:
        try:
            compress_media(file_path, output_path, quality=crf)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def media_capture_frame(self, file_path: str, output_path: Any = "", timestamp: float = 1.0) -> dict[str, Any]:
        try:
            import tempfile
            if isinstance(output_path, (int, float)) or (isinstance(output_path, str) and output_path.replace(".", "", 1).isdigit()):
                timestamp = float(output_path)
                output_path = ""
            target = str(output_path) or os.path.join(tempfile.gettempdir(), f"frame_{int(timestamp * 1000)}.png")
            extract_frame(file_path, target, timestamp_sec=float(timestamp))
            res = {"success": True, "output_path": output_path or target}
            if os.path.isfile(target):
                with open(target, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
                    res["data_url"] = f"data:image/png;base64,{b64}"
            return res
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def media_mute_video(self, file_path: str, output_path: str) -> dict[str, Any]:
        try:
            mute_video(file_path, output_path)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def media_mute(self, file_path: str, output_path: str) -> dict[str, Any]:
        return self.media_mute_video(file_path, output_path)

    # 3D Model Studio WebGL Operations
    def model3d_load_mesh(self, file_path: str) -> dict[str, Any]:
        if not os.path.isfile(file_path):
            return {"error": f"File not found: {file_path}"}
        try:
            model = model_ops.load(file_path)
            details = model_ops.info(model)
            verts, faces = model_ops.tessellated_preview(model)
            if len(verts) == 0:
                return {"error": "Mesh contains no vertices."}

            bounds_min = np.min(verts, axis=0)
            bounds_max = np.max(verts, axis=0)
            dims = (bounds_max - bounds_min).tolist()
            center = (bounds_min + bounds_max) / 2.0
            scale = float(np.max(bounds_max - bounds_min))
            norm_verts = (verts - center) / (scale / 2.0) if scale > 0 else verts

            return {
                "success": True,
                "path": file_path,
                "vertex_count": int(len(verts)),
                "vertices_count": int(len(verts)),
                "face_count": int(len(faces)),
                "faces_count": int(len(faces)),
                "dimensions": dims,
                "vertices": norm_verts.astype(np.float32).flatten().tolist(),
                "faces": faces.astype(np.int32).flatten().tolist(),
                "bounds_min": bounds_min.tolist(),
                "bounds_max": bounds_max.tolist(),
                "volume": details.get("volume"),
                "surface_area": details.get("surface_area"),
                "watertight": details.get("watertight", False),
                "is_watertight": details.get("watertight", False),
            }
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def model3d_load(self, file_path: str) -> dict[str, Any]:
        return self.model3d_load_mesh(file_path)

    def model3d_cut_mesh(self, file_path: str, axis: str, position_ratio: float, output_path: str, cap: bool = True) -> dict[str, Any]:
        try:
            model = model_ops.load(file_path)
            verts, _ = model_ops.tessellated_preview(model)
            bmin = np.min(verts, axis=0)
            bmax = np.max(verts, axis=0)

            ratio = max(0.01, min(0.99, float(position_ratio)))
            ax = axis.lower().strip()
            if ax == "x":
                normal = (1.0, 0.0, 0.0)
                origin = (bmin[0] + (bmax[0] - bmin[0]) * ratio, 0.0, 0.0)
            elif ax == "y":
                normal = (0.0, 1.0, 0.0)
                origin = (0.0, bmin[1] + (bmax[1] - bmin[1]) * ratio, 0.0)
            else:
                normal = (0.0, 0.0, 1.0)
                origin = (0.0, 0.0, bmin[2] + (bmax[2] - bmin[2]) * ratio)

            piece_a, _ = model_ops.cut(model, origin, normal, cap=cap)
            fmt = os.path.splitext(output_path)[1].lstrip(".").lower() or "stl"
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            model_ops.export(piece_a, output_path, fmt)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def model3d_repair_mesh(self, file_path: str, output_path: str) -> dict[str, Any]:
        try:
            model = model_ops.load(file_path)
            repaired = model_ops.repair(model)
            fmt = os.path.splitext(output_path)[1].lstrip(".").lower() or "stl"
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            model_ops.export(repaired, output_path, fmt)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def model3d_scale_mesh(self, file_path: str, scale_factor: float, output_path: str) -> dict[str, Any]:
        try:
            model = model_ops.load(file_path)
            scaled = model_ops.scale(model, scale_factor)
            fmt = os.path.splitext(output_path)[1].lstrip(".").lower() or "stl"
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            model_ops.export(scaled, output_path, fmt)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def model3d_export(self, file_path: str, output_path: str, target_fmt: str) -> dict[str, Any]:
        try:
            model = model_ops.load(file_path)
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            model_ops.export(model, output_path, target_fmt)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def model3d_measure(self, point_a: list[float], point_b: list[float]) -> dict[str, Any]:
        try:
            pt_a = (float(point_a[0]), float(point_a[1]), float(point_a[2]))
            pt_b = (float(point_b[0]), float(point_b[1]), float(point_b[2]))
            dist = model_ops.measure_distance(pt_a, pt_b)
            return {"success": True, "distance": dist}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # Universal Converter operations
    def converter_available_targets(self, extension: str) -> list[str]:
        path = f"file{extension}" if extension.startswith(".") else f"file.{extension}"
        return available_targets(path)

    def convert_file(self, source_path: str, arg2: str, arg3: str, dpi: int = 144) -> dict[str, Any]:
        try:
            # Handle (source_path, target_format, output_dir) and (source_path, output_dir, target_format)
            if any(sep in arg3 for sep in ("/", "\\", ":")) or os.path.isdir(arg3):
                target_format = arg2
                output_dir = arg3
            elif any(sep in arg2 for sep in ("/", "\\", ":")) or os.path.isdir(arg2):
                output_dir = arg2
                target_format = arg3
            elif len(arg2) <= 8 and not os.path.isdir(arg2):
                target_format = arg2
                output_dir = arg3
            else:
                output_dir = arg2
                target_format = arg3
            out_files = convert_file(source_path, output_dir, target_format, dpi=dpi)
            out_p = out_files[0] if out_files else output_dir
            return {"success": True, "output_path": out_p, "output_files": out_files}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def converter_convert_file(self, source_path: str, arg2: str, arg3: str) -> dict[str, Any]:
        return self.convert_file(source_path, arg2, arg3)

    def converter_batch(self, file_paths: list[str], target_format: str, output_dir: str) -> dict[str, Any]:
        try:
            items = [BatchConversionItem(input_path=p, target_format=target_format) for p in file_paths]
            summary = batch_convert_files(items, output_dir=output_dir)
            return {"success": True, "converted": len(summary), "output_dir": output_dir}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # Hash and Checksum operations
    def compute_file_hash(self, file_path: str, algorithm: str = "sha256") -> dict[str, Any]:
        try:
            val = hash_file(file_path, algorithm=algorithm)
            return {"hash": val, "algorithm": algorithm}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def compute_hash(self, file_path: str, algorithm: str = "sha256") -> dict[str, Any]:
        return self.compute_file_hash(file_path, algorithm=algorithm)

    def compute_text_hash(self, text: str, algorithm: str = "sha256") -> dict[str, Any]:
        try:
            val = hash_text(text, algorithm=algorithm)
            return {"hash": val, "algorithm": algorithm}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def hash_text(self, text: str, algorithm: str = "sha256") -> dict[str, Any]:
        return self.compute_text_hash(text, algorithm=algorithm)

    def verify_checksum(self, file_path: str, expected_hash: str, algorithm: str = "") -> dict[str, Any]:
        try:
            exp = expected_hash.strip()
            algo = algorithm.lower().strip() if algorithm else infer_algorithm_from_digest_length(len(exp))
            actual = hash_file(file_path, algorithm=algo)
            match = actual.lower() == exp.lower()
            return {
                "match": match,
                "matches": match,
                "actual": actual,
                "computed": actual,
                "expected": expected_hash,
                "algorithm": algo,
            }
        except Exception as exc:  # noqa: 23
            return {"error": str(exc), "match": False, "matches": False}

    def verify_hash(self, file_path: str, expected_hash: str, algorithm: str = "") -> dict[str, Any]:
        return self.verify_checksum(file_path, expected_hash, algorithm=algorithm)

    def generate_manifest(self, dir_path: str, algorithm: str = "sha256", output_path: str = "") -> dict[str, Any]:
        try:
            out = output_path or os.path.join(dir_path, f"checksums_{algorithm}.txt")
            generate_checksum_manifest(dir_path, out, algorithm=algorithm)
            cnt = 0
            if os.path.exists(out):
                with open(out, "r", encoding="utf-8", errors="replace") as f:
                    cnt = sum(1 for line in f if line.strip() and not line.startswith("#"))
            return {"success": True, "manifest_path": out, "file_count": cnt}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def verify_manifest(self, arg1: str, arg2: str) -> dict[str, Any]:
        try:
            if os.path.isfile(arg1) and (os.path.isdir(arg2) or not os.path.isfile(arg2)):
                manifest_path = arg1
                dir_path = arg2
            else:
                dir_path = arg1
                manifest_path = arg2
            res = verify_checksum_manifest(manifest_path, base_dir=dir_path)
            all_match = (res.get("failed", 0) == 0 and res.get("missing", 0) == 0 and res.get("total", 0) > 0)
            mismatches = [r for r in res.get("results", []) if r.get("status") != "PASS"]
            return {
                "success": True,
                "results": res,
                "matches": all_match,
                "mismatches": mismatches,
                "passed": res.get("passed", 0),
                "failed": res.get("failed", 0),
                "missing": res.get("missing", 0),
                "total": res.get("total", 0),
            }
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def verify_checksum_manifest(self, dir_path: str, manifest_path: str) -> dict[str, Any]:
        return self.verify_manifest(dir_path, manifest_path)

    # QR & Barcode operations
    def generate_qr(self, text: str, arg2: Any = "M", arg3: Any = "#000000", arg4: Any = "#ffffff", arg5: Any = 10, arg6: Any = 4) -> dict[str, Any]:
        try:
            # Handle (text, level, box_size, border, fg, bg) and (text, level, fg, bg, box_size, border)
            if isinstance(arg3, (int, float)) or (isinstance(arg3, str) and arg3.isdigit()):
                box_size = int(arg3)
                border = int(arg4)
                fg_color = str(arg5)
                bg_color = str(arg6)
                error_level = str(arg2)
            else:
                error_level = str(arg2)
                fg_color = str(arg3)
                bg_color = str(arg4)
                box_size = int(arg5)
                border = int(arg6)
            img = generate_qr_code(
                payload=text,
                error_correction=error_level,
                fill_color=fg_color,
                back_color=bg_color,
                box_size=box_size,
                border=border,
            )
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return {"data_url": f"data:image/png;base64,{b64}"}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def generate_qr_svg(self, text: str, arg2: Any = "M", arg3: Any = "#000000", arg4: Any = "#ffffff", arg5: Any = 10, arg6: Any = 4) -> dict[str, Any]:
        try:
            if isinstance(arg3, (int, float)) or (isinstance(arg3, str) and arg3.isdigit()):
                box_size = int(arg3)
                border = int(arg4)
                fg_color = str(arg5)
                bg_color = str(arg6)
                error_level = str(arg2)
            else:
                error_level = str(arg2)
                fg_color = str(arg3)
                bg_color = str(arg4)
                box_size = int(arg5)
                border = int(arg6)
            svg_content = generate_qr_svg(
                payload=text,
                error_correction=error_level,
                box_size=box_size,
                border=border,
                fill_color=fg_color,
                back_color=bg_color,
            )
            return {"svg": svg_content}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def generate_barcode(self, text: str, barcode_type: str = "code128", include_label: bool = True, fg_color: str = "#000000", bg_color: str = "#ffffff") -> dict[str, Any]:
        try:
            img = generate_barcode(text, barcode_type=barcode_type)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return {"data_url": f"data:image/png;base64,{b64}"}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def decode_qr(self, image_path: str) -> dict[str, Any]:
        try:
            results = decode_qr_and_barcodes(image_path)
            codes = [{"payload": r["payload"], "data": r["payload"], "type": r["type"]} for r in results]
            return {"results": codes, "codes": codes}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # Data & Structured JSON operations
    def format_json(self, raw_text: str, indent: int = 2) -> dict[str, Any]:
        try:
            parsed = json.loads(raw_text)
            return {"formatted": json.dumps(parsed, indent=indent)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def minify_json(self, raw_text: str) -> dict[str, Any]:
        try:
            return {"minified": ops_minify_json(raw_text)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def validate_json(self, raw_text: str) -> dict[str, Any]:
        try:
            json.loads(raw_text)
            return {"valid": True, "message": "Valid JSON syntax."}
        except json.JSONDecodeError as exc:
            return {"valid": False, "message": f"Syntax Error on line {exc.lineno}, col {exc.colno}: {exc.msg}"}
        except Exception as exc:  # noqa: 23
            return {"valid": False, "message": str(exc)}

    def convert_data_format(self, raw_text: str, source_fmt: str, target_fmt: str) -> dict[str, Any]:
        try:
            result = ops_convert_data(raw_text, source_fmt, target_fmt)
            return {"converted": result, "output": result}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def query_jsonpath(self, raw_text: str, path: str) -> dict[str, Any]:
        try:
            data = json.loads(raw_text)
            results = ops_query_jsonpath(data, path)
            return {"results": results, "result": results}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def infer_json_schema(self, raw_text: str) -> dict[str, Any]:
        try:
            data = json.loads(raw_text)
            schema = ops_infer_schema(data)
            return {"schema": schema}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def format_code(self, raw_text: str, lang: str) -> dict[str, Any]:
        try:
            formatter = {
                "css": format_css,
                "javascript": format_javascript,
                "js": format_javascript,
                "sql": format_sql,
                "xml": format_xml,
                "yaml": format_yaml,
            }.get(lang.lower())
            if not formatter:
                return {"error": f"Unsupported language: {lang}"}
            return {"formatted": formatter(raw_text)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def format_sql(self, raw_text: str) -> dict[str, Any]:
        return self.format_code(raw_text, "sql")

    def format_css(self, raw_text: str) -> dict[str, Any]:
        return self.format_code(raw_text, "css")

    def format_javascript(self, raw_text: str) -> dict[str, Any]:
        return self.format_code(raw_text, "javascript")

    def format_js(self, raw_text: str) -> dict[str, Any]:
        return self.format_javascript(raw_text)

    def format_xml(self, raw_text: str) -> dict[str, Any]:
        return self.format_code(raw_text, "xml")

    def format_yaml(self, raw_text: str) -> dict[str, Any]:
        return self.format_code(raw_text, "yaml")

    # Text tools operations
    def text_case_transform(self, text: str, mode: str) -> dict[str, Any]:
        try:
            fn = {
                "upper": to_uppercase,
                "lower": to_lowercase,
                "title": to_title_case,
                "camel": to_camel_case,
                "snake": to_snake_case,
                "kebab": to_kebab_case,
                "constant": to_constant_case,
                "sentence": to_sentence_case,
            }.get(mode.lower())
            if not fn:
                return {"error": f"Unsupported mode: {mode}"}
            return {"result": fn(text)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def text_line_ops(self, text: str, op: str) -> dict[str, Any]:
        try:
            if op == "sort":
                return {"result": sort_lines(text)}
            if op == "dedupe":
                return {"result": dedupe_lines(text)}
            if op == "reverse":
                return {"result": reverse_lines(text)}
            if op == "remove_blank":
                lines = [line for line in text.splitlines() if line.strip()]
                return {"result": "\n".join(lines)}
            if op == "number":
                lines = [f"{i + 1}. {line}" for i, line in enumerate(text.splitlines())]
                return {"result": "\n".join(lines)}
            return {"error": f"Unknown line operation: {op}"}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def text_regex_replace(self, text: str, pattern: str, replacement: str) -> dict[str, Any]:
        try:
            return {"result": re.sub(pattern, replacement, text)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def text_diff(self, text1: str, text2: str) -> dict[str, Any]:
        try:
            lines1 = text1.splitlines(keepends=True)
            lines2 = text2.splitlines(keepends=True)
            diff = "".join(difflib.unified_diff(lines1, lines2, fromfile="Original", tofile="Modified"))
            return {"diff": diff or "Texts are identical."}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # Word counter operations
    def word_counter_analyze(self, text: str) -> dict[str, Any]:
        try:
            return analyze_text(text)
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def word_counter_analyze_file(self, file_path: str) -> dict[str, Any]:
        try:
            text = extract_text_from_file(file_path)
            res = dict(analyze_text(text))
            res["file_path"] = file_path
            res["text"] = text
            return res
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def word_counter_generate_report(self, text: str) -> dict[str, Any]:
        try:
            stats = analyze_text(text)
            report = generate_report(stats)
            return {"stats": stats, "report": report}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # Metadata operations
    def metadata_inspect(self, file_path: str) -> dict[str, Any]:
        try:
            meta = inspect_metadata(file_path)
            return {"metadata": meta, "fields": meta}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def metadata_strip(self, file_path: str, output_path: str) -> dict[str, Any]:
        try:
            strip_metadata(file_path, output_path)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def metadata_export(self, file_path: str, output_path: str) -> dict[str, Any]:
        try:
            export_metadata(file_path, output_path)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # Batch Renamer operations
    def renamer_preview(self, file_paths: list[str], pattern: Any = "", replace: str = "", mode: str = "find_replace", prefix: str = "", suffix: str = "", start_num: int = 1, step: int = 1, case_sensitive: bool = True, use_regex: bool = False, include_ext: bool = False, padding: int = 3, keep_name: bool = False, case_type: str = "upper", new_ext: str = "") -> dict[str, Any]:
        try:
            if isinstance(pattern, dict):
                d = pattern
                mode = d.get("mode", "find_replace")
                replace = d.get("replace", "")
                prefix = d.get("prefix", "")
                suffix = d.get("suffix", "")
                start_num = d.get("start_num", 1)
                step = d.get("step", 1)
                padding = d.get("pad", 3)
                case_sensitive = d.get("case_sensitive", True)
                use_regex = d.get("is_regex", False)
                include_ext = d.get("include_ext", False)
                case_type = d.get("case_transform", "upper")
                new_ext = d.get("new_ext", "")
                num_style = d.get("num_style", "")
                pattern = d.get("find", "")
            else:
                num_style = ""
            mode_map = {
                "replace": "find_replace",
                "prefix": "prefix_suffix",
                "number": "numbering",
                "case": "change_case",
                "ext": "extension",
            }
            m = mode_map.get(mode, mode)
            params = {
                "find": pattern,
                "replace": replace,
                "prefix": prefix,
                "suffix": suffix,
                "start": start_num,
                "step": step,
                "case_sensitive": case_sensitive,
                "use_regex": use_regex,
                "include_extension": include_ext,
                "padding": padding,
                "keep_name": keep_name,
                "case_type": case_type,
                "new_extension": new_ext,
                "num_style": num_style,
            }
            plan = preview_renames(file_paths, mode=m, params=params)
            preview_items = [
                {
                    "src": item.old_path,
                    "dst": item.new_path,
                    "original": item.old_path,
                    "target": item.new_path,
                    "status": item.error or "ok",
                }
                for item in plan
            ]
            self._last_renames = [{"src": it["src"], "dst": it["dst"]} for it in preview_items if it["status"] == "ok"]
            return {"preview": preview_items}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def renamer_execute(self, rename_items: list[dict[str, str]]) -> dict[str, Any]:
        try:
            plans = [
                RenamePlan(
                    old_path=item["src"],
                    old_name=os.path.basename(item["src"]),
                    new_name=os.path.basename(item["dst"]),
                    new_path=item["dst"],
                )
                for item in rename_items
            ]
            results = execute_renames(plans)
            self._last_undo_pairs = [{"src": r.old_path, "dst": r.new_path} for r in results if r.success]
            return {"success": True, "count": len(results), "results": [{"src": r.old_path, "dst": r.new_path, "success": r.success, "error": r.error} for r in results]}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def renamer_apply(self, rename_items: list[dict[str, str]] | None = None) -> dict[str, Any]:
        items = rename_items if rename_items is not None else self._last_renames
        if not items:
            return {"error": "No rename operations pending."}
        return self.renamer_execute(items)

    def renamer_undo(self, rename_pairs: list[dict[str, str]] | None = None) -> dict[str, Any]:
        try:
            pairs_source = rename_pairs if rename_pairs is not None else self._last_undo_pairs
            if not pairs_source:
                return {"error": "No previous rename operation to undo."}
            pairs = [(item["src"], item["dst"]) for item in pairs_source]
            reverse_pairs = undo_renames(pairs)
            plans = [
                RenamePlan(
                    old_path=dst,
                    old_name=os.path.basename(dst),
                    new_name=os.path.basename(src),
                    new_path=src,
                )
                for dst, src in reverse_pairs
            ]
            results = execute_renames(plans)
            self._last_undo_pairs = []
            return {
                "success": True,
                "count": len(results),
                "results": [{"src": r.old_path, "dst": r.new_path, "success": r.success, "error": r.error} for r in results],
            }
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # Markdown studio operations
    def markdown_to_html(self, raw_markdown: str) -> dict[str, Any]:
        try:
            html = render_markdown_to_html(raw_markdown)
            return {"html": html}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def render_markdown(self, raw_markdown: str) -> dict[str, Any]:
        return self.markdown_to_html(raw_markdown)

    def markdown_export_html(self, raw_markdown: str, output_path: str) -> dict[str, Any]:
        try:
            body = render_markdown_to_html(raw_markdown)
            full_html = (
                "<!DOCTYPE html>\n<html>\n<head>\n<meta charset='utf-8'>\n"
                "<title>Markdown Document</title>\n"
                "<style>body{font-family:sans-serif;max-width:800px;margin:40px auto;line-height:1.6;color:#1e293b;padding:0 20px;}</style>\n"
                f"</head>\n<body>\n{body}\n</body>\n</html>"
            )
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_html)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def markdown_export_pdf(self, raw_markdown: str, output_path: str) -> dict[str, Any]:
        try:
            html = render_markdown_to_html(raw_markdown)
            doc = pymupdf.open()
            page = doc.new_page(width=595, height=842)
            rect = pymupdf.Rect(40, 40, 555, 802)
            page.insert_htmlbox(rect, html)
            doc.save(output_path)
            doc.close()
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # Palette operations
    def palette_extract(self, file_path: str, num_colors: int = 6) -> dict[str, Any]:
        try:
            img = Image.open(file_path)
            swatches = extract_palette(img, n_colors=num_colors)
            colors = [{"hex": s.hex_code, "name": s.name, "percentage": s.percentage, "rgb": list(s.rgb)} for s in swatches]
            return {"palette": colors, "colors": colors}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def palette_export_gpl(self, colors: list[dict[str, Any]], palette_name: str = "FOSSEverything") -> dict[str, Any]:
        try:
            output_path = ""
            name = palette_name
            if palette_name.lower().endswith(".gpl") or os.sep in palette_name or "/" in palette_name:
                output_path = palette_name
                name = os.path.splitext(os.path.basename(palette_name))[0]
            lines = ["GIMP Palette", f"Name: {name}", "#", "# Columns: 4"]
            for c in colors:
                rgb = c.get("rgb", [0, 0, 0])
                color_name = c.get("name") or c.get("hex", "Color")
                lines.append(f"{rgb[0]:3d} {rgb[1]:3d} {rgb[2]:3d} {color_name}")
            gpl_text = "\n".join(lines)
            if output_path:
                target_dir = os.path.dirname(os.path.abspath(output_path))
                if target_dir:
                    os.makedirs(target_dir, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(gpl_text)
            return {"success": True, "gpl": gpl_text, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # Photo Collage operations
    def collage_create(self, file_paths: list[str], output_path: str = "", columns: int = 2, spacing: int = 12, bg_color: str = "#0f172a", radius: int = 0, aspect: str = "square") -> dict[str, Any]:
        try:
            rgb = _hex_to_rgb_int(bg_color)
            thumb_w = 400
            thumb_h = 400
            if aspect == "4:3":
                thumb_w, thumb_h = 400, 300
            elif aspect == "16:9":
                thumb_w, thumb_h = 400, 225
            elif aspect == "3:4":
                thumb_w, thumb_h = 300, 400
            elif ":" in aspect:
                parts = aspect.split(":")
                w_ratio = float(parts[0])
                h_ratio = float(parts[1])
                if w_ratio >= h_ratio:
                    thumb_w = 400
                    thumb_h = max(1, int(round(400 * h_ratio / w_ratio)))
                else:
                    thumb_h = 400
                    thumb_w = max(1, int(round(400 * w_ratio / h_ratio)))

            cfg = CollageConfig(
                cols=columns,
                thumb_width=thumb_w,
                thumb_height=thumb_h,
                padding=spacing,
                bg_color=rgb,
                corner_radius=radius,
            )
            img = make_collage(file_paths, config=cfg)
            res: dict[str, Any] = {"success": True}
            if output_path:
                ext = os.path.splitext(output_path)[1].lstrip(".").upper() or "PNG"
                fmt = "JPEG" if ext in ("JPG", "JPEG") else "PNG"
                if fmt == "JPEG" and img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")
                img.save(output_path, format=fmt)
                res["output_path"] = output_path
            res["data_url"] = _img_to_data_url(img)
            return res
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def collage_preview(self, file_paths: list[str], columns: int = 2, spacing: int = 12, bg_color: str = "#0f172a", radius: int = 0, aspect: str = "square") -> dict[str, Any]:
        return self.collage_create(file_paths, "", columns=columns, spacing=spacing, bg_color=bg_color, radius=radius, aspect=aspect)

    # Encoding operations
    def encoding_transform(self, text: str, method: str, action: str) -> dict[str, Any]:
        try:
            m = method.lower().strip()
            a = action.lower().strip()
            if m == "base64":
                res = base64_encode_text(text) if a == "encode" else base64_decode_text(text)
            elif m == "url":
                res = url_encode(text) if a == "encode" else url_decode(text)
            elif m == "html":
                res = html_encode(text) if a == "encode" else html_decode(text)
            elif m == "hex":
                res = hex_encode_text(text) if a == "encode" else hex_decode_text(text)
            elif m == "binary":
                res = binary_encode_bytes(text.encode("utf-8")) if a == "encode" else binary_decode_to_bytes(text).decode("utf-8", errors="replace")
            else:
                return {"error": f"Unknown encoding method: {method}"}
            return {"result": res}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # OCR operations
    def ocr_image(self, file_path: str, language: str = "eng") -> dict[str, Any]:
        try:
            res = ocr_file(file_path, language=language)
            text = res.get("text", "")
            words = len(text.split()) if text else 0
            return {
                "success": True,
                "text": text,
                "word_count": words,
                "confidence": res.get("confidence", 95),
            }
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def ocr_languages(self) -> list[str]:
        try:
            langs = get_supported_languages()
            if isinstance(langs, dict):
                return list(langs.keys())
            if isinstance(langs, list):
                return langs
            return ["eng"]
        except Exception:  # noqa: 23
            return ["eng"]

    def ocr_create_searchable_pdf(self, file_path: str, output_path: str, language: str = "eng", dpi: int = 150) -> dict[str, Any]:
        try:
            ops_create_searchable_pdf(file_path, output_path, language=language, dpi=dpi)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # Archive operations
    def archive_create(self, file_paths: list[str] | str, output_path: str, fmt: str = "zip") -> dict[str, Any]:
        try:
            if isinstance(file_paths, str):
                create_archive(file_paths, output_path, archive_format=fmt)
            elif len(file_paths) == 1:
                create_archive(file_paths[0], output_path, archive_format=fmt)
            else:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                if fmt in ("tar", "tar.gz"):
                    import tarfile
                    mode = "w:gz" if fmt == "tar.gz" else "w"
                    with tarfile.open(output_path, mode) as tf:
                        for p in file_paths:
                            tf.add(p, arcname=os.path.basename(p))
                else:
                    import zipfile
                    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                        for p in file_paths:
                            zf.write(p, arcname=os.path.basename(p))
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def archive_extract(self, archive_path: str, output_dir: str) -> dict[str, Any]:
        try:
            extract_archive(archive_path, output_dir)
            return {"success": True, "output_dir": output_dir}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def archive_list(self, archive_path: str) -> dict[str, Any]:
        try:
            ext = os.path.splitext(archive_path)[1].lower()
            items = []
            if ext == ".zip":
                import zipfile
                with zipfile.ZipFile(archive_path, "r") as zf:
                    for info in zf.infolist():
                        items.append({"path": info.filename, "size": info.file_size})
            elif ext in (".tar", ".gz", ".tgz"):
                import tarfile
                mode = "r:gz" if ext in (".gz", ".tgz") else "r"
                with tarfile.open(archive_path, mode) as tf:
                    for member in tf.getmembers():
                        items.append({"path": member.name, "size": member.size})
            else:
                names = list_archive_contents(archive_path)
                items = [{"path": name, "size": 0} for name in names]
            return {"success": True, "items": items, "entries": [it["path"] for it in items]}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def archive_test(self, archive_path: str) -> dict[str, Any]:
        try:
            res = test_archive(archive_path)
            if res.get("valid"):
                count = res.get("count", 0)
                msg = f"Archive integrity verified ({count} entries checked, no corruption detected)."
                return {"success": True, "message": msg, "details": res}
            err = res.get("error", "Archive verification failed.")
            return {"success": False, "error": err}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # Office operations
    def office_extract(self, file_path: str) -> dict[str, Any]:
        try:
            text = extract_text_from_office(file_path)
            return {"success": True, "text": text}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def office_docx_to_pdf(self, input_path: str, output_path: str) -> dict[str, Any]:
        try:
            docx_to_pdf(input_path, output_path)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def office_docx_to_markdown(self, input_path: str, output_path: str = "") -> dict[str, Any]:
        try:
            md = docx_to_markdown(input_path)
            if output_path:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(md)
            return {"success": True, "markdown": md, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def office_pptx_to_markdown(self, input_path: str, output_path: str = "") -> dict[str, Any]:
        try:
            md = pptx_to_markdown(input_path)
            if output_path:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(md)
            return {"success": True, "markdown": md, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def office_xlsx_to_csv(self, input_path: str, output_path: str) -> dict[str, Any]:
        try:
            xlsx_to_csv(input_path, output_path)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    # Screen Capture operations
    def screenshot_capture_full(self) -> dict[str, Any]:
        try:
            img = capture_full_screen()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return {"success": True, "data_url": f"data:image/png;base64,{b64}"}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def capture_screen(self) -> dict[str, Any]:
        return self.screenshot_capture_full()

    # Network Monitor operations
    def network_get_connections(self) -> dict[str, Any]:
        results = []
        try:
            try:
                conns = psutil.net_connections(kind="inet")
            except (psutil.AccessDenied, PermissionError):
                conns = []
                for proc in psutil.process_iter(["pid"]):
                    try:
                        conns.extend(proc.net_connections(kind="inet"))
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
            for conn in conns:
                proc_name = "System"
                if conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        proc_name = proc.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        proc_name = f"PID {conn.pid}"
                l_ip = conn.laddr.ip if conn.laddr else "-"
                l_port = conn.laddr.port if conn.laddr else 0
                r_ip = conn.raddr.ip if conn.raddr else ""
                r_port = conn.raddr.port if conn.raddr else 0
                proto = "TCP" if conn.type == 1 else "UDP"
                results.append({
                    "pid": conn.pid or 0,
                    "process": proc_name,
                    "process_name": proc_name,
                    "local": f"{l_ip}:{l_port}",
                    "remote": f"{r_ip}:{r_port}" if r_ip else "-",
                    "local_address": l_ip,
                    "local_port": l_port,
                    "remote_address": r_ip,
                    "remote_port": r_port,
                    "protocol": proto,
                    "type": proto,
                    "status": conn.status,
                })
        except Exception:  # noqa: 23
            pass
        return {"connections": results}

    def get_network_connections(self) -> dict[str, Any]:
        return self.network_get_connections()

    # Playlist operations
    def playlist_fetch(self, url: str) -> dict[str, Any]:
        cleaned = clean_music_title(url)
        return {"title": cleaned}

    # Resume Builder operations
    def resume_sample(self) -> dict[str, Any]:
        master = create_sample_master_resume()
        return resume_to_dict(master)

    def resume_load_file(self, file_path: str) -> dict[str, Any]:
        try:
            master = load_resume_file(file_path)
            return {"success": True, "resume": resume_to_dict(master)}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def resume_save_file(self, resume_data: dict[str, Any], file_path: str) -> dict[str, Any]:
        try:
            master = resume_from_dict(resume_data)
            save_resume_file(master, file_path)
            return {"success": True, "output_path": file_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def resume_render_html(self, resume_data: dict[str, Any], layout: str = "dual-column", theme: str = "modern") -> dict[str, Any]:
        try:
            master = resume_from_dict(resume_data)
            html = resume_export_html(master, theme=theme, layout=layout)
            return {"html": html}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def resume_analyze_ats(self, resume_data: dict[str, Any], job_description: str) -> dict[str, Any]:
        try:
            master = resume_from_dict(resume_data)
            res = analyze_ats_match(master, job_description)
            res["matched_keywords"] = res.get("matched", [])
            res["missing_keywords"] = res.get("missing", [])
            return res
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def resume_export_pdf(self, resume_data: dict[str, Any], output_path: str, theme: str = "modern") -> dict[str, Any]:
        try:
            master = resume_from_dict(resume_data)
            resume_export_pdf(master, output_path, theme=theme)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def resume_export_docx(self, resume_data: dict[str, Any], output_path: str, theme: str = "modern") -> dict[str, Any]:
        try:
            master = resume_from_dict(resume_data)
            resume_export_docx(master, output_path, theme=theme)
            return {"success": True, "output_path": output_path}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def resume_export_markdown(self, resume_data: dict[str, Any]) -> dict[str, Any]:
        try:
            master = resume_from_dict(resume_data)
            md = resume_export_markdown(master)
            return {"markdown": md}
        except Exception as exc:  # noqa: 23
            return {"error": str(exc)}

    def ping(self) -> str:
        return "pong"
