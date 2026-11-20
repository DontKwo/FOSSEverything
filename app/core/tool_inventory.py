"""Canonical tool inventory defining capabilities, formats, dependencies, and test coverage."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.home_apps import HOME_APPS


@dataclass(frozen=True)
class ToolInventoryEntry:
    id: str
    name: str
    category: str
    purpose: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    supported_formats: tuple[str, ...]
    optional_dependencies: tuple[str, ...]
    os_support: tuple[str, ...]
    offline_behavior: str
    destructive_risk: str
    test_modules: tuple[str, ...]


ALL_PLATFORMS: tuple[str, ...] = ("windows", "macos", "linux")

TOOL_INVENTORY: tuple[ToolInventoryEntry, ...] = (
    ToolInventoryEntry(
        id="pdf",
        name="PDF Studio",
        category="Documents",
        purpose="Inspect, merge, split, reorder, protect, water-mark, and extract text from PDF documents.",
        inputs=("PDF documents",),
        outputs=("Merged/split/modified PDF", "Extracted text"),
        supported_formats=(".pdf",),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline local processing",
        destructive_risk="low (creates new files by default)",
        test_modules=(
            "tests/test_pdf_workspace.py",
            "tests/test_pdf_ops_extended.py",
            "tests/test_pdf_ops_extensions.py",
            "tests/test_pdf_security_and_organizer.py",
        ),
    ),
    ToolInventoryEntry(
        id="ocr",
        name="OCR Studio",
        category="Documents",
        purpose="Extract text from scans and images, generate searchable PDFs completely offline.",
        inputs=("Scanned images", "PDF scans"),
        outputs=("Plain text", "Markdown", "Searchable PDF"),
        supported_formats=(".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp", ".pdf"),
        optional_dependencies=("tesseract",),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline local OCR",
        destructive_risk="none (read-only source)",
        test_modules=("tests/test_ocr_ops.py", "tests/test_ocr_smart.py"),
    ),
    ToolInventoryEntry(
        id="markdown",
        name="Markdown Studio",
        category="Documents",
        purpose="Side-by-side Markdown editing and live rendering with GFM, CommonMark, and HTML/PDF export.",
        inputs=("Markdown text", "CommonMark files"),
        outputs=("Rendered HTML", "Exported PDF", "Formatted Markdown"),
        supported_formats=(".md", ".markdown", ".mdown", ".txt"),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline editor and renderer",
        destructive_risk="none",
        test_modules=("tests/test_markdown_ops.py", "tests/test_markdown_flavors.py"),
    ),
    ToolInventoryEntry(
        id="resume",
        name="Resume Studio",
        category="Documents",
        purpose="Engineering resume builder with UT Austin Engineering Theme formatting and PDF export.",
        inputs=("Resume JSON schemas", "Draft content"),
        outputs=("Compiled PDF resume", "Structured JSON"),
        supported_formats=(".json",),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline local typesetting",
        destructive_risk="none",
        test_modules=("tests/test_resume_ops.py", "tests/test_resume_gnc_format.py"),
    ),
    ToolInventoryEntry(
        id="images",
        name="Image Studio",
        category="Visuals",
        purpose="Crop, resize, adjust, remove backgrounds, apply filters, and convert images.",
        inputs=("Raster and raw image files",),
        outputs=("Adjusted images", "Transparent PNGs", "Filtered media"),
        supported_formats=(".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".heic", ".raw"),
        optional_dependencies=("u2net (optional offline model)",),
        os_support=ALL_PLATFORMS,
        offline_behavior="Local processing, optional on-demand model download",
        destructive_risk="low (non-destructive by default)",
        test_modules=("tests/test_image_ops.py", "tests/test_photo_tools.py", "tests/test_rembg_models.py"),
    ),
    ToolInventoryEntry(
        id="collage",
        name="Collage & Layers",
        category="Visuals",
        purpose="Freeform layered canvas and grid collage maker with multi-layer export.",
        inputs=("Image assets", "Canvas elements"),
        outputs=("Composed collages", "Layered PSD", "ORA bundles"),
        supported_formats=(".png", ".jpg", ".jpeg", ".webp", ".psd", ".ora"),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline canvas composition",
        destructive_risk="none",
        test_modules=("tests/test_collage_ops.py", "tests/test_collage_layers.py"),
    ),
    ToolInventoryEntry(
        id="palette",
        name="Color Palette",
        category="Visuals",
        purpose="Extract dominant color palettes, pixel loupe eyedropper, and WCAG contrast audit.",
        inputs=("Image files", "Hex color values"),
        outputs=("Extracted color swatches", "WCAG contrast reports", "Palette tokens"),
        supported_formats=(".png", ".jpg", ".jpeg", ".webp", ".bmp"),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline clustering and math",
        destructive_risk="none (read-only analysis)",
        test_modules=("tests/test_palette_ops.py", "tests/test_palette_kmeans.py"),
    ),
    ToolInventoryEntry(
        id="model3d",
        name="3D Model Studio",
        category="Visuals",
        purpose="Inspect 3D geometry, cut with slicing planes, repair meshes, and convert formats.",
        inputs=("3D CAD and mesh models",),
        outputs=("Repaired meshes", "Sliced geometries", "Converted models"),
        supported_formats=(".stl", ".obj", ".step", ".stp"),
        optional_dependencies=("cadquery-ocp (STEP/IGES support)",),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline mesh computations",
        destructive_risk="low (writes new mesh file)",
        test_modules=("tests/test_model3d_ops.py",),
    ),
    ToolInventoryEntry(
        id="media",
        name="Audio & Video Studio",
        category="Media",
        purpose="Trim media, extract audio tracks, adjust speed, and convert video clips.",
        inputs=("Video and audio files",),
        outputs=("Transcoded streams", "Extracted audio", "Animated GIFs"),
        supported_formats=(".mp4", ".mkv", ".mov", ".avi", ".webm", ".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"),
        optional_dependencies=("ffmpeg",),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline local transcoding",
        destructive_risk="low (creates separate output media)",
        test_modules=("tests/test_media_ops.py", "tests/test_media_stream_server.py"),
    ),
    ToolInventoryEntry(
        id="playlist",
        name="Playlist Porter",
        category="Media",
        purpose="Convert and migrate music playlists between Spotify, YouTube, and local files.",
        inputs=("Playlist URLs", "M3U/M3U8 playlists", "CSV tracks"),
        outputs=("Exported M3U8", "Track CSV", "Migrated playlist targets"),
        supported_formats=(".m3u", ".m3u8", ".csv", ".json"),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="Offline file parsing with optional user-authorized API sync",
        destructive_risk="none",
        test_modules=("tests/test_playlist_ops.py", "tests/test_playlist_api.py"),
    ),
    ToolInventoryEntry(
        id="converter",
        name="File Converter",
        category="Files & Storage",
        purpose="Universal multi-threaded format converter for documents, office, images, and data.",
        inputs=("Source files in any supported category",),
        outputs=("Converted destination format files",),
        supported_formats=(".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp", ".pdf", ".png", ".jpg", ".webp", ".csv", ".json"),
        optional_dependencies=("libreoffice/soffice", "pandoc"),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline document and media conversion",
        destructive_risk="low (writes new file, preserves source)",
        test_modules=(
            "tests/test_converter_ops.py",
            "tests/test_converter_and_compressor.py",
            "tests/test_converter_batch_office.py",
            "tests/test_office_ops.py",
        ),
    ),
    ToolInventoryEntry(
        id="compressor",
        name="File Compressor",
        category="Files & Storage",
        purpose="Centralized optimization and compression for PDFs, media, images, and archives.",
        inputs=("Uncompressed files",),
        outputs=("Size-optimized files",),
        supported_formats=(".pdf", ".png", ".jpg", ".webp", ".mp4", ".zip"),
        optional_dependencies=("ffmpeg",),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline compression algorithms",
        destructive_risk="low (safely writes to separate compressed target)",
        test_modules=("tests/test_compressor_estimate.py", "tests/test_converter_and_compressor.py"),
    ),
    ToolInventoryEntry(
        id="archive",
        name="Archive Studio",
        category="Files & Storage",
        purpose="Create, inspect, extract, and password-protect ZIP, TAR, GZ, XZ, and BZ2 archives.",
        inputs=("Archive bundles", "Files/directories to archive"),
        outputs=("Extracted directory tree", "Compressed archive bundle", "Encrypted bundle"),
        supported_formats=(".zip", ".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2", ".fossbundle"),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline streaming archive operations",
        destructive_risk="medium (extracts files into target folder)",
        test_modules=(
            "tests/test_archive_ops.py",
            "tests/test_archive_security_and_formats.py",
            "tests/test_archive_sha256.py",
        ),
    ),
    ToolInventoryEntry(
        id="renamer",
        name="Batch Renamer",
        category="Files & Storage",
        purpose="Rule-based batch renaming with live preview, collision checking, and undo logging.",
        inputs=("Lists of file paths", "Renaming rules"),
        outputs=("Renamed filesystem targets", "Undo log"),
        supported_formats=("*",),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline filesystem operations",
        destructive_risk="high (in-place rename with undo journal)",
        test_modules=("tests/test_renamer_ops.py", "tests/test_renamer_pipeline.py", "tests/test_renamer_api_undo.py"),
    ),
    ToolInventoryEntry(
        id="metadata",
        name="Metadata Tools",
        category="Security & Network",
        purpose="Inspect and sanitize EXIF, GPS, author, and revision metadata before sharing files.",
        inputs=("Images", "Office documents", "PDFs", "Media"),
        outputs=("Sanitized files without private metadata", "Metadata JSON report"),
        supported_formats=(".png", ".jpg", ".jpeg", ".webp", ".pdf", ".docx", ".xlsx", ".pptx", ".odt", ".mp4", ".mp3"),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline metadata parsing and stripping",
        destructive_risk="low (writes sanitized copy by default)",
        test_modules=("tests/test_metadata_ops.py", "tests/test_metadata_office_sanitize.py"),
    ),
    ToolInventoryEntry(
        id="qr",
        name="QR & Barcode Studio",
        category="Utilities",
        purpose="Generate custom styled QR codes and 1D barcodes; decode codes from images or clipboard.",
        inputs=("Text payload", "Barcode images"),
        outputs=("QR code SVG/PNG", "1D barcode SVG/PNG", "Decoded text payload"),
        supported_formats=(".png", ".jpg", ".svg"),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline generation and decoding",
        destructive_risk="none",
        test_modules=("tests/test_qr_ops.py",),
    ),
    ToolInventoryEntry(
        id="network_monitor",
        name="Network Monitor",
        category="Security & Network",
        purpose="Audit active network connections by process, detect unknown IPs, and inspect logs.",
        inputs=("Live host sockets",),
        outputs=("Process socket table", "Resolved domain log", "SQLite connection database"),
        supported_formats=(".db", ".sqlite"),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline host socket queries",
        destructive_risk="none (read-only audit)",
        test_modules=(
            "tests/test_network_monitor_db.py",
            "tests/test_network_monitor_monitor.py",
            "tests/test_network_monitor_resolver.py",
        ),
    ),
    ToolInventoryEntry(
        id="sherlock",
        name="Sherlock Username Search",
        category="Security & Network",
        purpose="Search for online accounts and social media presences by username across platforms.",
        inputs=("Target username string",),
        outputs=("Discovered profile URLs", "JSON/CSV scan results"),
        supported_formats=(".json", ".csv"),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="Local rule evaluation; connects only to public endpoints queried by user",
        destructive_risk="none",
        test_modules=("tests/test_sherlock.py",),
    ),
    ToolInventoryEntry(
        id="unit_converter",
        name="Unit Converter",
        category="Data & Text",
        purpose="Scientific unit converter supporting 30 physical categories and dimensional equations.",
        inputs=("Quantity strings", "Dimensional expressions"),
        outputs=("Converted physical quantities", "Unit breakdown"),
        supported_formats=(),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline physical calculations via Pint",
        destructive_risk="none",
        test_modules=("tests/test_unit_converter_pint.py",),
    ),
    ToolInventoryEntry(
        id="data",
        name="Data Studio",
        category="Data & Text",
        purpose="Format, validate, query, and inter-convert JSON, YAML, TOML, CSV, XML, and HDF5 data.",
        inputs=("Structured data files",),
        outputs=("Formatted data", "Converted schema", "Query results"),
        supported_formats=(".json", ".yaml", ".yml", ".toml", ".csv", ".xml", ".h5", ".hdf5"),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline parser and schema validation",
        destructive_risk="none",
        test_modules=("tests/test_data_ops.py", "tests/test_hdf5_reader.py"),
    ),
    ToolInventoryEntry(
        id="text_tools",
        name="Text & Word Studio",
        category="Data & Text",
        purpose="Side-by-side text diff, case conversion, line transformations, and readability stats.",
        inputs=("Plain text",),
        outputs=("Diff HTML", "Transformed text", "Readability scores"),
        supported_formats=(".txt", ".diff", ".patch"),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline text algorithms",
        destructive_risk="none",
        test_modules=("tests/test_text_tools_ops.py",),
    ),
    ToolInventoryEntry(
        id="encoding",
        name="Encoding & Decoding",
        category="Data & Text",
        purpose="Encode and decode text and files across Base64, URL, HTML entities, hex, and binary.",
        inputs=("Raw text", "Binary files"),
        outputs=("Encoded string", "Decoded binary payload"),
        supported_formats=("*",),
        optional_dependencies=(),
        os_support=ALL_PLATFORMS,
        offline_behavior="100% offline local encoding routines",
        destructive_risk="none",
        test_modules=("tests/test_encoding_ops.py",),
    ),
)


def get_tool_inventory() -> tuple[ToolInventoryEntry, ...]:
    # Return the full canonical tool inventory.
    return TOOL_INVENTORY


def get_tool_entry(tool_id: str) -> ToolInventoryEntry | None:
    # Look up a canonical tool inventory entry by its unique ID.
    target = tool_id.strip().lower()
    for entry in TOOL_INVENTORY:
        if entry.id.lower() == target:
            return entry
    return None


def validate_tool_inventory(project_root: Path | None = None) -> dict[str, Any]:
    # Validate that every visible tool is registered and all test modules exist.
    root = project_root or Path(__file__).resolve().parent.parent.parent
    inventory_map = {entry.id: entry for entry in TOOL_INVENTORY}
    home_app_ids = {app.id for app in HOME_APPS}

    missing_inventory = sorted(list(home_app_ids - set(inventory_map.keys())))
    missing_tests: list[str] = []

    for entry in TOOL_INVENTORY:
        for mod in entry.test_modules:
            mod_path = root / mod
            if not mod_path.exists():
                missing_tests.append(f"{entry.id}: {mod}")

    valid = len(missing_inventory) == 0 and len(missing_tests) == 0
    return {
        "valid": valid,
        "total_tools": len(TOOL_INVENTORY),
        "missing_inventory": missing_inventory,
        "missing_tests": missing_tests,
    }
