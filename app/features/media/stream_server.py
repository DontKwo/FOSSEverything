import atexit
import http.server
import mimetypes
import os
import threading
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

STREAM_ROUTE = "/api/media_stream"
CHUNK_BYTES = 256 * 1024

MEDIA_EXTENSIONS = frozenset({
    ".mp4", ".m4v", ".mkv", ".webm", ".avi", ".mov", ".wmv", ".flv", ".mpg", ".mpeg", ".ts", ".mts",
    ".m2ts", ".3gp", ".ogv", ".mp3", ".wav", ".flac", ".aac", ".ogg", ".oga", ".opus", ".m4a", ".wma",
    ".aiff", ".aif",
})

MIME_OVERRIDES = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".ogv": "video/ogg",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".opus": "audio/ogg",
    ".m4a": "audio/mp4",
}


def _norm_key(path: str) -> str:
    # Return the case-normalized absolute form used as the registry key.
    return os.path.normcase(os.path.abspath(path))


def calc_content_type(path: str) -> str:
    # Pick the response MIME type from the file extension.
    ext = os.path.splitext(path)[1].lower()
    if ext in MIME_OVERRIDES:
        return MIME_OVERRIDES[ext]
    guessed, _enc = mimetypes.guess_type(path)
    return guessed or "application/octet-stream"


def parse_range_header(header: str, size: int) -> tuple[int, int] | None:
    # Parse a single byte range into inclusive (start, end); raises ValueError when unsatisfiable.
    unit, _sep, spec = header.partition("=")
    if unit.strip().lower() != "bytes" or "," in spec:
        return None
    first, _dash, last = spec.strip().partition("-")
    if not first and not last:
        return None
    if not first:
        suffix = int(last)
        if suffix <= 0:
            raise ValueError("unsatisfiable")
        return max(0, size - suffix), size - 1
    start = int(first)
    end = int(last) if last else size - 1
    if start >= size or end < start:
        raise ValueError("unsatisfiable")
    return start, min(end, size - 1)


class _StreamHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        # Silence per-request stderr logging.
        return None

    def do_GET(self) -> None:
        # Serve the requested file body.
        self._serve(send_body=True)

    def do_HEAD(self) -> None:
        # Serve headers only.
        self._serve(send_body=False)

    def do_OPTIONS(self) -> None:
        # Answer CORS preflight requests.
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Range")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _reply(self, code: int, message: str) -> None:
        # Send a short plain-text error response.
        body = message.encode("ascii", "replace")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=ascii")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _serve(self, send_body: bool) -> None:
        # Resolve the registered file and stream the full body or one byte range.
        parts = urlsplit(self.path)
        if parts.path != STREAM_ROUTE:
            self._reply(404, "not found")
            return
        values = parse_qs(parts.query).get("path", [])
        if not values or not values[0]:
            self._reply(400, "missing path")
            return
        raw_path = values[0]
        if ".." in Path(raw_path).parts or "\x00" in raw_path:
            self._reply(403, "forbidden")
            return
        registry: MediaStreamServer = getattr(self.server, "owner")
        if not registry.is_registered(raw_path):
            self._reply(403, "forbidden")
            return
        if not os.path.isfile(raw_path):
            self._reply(404, "file missing")
            return
        size = os.path.getsize(raw_path)
        start, end, status = 0, size - 1, 200
        range_header = self.headers.get("Range")
        if range_header:
            try:
                parsed = parse_range_header(range_header, size)
            except ValueError:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                return
            if parsed is not None:
                start, end = parsed
                status = 206
        length = end - start + 1 if size > 0 else 0
        self.send_response(status)
        self.send_header("Content-Type", calc_content_type(raw_path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if not send_body or length == 0:
            return
        self._write_range(raw_path, start, length)

    def _write_range(self, path: str, start: int, length: int) -> None:
        # Copy length bytes from offset start, ignoring client disconnects.
        remaining = length
        try:
            with open(path, "rb") as handle:
                handle.seek(start)
                while remaining > 0:
                    chunk = handle.read(min(CHUNK_BYTES, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (ConnectionError, OSError):
            self.close_connection = True


class _Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    owner: "MediaStreamServer"


class MediaStreamServer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._allowed: set[str] = set()
        self._httpd: _Server | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> int:
        # Start the loopback server on a free port if needed and return the port.
        with self._lock:
            if self._httpd is None:
                httpd = _Server(("127.0.0.1", 0), _StreamHandler)
                httpd.owner = self
                thread = threading.Thread(target=httpd.serve_forever, name="media-stream", daemon=True)
                thread.start()
                self._httpd = httpd
                self._thread = thread
            return int(self._httpd.server_address[1])

    def stop(self) -> None:
        # Shut the server down and release the port.
        with self._lock:
            httpd, self._httpd, self._thread = self._httpd, None, None
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()

    def register(self, path: str) -> str:
        # Allow one file and return its streaming URL.
        with self._lock:
            self._allowed.add(_norm_key(path))
        port = self.start()
        return f"http://127.0.0.1:{port}{STREAM_ROUTE}?path={quote(path, safe='')}"

    def is_registered(self, path: str) -> bool:
        # Report whether the file was registered through register().
        with self._lock:
            return _norm_key(path) in self._allowed


_SHARED = MediaStreamServer()
atexit.register(_SHARED.stop)


def register_media_file(path: str) -> str:
    # Register a file with the shared server and return its HTTP URL.
    return _SHARED.register(path)


def stop_shared_server() -> None:
    # Stop the shared server.
    _SHARED.stop()
