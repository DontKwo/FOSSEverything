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


HOME_CATEGORIES: tuple[str, ...] = ("Documents", "Visuals", "Media", "Utilities", "Data")

HOME_APPS: tuple[HomeApp, ...] = (
    HomeApp("pdf", "PDF Studio", "PDF", "Documents", "Merge, reorder, split, extract text, and password protect PDFs.", ("pdf", "document", "pages", "protect", "reorder", "watermark", "page numbers", "extract text")),
    HomeApp("ocr", "OCR Studio", "OCR", "Documents", "Extract text from scans and images; create searchable PDFs completely offline.", ("ocr", "scan", "text", "markdown", "tesseract", "searchable pdf", "extract text")),
    HomeApp("markdown", "Markdown Studio", "Markdown", "Documents", "Side-by-side Markdown editor and live renderer with GitHub GFM, CommonMark, and HTML/PDF export.", ("markdown", "md", "editor", "preview", "html", "table", "bold", "italic", "gfm")),
    HomeApp("resume", "Resume Studio", "Resume", "Documents", "Engineering resume builder with exact UT Austin Engineering Theme formatting and live PDF preview.", ("resume", "cv", "career", "builder", "tailor", "ats", "export pdf", "ut austin", "gnc")),
    HomeApp("images", "Image Studio", "Images", "Visuals", "Background remover model manager, crop, resize, adjust, and creative ASCII/GIF tools.", ("image", "photo", "png", "jpg", "webp", "enhance", "filter", "rembg", "background")),
    HomeApp("collage", "Collage & Layers", "Collage", "Visuals", "Freeform layered canvas and grid collage maker with PSD, ORA, and multi-layer export.", ("collage", "grid", "layers", "psd", "ora", "canvas", "combine photos")),
    HomeApp("palette", "Color Palette", "Palette", "Visuals", "Extract color palettes, live eyedropper pixel loupe, and WCAG contrast checker.", ("palette", "colors", "extract colors", "swatches", "dominant colors", "hex", "eyedropper", "wcag", "contrast")),
    HomeApp("model3d", "3D Model Studio", "3D Models", "Visuals", "Cut with planes, inspect geometry, repair mesh, scale, measure, and convert STL/OBJ/STEP.", ("3d", "stl", "obj", "step", "cad", "mesh", "cut plane", "slice", "watertight")),
    HomeApp("media", "Audio & Video Studio", "Audio & Video", "Media", "Trim, extract audio, generate Whisper subtitles, adjust speed, and convert video to GIF.", ("media", "audio", "video", "trim", "cut", "subtitles", "whisper", "mp4", "mp3")),
    HomeApp("playlist", "Playlist Porter", "Playlist Porter", "Media", "Convert playlists between Spotify, YouTube, and YouTube Music with M3U8/CSV export.", ("playlist", "spotify", "youtube", "music", "convert playlist", "m3u8", "csv", "sync")),
    HomeApp("converter", "File Converter", "Converter", "Utilities", "Universal file converter for documents, office, images, media, data, and 3D models.", ("convert", "format", "export", "files", "batch convert", "queue", "docx", "xlsx", "pptx", "odt", "ods", "odp", "office", "word", "excel", "powerpoint")),
    HomeApp("compressor", "File Compressor", "Compressor", "Utilities", "Centralized compression for PDF documents, images, video, audio, and archives.", ("compress", "reduce", "zip", "optimize", "shrink", "archive", "pdf", "video")),
    HomeApp("archive", "Archive Studio", "Archive", "Utilities", "Create, inspect, extract, and password-protect ZIP, TAR.GZ, TAR.XZ, and TAR.BZ2 archives.", ("zip", "tar", "archive", "compress", "extract", "unzip", "bundle")),
    HomeApp("renamer", "Batch Renamer", "Renamer", "Utilities", "Zero-regex visual step renaming with live before-and-after preview and instant undo.", ("rename", "batch", "numbering", "prefix", "suffix", "replace text", "date", "undo")),
    HomeApp("metadata", "Metadata Tools", "Metadata", "Utilities", "Inspect, edit, or remove metadata from images, PDFs, office docs, and media before sharing.", ("metadata", "privacy", "exif", "strip", "gps", "docx", "pptx", "xlsx", "odt", "ods", "odp", "office")),
    HomeApp("qr", "QR & Barcode Studio", "QR & Barcodes", "Utilities", "Generate custom QR codes and 1D barcodes, and scan codes from images or clipboard.", ("qr", "barcode", "wifi", "link", "generator", "offline", "logo", "svg", "scan", "decode", "ean", "code128")),
    HomeApp("network_monitor", "Network Monitor", "Network Monitor", "Utilities", "Watch live outbound connections by process, flag unknown destinations, and query history.", ("network", "traffic", "connections", "firewall", "monitor", "process", "domain", "psutil")),
    HomeApp("unit_converter", "Unit Converter", "Unit Converter", "Data", "Scientific unit converter supporting 30 categories and compound dimensional expressions.", ("unit", "converter", "metric", "imperial", "temperature", "pressure", "energy", "power", "engineering")),
    HomeApp("data", "Data Studio", "Data Studio", "Data", "Format, minify, validate, convert, and query JSON, YAML, TOML, CSV, XML, and SQL.", ("json", "yaml", "csv", "xml", "format", "minify", "validate", "jsonpath", "schema")),
    HomeApp("text_tools", "Text & Word Studio", "Text & Words", "Data", "Text transforms, side-by-side diff, readability analytics, grammar inspection, and citations.", ("text", "case", "diff", "sort lines", "dedupe", "word count", "readability", "grammar", "citations")),
    HomeApp("encoding", "Encoding & Decoding", "Encoding", "Data", "Encode and decode text and files between Base64, URL, HTML entities, hex, and binary.", ("base64", "url encode", "html entities", "hex", "binary", "encode", "decode", "rot13", "ciphers")),
)
