"""Unit tests for Playlist Porter (Spotify <-> YouTube)."""
import json
import os
import tempfile
import unittest
import urllib.error
from unittest.mock import patch
from app.features.playlist import ops as playlist_ops


class PlaylistOpsTests(unittest.TestCase):
    def test_clean_music_title(self) -> None:
        raw = "Queen - Bohemian Rhapsody (Official Music Video) [HD]"
        artist, title = playlist_ops.clean_music_title(raw)
        self.assertEqual(artist, "Queen")
        self.assertEqual(title, "Bohemian Rhapsody")

        raw2 = "Daft Punk ft. Pharrell Williams - Get Lucky (Official Audio)"
        artist2, title2 = playlist_ops.clean_music_title(raw2)
        self.assertEqual(artist2, "Daft Punk ft. Pharrell Williams")
        self.assertEqual(title2, "Get Lucky")

    def test_parse_tracklist_text(self) -> None:
        sample = """
        1. Linkin Park - In The End (Official HD Video)
        2. The Weeknd - Blinding Lights
        """
        tracks = playlist_ops.parse_tracklist_text(sample)
        self.assertEqual(len(tracks), 2)
        self.assertEqual(tracks[0].artist, "Linkin Park")
        self.assertEqual(tracks[0].title, "In The End")
        self.assertIn("youtube.com", tracks[0].youtube_url)
        self.assertIn("spotify.com", tracks[0].spotify_url)

    def test_export_m3u8_and_csv(self) -> None:
        tracks = [
            playlist_ops.build_track("Queen", "Radio Ga Ga"),
            playlist_ops.build_track("Daft Punk", "One More Time"),
        ]
        with tempfile.TemporaryDirectory() as td:
            m3u8_path = os.path.join(td, "test.m3u8")
            playlist_ops.export_m3u8_playlist(tracks, m3u8_path)
            self.assertTrue(os.path.exists(m3u8_path))

            csv_path = os.path.join(td, "test.csv")
            playlist_ops.export_csv_playlist(tracks, csv_path)
            self.assertTrue(os.path.exists(csv_path))


if __name__ == "__main__":
    unittest.main()


class PlaylistOpsApiTests(unittest.TestCase):
    def test_fetch_spotify_playlist_follows_pagination(self) -> None:
        pages = [
            {
                "items": [{
                    "track": {
                        "name": "First Song",
                        "artists": [{"name": "Artist One"}],
                        "album": {"name": "Album One"},
                        "duration_ms": 123000,
                    }
                }],
                "next": "https://api.spotify.com/v1/playlists/abc123/items?limit=100&offset=100",
                "total": 2,
            },
            {
                "items": [{
                    "track": {
                        "name": "Second Song",
                        "artists": [{"name": "Artist Two"}],
                        "album": {"name": "Album Two"},
                        "duration_ms": 456000,
                    }
                }],
                "next": None,
                "total": 2,
            },
        ]

        def fake_json_request(url: str, headers: dict | None = None, timeout: int | None = None, retries: int | None = None) -> dict:
            if url == 'https://api.spotify.com/v1/me':
                return {'id': 'owner'}
            if url == 'https://api.spotify.com/v1/playlists/abc123':
                return {'owner': {'id': 'owner'}, 'collaborative': False}
            if url.startswith('https://api.spotify.com/v1/playlists/abc123/items'):
                page = pages.pop(0)
                return page
            raise AssertionError(f'Unexpected URL: {url}')

        with patch.object(playlist_ops, '_load_spotify_client_id', return_value='id'):
            with patch.object(playlist_ops, 'get_spotify_user_token', return_value='token'):
                with patch.object(playlist_ops, '_spotify_json_request', side_effect=fake_json_request):
                    tracks = playlist_ops.fetch_spotify_playlist('https://open.spotify.com/playlist/abc123')

        self.assertEqual(len(tracks), 2)
        self.assertEqual(tracks[0].title, 'First Song')
        self.assertEqual(tracks[1].title, 'Second Song')

    def test_fetch_spotify_playlist_uses_next_loop_until_none(self) -> None:
        pages = [
            {"items": [{"track": {"name": "Song 1", "artists": [{"name": "Artist A"}], "album": {"name": "Album A"}, "duration_ms": 1000}}], "next": "https://api.spotify.com/v1/playlists/abc123/items?limit=100&offset=100", "total": 2},
            {"items": [{"track": {"name": "Song 2", "artists": [{"name": "Artist B"}], "album": {"name": "Album B"}, "duration_ms": 2000}}], "next": None, "total": 2},
        ]

        def fake_json_request(url: str, headers: dict | None = None, timeout: int | None = None, retries: int | None = None) -> dict:
            if url == 'https://api.spotify.com/v1/me':
                return {'id': 'owner'}
            if url == 'https://api.spotify.com/v1/playlists/abc123':
                return {'owner': {'id': 'owner'}, 'collaborative': False}
            if url.startswith('https://api.spotify.com/v1/playlists/abc123/items'):
                page = pages.pop(0)
                return page
            raise AssertionError(f'Unexpected URL: {url}')

        with patch.object(playlist_ops, '_load_spotify_client_id', return_value='id'):
            with patch.object(playlist_ops, 'get_spotify_user_token', return_value='token'):
                with patch.object(playlist_ops, '_spotify_json_request', side_effect=fake_json_request):
                    tracks = playlist_ops.fetch_spotify_playlist('https://open.spotify.com/playlist/abc123')

        self.assertEqual(len(tracks), 2)
        self.assertEqual(tracks[0].title, 'Song 1')
        self.assertEqual(tracks[1].title, 'Song 2')

    def test_fetch_spotify_playlist_raises_clear_error_when_no_tracks(self) -> None:
        def fake_json_request(url: str, headers: dict | None = None, timeout: int | None = None, retries: int | None = None) -> dict:
            if url == 'https://api.spotify.com/v1/me':
                return {'id': 'owner'}
            if url == 'https://api.spotify.com/v1/playlists/abc123':
                return {'owner': {'id': 'owner'}, 'collaborative': False}
            if url.startswith('https://api.spotify.com/v1/playlists/abc123/items'):
                return {'items': [], 'next': None, 'total': 0}
            raise AssertionError(f'Unexpected URL: {url}')

        with patch.object(playlist_ops, '_load_spotify_client_id', return_value='id'):
            with patch.object(playlist_ops, 'get_spotify_user_token', return_value='token'):
                with patch.object(playlist_ops, '_spotify_json_request', side_effect=fake_json_request):
                    with self.assertRaisesRegex(RuntimeError, "No tracks were returned"):
                        playlist_ops.fetch_spotify_playlist('https://open.spotify.com/playlist/abc123')

    def test_fetch_spotify_playlist_handles_new_item_field(self) -> None:
        def fake_json_request(url: str, headers: dict | None = None, timeout: int | None = None, retries: int | None = None) -> dict:
            if url == 'https://api.spotify.com/v1/me':
                return {'id': 'owner'}
            if url == 'https://api.spotify.com/v1/playlists/abc123':
                return {'owner': {'id': 'owner'}, 'collaborative': False}
            if url.startswith('https://api.spotify.com/v1/playlists/abc123/items'):
                return {
                    'items': [{
                        'item': {
                            'name': 'New Schema Song',
                            'artists': [{'name': 'New Artist'}],
                            'album': {'name': 'New Album'},
                            'duration_ms': 200000,
                        }
                    }],
                    'next': None,
                    'total': 1,
                }
            raise AssertionError(f'Unexpected URL: {url}')

        with patch.object(playlist_ops, '_load_spotify_client_id', return_value='id'):
            with patch.object(playlist_ops, 'get_spotify_user_token', return_value='token'):
                with patch.object(playlist_ops, '_spotify_json_request', side_effect=fake_json_request):
                    tracks = playlist_ops.fetch_spotify_playlist('https://open.spotify.com/playlist/abc123')

        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].title, 'New Schema Song')
        self.assertEqual(tracks[0].artist, 'New Artist')

    def test_fetch_live_playlist_exceeds_1000_tracks(self) -> None:
        client_id = playlist_ops._load_spotify_client_id()
        if not client_id:
            self.skipTest('Live Spotify playlist verification requires an app Client ID; public playlists are rate-limited without them.')
        if not playlist_ops.get_spotify_user_token():
            self.skipTest('Live Spotify playlist verification requires the user to be logged in and authorized for the app.')
        url = 'https://open.spotify.com/playlist/644soUNhgCjMB5eSr99Agfsi=4f990a6046e8472d'
        try:
            tracks = playlist_ops.fetch_spotify_playlist(url)
        except RuntimeError as exc:
            message = str(exc).lower()
            if (
                '400' in message or '401' in message or '404' in message or 'invalid' in message
                or 'expired' in message or 'rate-limited' in message or 'not owned' in message
            ):
                self.skipTest(f'Live Spotify verification skipped because the saved credentials are invalid, rate-limited, or the playlist is not owned by the logged-in user: {exc}')
            raise
        self.assertGreaterEqual(len(tracks), 1000)
