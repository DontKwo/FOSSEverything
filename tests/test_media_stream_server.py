"""Unit tests for the loopback media streaming server."""
import http.client
import os
import unittest
from typing import Any
from urllib.parse import quote, urlsplit

from app.features.media.stream_server import (
    STREAM_ROUTE,
    MediaStreamServer,
    parse_range_header,
)
from app.web.api import WebApi
from tests.test_support import TempDirTestCase

PAYLOAD = bytes(range(256)) * 40


class TestRangeParsing(unittest.TestCase):
    def test_closed_range(self) -> None:
        self.assertEqual(parse_range_header("bytes=10-19", 100), (10, 19))

    def test_open_ended_range(self) -> None:
        self.assertEqual(parse_range_header("bytes=90-", 100), (90, 99))

    def test_suffix_range(self) -> None:
        self.assertEqual(parse_range_header("bytes=-10", 100), (90, 99))

    def test_end_clamped_to_size(self) -> None:
        self.assertEqual(parse_range_header("bytes=50-500", 100), (50, 99))

    def test_start_past_end_unsatisfiable(self) -> None:
        with self.assertRaises(ValueError):
            parse_range_header("bytes=100-120", 100)

    def test_multi_range_ignored(self) -> None:
        self.assertIsNone(parse_range_header("bytes=0-1,5-6", 100))


class TestMediaStreamServer(TempDirTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.media_path = os.path.join(self.work_dir, "clip.mp4")
        with open(self.media_path, "wb") as handle:
            handle.write(PAYLOAD)
        self.server = MediaStreamServer()
        self.url = self.server.register(self.media_path)
        self.port = urlsplit(self.url).port
        self.addCleanup(self.server.stop)

    def _request(self, method: str, target: str, headers: dict[str, str] | None = None) -> tuple[int, Any, bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, target, headers=headers or {})
            resp = conn.getresponse()
            return resp.status, resp, resp.read()
        finally:
            conn.close()

    def _target(self, path: str) -> str:
        return f"{STREAM_ROUTE}?path={quote(path, safe='')}"

    def test_url_is_loopback_http(self) -> None:
        self.assertTrue(self.url.startswith("http://127.0.0.1:"))
        self.assertIn(STREAM_ROUTE, self.url)

    def test_full_get(self) -> None:
        status, resp, body = self._request("GET", self._target(self.media_path))
        self.assertEqual(status, 200)
        self.assertEqual(body, PAYLOAD)
        self.assertEqual(resp.getheader("Content-Type"), "video/mp4")
        self.assertEqual(resp.getheader("Accept-Ranges"), "bytes")
        self.assertEqual(int(resp.getheader("Content-Length")), len(PAYLOAD))

    def test_range_get_returns_206(self) -> None:
        status, resp, body = self._request("GET", self._target(self.media_path), {"Range": "bytes=100-199"})
        self.assertEqual(status, 206)
        self.assertEqual(body, PAYLOAD[100:200])
        self.assertEqual(resp.getheader("Content-Range"), f"bytes 100-199/{len(PAYLOAD)}")
        self.assertEqual(int(resp.getheader("Content-Length")), 100)

    def test_open_ended_and_suffix_ranges(self) -> None:
        size = len(PAYLOAD)
        status, _resp, body = self._request("GET", self._target(self.media_path), {"Range": f"bytes={size - 5}-"})
        self.assertEqual((status, body), (206, PAYLOAD[-5:]))
        status, _resp, body = self._request("GET", self._target(self.media_path), {"Range": "bytes=-7"})
        self.assertEqual((status, body), (206, PAYLOAD[-7:]))

    def test_unsatisfiable_range_returns_416(self) -> None:
        size = len(PAYLOAD)
        status, resp, _body = self._request("GET", self._target(self.media_path), {"Range": f"bytes={size}-"})
        self.assertEqual(status, 416)
        self.assertEqual(resp.getheader("Content-Range"), f"bytes */{size}")

    def test_head_has_headers_and_no_body(self) -> None:
        status, resp, body = self._request("HEAD", self._target(self.media_path))
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertEqual(int(resp.getheader("Content-Length")), len(PAYLOAD))

    def test_head_range(self) -> None:
        status, resp, body = self._request("HEAD", self._target(self.media_path), {"Range": "bytes=0-9"})
        self.assertEqual(status, 206)
        self.assertEqual(body, b"")
        self.assertEqual(int(resp.getheader("Content-Length")), 10)

    def test_unregistered_path_is_403(self) -> None:
        other = os.path.join(self.work_dir, "other.mp4")
        with open(other, "wb") as handle:
            handle.write(b"x")
        status, _resp, _body = self._request("GET", self._target(other))
        self.assertEqual(status, 403)

    def test_traversal_is_403(self) -> None:
        sneaky = os.path.join(self.work_dir, "sub", "..", "clip.mp4")
        status, _resp, _body = self._request("GET", self._target(sneaky))
        self.assertEqual(status, 403)

    def test_registered_but_deleted_is_404(self) -> None:
        os.remove(self.media_path)
        status, _resp, _body = self._request("GET", self._target(self.media_path))
        self.assertEqual(status, 404)

    def test_unknown_route_is_404(self) -> None:
        status, _resp, _body = self._request("GET", "/api/other?path=x")
        self.assertEqual(status, 404)

    def test_missing_path_param_is_400(self) -> None:
        status, _resp, _body = self._request("GET", STREAM_ROUTE)
        self.assertEqual(status, 400)

    def test_stop_releases_server(self) -> None:
        self.server.stop()
        with self.assertRaises(OSError):
            self._request("GET", self._target(self.media_path))

    def test_server_thread_is_daemon(self) -> None:
        self.assertTrue(self.server._thread is not None and self.server._thread.daemon)


class TestMediaFileUrlApi(TempDirTestCase):
    def test_returns_http_stream_url(self) -> None:
        media_path = os.path.join(self.work_dir, "tone.wav")
        with open(media_path, "wb") as handle:
            handle.write(b"RIFF" + bytes(64))
        res = WebApi().media_get_file_url({"file_path": media_path})
        self.assertTrue(res["ok"])
        self.assertTrue(res["url"].startswith("http://127.0.0.1:"))
        port = urlsplit(res["url"]).port
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", urlsplit(res["url"]).path + "?" + urlsplit(res["url"]).query, headers={"Range": "bytes=0-3"})
        resp = conn.getresponse()
        self.assertEqual((resp.status, resp.read()), (206, b"RIFF"))
        conn.close()

    def test_missing_file_fails(self) -> None:
        res = WebApi().media_get_file_url({"file_path": os.path.join(self.work_dir, "nope.mp4")})
        self.assertFalse(res["ok"])

    def test_non_media_extension_rejected(self) -> None:
        text_path = os.path.join(self.work_dir, "secret.txt")
        with open(text_path, "w", encoding="ascii") as handle:
            handle.write("data")
        res = WebApi().media_get_file_url({"file_path": text_path})
        self.assertFalse(res["ok"])


if __name__ == "__main__":
    unittest.main()
