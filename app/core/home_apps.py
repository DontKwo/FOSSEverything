"""Home workspace metadata and definitions for FOSSEverything."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HomeApp:
    """A workspace definition shown on the local home screen."""

    id: str
    name: str
    category: str
    description: str
    keywords: tuple[str, ...]
    available: bool = False

    @property
    def search_text(self) -> str:
        return " ".join((self.name, self.category, self.description, *self.keywords)).lower()


HOME_APPS: tuple[HomeApp, ...] = (
    HomeApp("pdf", "PDF Editor", "Documents", "View, annotate, merge, split, compress, protect, watermark, number, and organize PDFs.", ("pdf", "document", "forms", "pages", "protect", "reorder", "watermark", "page numbers", "extract text"), True),
    HomeApp("images", "Image Editor", "Images", "Crop, resize, mark up, auto-enhance, filter, redact, screenshot, convert, and batch-process images.", ("image", "photo", "png", "jpg", "webp", "enhance", "filter", "screenshot", "snip"), True),
    HomeApp("media", "Video & Audio", "Media", "Trim, cut, extract audio, convert, compress, mute, and capture frames from video and audio locally.", ("video", "audio", "trim", "cut", "mp4", "mp3", "mov", "mkv", "compress", "extract audio", "snapshot"), True),
    HomeApp("ocr", "OCR & Text", "Documents", "Extract text from scans and images; create searchable PDFs completely offline.", ("ocr", "scan", "text", "markdown", "tesseract", "searchable pdf", "extract text"), True),
    HomeApp("resume", "Resume Builder", "Documents", "Build a master resume and check/uncheck bullets and reorder sections to tailor per job.", ("resume", "cv", "career", "builder", "tailor", "ats", "export pdf", "job"), True),
    HomeApp("word_counter", "Word Counter", "Documents", "Count words, sentences, reading time, and readability score for any document.", ("word count", "character count", "stats", "readability", "flesch", "reading time", "docx", "pdf"), True),
    HomeApp("playlist", "Playlist Porter", "Media", "Convert playlists between Spotify, YouTube, and YouTube Music: fetch tracks, open per-track search links, and export M3U8/CSV.", ("playlist", "spotify", "youtube", "music", "convert playlist", "m3u8", "csv", "sync"), True),
    HomeApp("converter", "File Converter", "Utilities", "Convert files single or in batch queues across images, PDFs, videos, audios, JSON, and CSV.", ("convert", "format", "export", "files", "batch convert", "queue"), True),
    HomeApp("metadata", "Metadata Tools", "Utilities", "Inspect, edit, or remove image/PDF/office/audio/video metadata before sharing.", ("metadata", "privacy", "exif", "strip", "docx", "pptx", "xlsx"), True),
    HomeApp("qr", "QR Codes & Barcodes", "Utilities", "Generate custom offline QR codes and scan/decode QR codes and barcodes from images/PDFs.", ("qr", "barcode", "wifi", "link", "generator", "offline", "logo", "svg", "scan", "decode"), True),
    HomeApp("renamer", "Batch Renamer", "Utilities", "Rename groups of files with regex, sequential numbers, prefixes, and live previews.", ("rename", "batch", "regex", "numbering", "bulk"), True),
    HomeApp("data", "Data Tools", "Data", "Format, pretty-print, minify, validate, JSONPath query, infer schema, and convert structured data.", ("json", "yaml", "csv", "xml", "format", "minify", "validate", "jsonpath", "schema"), True),
    HomeApp("markdown", "Markdown Studio", "Documents", "Side-by-side live Markdown editor and HTML preview with formatting insertion toolbar.", ("markdown", "md", "editor", "preview", "html", "table", "bold", "italic"), True),
    HomeApp("hash", "Hash & Checksum", "Utilities", "Compute file hashes and generate/verify directory checksum manifests offline.", ("hash", "checksum", "sha256", "md5", "sha512", "integrity", "verify", "manifest"), True),
    HomeApp("palette", "Color Palette", "Images", "Extract dominant color palettes and sample exact pixel colors with mouse eyedropper.", ("palette", "colors", "extract colors", "swatches", "dominant colors", "hex", "eyedropper"), True),
    HomeApp("collage", "Photo Collage", "Images", "Create customizable photo grid collages and side-by-side compositions.", ("collage", "grid", "combine photos", "side by side", "photo grid"), True),
    HomeApp("model3d", "3D Model Studio", "Utilities", "Cut, repair, measure, scale, and convert STL/OBJ/STEP 3D models locally.", ("3d", "stl", "obj", "step", "cad", "mesh", "cut plane", "slice"), True),
    HomeApp("text_tools", "Text Tools", "Utilities", "Case conversion, reversal, whitespace cleanup, line operations, regex replace, diff, and text/ASCII/binary conversion.", ("text", "case", "diff", "regex", "sort lines", "dedupe", "reverse", "camelcase", "snake_case", "ascii", "binary"), True),
    HomeApp("encoding", "Encoding / Decoding", "Utilities", "Encode and decode text and files between Base64, URL/percent-encoding, HTML entities, hex, and binary.", ("base64", "url encode", "html entities", "hex", "binary", "encode", "decode"), True),
    HomeApp("network_monitor", "Network Monitor", "Utilities", "Watch live outbound connections by process, flag new/unknown destinations, and search connection history.", ("network", "traffic", "connections", "firewall", "monitor", "process", "domain", "psutil"), True),
    HomeApp("archive", "Archive Studio", "Utilities", "Create, list, and extract ZIP, TAR, and TAR.GZ archives offline.", ("zip", "tar", "archive", "compress", "extract", "unzip"), True),
    HomeApp("office", "Office Tools", "Documents", "Extract clean text and convert DOCX, PPTX, XLSX, ODT, ODS, ODP documents.", ("docx", "pptx", "xlsx", "office", "word", "excel", "powerpoint", "convert"), True),
    HomeApp("screenshot", "Screen Capture", "Utilities", "Capture full screen, active windows, or custom snipping regions offline.", ("screenshot", "screen", "snip", "capture", "grab"), True),
)

