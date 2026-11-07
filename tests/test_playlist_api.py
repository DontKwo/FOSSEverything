"""API-level tests for playlist JSON export and remote fetch error reasons."""
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from app.web.api import WebApi
from tests.test_support import TempDirTestCase

TRACKS = [
    {"artist": "Queen", "title": "Bohemian Rhapsody", "album": "A Night at the Opera"},
    {"artist": "The Beatles", "title": "Hey Jude", "album": ""},
]


class TestPlaylistExportJson(TempDirTestCase):
    def test_json_export_writes_track_objects(self) -> None:
        out_path = os.path.join(self.work_dir, "playlist.json")
        res = WebApi().playlist_export_json({"tracks": TRACKS, "output_path": out_path})
        self.assertTrue(res["ok"])
        with open(out_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual([t["title"] for t in data["tracks"]], ["Bohemian Rhapsody", "Hey Jude"])
        self.assertIn("youtube_music_url", data["tracks"][0])

    def test_m3u8_and_csv_export_follow_output_path(self) -> None:
        api = WebApi()
        m3u8_path = os.path.join(self.work_dir, "playlist.m3u8")
        csv_path = os.path.join(self.work_dir, "playlist.csv")
        self.assertTrue(api.playlist_export_m3u8({"tracks": TRACKS, "output_path": m3u8_path})["ok"])
        self.assertTrue(api.playlist_export_csv({"tracks": TRACKS, "output_path": csv_path})["ok"])
        with open(m3u8_path, "r", encoding="utf-8") as handle:
            self.assertTrue(handle.read().startswith("#EXTM3U"))


class TestPlaylistFetchErrors(unittest.TestCase):
    def _fetch_with(self, exc: Exception) -> dict:
        with patch("app.web.api.tool_playlist.fetch_playlist_from_url", side_effect=exc):
            return WebApi().playlist_fetch({"url": "https://open.spotify.com/playlist/abc"})

    def test_http_error_reason(self) -> None:
        res = self._fetch_with(urllib.error.HTTPError("u", 404, "Not Found", None, None))
        self.assertFalse(res["ok"])
        self.assertIn("HTTP 404", res["error"])

    def test_network_error_reason(self) -> None:
        res = self._fetch_with(urllib.error.URLError("getaddrinfo failed"))
        self.assertFalse(res["ok"])
        self.assertIn("getaddrinfo failed", res["error"])
        self.assertIn("internet connection", res["error"])

    def test_timeout_reason(self) -> None:
        res = self._fetch_with(TimeoutError("Spotify request timed out after 60 seconds."))
        self.assertIn("timed out", res["error"])

    def test_unrecognized_url_message_is_passed_through(self) -> None:
        res = WebApi().playlist_fetch({"url": "https://example.com/nothing"})
        self.assertFalse(res["ok"])
        self.assertIn("not recognized", res["error"])


if __name__ == "__main__":
    unittest.main()
