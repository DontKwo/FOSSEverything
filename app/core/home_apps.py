from dataclasses import dataclass


@dataclass(frozen=True)
class HomeApp:
    id: str
    name: str
    nav_name: str
    category: str
    description: str
    keywords: tuple[str, ...]
    available: bool = True

    @property
    def search_text(self) -> str:
        # Generate combined lowercase search text.
        return " ".join((self.name, self.nav_name, self.category, self.description, *self.keywords)).lower()


HOME_APPS: tuple[HomeApp, ...] = (
    HomeApp("pdf", "PDF Tools", "PDF Tools", "Documents", "Merge, reorder, split, extract text, and password protect PDFs.", ("pdf", "document", "pages", "protect", "reorder", "watermark", "page numbers", "extract text")),
    HomeApp("images", "Image Tools", "Image Tools", "Visuals", "Convert formats, crop, resize, rotate, flip, remove background, and compress images.", ("image", "photo", "png", "jpg", "webp", "enhance", "filter", "screenshot", "snip")),
    HomeApp("ocr", "OCR Studio", "OCR Studio", "Documents", "Extract text from scans and images; create searchable PDFs completely offline.", ("ocr", "scan", "text", "markdown", "tesseract", "searchable pdf", "extract text")),
    HomeApp("resume", "Resume Builder", "Resume Builder", "Documents", "Build a master resume and check bullets and reorder sections to tailor per job.", ("resume", "cv", "career", "builder", "tailor", "ats", "export pdf", "job")),
    HomeApp("playlist", "Playlist Porter", "Playlist Porter", "Media", "Convert playlists between Spotify, YouTube, and YouTube Music with M3U8/CSV export.", ("playlist", "spotify", "youtube", "music", "convert playlist", "m3u8", "csv", "sync")),
    HomeApp("converter", "File Converter", "Converter", "Utilities", "Universal file converter: convert any document, image, media, 3D, or data file format into any other.", ("convert", "format", "export", "files", "batch convert", "queue")),
    HomeApp("compressor", "File Compressor", "Compressor", "Utilities", "Centralized compression for PDF documents, images, video, audio, and archives.", ("compress", "reduce", "zip", "optimize", "shrink", "archive", "pdf", "video")),
    HomeApp("metadata", "Metadata Tools", "Metadata", "Utilities", "Inspect, edit, or remove image/PDF/office/audio/video metadata before sharing.", ("metadata", "privacy", "exif", "strip", "docx", "pptx", "xlsx")),
    HomeApp("qr", "QR and Barcodes", "QR & Barcodes", "Utilities", "Generate custom offline QR codes and scan/decode barcodes from images and PDFs.", ("qr", "barcode", "wifi", "link", "generator", "offline", "logo", "svg", "scan", "decode")),
    HomeApp("renamer", "Batch Renamer", "Renamer", "Utilities", "Rename groups of files with regex, sequential numbers, prefixes, and live previews.", ("rename", "batch", "regex", "numbering", "bulk")),
    HomeApp("data", "Data Studio", "Data Tools", "Data", "Format, minify, validate, convert, and query JSON, YAML, TOML, CSV, XML, and SQL.", ("json", "yaml", "csv", "xml", "format", "minify", "validate", "jsonpath", "schema")),
    HomeApp("markdown", "Markdown Preview", "Markdown Studio", "Documents", "Side-by-side live Markdown editor and HTML preview with formatting insertion toolbar.", ("markdown", "md", "editor", "preview", "html", "table", "bold", "italic")),
    HomeApp("palette", "Color Palette", "Color Palette", "Visuals", "Extract dominant color palettes and sample exact pixel colors with mouse eyedropper.", ("palette", "colors", "extract colors", "swatches", "dominant colors", "hex", "eyedropper")),
    HomeApp("collage", "Photo Collage", "Collage", "Visuals", "Create customizable photo grid collages and side-by-side compositions.", ("collage", "grid", "combine photos", "side by side", "photo grid")),
    HomeApp("model3d", "3D Model Studio", "3D Models", "Visuals", "Cut, repair, measure, scale, and convert STL/OBJ 3D models locally.", ("3d", "stl", "obj", "step", "cad", "mesh", "cut plane", "slice")),
    HomeApp("text_tools", "Text Tools", "Text Tools", "Data", "Case conversion, word counter, readability analytics, grammar inspection, citations, and diff.", ("text", "case", "diff", "regex", "sort lines", "dedupe", "reverse", "word count")),
    HomeApp("encoding", "Encoding / Decoding", "Encoding", "Data", "Encode and decode text and files between Base64, URL, HTML entities, hex, and binary.", ("base64", "url encode", "html entities", "hex", "binary", "encode", "decode")),
    HomeApp("network_monitor", "Network Monitor", "Network", "Utilities", "Watch live outbound connections by process, flag unknown destinations, and query history.", ("network", "traffic", "connections", "firewall", "monitor", "process", "domain", "psutil")),
    HomeApp("archive", "Archive Studio", "Archives", "Utilities", "Create, list, and extract ZIP, TAR, and TAR.GZ archives offline.", ("zip", "tar", "archive", "compress", "extract", "unzip")),
    HomeApp("office", "Office Tools", "Office Docs", "Documents", "Extract clean text and convert DOCX, PPTX, XLSX, ODT, ODS, ODP documents.", ("docx", "pptx", "xlsx", "office", "word", "excel", "powerpoint", "convert")),
)
