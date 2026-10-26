from typing import Any

from app.features.playlist import youtube_ops
from app.features.playlist.ops import (
    _clear_spotify_user_token_cache,
    detect_url_platform,
    export_csv_playlist,
    export_m3u8_playlist,
    fetch_playlist_from_url,
    get_spotify_user_token,
    parse_tracklist_text,
    start_spotify_user_login,
)
from app.features.playlist.youtube_ops import (
    YouTubePlaylistResult,
    build_youtube_playlist_from_tracks,
    clear_youtube_token_cache,
    get_resumable_import,
    has_youtube_login,
    start_youtube_login,
)
from app.web.api.result import api_method, ok, require


class PlaylistApiMixin:
    @api_method
    def playlist_fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        # Fetch playlist track metadata from Spotify or YouTube URL.
        require(params, "url")
        url = str(params["url"]).strip()
        platform = detect_url_platform(url)
        tracks = fetch_playlist_from_url(url)
        track_list = [
            {
                "title": t.title,
                "artist": t.artist,
                "album": t.album,
                "duration": t.duration_ms // 1000 if t.duration_ms else 0,
            }
            for t in tracks
        ]
        return ok(tracks=track_list, count=len(track_list), platform=platform)

    @api_method
    def playlist_parse_text(self, params: dict[str, Any]) -> dict[str, Any]:
        # Parse freeform text or tracklist list into structured tracks.
        require(params, "text")
        text = str(params["text"])
        tracks = parse_tracklist_text(text)
        track_list = [{"title": t.title, "artist": t.artist} for t in tracks]
        return ok(tracks=track_list, count=len(track_list))

    @api_method
    def playlist_export_csv(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export track list to CSV spreadsheet file.
        require(params, "tracks", "output_path")
        from app.features.playlist.ops import build_track
        tracks = [build_track(str(t.get("title", "")), artist=str(t.get("artist", ""))) for t in params["tracks"]]
        out_p = str(params["output_path"])
        export_csv_playlist(tracks, out_p)
        return ok(output_path=out_p)

    @api_method
    def playlist_export_m3u8(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export track list to M3U8 multimedia playlist file.
        require(params, "tracks", "output_path")
        from app.features.playlist.ops import build_track
        tracks = [build_track(str(t.get("title", "")), artist=str(t.get("artist", ""))) for t in params["tracks"]]
        out_p = str(params["output_path"])
        export_m3u8_playlist(tracks, out_p)
        return ok(output_path=out_p)

    @api_method
    def playlist_spotify_auth(self, params: dict[str, Any]) -> dict[str, Any]:
        # Manage Spotify authentication and user token cache.
        action = str(params.get("action", "status")).lower()
        if action == "login":
            require(params, "client_id", "client_secret")
            token = start_spotify_user_login(str(params["client_id"]), str(params["client_secret"]))
            return ok(logged_in=bool(token), token=token)
        elif action == "clear":
            _clear_spotify_user_token_cache()
            return ok(cleared=True)
        token = get_spotify_user_token()
        return ok(has_token=bool(token))

    @api_method
    def playlist_youtube_auth(self, params: dict[str, Any]) -> dict[str, Any]:
        # Manage YouTube OAuth login credentials.
        action = str(params.get("action", "status")).lower()
        if action == "login":
            creds = start_youtube_login()
            return ok(logged_in=bool(creds))
        elif action == "clear":
            clear_youtube_token_cache()
            return ok(cleared=True)
        logged_in = has_youtube_login()
        return ok(has_login=logged_in)

    @api_method
    def playlist_youtube_build(self, params: dict[str, Any]) -> dict[str, Any]:
        # Recreate tracklist on YouTube account as new playlist.
        require(params, "playlist_title", "tracks")
        title = str(params["playlist_title"])
        from app.features.playlist.ops import build_track
        tracks = [build_track(str(t.get("title", "")), artist=str(t.get("artist", ""))) for t in params["tracks"]]
        res: YouTubePlaylistResult = build_youtube_playlist_from_tracks(title, tracks)
        resumable = get_resumable_import(title)
        return ok(playlist_id=res.playlist_id, playlist_url=res.playlist_url, added_count=res.added_count, resumable=bool(resumable))
