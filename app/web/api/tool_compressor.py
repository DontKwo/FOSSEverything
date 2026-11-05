from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

from app.features.archive.ops import create_multi_source_archive, extract_archive
from app.features.media.ops import compress_media
from app.features.pdf.ops import compress_pdf
from app.web.api.result import api_method, ok, require

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".gif", ".avif"}
PDF_EXTENSIONS = {".pdf"}
MEDIA_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz"}
TEXT_EXTENSIONS = {".txt", ".csv", ".json", ".xml", ".html", ".htm", ".md", ".log", ".yaml", ".yml", ".ini", ".py", ".js", ".css"}
IMAGE_KEEP_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
PROFILE_ORDER = ("light", "balanced", "aggressive")
ESTIMATE_RATIOS: dict[str, tuple[float, float, float]] = {
    "PDF": (0.10, 0.25, 0.45),
    "Image": (0.12, 0.30, 0.50),
    "PNG": (0.30, 0.45, 0.60),
    "PNG_LOSSLESS": (0.05, 0.08, 0.10),
    "Media": (0.20, 0.40, 0.65),
    "Archive": (0.02, 0.05, 0.08),
    "Text": (0.55, 0.65, 0.70),
    "General": (0.03, 0.05, 0.08),
}


def _detect_compressor_category(path_str: str) -> str:
    # Classify file extension into compression family.
    ext = Path(path_str).suffix.lower()
    if ext in PDF_EXTENSIONS:
        return "PDF"
    if ext in IMAGE_EXTENSIONS:
        return "Image"
    if ext in MEDIA_EXTENSIONS:
        return "Media"
    if ext in ARCHIVE_EXTENSIONS:
        return "Archive"
    return "General"


def _output_suffix(category: str, src_suffix: str) -> str:
    # Extension of the file the compressor writes for this category and source.
    suffix = src_suffix.lower()
    if category == "Image":
        return suffix if suffix in IMAGE_KEEP_EXTENSIONS else ".jpg"
    if category in ("PDF", "Media"):
        return suffix
    return ".zip"


def _estimate_ratio(category: str, suffix: str, preset: str, lossy_png: bool) -> float:
    # Expected fraction of bytes removed for a category under one profile.
    ext = suffix.lower()
    if category == "Image" and ext == ".png":
        key = "PNG" if lossy_png else "PNG_LOSSLESS"
    elif category == "General" and ext in TEXT_EXTENSIONS:
        key = "Text"
    else:
        key = category if category in ESTIMATE_RATIOS else "General"
    index = PROFILE_ORDER.index(preset) if preset in PROFILE_ORDER else 1
    return ESTIMATE_RATIOS[key][index]


def _compress_image_file(
    in_path: str,
    out_path: str,
    preset: str = "balanced",
    lossy_png: bool = True,
    png_colors: int = 128,
    max_dimension: int | None = None,
) -> str:
    # Compress image with quality optimization and optional PNG quantization.
    img = Image.open(in_path)
    if max_dimension and max_dimension > 0:
        width, height = img.size
        if width > max_dimension or height > max_dimension:
            ratio = min(max_dimension / width, max_dimension / height)
            new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

    ext = Path(in_path).suffix.lower()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    if ext == ".png":
        if lossy_png:
            colors = max(16, min(256, png_colors))
            q_img = img.quantize(colors=colors, method=Image.Quantize.FASTOCTREE)
            q_img.save(out_path, format="PNG", optimize=True, compress_level=9)
        else:
            img.save(out_path, format="PNG", optimize=True, compress_level=9)
    elif ext in (".jpg", ".jpeg"):
        quality = 65 if preset == "aggressive" else (85 if preset == "light" else 75)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(out_path, format="JPEG", quality=quality, optimize=True)
    elif ext == ".webp":
        quality = 60 if preset == "aggressive" else (85 if preset == "light" else 75)
        img.save(out_path, format="WEBP", quality=quality, method=6)
    else:
        # Default fallback to WebP or optimized PNG
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(out_path, format="JPEG", quality=75, optimize=True)
    return out_path


def _repack_or_compress_archive(in_path: str, out_path: str) -> str:
    # Repack archive entries at level 9 without double-nesting.
    ext = Path(in_path).suffix.lower()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    if ext in ARCHIVE_EXTENSIONS:
        with tempfile.TemporaryDirectory(prefix="repack_") as tmp_dir:
            extract_archive(in_path, tmp_dir)
            entries = [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir)]
            if not entries:
                entries = [tmp_dir]
            create_multi_source_archive(entries, out_path, fmt="zip", compression_level=9)
    else:
        create_multi_source_archive([in_path], out_path, fmt="zip", compression_level=9)
    return out_path


class CompressorApiMixin:
    @api_method
    def compressor_scan_inputs(self, params: dict[str, Any]) -> dict[str, Any]:
        # Expand mixed file and folder paths into compressible queue items.
        require(params, "paths")
        raw_paths = list(params["paths"])
        recursive = bool(params.get("recursive", True))

        discovered: list[dict[str, Any]] = []
        visited: set[str] = set()

        def _evaluate_file(f_path: Path, rel_dir: str) -> None:
            resolved = str(f_path.resolve())
            if resolved in visited or not f_path.is_file():
                return
            visited.add(resolved)
            if f_path.name.startswith(".") or f_path.name.startswith("~$"):
                return
            cat = _detect_compressor_category(str(f_path))
            discovered.append({
                "path": str(f_path),
                "name": f_path.name,
                "rel_dir": rel_dir,
                "size_bytes": f_path.stat().st_size,
                "category": cat,
                "output_ext": _output_suffix(cat, f_path.suffix),
            })

        for p_str in raw_paths:
            p = Path(p_str)
            if not p.exists():
                continue
            if p.is_file():
                _evaluate_file(p, "")
            elif p.is_dir():
                if recursive:
                    for root, dirs, files in os.walk(p):
                        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", ".venv", "__pycache__", "node_modules")]
                        rel = os.path.relpath(root, p)
                        rel_dir = "" if rel == "." else rel
                        for f_name in sorted(files):
                            _evaluate_file(Path(root) / f_name, rel_dir)
                else:
                    for entry in sorted(p.iterdir()):
                        if entry.is_file():
                            _evaluate_file(entry, "")

        return ok(items=discovered, total=len(discovered))

    @api_method
    def compressor_estimate_savings(self, params: dict[str, Any]) -> dict[str, Any]:
        # Estimate bytes saved per item and in total for a profile before running.
        require(params, "items")
        raw_items = list(params["items"])
        preset = str(params.get("preset", "balanced")).lower()
        lossy_png = bool(params.get("lossy_png", True))

        rows: list[dict[str, Any]] = []
        total_orig = 0
        total_saved = 0
        for item in raw_items:
            in_p = str(item.get("path") or item.get("file_path") or item.get("input_path", ""))
            if not os.path.isfile(in_p):
                continue
            orig_size = os.path.getsize(in_p)
            cat = str(item.get("category") or _detect_compressor_category(in_p))
            ratio = _estimate_ratio(cat, Path(in_p).suffix, preset, lossy_png)
            saved_b = int(orig_size * ratio)
            rows.append({
                "path": in_p,
                "original_bytes": orig_size,
                "estimated_bytes": orig_size - saved_b,
                "saved_bytes": saved_b,
                "saved_pct": round(ratio * 100.0, 1),
            })
            total_orig += orig_size
            total_saved += saved_b

        total_pct = round((total_saved / total_orig) * 100.0, 1) if total_orig > 0 else 0.0
        return ok(
            results=rows,
            total_original_bytes=total_orig,
            total_estimated_bytes=total_orig - total_saved,
            total_saved_bytes=total_saved,
            total_saved_pct=total_pct,
        )

    @api_method
    def compressor_compress_items(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compress queue items across PDF, Image, Media, and Archive categories.
        require(params, "items")
        raw_items = list(params["items"])
        preset = str(params.get("preset", "balanced")).lower()
        lossy_png = bool(params.get("lossy_png", True))
        png_colors = int(params.get("png_colors", 128))
        max_dim = int(params.get("max_dimension", 0)) or None
        target_mb = int(params.get("target_size_mb", 0)) or None
        out_dir = str(params.get("output_dir", "")).strip()
        preserve_tree = bool(params.get("preserve_tree", True))

        results: list[dict[str, Any]] = []
        total_orig = 0
        total_comp = 0
        succeeded = 0
        failed = 0

        for item in raw_items:
            in_p = str(item.get("path") or item.get("file_path") or item.get("input_path", ""))
            if not os.path.exists(in_p):
                results.append({"path": in_p, "output_path": "", "ok": False, "error": "File not found"})
                failed += 1
                continue

            orig_size = os.path.getsize(in_p)
            rel_dir = str(item.get("rel_dir", "")).strip()
            cat = str(item.get("category") or _detect_compressor_category(in_p))

            src_path = Path(in_p)
            if item.get("output_path"):
                out_p = str(item["output_path"])
            elif out_dir:
                item_dir = Path(out_dir) / rel_dir if (preserve_tree and rel_dir) else Path(out_dir)
                out_p = str(item_dir / f"{src_path.stem}_compressed{_output_suffix(cat, src_path.suffix)}")
            else:
                out_p = str(src_path.with_name(f"{src_path.stem}_compressed{_output_suffix(cat, src_path.suffix)}"))

            try:
                if cat == "Image":
                    _compress_image_file(
                        in_p,
                        out_p,
                        preset=preset,
                        lossy_png=lossy_png,
                        png_colors=png_colors,
                        max_dimension=max_dim,
                    )
                elif cat == "PDF":
                    lvl = "screen" if preset == "aggressive" else ("printer" if preset == "light" else "ebook")
                    compress_pdf(in_p, out_p, quality=lvl)
                elif cat == "Media":
                    p_val = "small_file" if preset == "aggressive" else ("high_quality" if preset == "light" else "balanced")
                    compress_media(in_p, out_p, preset=p_val)
                else:
                    _repack_or_compress_archive(in_p, out_p)

                comp_size = os.path.getsize(out_p) if os.path.exists(out_p) else orig_size
                saved_b = orig_size - comp_size
                saved_pct = round((saved_b / orig_size) * 100.0, 1) if orig_size > 0 else 0.0

                results.append({
                    "path": in_p,
                    "output_path": out_p,
                    "original_bytes": orig_size,
                    "compressed_bytes": comp_size,
                    "saved_bytes": saved_b,
                    "saved_pct": saved_pct,
                    "ok": True,
                    "error": None,
                })
                total_orig += orig_size
                total_comp += comp_size
                succeeded += 1
            except Exception as exc:
                results.append({
                    "path": in_p,
                    "output_path": "",
                    "original_bytes": orig_size,
                    "compressed_bytes": 0,
                    "saved_bytes": 0,
                    "saved_pct": 0.0,
                    "ok": False,
                    "error": str(exc),
                })
                failed += 1

        total_saved = total_orig - total_comp
        total_pct = round((total_saved / total_orig) * 100.0, 1) if total_orig > 0 else 0.0

        return ok(
            results=results,
            succeeded=succeeded,
            failed=failed,
            total_original_bytes=total_orig,
            total_compressed_bytes=total_comp,
            total_saved_bytes=total_saved,
            total_saved_pct=total_pct,
            summary=f"Compressed {succeeded} of {len(raw_items)} item(s)",
        )

