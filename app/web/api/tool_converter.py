import csv
import json
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

EXT_IMAGES = {".ico", ".icns", ".tga", ".dds", ".ppm", ".pgm", ".pbm", ".pcx", ".sgi", ".eps"}
EXT_MODELS = {".gltf", ".glb", ".3mf", ".dae", ".off", ".xyz"}
EXT_DATA = {".tsv", ".ndjson", ".ini", ".env", ".properties"}
EXT_DOCS = {".xps", ".oxps", ".cbz", ".cbr", ".rtf", ".html", ".htm", ".rst"}
EXT_SUBS = {".srt", ".vtt"}
EXT_PLAYLISTS = {".m3u", ".m3u8"}
EXT_FONTS = {".ttx"}


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
            targets = ["SRT", "VTT", "TXT", "JSON"]
            return ok(family="Subtitles", targets=targets, file_path=file_path)
        if ext in EXT_PLAYLISTS:
            targets = ["JSON", "CSV", "TXT", "M3U8"]
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
    def converter_convert_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert file to target format with optional quality and DPI parameters.
        require(params, "file_path", "target_format")
        file_path = str(params["file_path"])
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found: {file_path}")
        target_fmt = str(params["target_format"]).upper()
        out_p = params.get("output_path")
        dpi = int(params.get("dpi", 150))
        ext = os.path.splitext(file_path)[1].lower()

        if out_p:
            out_dir = str(Path(out_p).parent)
            target_path = str(out_p)
        else:
            out_dir = str(Path(file_path).parent)
            out_ext = f".{target_fmt.lower().replace(' (searchable)', '')}"
            target_path = str(Path(file_path).with_suffix(out_ext))

        # Handle extended images
        if ext in EXT_IMAGES or target_fmt in ("ICO",):
            try:
                img = Image.open(file_path)
                if target_fmt == "PDF":
                    img.convert("RGB").save(target_path, "PDF")
                elif target_fmt == "ICO":
                    img.resize((128, 128)).save(target_path, "ICO")
                elif target_fmt == "JPEG":
                    img.convert("RGB").save(target_path, "JPEG", quality=90)
                elif target_fmt in ("TXT", "MD", "PDF (SEARCHABLE)"):
                    if target_fmt == "PDF (SEARCHABLE)":
                        ocr_ops.create_searchable_pdf(file_path, target_path, dpi=dpi)
                    else:
                        res = ocr_ops.ocr_file(file_path, dpi=dpi)
                        ocr_ops.save_ocr_text(res, target_path, as_markdown=(target_fmt == "MD"))
                else:
                    img.save(target_path, format=target_fmt)
                return ok(output_path=target_path, files=[target_path])
            except (IOError, ValueError, RuntimeError) as img_err:
                log_msg = str(img_err)

        # Handle extended 3D formats
        if ext in EXT_MODELS or target_fmt in ("GLTF", "GLB", "3MF", "OFF"):
            try:
                mesh = trimesh.load(file_path)
                mesh.export(target_path)
                return ok(output_path=target_path, files=[target_path])
            except (IOError, ValueError, RuntimeError) as mesh_err:
                log_msg = str(mesh_err)

        # Handle extended data formats
        if ext in EXT_DATA or target_fmt in ("TSV", "NDJSON"):
            rows = _parse_data_to_rows(file_path, ext)
            res_p = _write_data_rows(rows, target_path, target_fmt)
            return ok(output_path=res_p, files=[res_p])

        # Handle document formats (XPS, CBZ, RTF, HTML)
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
                return ok(output_path=target_path, files=[target_path])
            except (IOError, ValueError, RuntimeError) as doc_err:
                log_msg = str(doc_err)

        # Fallback to standard converter ops
        created_files = convert_file(
            file_path,
            out_dir,
            target_fmt,
            dpi=dpi,
            output_stem=Path(target_path).stem if out_p else None,
        )
        res_path = created_files[0] if created_files else str(out_p or file_path)
        return ok(output_path=res_path, files=created_files)

    @api_method
    def convert_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for single file conversion.
        return self.converter_convert_file(params)

    @api_method
    def converter_batch_convert(self, params: dict[str, Any]) -> dict[str, Any]:
        # Batch convert list of files to respective target formats.
        require(params, "items")
        raw_items = list(params["items"])
        batch_items = [
            BatchConversionItem(
                input_path=str(item.get("input_path", item.get("source_path", ""))),
                target_format=str(item.get("target_format", "")),
                output_stem=item.get("output_stem"),
            )
            for item in raw_items
        ]
        out_dir = str(params.get("output_dir", ""))
        if not out_dir and batch_items:
            out_dir = str(Path(batch_items[0].input_path).parent)
        results = batch_convert_files(batch_items, out_dir)
        summary = f"Converted {len(results)} file(s)"
        return ok(results=results, summary=summary)

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
