"""YouTube playlist creation: turn a fetched/converted tracklist into a real YouTube playlist.

Uses the official YouTube Data API v3 (OAuth "installed app" flow) to search for each track
and add the best match to a newly created playlist. This requires a one-time Google Cloud
OAuth Client ID + Secret (Google's installed-app flow always issues both, even though the
secret isn't treated as confidential for desktop apps - unlike Spotify, there is no secretless
option here).
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable

from app.features.playlist.ops import PlaylistTrack
from app.system.settings import get_setting

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube"]


@dataclass
class YouTubePlaylistResult:
    playlist_id: str
    playlist_url: str
    matched: int
    unmatched: list[str] = field(default_factory=list)


def _load_youtube_client_config() -> dict[str, Any] | None:
    """Read the optional Google OAuth Client ID/Secret from env vars or app settings."""
    client_id = str(os.getenv("YOUTUBE_CLIENT_ID") or get_setting("youtube/client_id", "") or "")
    client_secret = str(os.getenv("YOUTUBE_CLIENT_SECRET") or get_setting("youtube/client_secret", "") or "")
    if not client_id or not client_secret:
        return None
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def _youtube_token_cache_path() -> str:
    cache_dir = os.path.join(os.path.expanduser("~"), ".fosseverything")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "youtube_token.json")


def clear_youtube_token_cache() -> None:
    """Delete the cached YouTube OAuth token so stale app/account tokens are not reused."""
    path = _youtube_token_cache_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:  # noqa: 10 (best-effort cache clear, not required for correctness)
            pass


def _import_state_path() -> str:
    cache_dir = os.path.join(os.path.expanduser("~"), ".fosseverything")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "youtube_import_state.json")


def _import_key(tracks: list[PlaylistTrack], playlist_title: str) -> str:
    payload = playlist_title + "|" + str(len(tracks)) + "|" + "|".join(
        f"{t.artist}-{t.title}" for t in tracks
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_import_state(key: str) -> dict[str, Any] | None:
    path = _import_state_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        return None
    return state if state.get("key") == key else None


def _save_import_state(state: dict[str, Any]) -> None:
    with open(_import_state_path(), "w", encoding="utf-8") as f:
        json.dump(state, f)


def clear_import_state() -> None:
    """Discard any in-progress YouTube playlist import, so the next attempt starts fresh."""
    path = _import_state_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:  # noqa: 10 (best-effort cache clear, not required for correctness)
            pass


def get_resumable_import(tracks: list[PlaylistTrack], playlist_title: str) -> tuple[int, int] | None:
    """Return (already_added, total) if a matching in-progress import can be resumed."""
    state = _load_import_state(_import_key(tracks, playlist_title))
    if state is None:
        return None
    return state["next_index"], state["total"]


def get_youtube_credentials(interactive: bool) -> Any | None:
    """Return valid cached YouTube credentials, refreshing if needed.

    If `interactive` is True and no valid cached token exists, opens a browser for the
    Google OAuth consent flow. If False, returns None instead of prompting.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    cache_path = _youtube_token_cache_path()
    creds = None
    if os.path.exists(cache_path):
        try:
            creds = Credentials.from_authorized_user_file(cache_path, YOUTUBE_SCOPES)
        except Exception:
            creds = None
            clear_youtube_token_cache()

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            return creds
        except Exception:
            clear_youtube_token_cache()
            creds = None

    if not interactive:
        return None

    from google_auth_oauthlib.flow import InstalledAppFlow

    client_config = _load_youtube_client_config()
    if client_config is None:
        raise RuntimeError(
            "YouTube API access is not configured. Save a valid Client ID and Client Secret first."
        )

    try:
        flow = InstalledAppFlow.from_client_config(client_config, scopes=YOUTUBE_SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True, prompt="consent")
    except Exception as exc:
        if "org_internal" in str(exc):
            raise RuntimeError(
                "YouTube login failed: this app's Google Cloud OAuth consent screen is set to "
                "'Internal', which restricts login to accounts inside one Google Workspace organization.\n"
                "Go to Google Cloud Console > APIs & Services > OAuth consent screen > Audience, "
                "and change User Type to 'External' (this puts the app in 'Testing' status, where you "
                "must add the signing-in Google account under Test users).\n\n"
                f"Details: {exc}"
            ) from exc
        raise RuntimeError(
            "YouTube login failed. If this happens right after signing in, the app is usually in "
            "Google's 'Testing' publishing status and your Google account is not listed as a test user.\n"
            "Go to Google Cloud Console > APIs & Services > OAuth consent screen > Audience, "
            "and add the signing-in Google account under Test users.\n\n"
            f"Details: {exc}"
        ) from exc

    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    return creds


def start_youtube_login() -> bool:
    """Open a browser for the Google OAuth flow and cache the resulting user token."""
    creds = get_youtube_credentials(interactive=True)
    return creds is not None


def has_youtube_login() -> bool:
    return get_youtube_credentials(interactive=False) is not None


def _build_youtube_client() -> Any:
    from googleapiclient.discovery import build

    creds = get_youtube_credentials(interactive=False)
    if creds is None:
        raise RuntimeError("YouTube login is required. Click 'Log in with YouTube' first.")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def _search_youtube_video_id(youtube: Any, query: str) -> str | None:
    from googleapiclient.errors import HttpError

    try:
        response = youtube.search().list(
            part="id", q=query, type="video", maxResults=1, videoCategoryId="10"
        ).execute()
        items = response.get("items") or []
        if not items:
            response = youtube.search().list(part="id", q=query, type="video", maxResults=1).execute()
            items = response.get("items") or []
        if not items:
            return None
        return items[0]["id"]["videoId"]
    except HttpError as exc:
        if "quota" in str(exc).lower():
            raise RuntimeError(
                "YouTube API daily quota was exceeded partway through this playlist. "
                "The quota resets daily (Pacific time); try again later or convert a smaller batch."
            ) from exc
        raise


def create_youtube_playlist(youtube: Any, title: str, description: str = "", privacy_status: str = "private") -> str:
    body = {
        "snippet": {"title": title, "description": description},
        "status": {"privacyStatus": privacy_status},
    }
    response = youtube.playlists().insert(part="snippet,status", body=body).execute()
    return response["id"]


def add_video_to_playlist(youtube: Any, playlist_id: str, video_id: str) -> None:
    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
    }
    youtube.playlistItems().insert(part="snippet", body=body).execute()


def build_youtube_playlist_from_tracks(
    tracks: list[PlaylistTrack],
    playlist_title: str,
    privacy_status: str = "private",
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> YouTubePlaylistResult:
    """Create (or resume) a real YouTube playlist and populate it by searching for each track.

    If a previous call for the same tracks/title ran out of API quota partway through, this
    picks up where it left off and keeps adding to the same playlist instead of starting over.
    """
    if not tracks:
        raise ValueError("No tracks to add - fetch or convert a playlist first.")

    youtube = _build_youtube_client()
    key = _import_key(tracks, playlist_title)
    total = len(tracks)
    state = _load_import_state(key)

    if state is not None:
        playlist_id = state["playlist_id"]
        start_index = state["next_index"]
        matched = state["matched"]
        unmatched = list(state["unmatched"])
    else:
        playlist_id = create_youtube_playlist(
            youtube, playlist_title, description="Created by FOSSEverything Playlist Porter"
        )
        start_index = 0
        matched = 0
        unmatched = []
        state = {
            "key": key, "playlist_id": playlist_id, "total": total,
            "next_index": 0, "matched": 0, "unmatched": [],
        }
        _save_import_state(state)

    try:
        for index in range(start_index, total):
            track = tracks[index]
            query = f"{track.artist} - {track.title}" if track.artist else track.title
            if progress_cb:
                progress_cb(index + 1, total, track.title or query)
            video_id = _search_youtube_video_id(youtube, query)
            if video_id:
                try:
                    add_video_to_playlist(youtube, playlist_id, video_id)
                    matched += 1
                except Exception:
                    unmatched.append(query)
            else:
                unmatched.append(query)

            state["next_index"] = index + 1
            state["matched"] = matched
            state["unmatched"] = unmatched
            _save_import_state(state)
    except RuntimeError as exc:
        if "quota" in str(exc).lower():
            remaining = total - state["next_index"]
            raise RuntimeError(
                f"Added {matched} of {total} tracks before hitting today's YouTube API quota. "
                f"{remaining} track(s) remain. Click 'Create YouTube Playlist...' again after the "
                "quota resets (about 24 hours, Pacific time) to keep adding to the same playlist."
            ) from exc
        raise

    clear_import_state()
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    return YouTubePlaylistResult(playlist_id=playlist_id, playlist_url=playlist_url, matched=matched, unmatched=unmatched)
