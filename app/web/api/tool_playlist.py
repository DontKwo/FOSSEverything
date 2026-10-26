from typing import Any

from app.features.playlist import youtube_ops
from app.features.playlist.ops import (
    PlaylistTrack,
    _clear_spotify_user_token_cache,
    build_track,
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
from app.system.settings import get_setting, set_setting
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
                "duration": t.duration_str,
                "spotify_url": t.spotify_url,
                "youtube_url": t.youtube_url,
                "youtube_music_url": t.youtube_music_url,
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
        track_list = [
            {
                "title": t.title,
                "artist": t.artist,
                "album": t.album,
                "duration": t.duration_str,
                "spotify_url": t.spotify_url,
                "youtube_url": t.youtube_url,
                "youtube_music_url": t.youtube_music_url,
            }
            for t in tracks
        ]
        return ok(tracks=track_list, count=len(track_list))

    @api_method
    def playlist_export_csv(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export track list to CSV spreadsheet file.
        require(params, "tracks", "output_path")
        tracks = [build_track(artist=str(t.get("artist", "")), title=str(t.get("title", ""))) for t in params["tracks"]]
        out_p = str(params["output_path"])
        export_csv_playlist(tracks, out_p)
        return ok(output_path=out_p)

    @api_method
    def playlist_export_m3u8(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export track list to M3U8 multimedia playlist file.
        require(params, "tracks", "output_path")
        tracks = [build_track(artist=str(t.get("artist", "")), title=str(t.get("title", ""))) for t in params["tracks"]]
        out_p = str(params["output_path"])
        export_m3u8_playlist(tracks, out_p)
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
        tracks = [build_track(artist=str(t.get("artist", "")), title=str(t.get("title", ""))) for t in params["tracks"]]
        res: YouTubePlaylistResult = build_youtube_playlist_from_tracks(title, tracks)
        resumable = get_resumable_import(tracks, title)
        return ok(playlist_id=res.playlist_id, playlist_url=res.playlist_url, added_count=res.matched, resumable=bool(resumable))
