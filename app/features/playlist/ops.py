"""Playlist Porter: convert playlists and tracklists between Spotify and YouTube / YouTube Music.

Supports:
- Direct Spotify playlist URLs using authenticated Spotify user OAuth
- Direct YouTube / YouTube Music playlist URLs (uses yt-dlp subprocess)
- Pasted tracklist text, CSV rows, M3U8 files
"""
from __future__ import annotations

import os
import re
import csv
import json
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from typing import TYPE_CHECKING, Any, Callable

from app.system.settings import get_setting

if TYPE_CHECKING:
    from spotipy.oauth2 import SpotifyPKCE

SPOTIFY_TIMEOUT_SECONDS = 60


@dataclass
class PlaylistTrack:
    title: str
    artist: str
    album: str = ""
    duration_str: str = ""
    spotify_url: str = ""
    youtube_url: str = ""
    youtube_music_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Patterns to strip from music video titles to recover clean song names
JUNK_PATTERNS = [
    r"\((?:official\s*|music\s*|hd\s*|4k\s*|hq\s*)*(?:video|audio|visualizer|lyric\s*video|mv)\)",
    r"\[(?:official\s*|music\s*|hd\s*|4k\s*|hq\s*)*(?:video|audio|visualizer|lyric\s*video|mv)\]",
    r"\(lyric\s*video\)",
    r"\[lyric\s*video\]",
    r"\(lyrics\)",
    r"\[lyrics\]",
    r"\(audio\)",
    r"\[audio\]",
    r"\(video\)",
    r"\[video\]",
    r"\(hd\)",
    r"\[hd\]",
    r"\(4k\)",
    r"\[4k\]",
    r"\(remastered\s*\d{4}\)",
    r"\[remastered\s*\d{4}\]",
    r"\(explicit\s*version\)",
    r"\[explicit\s*version\]",
    r"\(clean\s*version\)",
    r"\[clean\s*version\]",
    r"\(live(?:\s*at\s*.*)?\)",
    r"\[live(?:\s*at\s*.*)?\]",
    r"\(full\s*album\)",
    r"\[full\s*album\]",
]


def _strip_junk(text: str) -> str:
    """Apply junk pattern removal and clean up resulting artifacts."""
    for pat in JUNK_PATTERNS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    # Remove leftover empty brackets, parens, and dangling bracket chars
    text = re.sub(r"\(\s*\)|\[\s*\]", "", text)
    # Remove dangling opening or closing brackets/parens at end of string
    text = re.sub(r"[\(\[\s]+$", "", text).strip()
    # Normalize multiple spaces
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def clean_music_title(raw_title: str) -> tuple[str, str]:
    """Parse messy YouTube / video titles into clean (Artist, Track Title)."""
    t = raw_title.strip()

    # Remove URL if pasted
    t = re.sub(r"https://\S+", "", t).strip()

    # Apply junk removal first
    t = _strip_junk(t)

    # Split by standard delimiters (Artist - Title)
    delimiters = [" - ", " - ", " - ", " : ", " | "]
    for delim in delimiters:
        if delim in t:
            parts = t.split(delim, 1)
            artist = parts[0].strip()
            title = parts[1].strip()
            # Apply junk removal again to each part
            artist = _strip_junk(artist)
            title = _strip_junk(title)
            # Remove trailing feat/ft in title
            title = re.sub(r"\s*\(feat\.\s+.*\)$", "", title, flags=re.IGNORECASE).strip()
            return artist, title

    # If no delimiter, check if quotes used e.g. Artist "Song Name"
    quote_match = re.match(r'^([^"\'\(]+)\s*["\']([^"\']+)["\']', t)
    if quote_match:
        return quote_match.group(1).strip(), quote_match.group(2).strip()

    # Fallback: whole string is title, artist is unknown
    return "", t


def build_track(artist: str, title: str, album: str = "") -> PlaylistTrack:
    """Build a rich PlaylistTrack with direct query links."""
    clean_artist = artist.strip()
    clean_title = title.strip()

    if clean_artist and clean_title:
        search_query = f"{clean_artist} - {clean_title}"
    elif clean_title:
        search_query = clean_title
    else:
        search_query = clean_artist or "Unknown Track"

    encoded_q = urllib.parse.quote(search_query)

    yt_url = f"https://www.youtube.com/results?search_query={encoded_q}"
    ytm_url = f"https://music.youtube.com/search?q={encoded_q}"
    sp_url = f"https://open.spotify.com/search/{encoded_q}"

    return PlaylistTrack(
        title=clean_title or search_query,
        artist=clean_artist,
        album=album,
        spotify_url=sp_url,
        youtube_url=yt_url,
        youtube_music_url=ytm_url,
    )


def parse_tracklist_text(text: str) -> list[PlaylistTrack]:
    """Parse raw text, lines of 'Artist - Song', numbered lists, or URLs."""
    tracks = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        if line.startswith("#"):
            continue

        # Strip numbering: '1. Song' or '01 - Song' or '1) Song'
        line_clean = re.sub(r"^\d+[\.\)\-\s]+\s*", "", line).strip()
        if not line_clean:
            continue

        # Check if CSV line: "Title, Artist, Album"
        if "," in line_clean and ('"' in line_clean or len(line_clean.split(",")) in (2, 3)):
            try:
                reader = csv.reader([line_clean])
                row = next(reader)
                if len(row) >= 2:
                    t, a = row[0].strip(), row[1].strip()
                    alb = row[2].strip() if len(row) > 2 else ""
                    tracks.append(build_track(a, t, alb))
                    continue
            except Exception:  # noqa: 10 (fall through to plain-text parsing below)
                pass

        artist, title = clean_music_title(line_clean)
        tracks.append(build_track(artist, title))

    return tracks


def export_m3u8_playlist(tracks: list[PlaylistTrack], output_path: str, use_youtube_music: bool = True) -> str:
    """Export track list as standard extended M3U8 playlist with playable URLs."""
    lines = ["#EXTM3U", "#PLAYLIST:FOSSEverything Exported Playlist"]
    for tr in tracks:
        display = f"{tr.artist} - {tr.title}" if tr.artist else tr.title
        lines.append(f"#EXTINF:-1,{display}")
        url = tr.youtube_music_url if use_youtube_music else tr.youtube_url
        lines.append(url)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return output_path


def export_csv_playlist(tracks: list[PlaylistTrack], output_path: str) -> str:
    """Export tracks to universal CSV format (Title, Artist, Album, Spotify URL, YouTube URL)."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "Artist", "Album", "Spotify Search", "YouTube Search", "YouTube Music"])
        for tr in tracks:
            writer.writerow([tr.title, tr.artist, tr.album, tr.spotify_url, tr.youtube_url, tr.youtube_music_url])
    return output_path


# ─── URL Detection & Platform Fetching ────────────────────────────────────────

def detect_url_platform(url: str) -> str | None:
    """Return 'spotify', 'youtube', or None based on the URL."""
    url = url.strip()
    if re.search(r"open\.spotify\.com/(playlist|album|track)", url, re.IGNORECASE):
        return "spotify"
    if re.search(r"(youtube\.com|youtu\.be|music\.youtube\.com)", url, re.IGNORECASE):
        return "youtube"
    return None


def _build_spotify_api_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": "Bearer " + access_token,
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
    }

def _spotify_urlopen(request: urllib.request.Request, timeout: int = SPOTIFY_TIMEOUT_SECONDS) -> urllib.response.addinfourl:
    """Open Spotify URLs with a SSL fallback so public playlist fetches still work in broken cert environments."""
    last_exc: Exception | None = None
    contexts = [None, ssl.create_default_context(), ssl._create_unverified_context()]
    for context in contexts:
        try:
            if context is None:
                return urllib.request.urlopen(request, timeout=timeout)
            return urllib.request.urlopen(request, timeout=timeout, context=context)
        except Exception as exc:  # pragma: no cover - fallback behavior is environment-dependent
            last_exc = exc
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Failed to open Spotify URL.")


def _spotify_json_request(url: str, headers: dict[str, str], timeout: int = SPOTIFY_TIMEOUT_SECONDS, retries: int = 5) -> dict[str, Any]:
    """Fetch a Spotify JSON payload with rate-limit retry/backoff and a hard overall timeout."""
    deadline = time.monotonic() + timeout
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Spotify request timed out after {timeout} seconds.")
        try:
            req = urllib.request.Request(url, headers=headers)
            with _spotify_urlopen(req, timeout=min(remaining, timeout)) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code != 429:
                raise
            if attempt >= retries:
                raise TimeoutError(
                    "Spotify rate-limited the request; retries were exhausted within the request timeout."
                ) from exc
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            try:
                delay = float(retry_after) if retry_after is not None else min(2 ** attempt, remaining)
            except (TypeError, ValueError):
                delay = min(2 ** attempt, remaining)
            delay = min(max(delay, 0.5), remaining)
            if delay <= 0:
                raise TimeoutError(f"Spotify request timed out after {timeout} seconds.") from exc
            time.sleep(delay)
        except Exception:
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Failed to fetch Spotify JSON payload.")


def _spotify_track_from_api_item(item: dict[str, Any]) -> PlaylistTrack | None:
    """Normalize a Spotify API list response item into a PlaylistTrack."""
    if not isinstance(item, dict):
        return None

    if "item" in item:
        track = item.get("item")
    elif "track" in item:
        track = item.get("track")
    else:
        track = item
    if not isinstance(track, dict):
        return None

    title = track.get("name") or ""
    if not title:
        return None

    artist_data = track.get("artists") or []
    artist = ", ".join(a.get("name", "") for a in artist_data if isinstance(a, dict) and a.get("name"))

    album = ""
    album_data = track.get("album")
    if isinstance(album_data, dict):
        album = album_data.get("name", "")

    playlist_track = build_track(artist, title, album=album)
    playlist_track.duration_str = _ms_to_duration(track.get("duration_ms") or 0)
    return playlist_track


def _load_spotify_client_id() -> str:
    """Read the optional Spotify app Client ID from env vars or app settings."""
    client_id = (
        os.getenv("SPOTIPY_CLIENT_ID")
        or os.getenv("SPOTIFY_CLIENT_ID")
        or get_setting("spotify/client_id", "")
    )
    return str(client_id or "")


def _clear_spotify_user_token_cache() -> None:
    """Delete the cached OAuth user token so stale app/account tokens are not reused."""
    cache_dir = os.path.join(os.path.expanduser("~"), ".fosseverything")
    cache_path = os.path.join(cache_dir, "spotify_user_token.cache")
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
        except OSError:  # noqa: 10 (best-effort cache clear, not required for correctness)
            pass


def _get_spotify_oauth_manager() -> SpotifyPKCE | None:
    """Build a user-auth Spotify PKCE OAuth manager pinned to the loopback redirect URI.

    PKCE needs only a public Client ID (no Client Secret), which is the correct flow for a
    desktop app that can't safely embed a secret.
    """
    from spotipy.oauth2 import CacheFileHandler, SpotifyPKCE  # noqa: 13 (deferred: only needed when Spotify features are used)

    client_id = _load_spotify_client_id()
    if not client_id:
        return None

    cache_dir = os.path.join(os.path.expanduser("~"), ".fosseverything")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "spotify_user_token.cache")
    redirect_uri = (
        os.getenv("SPOTIPY_REDIRECT_URI")
        or os.getenv("SPOTIFY_REDIRECT_URI")
        or "http://127.0.0.1:8888/callback"
    )

    scope = "playlist-read-private playlist-read-collaborative"
    return SpotifyPKCE(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_handler=CacheFileHandler(cache_path=cache_path),
        open_browser=True,
    )


def get_spotify_user_token() -> str | None:
    """Return a valid user access token, if the user has completed Spotify login."""
    oauth = _get_spotify_oauth_manager()
    if oauth is None:
        return None
    try:
        cached = oauth.cache_handler.get_cached_token()
        if cached is None:
            return None
        token_info = oauth.validate_token(cached)
        if token_info is None:
            _clear_spotify_user_token_cache()
            return None
        return token_info.get("access_token")
    except Exception:
        _clear_spotify_user_token_cache()
        return None


def start_spotify_user_login() -> str:
    """Open a browser for the Spotify PKCE auth flow and cache the resulting user token."""
    oauth = _get_spotify_oauth_manager()
    if oauth is None:
        raise RuntimeError("Spotify API access is not configured. Save a valid Client ID first.")

    try:
        cached = oauth.cache_handler.get_cached_token()
        if cached is not None:
            validated = oauth.validate_token(cached)
            if validated is not None and validated.get("access_token"):
                return validated["access_token"]
            _clear_spotify_user_token_cache()

        access_token = oauth.get_access_token(check_cache=True)
        if access_token:
            return access_token
        raise RuntimeError("Spotify login did not return an access token.")
    except Exception as exc:
        _clear_spotify_user_token_cache()
        raise RuntimeError(f"Spotify login failed: {exc}") from exc


def _validate_spotify_playlist_access(playlist_id: str, token: str) -> None:
    """Check that the signed-in Spotify user owns or collaborates on the playlist.

    Spotify's current Developer Mode rules only return track items for playlists owned by or
    collaboratively shared with the authenticated account. Other playlists may look valid but
    return a 403 / empty items list even with a correct OAuth flow.
    """
    try:
        me = _spotify_json_request(
            "https://api.spotify.com/v1/me",
            headers=_build_spotify_api_headers(token),
            timeout=SPOTIFY_TIMEOUT_SECONDS,
            retries=3,
        )
    except Exception as exc:
        raise RuntimeError(f"Could not verify the Spotify account identity: {exc}") from exc

    me_id = (me or {}).get("id")
    if not me_id:
        raise RuntimeError("Could not determine the signed-in Spotify user ID.")

    try:
        playlist_meta = _spotify_json_request(
            f"https://api.spotify.com/v1/playlists/{playlist_id}",
            headers=_build_spotify_api_headers(token),
            timeout=SPOTIFY_TIMEOUT_SECONDS,
            retries=3,
        )
    except Exception as exc:
        raise RuntimeError(f"Could not read the Spotify playlist metadata: {exc}") from exc

    owner = (playlist_meta or {}).get("owner") or {}
    owner_id = owner.get("id")
    collaborative = bool((playlist_meta or {}).get("collaborative"))

    if me_id == owner_id or collaborative:
        return

    raise RuntimeError(
        "Spotify playlist access check failed: this playlist is not owned by the signed-in Spotify account "
        "and it is not marked collaborative for that account. Under Spotify's current Developer Mode rules, "
        "playlist items are only returned for playlists you own or collaborate on. "
        "Log in as the playlist owner or ask the owner to add you as a collaborator and retry."
    )


def fetch_spotify_playlist(url: str, progress_cb: Callable[[int, int, str], None] | None = None) -> list[PlaylistTrack]:
    """Fetch all tracks from a Spotify playlist/album URL using the authenticated user flow only."""
    from spotipy.exceptions import SpotifyException  # noqa: 13 (deferred: only needed when Spotify features are used)

    m = re.search(r"open\.spotify\.com/(playlist|album)/([A-Za-z0-9]+)", url)
    if not m:
        raise ValueError(
            "Could not parse Spotify playlist/album ID from URL.\n"
            "Expected format: https://open.spotify.com/playlist/..."
        )

    kind, playlist_id = m.group(1), m.group(2)
    client_id = _load_spotify_client_id()
    if not client_id:
        raise RuntimeError(
            "Spotify playlist imports require a valid Client ID. "
            "Save it in the Playlist tab and log in with Spotify before fetching a playlist."
        )

    user_token = get_spotify_user_token()
    if not user_token:
        raise RuntimeError(
            "Spotify user login is required for playlist imports. "
            "Click 'Log in with Spotify' in the Playlist tab and retry."
        )

    if kind == "playlist":
        _validate_spotify_playlist_access(playlist_id, user_token)

    endpoint = (
        f"https://api.spotify.com/v1/playlists/{playlist_id}/items"
        if kind == "playlist"
        else f"https://api.spotify.com/v1/albums/{playlist_id}/tracks"
    )
    offset = 0
    tracks: list[PlaylistTrack] = []
    seen_offsets: set[int] = set()
    try:
        while True:
            if offset in seen_offsets:
                break
            seen_offsets.add(offset)
            api_url = f"{endpoint}?limit=100&offset={offset}"
            payload = _spotify_json_request(
                api_url,
                headers=_build_spotify_api_headers(user_token),
                timeout=SPOTIFY_TIMEOUT_SECONDS,
                retries=5,
            )
            items = payload.get("items") or []
            total = payload.get("total") or 0
            if not items:
                break
            for item in items:
                playlist_track = _spotify_track_from_api_item(item)
                if playlist_track is None:
                    continue
                if progress_cb:
                    progress_cb(len(tracks) + 1, total or len(tracks) + 1, playlist_track.title)
                tracks.append(playlist_track)

            fetched = offset + len(items)
            if total and fetched >= total:
                break
            next_url = payload.get("next")
            if next_url:
                parsed = urllib.parse.urlparse(next_url)
                next_params = urllib.parse.parse_qs(parsed.query)
                next_offset_value = next_params.get("offset", [str(offset)])[0]
                try:
                    offset = int(next_offset_value)
                    continue
                except ValueError:
                    break
            if total and fetched < total:
                offset = fetched
                continue
            break
        if tracks:
            return tracks
        raise RuntimeError("No tracks were returned for this Spotify playlist.")
    except (TimeoutError, urllib.error.HTTPError, SpotifyException) as exc:
        _clear_spotify_user_token_cache()
        if progress_cb:
            progress_cb(0, 0, "")
        message = (
            "Spotify user-auth request failed. Please log in again to Spotify from the Playlist tab and retry.\n\n"
            "If this happens immediately after logging in, Spotify is usually rejecting the token because the app is in development mode and your account is not allowlisted.\n"
            "Go to the Spotify Developer Dashboard, open your app, then open Settings > Users Management and add the Spotify email that is signing in.\n"
            "The app owner also typically needs a Spotify Premium account for development mode to work.\n\n"
            f"Details: {exc}"
        )
        raise RuntimeError(message) from exc


def fetch_youtube_playlist(url: str, progress_cb: Callable[[int, int, str], None] | None = None) -> list[PlaylistTrack]:
    """Fetch tracks from a YouTube or YouTube Music playlist URL using yt-dlp.

    yt-dlp must be installed (pip install yt-dlp). No authentication required
    for public playlists.
    """
    import shutil
    ytdlp = shutil.which("yt-dlp") or shutil.which("yt_dlp")
    if not ytdlp:
        # Try as a Python module
        ytdlp = None

    cmd_base = [ytdlp or "yt-dlp"] if ytdlp else ["python", "-m", "yt_dlp"]
    cmd = cmd_base + [
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        "--quiet",
        url,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "yt-dlp is not installed or not on PATH.\n"
            "Install it with:  pip install yt-dlp\n"
            "or:               uv pip install yt-dlp"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("yt-dlp timed out. The playlist may be very large or the network is slow.") from exc

    if result.returncode not in (0, 1):  # yt-dlp returns 1 on partial success
        raise RuntimeError(f"yt-dlp failed:\n{result.stderr[:500]}")

    tracks = []
    lines = [ln for ln in result.stdout.splitlines() if ln.strip().startswith("{")]
    total = len(lines)
    for i, line in enumerate(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        raw_title = entry.get("title", "")
        raw_channel = entry.get("channel") or entry.get("uploader", "")
        duration_secs = entry.get("duration") or 0
        duration_str = _secs_to_duration(int(duration_secs))

        artist, title = clean_music_title(raw_title)
        # If splitting failed and channel name looks like an artist, use it
        if not artist and raw_channel:
            # Strip common channel suffixes like "- Topic", "VEVO", "Official"
            channel_clean = re.sub(
                r"\s*[-]\s*(topic|vevo|official|music|records)\s*$",
                "", raw_channel, flags=re.IGNORECASE
            ).strip()
            artist = channel_clean

        if progress_cb:
            progress_cb(i + 1, total, title or raw_title)

        track = build_track(artist, title or raw_title)
        track.duration_str = duration_str
        tracks.append(track)

    if not tracks:
        raise RuntimeError(
            "No tracks were returned by yt-dlp. The playlist may be private, empty, or the URL is invalid."
        )
    return tracks


def fetch_playlist_from_url(url: str, progress_cb: Callable[[int, int, str], None] | None = None) -> list[PlaylistTrack]:
    """Auto-detect platform and fetch tracks from a Spotify or YouTube playlist URL."""
    platform = detect_url_platform(url)
    if platform == "spotify":
        return fetch_spotify_playlist(url, progress_cb=progress_cb)
    elif platform == "youtube":
        return fetch_youtube_playlist(url, progress_cb=progress_cb)
    else:
        raise ValueError(
            "URL not recognized as a Spotify or YouTube playlist.\n"
            "Supported formats:\n"
            "  - https://open.spotify.com/playlist/...\n"
            "  - https://www.youtube.com/playlistlist=...\n"
            "  - https://music.youtube.com/browse/..."
        )


def _ms_to_duration(ms: int) -> str:
    if not ms:
        return ""
    secs = ms // 1000
    return _secs_to_duration(secs)


def _secs_to_duration(secs: int) -> str:
    if not secs:
        return ""
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

