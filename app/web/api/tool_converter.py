import csv
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import pymupdf as fitz
from PIL import Image
import trimesh
import yaml

from app.features.converter.ops import (
    BatchConversionItem,
    available_targets,
    batch_convert_files,
    conversion_summary,
    convert_file,
    export_enex,
    source_family,
)
from app.features.ocr import ops as ocr_ops
from app.web.api.result import api_method, ok, require

logger = logging.getLogger(__name__)

EXT_IMAGES = {".ico", ".icns", ".tga", ".dds", ".ppm", ".pgm", ".pbm", ".pcx", ".sgi", ".eps"}
EXT_MODELS = {".gltf", ".glb", ".3mf", ".dae", ".off", ".xyz"}
EXT_DATA = {".tsv", ".ndjson", ".ini", ".env", ".properties"}
EXT_DOCS = {".xps", ".oxps", ".cbz", ".cbr", ".rtf", ".html", ".htm", ".rst"}
EXT_SUBS = {".srt", ".vtt"}
EXT_PLAYLISTS = {".m3u", ".m3u8"}
EXT_FONTS = {".ttx"}
EXT_RASTER_QUALITY = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff", ".gif"}
EXT_TEXT = {".txt", ".text", ".md", ".markdown"}


def _parse_data_to_rows(file_path: str, ext: str) -> list[dict[str, Any]]:
    # Parse diverse structured and key-value formats into rows of dictionaries.
    rows: list[dict[str, Any]] = []
    if ext == ".tsv":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f_in:
            tsv_reader = csv.DictReader(f_in, delimiter="\t")
            rows = [dict(entry_row) for entry_row in tsv_reader]
    elif ext == ".ndjson":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f_in:
            for line in f_in:
                line_str = line.strip()
                if line_str:
                    try:
                        rows.append(json.loads(line_str))
                    except json.JSONDecodeError as decode_err:
                        decode_msg = str(decode_err)
    elif ext in (".ini", ".env", ".properties"):
        with open(file_path, "r", encoding="utf-8", errors="replace") as f_in:
            for line in f_in:
                stripped = line.strip()
                if stripped and not stripped.startswith(("#", ";", "[")):
                    if "=" in stripped:
                        key_name, val_str = stripped.split("=", 1)
                        rows.append({"key": key_name.strip(), "value": val_str.strip()})
                    elif ":" in stripped:
                        key_name, val_str = stripped.split(":", 1)
                        rows.append({"key": key_name.strip(), "value": val_str.strip()})
    return rows


def _write_data_rows(rows: list[dict[str, Any]], out_path: str, target_fmt: str) -> str:
    # Serialize uniform row dictionaries into selected output data formats.
    fmt = target_fmt.upper()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    if fmt == "JSON":
        with open(out_path, "w", encoding="utf-8") as f_out:
            json.dump(rows, f_out, indent=2)
    elif fmt == "NDJSON":
        with open(out_path, "w", encoding="utf-8") as f_out:
            for row_record in rows:
                f_out.write(json.dumps(row_record) + "\n")
    elif fmt in ("CSV", "TSV"):
        delim = "\t" if fmt == "TSV" else ","
        if rows:
            keys = list(rows[0].keys())
            with open(out_path, "w", encoding="utf-8", newline="") as f_out:
                writer = csv.DictWriter(f_out, fieldnames=keys, delimiter=delim)
                writer.writeheader()
                writer.writerows(rows)
        else:
            with open(out_path, "w", encoding="utf-8") as f_out:
                f_out.write("")
    elif fmt == "YAML":
        with open(out_path, "w", encoding="utf-8") as f_out:
            yaml.safe_dump(rows, f_out, sort_keys=False)
    elif fmt == "XML":
        with open(out_path, "w", encoding="utf-8") as f_out:
            f_out.write("<root>\n")
            for row_record in rows:
                f_out.write("  <item>\n")
                for col_name, col_val in row_record.items():
                    clean_tag = re.sub(r"[^a-zA-Z0-9_]", "_", str(col_name))
                    f_out.write(f"    <{clean_tag}>{col_val}</{clean_tag}>\n")
                f_out.write("  </item>\n")
            f_out.write("</root>\n")
    return out_path


def _uses_internal_route(file_path: str, target_format: str) -> bool:
    # True when the direct dispatch in _convert_single_internal handles this pair.
    ext = os.path.splitext(file_path)[1].lower()
    target_fmt = target_format.strip().upper()
    if ext in EXT_IMAGES or target_fmt == "ICO":
        return True
    if ext in EXT_RASTER_QUALITY and target_fmt in ("JPEG", "WEBP"):
        return True
    if ext in EXT_MODELS or target_fmt in ("GLTF", "GLB", "3MF", "OFF"):
        return True
    if ext in EXT_DATA or target_fmt in ("TSV", "NDJSON"):
        return True
    return ext in EXT_TEXT or ext in EXT_DOCS


def _convert_single_internal(
    file_path: str,
    target_format: str,
    output_dir: str,
    output_path: str | None = None,
    output_stem: str | None = None,
    dpi: int = 150,
    quality: int = 90,
) -> list[str]:
    # Unified converter dispatch supporting single and batch conversion.
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")
    raw_fmt = target_format.strip()
    if raw_fmt.lower() in ("pdf (searchable)", "pdf_searchable"):
        target_fmt = "PDF (Searchable)"
    else:
        target_fmt = raw_fmt.upper()

    ext = os.path.splitext(file_path)[1].lower()
    os.makedirs(output_dir, exist_ok=True)

    if output_path:
        target_path = str(output_path)
    else:
        stem = output_stem or Path(file_path).stem
        if target_fmt == "PDF (Searchable)":
            out_ext = ".pdf"
        elif target_fmt == "M3U8":
            out_ext = ".m3u8"
        else:
            out_ext = f".{target_fmt.lower()}"
        target_path = str(Path(output_dir) / f"{stem}{out_ext}")

    if ext in EXT_IMAGES or target_fmt == "ICO" or (ext in EXT_RASTER_QUALITY and target_fmt in ("JPEG", "WEBP")):
        try:
            img = Image.open(file_path)
            if target_fmt == "PDF":
                img.convert("RGB").save(target_path, "PDF")
            elif target_fmt == "ICO":
                img.resize((128, 128)).save(target_path, "ICO")
            elif target_fmt == "JPEG":
                img.convert("RGB").save(target_path, "JPEG", quality=quality)
            elif target_fmt == "WEBP":
                img.save(target_path, "WEBP", quality=quality)
            elif target_fmt in ("TXT", "MD", "PDF (SEARCHABLE)", "PDF (Searchable)"):
                if target_fmt in ("PDF (SEARCHABLE)", "PDF (Searchable)"):
                    ocr_ops.create_searchable_pdf(file_path, target_path, dpi=dpi)
                else:
                    res = ocr_ops.ocr_file(file_path, dpi=dpi)
                    ocr_ops.save_ocr_text(res, target_path, as_markdown=(target_fmt == "MD"))
            else:
                img.save(target_path, format=target_fmt)
            return [target_path]
        except (IOError, ValueError, RuntimeError) as err:
            logger.debug("Unified image conversion failed, attempting general converter: %s", err)

    if ext in EXT_MODELS or target_fmt in ("GLTF", "GLB", "3MF", "OFF"):
        try:
            mesh = trimesh.load(file_path)
            mesh.export(target_path)
            return [target_path]
        except (IOError, ValueError, RuntimeError) as err:
            logger.debug("Unified mesh conversion failed, attempting general converter: %s", err)

    if ext in EXT_DATA or target_fmt in ("TSV", "NDJSON"):
        rows = _parse_data_to_rows(file_path, ext)
        res_p = _write_data_rows(rows, target_path, target_fmt)
        return [res_p]

    if ext in (".txt", ".text", ".md", ".markdown"):
        txt_body = Path(file_path).read_text(encoding="utf-8", errors="replace")
        with open(target_path, "w", encoding="utf-8") as f_txt:
            f_txt.write(txt_body)
        return [target_path]

    if ext in EXT_DOCS:
        try:
            doc = fitz.open(file_path)
            if target_fmt == "PDF":
                doc.save(target_path)
            elif target_fmt in ("TXT", "MD"):
                txt = "\n\n".join(page.get_text() for page in doc)
                with open(target_path, "w", encoding="utf-8") as f_out:
                    f_out.write(txt)
            elif target_fmt in ("PNG", "JPEG", "WEBP"):
                page = doc.load_page(0)
                pix = page.get_pixmap(dpi=dpi)
                pix.save(target_path)
            return [target_path]
        except (IOError, ValueError, RuntimeError) as err:
            logger.debug("Unified document conversion failed, attempting general converter: %s", err)

    stem_val = Path(target_path).stem if output_path else output_stem
    return convert_file(
        file_path,
        output_dir,
        target_fmt,
        dpi=dpi,
        output_stem=stem_val,
    )


class ConverterApiMixin:
    @api_method
    def converter_available_targets(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return list of compatible destination formats for source file.
        require(params, "file_path")
        file_path = str(params["file_path"])
        ext = os.path.splitext(file_path)[1].lower()

        if ext in EXT_IMAGES:
            targets = ["PNG", "JPEG", "WEBP", "BMP", "TIFF", "ICO", "PDF", "PDF (Searchable)", "TXT", "MD"]
            return ok(family="Image", targets=targets, file_path=file_path)
        if ext in EXT_MODELS:
            targets = ["STL", "OBJ", "PLY", "GLTF", "GLB", "3MF", "OFF"]
            return ok(family="Model3D", targets=targets, file_path=file_path)
        if ext in EXT_DATA:
            targets = ["JSON", "YAML", "CSV", "TSV", "TOML", "XML", "NDJSON"]
            return ok(family="Data", targets=targets, file_path=file_path)
        if ext in EXT_DOCS:
            targets = ["PDF", "PNG", "JPEG", "WEBP", "TXT", "MD"]
            return ok(family="Document", targets=targets, file_path=file_path)
        if ext in EXT_SUBS:
            targets = ["SRT", "VTT", "TXT"]
            return ok(family="Subtitle", targets=targets, file_path=file_path)
        if ext in EXT_PLAYLISTS:
            targets = ["M3U8", "CSV", "JSON", "TXT"]
            return ok(family="Playlist", targets=targets, file_path=file_path)
        if ext in EXT_FONTS:
            targets = ["TTF", "OTF", "WOFF", "WOFF2"]
            return ok(family="Font", targets=targets, file_path=file_path)

        family = source_family(file_path)
        targets = available_targets(file_path)
        if family == "Image":
            extra = ["ICO", "PDF", "TIFF"]
            targets = list(dict.fromkeys(targets + extra))
        elif family == "Data":
            extra = ["TSV", "NDJSON"]
            targets = list(dict.fromkeys(targets + extra))
        elif family == "Model3D":
            extra = ["GLTF", "GLB", "3MF", "OFF"]
            targets = list(dict.fromkeys(targets + extra))

        return ok(family=family or "File", targets=targets, file_path=file_path)

    @api_method
    def converter_scan_inputs(self, params: dict[str, Any]) -> dict[str, Any]:
        # Expand mixed file and folder paths into convertible queue descriptors.
        require(params, "paths")
        raw_paths = list(params["paths"])
        recursive = bool(params.get("recursive", True))
        family_filter = str(params.get("family_filter", "all")).lower()
        ext_filter_str = str(params.get("extension_filter", "")).strip().lower()
        ext_filters = {e.strip() if e.strip().startswith(".") else f".{e.strip()}" for e in ext_filter_str.split(",") if e.strip()}

        discovered: list[dict[str, Any]] = []
        visited: set[str] = set()

        def _evaluate_file(f_path: Path, rel_dir: str) -> None:
            resolved = str(f_path.resolve())
            if resolved in visited or not f_path.is_file():
                return
            visited.add(resolved)
            ext = f_path.suffix.lower()
            if ext_filters and ext not in ext_filters:
                return

            if f_path.name.startswith(".") or f_path.name.startswith("~$"):
                return

            res = self.converter_available_targets({"file_path": str(f_path)})
            targets = res.get("targets", [])
            fam = res.get("family", "File")

            if not targets:
                return

            if family_filter != "all":
                if family_filter == "image" and fam != "Image":
                    return
                elif family_filter in ("document", "office") and fam not in ("Document", "Office", "PDF"):
                    return
                elif family_filter in ("audio", "video", "media") and fam not in ("Audio", "Video"):
                    return
                elif family_filter == "data" and fam != "Data":
                    return
                elif family_filter == "model3d" and fam != "Model3D":
                    return

            def_target = targets[0] if targets else ""
            discovered.append({
                "path": str(f_path),
                "name": f_path.name,
                "rel_dir": rel_dir,
                "size_bytes": f_path.stat().st_size,
                "family": fam,
                "targets": targets,
                "default_target": def_target,
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
    def converter_convert_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert file to target format with optional quality and DPI parameters.
        require(params, "target_format")
        file_path = str(params.get("file_path") or params.get("input_path") or "")
        if not file_path:
            raise ValueError("Parameter file_path or input_path is required")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found: {file_path}")

        target_fmt = str(params["target_format"])
        out_p = params.get("output_path")
        out_dir = str(params.get("output_dir") or (Path(out_p).parent if out_p else Path(file_path).parent))
        output_stem = params.get("output_stem")
        dpi = int(params.get("dpi", 150))
        quality = int(params.get("quality", 90))

        created_files = _convert_single_internal(
            file_path,
            target_fmt,
            out_dir,
            output_path=out_p,
            output_stem=output_stem,
            dpi=dpi,
            quality=quality,
        )
        res_path = created_files[0] if created_files else str(out_p or file_path)
        if out_p and len(created_files) == 1 and os.path.abspath(res_path) != os.path.abspath(str(out_p)):
            os.replace(res_path, str(out_p))
            res_path = str(out_p)
            created_files = [res_path]
        return ok(output_path=res_path, files=created_files)

    @api_method
    def convert_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for single file conversion.
        return self.converter_convert_file(params)

    @api_method
    def converter_batch_convert(self, params: dict[str, Any]) -> dict[str, Any]:
        # Batch convert files, routing standard pairs through batch_convert_files.
        require(params, "items")
        raw_items = list(params["items"])
        out_dir = str(params.get("output_dir", "")).strip()
        preserve_tree = bool(params.get("preserve_tree", True))
        dpi = int(params.get("dpi", 150))
        quality = int(params.get("quality", 90))

        if not out_dir and raw_items:
            first_path = str(raw_items[0].get("path") or raw_items[0].get("input_path", ""))
            out_dir = str(Path(first_path).parent / "converted") if first_path else "."

        os.makedirs(out_dir, exist_ok=True)
        results: list[dict[str, Any]] = [{} for _ in raw_items]
        grouped: dict[str, list[tuple[int, BatchConversionItem]]] = {}

        for idx, item in enumerate(raw_items):
            in_p = str(item.get("path") or item.get("input_path") or item.get("source_path", ""))
            tgt_fmt = str(item.get("target_format", ""))
            rel_dir = str(item.get("rel_dir", "")).strip()
            item_out_dir = str(Path(out_dir) / rel_dir) if (preserve_tree and rel_dir) else out_dir

            if _uses_internal_route(in_p, tgt_fmt):
                try:
                    created = _convert_single_internal(
                        in_p, tgt_fmt, item_out_dir, output_stem=item.get("output_stem"), dpi=dpi, quality=quality
                    )
                    results[idx] = {"path": in_p, "output_path": created[0] if created else "", "ok": True, "error": None}
                except Exception as exc:
                    results[idx] = {"path": in_p, "output_path": "", "ok": False, "error": str(exc)}
                continue

            batch_item = BatchConversionItem(input_path=in_p, target_format=tgt_fmt, output_stem=item.get("output_stem"))
            grouped.setdefault(item_out_dir, []).append((idx, batch_item))

        for group_dir, pairs in grouped.items():
            finished = batch_convert_files([pair[1] for pair in pairs], group_dir, dpi=dpi)
            for (idx, _), done_item in zip(pairs, finished):
                is_done = done_item.status == "done"
                results[idx] = {
                    "path": done_item.input_path,
                    "output_path": done_item.output_paths[0] if done_item.output_paths else "",
                    "ok": is_done,
                    "error": done_item.error,
                }

        succeeded = sum(1 for res_row in results if res_row.get("ok"))
        failed = len(results) - succeeded
        summary = f"Converted {succeeded} file(s), {failed} failed"
        return ok(results=results, succeeded=succeeded, failed=failed, summary=summary)

    @api_method
    def converter_summary(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return explanation of output shape before conversion.
        require(params, "file_path", "target_format")
        file_path = str(params["file_path"])
        target_fmt = str(params["target_format"])
        summary_text = conversion_summary(file_path, target_fmt)
        return ok(summary=summary_text)

    @api_method
    def conversion_summary(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for converter summary.
        return self.converter_summary(params)

    @api_method
    def converter_batch(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for batch conversion.
        return self.converter_batch_convert(params)

    @api_method
    def converter_export_enex(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export notes collection to Evernote ENEX XML archive.
        require(params, "notes", "output_path")
        notes = list(params["notes"])
        out_path = str(params["output_path"])
        res_p = export_enex(notes, out_path)
        return ok(output_path=res_p)

    @api_method
    def converter_source_family(self, params: dict[str, Any]) -> dict[str, Any]:
        # Identify source file media family (image, document, audio, video, ebook).
        require(params, "file_path")
        file_path = str(params["file_path"])
        fam = source_family(file_path)
        return ok(family=fam or "Generic", file_path=file_path)
