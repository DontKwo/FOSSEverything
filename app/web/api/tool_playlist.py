import socket
import urllib.error
from pathlib import Path
from typing import Any

from app.features.playlist.ops import (
    build_track,
    export_csv_playlist,
    export_json_playlist,
    export_m3u8_playlist,
    fetch_playlist_from_url,
    get_spotify_user_token,
    parse_tracklist_text,
    start_spotify_user_login,
    _clear_spotify_user_token_cache,
)
from app.features.playlist.youtube_ops import (
    YouTubePlaylistResult,
    build_youtube_playlist_from_tracks,
    clear_youtube_token_cache,
    get_resumable_import,
    has_youtube_login,
    start_youtube_login,
)
from app.system.settings import get_setting, set_setting
from app.web.api.result import api_method, fail, ok, require


def _describe_fetch_error(exc: Exception) -> str:
    # Turn a remote fetch exception into a short, user-readable reason.
    if isinstance(exc, urllib.error.HTTPError):
        return f"The server answered HTTP {exc.code} ({exc.reason}). The playlist may be private, removed, or rate limited."
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return f"The request timed out. {exc}".strip()
    if isinstance(exc, urllib.error.URLError):
        return f"Could not reach the server: {exc.reason}. Check your internet connection."
    if isinstance(exc, ConnectionError):
        return f"The connection was interrupted: {exc}"
    message = str(exc).strip()
    return message if message else f"{exc.__class__.__name__} while fetching the playlist."


class PlaylistApiMixin:
    @api_method
    def playlist_fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        # Fetch tracks from a Spotify or YouTube playlist URL.
        require(params, "url")
        url = str(params["url"]).strip()
        try:
            tracks = fetch_playlist_from_url(url)
        except Exception as exc:
            return fail(_describe_fetch_error(exc), code="FetchError")
        track_dicts = [t.to_dict() for t in tracks]
        return ok(tracks=track_dicts, count=len(tracks))

    @api_method
    def playlist_parse_text(self, params: dict[str, Any]) -> dict[str, Any]:
        # Parse plain-text lines formatted as Artist - Title into tracks.
        require(params, "text")
        raw_text = str(params["text"])
        tracks = parse_tracklist_text(raw_text)
        track_dicts = [t.to_dict() for t in tracks]
        return ok(tracks=track_dicts, count=len(tracks))

    @api_method
    def playlist_import_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Import tracks from local playlist file (m3u, m3u8, csv, txt).
        target_path_str = params.get("file_path") or params.get("path")
        if not target_path_str:
            return fail("Missing required parameter: file_path")
        p = Path(str(target_path_str))
        if not p.exists():
            return fail(f"File not found: {p}")
        text = p.read_text(encoding="utf-8", errors="replace")
        tracks = parse_tracklist_text(text)
        track_dicts = [t.to_dict() for t in tracks]
        return ok(tracks=track_dicts, count=len(tracks), file_path=str(p.resolve()))

    @api_method
    def playlist_export_csv(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export track list to CSV spreadsheet file.
        require(params, "tracks", "output_path")
        tracks = [
            build_track(
                artist=str(t.get("artist", "")),
                title=str(t.get("title", "")),
                album=str(t.get("album", "")),
            )
            for t in params["tracks"]
        ]
        out_p = str(params["output_path"])
        export_csv_playlist(tracks, out_p)
        return ok(output_path=out_p)

    @api_method
    def playlist_export_m3u8(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export track list to M3U8 multimedia playlist file.
        require(params, "tracks", "output_path")
        tracks = [
            build_track(
                artist=str(t.get("artist", "")),
                title=str(t.get("title", "")),
                album=str(t.get("album", "")),
            )
            for t in params["tracks"]
        ]
        out_p = str(params["output_path"])
        export_m3u8_playlist(tracks, out_p)
        return ok(output_path=out_p)

    @api_method
    def playlist_export_json(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export track list to a JSON file.
        require(params, "tracks", "output_path")
        tracks = [
            build_track(
                artist=str(t.get("artist", "")),
                title=str(t.get("title", "")),
                album=str(t.get("album", "")),
            )
            for t in params["tracks"]
        ]
        out_p = str(params["output_path"])
        export_json_playlist(tracks, out_p)
        return ok(output_path=out_p)

    @api_method
    def playlist_spotify_auth(self, params: dict[str, Any]) -> dict[str, Any]:
        # Manage Spotify authentication and user token cache.
        action = str(params.get("action", "status")).lower()
        if "client_id" in params:
            set_setting("spotify/client_id", str(params["client_id"]).strip())
        if action == "save_client_id":
            return ok(saved=True)
        if action == "login":
            token = start_spotify_user_login()
            return ok(logged_in=bool(token), token=token)
        elif action == "clear":
            _clear_spotify_user_token_cache()
            return ok(cleared=True)
        token = get_spotify_user_token()
        client_id = get_setting("spotify/client_id", "")
        return ok(has_token=bool(token), client_id=client_id)

    @api_method
    def playlist_youtube_auth(self, params: dict[str, Any]) -> dict[str, Any]:
        # Manage YouTube OAuth login credentials.
        action = str(params.get("action", "status")).lower()
        if "client_id" in params:
            set_setting("youtube/client_id", str(params["client_id"]).strip())
        if "client_secret" in params:
            set_setting("youtube/client_secret", str(params["client_secret"]).strip())
        if action == "save_credentials":
            return ok(saved=True)
        if action == "login":
            logged_in = start_youtube_login()
            return ok(logged_in=bool(logged_in))
        elif action == "clear":
            clear_youtube_token_cache()
            return ok(cleared=True)
        logged_in = has_youtube_login()
        client_id = get_setting("youtube/client_id", "")
        return ok(has_login=logged_in, client_id=client_id)

    @api_method
    def playlist_youtube_build(self, params: dict[str, Any]) -> dict[str, Any]:
        # Recreate tracklist on YouTube account as new playlist.
        require(params, "playlist_title", "tracks")
        title = str(params["playlist_title"])
        tracks = [
            build_track(
                artist=str(t.get("artist", "")),
                title=str(t.get("title", "")),
                album=str(t.get("album", "")),
            )
            for t in params["tracks"]
        ]
        res: YouTubePlaylistResult = build_youtube_playlist_from_tracks(tracks, title)
        resumable = get_resumable_import(tracks, title)
        return ok(playlist_id=res.playlist_id, playlist_url=res.playlist_url, added_count=res.matched, resumable=bool(resumable))
