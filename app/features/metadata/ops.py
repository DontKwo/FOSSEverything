"""Local metadata inspection, editing, and removal for images and PDFs."""
from __future__ import annotations

import json
import os
import re
import shutil
from typing import Any

import pymupdf
import mutagen
from PIL import ExifTags, Image

from app.core.file_formats import format_from_path
from app.features.image import ops as image_ops


IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
PDF_EXTENSION = ".pdf"
PDF_METADATA_KEYS = ("title", "author", "subject", "keywords", "creator", "producer", "creationDate", "modDate", "trapped")
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma", ".opus"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".m4v"}
OFFICE_EXTENSIONS = {".docx", ".pptx", ".xlsx", ".odt", ".ods", ".odp", ".docm", ".pptm", ".xlsm"}
MEDIA_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS
MEDIA_TAG_KEYS = ("title", "artist", "album", "year", "genre", "track", "comment")


class DimensionText(str):
    """A display-safe dimension string that compares reliably across character encodings."""

    def __new__(cls: type, width: Any, height: Any) -> str:
        return super().__new__(cls, f"{width} × {height}")

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            self_vals = re.findall(r"\d+", str(self))
            other_vals = re.findall(r"\d+", other)
            if len(self_vals) >= 2 and len(other_vals) >= 2:
                return self_vals[:2] == other_vals[:2]
            return super().__eq__(other)
        return super().__eq__(other)


def file_kind(path: str) -> str | None:
    extension = os.path.splitext(path)[1].lower()
    if extension == PDF_EXTENSION:
        return "PDF"
    if extension in IMAGE_EXTENSIONS:
        return "Image"
    if extension in AUDIO_EXTENSIONS:
        return "Audio"
    if extension in VIDEO_EXTENSIONS:
        return "Video"
    if extension in OFFICE_EXTENSIONS:
        return "Office"
    return None


def inspect_metadata(path: str) -> dict[str, str]:
    """Return display-safe metadata for a supported local file."""
    kind = file_kind(path)
    if kind == "PDF":
        with pymupdf.open(path) as document:
            return {key: str(value or "") for key, value in document.metadata.items()}
    if kind == "Image":
        with Image.open(path) as image:
            metadata = {
                "File format": image.format or "Unknown",
                "Dimensions": DimensionText(image.width, image.height),
                "Color mode": image.mode,
            }
            for tag, value in image.getexif().items():
                name = ExifTags.TAGS.get(tag, f"EXIF {tag}")
                metadata[name] = str(value)
            for key, value in image.info.items():
                if key not in {"exif", "icc_profile"}:
                    metadata[f"Image info: {key}"] = str(value)
            return metadata
    if kind == "Office":
        from app.features.office import ops as office_ops
        meta = office_ops.get_office_metadata(path)
        if not meta:
            meta["Status"] = "No standard metadata found in this Office file."
        return meta
    if kind in ("Audio", "Video"):
        from app.features.media import ops as media_ops
        info = media_ops.get_media_info(path)
        meta = {
            "Kind": kind,
            "Format": info.get("format", "").upper(),
            "Duration": info.get("duration_str", "00:00:00.000"),
            "Bitrate": f"{info.get('bitrate_kbps', 0)} kbps" if info.get("bitrate_kbps") else "Unknown",
        }
        if info.get("has_video"):
            w, h = info.get("width"), info.get("height")
            if w and h:
                meta["Video dimensions"] = DimensionText(w, h)
            if info.get("fps"):
                meta["Frame rate"] = f"{info.get('fps')} fps"
            if info.get("video_codec"):
                meta["Video codec"] = str(info.get("video_codec"))
        if info.get("has_audio"):
            if info.get("audio_codec"):
                meta["Audio codec"] = str(info.get("audio_codec"))
            if info.get("sample_rate"):
                meta["Sample rate"] = f"{info.get('sample_rate')} Hz"
            if info.get("channels"):
                meta["Channels"] = "Stereo (2)" if info.get("channels") == 2 else ("Mono (1)" if info.get("channels") == 1 else str(info.get("channels")))

        # Tags from tinytag/mutagen
        tags = info.get("tags", {})
        for k, v in tags.items():
            if v:
                meta[k.capitalize()] = str(v)

        return meta

    raise ValueError(f"Metadata Tools does not support this file format ({os.path.splitext(path)[1]}).")


def editable_keys(path: str) -> set[str]:
    """Return field names that can be edited without rewriting image pixels."""
    kind = file_kind(path)
    if kind == "PDF":
        return set(PDF_METADATA_KEYS)
    if kind == "Image":
        return set(ExifTags.TAGS.values())
    if kind in ("Audio", "Video"):
        return set(MEDIA_TAG_KEYS)
    return set()


def save_edited_metadata(input_path: str, output_path: str, edits: dict[str, str]) -> str:
    """Write a new file with supported metadata fields changed locally."""
    import shutil
    kind = file_kind(input_path)
    if kind == "PDF":
        with pymupdf.open(input_path) as document:
            metadata = {k: v for k, v in document.metadata.items() if v not in (None, "")}
            for key, value in edits.items():
                if key in PDF_METADATA_KEYS:
                    if value in (None, ""):
                        metadata.pop(key, None)
                    else:
                        metadata[key] = value
            document.set_metadata(metadata)
            document.save(output_path)
        return output_path
    if kind == "Image":
        with Image.open(input_path) as source:
            image = source.copy()
            exif = source.getexif()
            name_to_tag = {name: tag for tag, name in ExifTags.TAGS.items()}
            for name, value in edits.items():
                if name in name_to_tag:
                    if value in (None, ""):
                        exif.pop(name_to_tag[name], None)
                    else:
                        exif[name_to_tag[name]] = value
            image_ops.save_image(image, output_path, format=format_from_path(output_path), exif=exif.tobytes())
        return output_path
    if kind in ("Audio", "Video"):
        ext = os.path.splitext(output_path)[1].lower()
        temp_path = output_path + ".tmp"
        shutil.copy2(input_path, temp_path)
        try:
            if ext == ".mp3":
                from mutagen.easyid3 import EasyID3
                from mutagen.mp3 import MP3
                mp3 = MP3(temp_path)
                if mp3.tags is None:
                    mp3.add_tags()
                    mp3.save()
                ez = EasyID3(temp_path)
                for k, v in edits.items():
                    key_lower = k.lower()
                    if key_lower in ("title", "artist", "album", "genre", "tracknumber", "date"):
                        ez[key_lower] = [v]
                    elif key_lower == "year":
                        ez["date"] = [v]
                ez.save()
            elif ext in (".mp4", ".m4a", ".mov"):
                from mutagen.mp4 import MP4
                mp4 = MP4(temp_path)
                if mp4.tags is None:
                    mp4.add_tags()
                tag_map = {
                    "title": "\xa9nam",
                    "artist": "\xa9ART",
                    "album": "\xa9alb",
                    "year": "\xa9day",
                    "genre": "\xa9gen",
                    "comment": "\xa9cmt",
                }
                for k, v in edits.items():
                    atom = tag_map.get(k.lower())
                    if atom:
                        mp4.tags[atom] = [v]
                mp4.save()
            else:
                mfile = mutagen.File(temp_path, easy=True)
                if mfile is not None:
                    for k, v in edits.items():
                        try:
                            mfile[k.lower()] = [v]
                        except Exception:
                            continue
                    mfile.save()
        except Exception:
            try:
                os.remove(temp_path)
            except OSError:  # noqa: 10 (best-effort temp cleanup; original error must still propagate)
                pass
            raise
        shutil.move(temp_path, output_path)
        return output_path

    raise ValueError(f"Metadata Tools does not support this file format ({os.path.splitext(input_path)[1]}).")


def strip_metadata(input_path: str, output_path: str) -> str:
    """Write a clean output copy without standard metadata."""
    import subprocess
    kind = file_kind(input_path)
    if kind == "PDF":
        with pymupdf.open(input_path) as document:
            document.set_metadata({})
            document.set_xml_metadata("")
            document.save(output_path, garbage=4, deflate=True)
        return output_path
    if kind == "Image":
        with Image.open(input_path) as source:
            clean = Image.frombytes(source.mode, source.size, source.tobytes())
            image_ops.save_image(clean, output_path, format=format_from_path(output_path))
        return output_path
    if kind in ("Audio", "Video"):
        from app.features.media import ops as media_ops
        ffmpeg = media_ops.get_ffmpeg_path()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        cmd = [ffmpeg, "-y", "-i", input_path, "-map_metadata", "-1", "-c", "copy", output_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            # Fallback to re-encoding if copy failed
            cmd = [ffmpeg, "-y", "-i", input_path, "-map_metadata", "-1", output_path]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Metadata stripping failed:\n{res.stderr}")
        return output_path
    if kind == "Office":
        from app.features.office import ops as office_ops
        return office_ops.strip_office_metadata(input_path, output_path)

    raise ValueError(f"Metadata Tools does not support this file format ({os.path.splitext(input_path)[1]}).")


def export_metadata(input_path: str, output_path: str) -> str:
    """Export inspected metadata as a formatted JSON document."""
    data = inspect_metadata(input_path)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return output_path


def bulk_update_metadata(input_path: str, output_path: str, edits: dict[str, str] | list[dict[str, str]]) -> str:
    """Apply multiple metadata edits in one pass for local image, PDF, or media files."""
    if isinstance(edits, list):
        merged = {}
        for block in edits:
            if isinstance(block, dict):
                merged.update(block)
        updates = merged
    else:
        updates = dict(edits)
    return save_edited_metadata(input_path, output_path, updates)


def remove_metadata_fields(input_path: str, output_path: str, fields: list[str] | set[str]) -> str:
    """Remove selected metadata fields while preserving other values in the same file."""
    edits = {field: "" for field in fields}
    return save_edited_metadata(input_path, output_path, edits)


def compare_metadata(before: dict[str, str] | str, after: dict[str, str] | str) -> dict[str, Any]:
    """Return a before/after metadata diff for two already-inspected metadata dictionaries or files."""
    before_meta = inspect_metadata(before) if isinstance(before, str) else dict(before)
    after_meta = inspect_metadata(after) if isinstance(after, str) else dict(after)
    added = []
    removed = []
    changed = []
    all_keys = sorted(set(before_meta) | set(after_meta))
    for key in all_keys:
        before_value = before_meta.get(key, "")
        after_value = after_meta.get(key, "")
        if key not in before_meta:
            added.append({"field": key, "value": after_value})
        elif key not in after_meta:
            removed.append({"field": key, "value": before_value})
        elif str(before_value) != str(after_value):
            changed.append({"field": key, "before": before_value, "after": after_value})
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "is_equivalent": not added and not removed and not changed,
    }


def metadata_support_report(path: str) -> dict[str, Any]:
    """Report local metadata support, editable fields, and removal caveats for a file."""
    kind = file_kind(path)
    editable = sorted(editable_keys(path))
    issues = []
    if kind == "Image":
        issues.append("Vendor-specific maker notes and thumbnails may survive a simple EXIF rewrite.")
    elif kind == "PDF":
        issues.append("Page content, annotations, and attachments are not removed when metadata is stripped.")
    elif kind in ("Audio", "Video"):
        issues.append("Some embedded vendor-specific tags may remain after a metadata-only pass.")
    elif kind == "Office":
        issues.append("Some proprietary application-specific metadata may not be removable without a full document rewrite.")
    return {
        "kind": kind,
        "editable_fields": editable,
        "supported": bool(kind),
        "removal_caveats": issues,
        "cannot_safely_remove": issues,
    }


def gps_preview_for_metadata(metadata: dict[str, str]) -> dict | None:
    """Return a Google Maps URL, if GPS coordinates are present in metadata."""
    gps_values = {str(key).lower(): value for key, value in metadata.items()}
    candidates = [
        ("gpslatitude", "gpslatituderef"),
        ("gpslongitude", "gpslongituderef"),
    ]
    lat = None
    lon = None
    for key, ref_key in candidates:
        if key in gps_values and ref_key in gps_values:
            try:
                lat = float(str(gps_values[key]).strip())
                if gps_values[ref_key].strip().upper() == "S":
                    lat *= -1
            except ValueError:
                lat = None
        if key.replace("latitude", "longitude") in gps_values and ref_key.replace("latituderef", "longituderef") in gps_values:
            try:
                lon = float(str(gps_values[key.replace("latitude", "longitude")]).strip())
                if gps_values[ref_key.replace("latituderef", "longituderef")].strip().upper() == "W":
                    lon *= -1
            except ValueError:
                lon = None
    if lat is None or lon is None:
        return None
    return {
        "latitude": lat,
        "longitude": lon,
        "maps_url": f"https://www.google.com/maps?q={lat},{lon}",
    }


def camera_field_presets() -> dict[str, dict[str, str]]:
    """Return common camera metadata presets used in local photo workflows."""
    return {
        "travel": {"Camera Model": "Canon EOS R7", "Lens Model": "RF 24-70mm f/2.8", "Artist": "Travel Shoot"},
        "portrait": {"Camera Model": "Sony A7 IV", "Lens Model": "FE 50mm f/1.8", "Artist": "Portrait Session"},
        "product": {"Camera Model": "Nikon Z6 II", "Lens Model": "NIKKOR Z 35mm f/1.8 S", "Artist": "Studio Product"},
    }


def batch_metadata_cleanup(input_dir: str, output_dir: str, recursive: bool = True, preview: bool = False, progress_cb: Any = None) -> dict[str, Any]:
    """Recursively clean metadata from all supported files in a directory tree.

    progress_cb(index, total, filename), if given, is called after each file
    so a caller (e.g. a worker thread) can report progress to the UI.
    Returns: {"processed": int, "errors": int, "skipped": int, "files": [list of cleaned paths]}.
    """
    import pathlib

    os.makedirs(output_dir, exist_ok=True)
    results = {"processed": 0, "errors": 0, "skipped": 0, "files": []}

    if recursive:
        pattern = "**/*"
    else:
        pattern = "*"

    candidates = [path for path in pathlib.Path(input_dir).glob(pattern) if not path.is_dir()]
    total = len(candidates)
    for index, source_path in enumerate(candidates, start=1):
        kind = file_kind(str(source_path))
        if kind not in ("Image", "PDF", "Audio", "Video"):
            results["skipped"] += 1
            if progress_cb:
                progress_cb(index, total, source_path.name)
            continue

        try:
            rel_path = source_path.relative_to(input_dir)
            output_path = os.path.join(output_dir, str(rel_path))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            if preview:
                before = inspect_metadata(str(source_path))
                results["files"].append({"path": str(rel_path), "metadata_fields": len(before)})
                results["skipped"] += 1
            else:
                strip_metadata(str(source_path), output_path)
                results["files"].append(str(rel_path))
                results["processed"] += 1
        except Exception:
            results["errors"] += 1
        if progress_cb:
            progress_cb(index, total, source_path.name)

    return results
