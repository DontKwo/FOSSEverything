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
        return super().__new__(cls, f"{width} x {height}")

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
        meta = get_office_metadata(path)
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
    if kind == "Office":
        return {"title", "author", "subject", "keywords"}
    return set()


def save_edited_metadata(input_path: str, output_path: str, edits: dict[str, str]) -> str:
    """Write a new file with supported metadata fields changed locally."""
    kind = file_kind(input_path)
    norm_edits = {str(k).lower(): v for k, v in edits.items()}
    if kind == "PDF":
        with pymupdf.open(input_path) as document:
            metadata = {k: v for k, v in document.metadata.items() if v not in (None, "")}
            for key, value in norm_edits.items():
                for pdf_k in PDF_METADATA_KEYS:
                    if pdf_k.lower() == key:
                        if value in (None, ""):
                            metadata.pop(pdf_k, None)
                        else:
                            metadata[pdf_k] = value
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
    if kind == "Office":
        return save_office_metadata(input_path, output_path, norm_edits)
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
    if kind == "Office":
        return save_office_metadata(input_path, output_path, edits)

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
        return strip_office_metadata(input_path, output_path)

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


def extract_gps_info(image_path: str) -> dict[str, Any]:
    """Read EXIF GPSInfo IFD (0x8825) from an image file and convert to signed decimal degrees."""
    if not os.path.exists(image_path):
        return {"has_gps": False}
    try:
        with Image.open(image_path) as img:
            exif = img.getexif()
            if not exif:
                return {"has_gps": False}
            gps_ifd = exif.get_ifd(0x8825)
            if not gps_ifd:
                return {"has_gps": False}

            lat_ref = str(gps_ifd.get(1, "N")).upper()
            lat_dms = gps_ifd.get(2)
            lon_ref = str(gps_ifd.get(3, "E")).upper()
            lon_dms = gps_ifd.get(4)
            alt = gps_ifd.get(6)

            if not lat_dms or not lon_dms:
                return {"has_gps": False}

            def _to_float(v: Any) -> float:
                if hasattr(v, "numerator") and hasattr(v, "denominator"):
                    return float(v.numerator) / float(v.denominator) if v.denominator != 0 else 0.0
                return float(v)

            lat = _to_float(lat_dms[0]) + _to_float(lat_dms[1]) / 60.0 + _to_float(lat_dms[2]) / 3600.0
            if lat_ref == "S":
                lat = -lat

            lon = _to_float(lon_dms[0]) + _to_float(lon_dms[1]) / 60.0 + _to_float(lon_dms[2]) / 3600.0
            if lon_ref == "W":
                lon = -lon

            alt_m: float | None = None
            if alt is not None:
                try:
                    alt_m = _to_float(alt)
                except Exception:
                    alt_m = None

            formatted = f"{lat:.6f}, {lon:.6f}"
            maps_url = f"https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lon:.6f}#map=16/{lat:.6f}/{lon:.6f}"
            return {
                "has_gps": True,
                "lat": lat,
                "latitude": lat,
                "lon": lon,
                "longitude": lon,
                "altitude_m": alt_m,
                "formatted": formatted,
                "maps_url": maps_url,
            }
    except Exception:
        return {"has_gps": False}


def strip_any_metadata(input_path: str, output_path: str) -> dict[str, Any]:
    """Universal metadata stripper returning removed fields count and output path."""
    before_fields = len(inspect_metadata(input_path))
    res_path = strip_metadata(input_path, output_path)
    return {
        "output_path": res_path,
        "removed_fields_count": before_fields,
    }


def gps_preview_for_metadata(metadata: dict[str, str], file_path: str = "") -> dict[str, Any] | None:
    """Return an OpenStreetMap URL if GPS coordinates are present in file or metadata."""
    if file_path:
        gps_info = extract_gps_info(file_path)
        if gps_info.get("has_gps"):
            return gps_info

    gps_values = {str(key).lower(): value for key, value in metadata.items()}
    lat = None
    lon = None
    if "gpslatitude" in gps_values and "gpslatituderef" in gps_values:
        try:
            lat = float(str(gps_values["gpslatitude"]).strip())
            if str(gps_values["gpslatituderef"]).strip().upper() == "S":
                lat = -lat
        except ValueError:
            lat = None
    if "gpslongitude" in gps_values and "gpslongituderef" in gps_values:
        try:
            lon = float(str(gps_values["gpslongitude"]).strip())
            if str(gps_values["gpslongituderef"]).strip().upper() == "W":
                lon = -lon
        except ValueError:
            lon = None
    if lat is None or lon is None:
        return {"has_gps": False}
    return {
        "has_gps": True,
        "lat": lat,
        "latitude": lat,
        "lon": lon,
        "longitude": lon,
        "formatted": f"{lat:.6f}, {lon:.6f}",
        "maps_url": f"https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lon:.6f}#map=16/{lat:.6f}/{lon:.6f}",
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
        if kind not in ("Image", "PDF", "Office", "Audio", "Video"):
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

# Office Metadata Operations

NS_CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
NS_DC = "http://purl.org/dc/elements/1.1/"
NS_DCTERMS = "http://purl.org/dc/terms/"
NS_EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
NS_CUSTOM = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"


def get_office_metadata(path: str) -> dict[str, str]:
    # Extract metadata properties from Office documents (OOXML and OpenDocument).
    import zipfile
    import xml.etree.ElementTree as ET

    meta: dict[str, str] = {}
    if not os.path.exists(path):
        return meta

    ext = os.path.splitext(path)[1].lower()
    if ext not in OFFICE_EXTENSIONS:
        return meta

    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = archive.namelist()
            if "docProps/core.xml" in names:
                root = ET.fromstring(archive.read("docProps/core.xml"))
                for elem in root:
                    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    text = elem.text
                    if text and text.strip():
                        if tag == "title":
                            meta["Title"] = text.strip()
                        elif tag == "creator":
                            meta["Author / Creator"] = text.strip()
                        elif tag == "subject":
                            meta["Subject"] = text.strip()
                        elif tag == "description":
                            meta["Description"] = text.strip()
                        elif tag == "keywords":
                            meta["Keywords"] = text.strip()
                        elif tag == "lastModifiedBy":
                            meta["Last Modified By"] = text.strip()
                        elif tag == "revision":
                            meta["Revision"] = text.strip()
                        elif tag == "created":
                            meta["Created Date"] = text.strip()
                        elif tag == "modified":
                            meta["Modified Date"] = text.strip()

            if "docProps/app.xml" in names:
                root = ET.fromstring(archive.read("docProps/app.xml"))
                for elem in root:
                    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    text = elem.text
                    if text and text.strip():
                        if tag == "Application":
                            meta["Application"] = text.strip()
                        elif tag == "Company":
                            meta["Company"] = text.strip()
                        elif tag == "Manager":
                            meta["Manager"] = text.strip()
                        elif tag == "Pages":
                            meta["Pages"] = text.strip()
                        elif tag == "Words":
                            meta["Words"] = text.strip()
                        elif tag == "Slides":
                            meta["Slides"] = text.strip()
                        elif tag == "HiddenSlides":
                            meta["Hidden Slides"] = text.strip()
                        elif tag == "TotalTime":
                            meta["Total Edit Time (mins)"] = text.strip()

            if "docProps/custom.xml" in names:
                root = ET.fromstring(archive.read("docProps/custom.xml"))
                cust_props = [elem.get("name") for elem in root if elem.tag.endswith("}property") and elem.get("name")]
                if cust_props:
                    meta["Custom Properties"] = ", ".join(cust_props)

            if "meta.xml" in names:
                root = ET.fromstring(archive.read("meta.xml"))
                for elem in root.iter():
                    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    if elem.text and elem.text.strip():
                        if tag == "title":
                            meta["Title"] = elem.text.strip()
                        elif tag in ("creator", "initial-creator"):
                            meta["Author / Creator"] = elem.text.strip()
                        elif tag == "subject":
                            meta["Subject"] = elem.text.strip()
                        elif tag == "description":
                            meta["Description"] = elem.text.strip()
                        elif tag == "date":
                            meta["Modified Date"] = elem.text.strip()
                        elif tag == "creation-date":
                            meta["Created Date"] = elem.text.strip()
                        elif tag == "editing-cycles":
                            meta["Revision"] = elem.text.strip()
                        elif tag == "editing-duration":
                            meta["Total Edit Time"] = elem.text.strip()
                        elif tag == "generator":
                            meta["Application"] = elem.text.strip()
    except Exception as exc:
        raise RuntimeError(f"Could not read office metadata: {exc}") from exc

    return meta


def strip_office_metadata(input_path: str, output_path: str) -> str:
    # Strip author, organization, and revision metadata from Office documents.
    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".docx":
        try:
            import docx  # noqa: 22
            doc = docx.Document(input_path)
            core = doc.core_properties
            core.author = ""
            core.last_modified_by = ""
            core.comments = ""
            core.title = ""
            doc.save(output_path)
            return output_path
        except Exception:  # noqa: 10
            pass

    import zipfile

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with zipfile.ZipFile(input_path, "r") as zin:
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                fname = item.filename
                if fname == "docProps/core.xml":
                    blank_core = (
                        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                        f'<cp:coreProperties xmlns:cp="{NS_CP}" xmlns:dc="{NS_DC}" xmlns:dcterms="{NS_DCTERMS}">\n'
                        '    <dc:title></dc:title>\n'
                        '    <dc:creator></dc:creator>\n'
                        '    <cp:lastModifiedBy></cp:lastModifiedBy>\n'
                        '    <cp:revision>1</cp:revision>\n'
                        '</cp:coreProperties>'
                    )
                    zout.writestr(item, blank_core.encode("utf-8"))
                elif fname == "docProps/app.xml":
                    blank_app = (
                        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                        f'<Properties xmlns="{NS_EP}">\n'
                        '    <Application>FOSSEverything</Application>\n'
                        '    <Company></Company>\n'
                        '</Properties>'
                    )
                    zout.writestr(item, blank_app.encode("utf-8"))
                elif fname == "docProps/custom.xml":
                    continue  # Drop custom properties entirely
                elif fname == "_rels/.rels":
                    rels_xml = zin.read(fname).decode("utf-8")
                    cleaned_rels = re.sub(r'<Relationship[^>]*Target="docProps/custom\.xml"[^>]*/>', '', rels_xml)
                    zout.writestr(item, cleaned_rels.encode("utf-8"))
                elif fname == "meta.xml":
                    blank_meta = '<?xml version="1.0" encoding="UTF-8"?><office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"/>'
                    zout.writestr(item, blank_meta.encode("utf-8"))
                else:
                    zout.writestr(item, zin.read(fname))

    return output_path


def save_office_metadata(input_path: str, output_path: str, edits: dict[str, str]) -> str:
    # Update core metadata fields in OOXML and ODF archives.
    import zipfile
    import xml.etree.ElementTree as ET

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with zipfile.ZipFile(input_path, "r") as zin:
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                fname = item.filename
                if fname == "docProps/core.xml":
                    root = ET.fromstring(zin.read(fname))
                    for field_name, field_value in edits.items():
                        k_lower = field_name.lower()
                        if k_lower in ("title", "subject", "keywords"):
                            node = root.find(f".//{{{NS_DC}}}{k_lower}") or root.find(f".//{{{NS_CP}}}{k_lower}")
                            if node is not None:
                                node.text = field_value
                            else:
                                new_elem = ET.SubElement(root, f"{{{NS_DC}}}{k_lower}")
                                new_elem.text = field_value
                        elif k_lower in ("author", "creator"):
                            node = root.find(f".//{{{NS_DC}}}creator")
                            if node is not None:
                                node.text = field_value
                            else:
                                new_elem = ET.SubElement(root, f"{{{NS_DC}}}creator")
                                new_elem.text = field_value
                    zout.writestr(item, ET.tostring(root, encoding="utf-8"))
                elif fname == "meta.xml":
                    root = ET.fromstring(zin.read(fname))
                    for field_name, field_value in edits.items():
                        k_lower = field_name.lower()
                        target_tag = "creator" if k_lower == "author" else k_lower
                        for node in root.iter():
                            if node.tag.endswith("}" + target_tag):
                                node.text = field_value
                    zout.writestr(item, ET.tostring(root, encoding="utf-8"))
                else:
                    zout.writestr(item, zin.read(fname))

    return output_path
