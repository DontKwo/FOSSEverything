"""Playlist Porter: convert playlists between Spotify and YouTube / YouTube Music."""
from __future__ import annotations

import os
from typing import Optional, Any
from PyQt6.QtCore import Qt, QSettings, QUrl, QThread, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QFont, QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QTextEdit, QPushButton,
    QLabel, QLineEdit, QFileDialog, QMessageBox, QGroupBox, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QFrame, QInputDialog,
    QDialog, QDialogButtonBox
)

from app.core.customizable_toolbar import AppToolBar
from app.features.playlist import ops as playlist_ops
from app.features.playlist import youtube_ops
from app.core.theme import resolved_palette, theme_signals
from app.core.tooltips import get_tooltip_for
from app.ui.ui_scaling import scaled_font_size


def _show_setup_instructions(parent: QWidget, title: str, html_body: str) -> None:
    """Show a step-by-step setup guide with real clickable links."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(480)

    layout = QVBoxLayout(dialog)
    label = QLabel(html_body)
    label.setWordWrap(True)
    label.setOpenExternalLinks(True)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    layout.addWidget(label)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    buttons.accepted.connect(dialog.accept)
    buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(dialog.accept)
    layout.addWidget(buttons)

    dialog.exec()


class _FetchWorker(QThread):
    """Background thread: fetch playlist tracks from a URL."""
    progress = pyqtSignal(int, int, str)   # current, total, track_name
    finished = pyqtSignal(list)            # list[PlaylistTrack]
    error = pyqtSignal(str)

    def __init__(self, url: str, parent: Optional[QThread] = None) -> None:
        super().__init__(parent)
        self.url: str = url

    def run(self) -> None:
        try:
            tracks: list = playlist_ops.fetch_playlist_from_url(
                self.url,
                progress_cb=lambda cur, total, name: self.progress.emit(cur, total, name),
            )
            self.finished.emit(tracks)
        except Exception as exc:
            self.error.emit(str(exc))


class _YouTubePlaylistWorker(QThread):
    """Background thread: create a real YouTube playlist from a tracklist."""
    progress = pyqtSignal(int, int, str)                          # current, total, track_name
    finished_ok = pyqtSignal(object)                               # YouTubePlaylistResult
    error = pyqtSignal(str)

    def __init__(self, tracks: list, title: str, privacy_status: str, parent: Optional[QThread] = None) -> None:
        super().__init__(parent)
        self.tracks = tracks
        self.title = title
        self.privacy_status = privacy_status

    def run(self) -> None:
        try:
            result = youtube_ops.build_youtube_playlist_from_tracks(
                self.tracks,
                self.title,
                privacy_status=self.privacy_status,
                progress_cb=lambda cur, total, name: self.progress.emit(cur, total, name),
            )
            self.finished_ok.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class PlaylistTab(QWidget):
    """Interactive workspace for converting music playlists between platforms."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.settings: QSettings = QSettings("FOSSEverything", "FOSSEverything")
        self.tracks: list = []
        self._fetch_worker: Optional[_FetchWorker] = None
        self._youtube_worker: Optional[_YouTubePlaylistWorker] = None
        self._build_ui()
        theme_signals.changed.connect(self._refresh_theme_colors)

    def _refresh_theme_colors(self) -> None:
        muted = resolved_palette(self.settings)["muted"]
        self.fetch_status.setStyleSheet(f"color: {muted}; min-width: 160px;")
        self.status_label.setStyleSheet(f"color: {muted}; font-weight: 500;")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Header ──────────────────────────────────────────────────────────
        title_label = QLabel("Playlist Porter (Spotify <-> YouTube / YouTube Music)")
        title_label.setStyleSheet("font-weight: 700;")
        root.addWidget(title_label)

        top_bar = AppToolBar(self.settings, "playlist_toolbar")
        top_bar.add_action("Open File (CSV, TXT, M3U8)...", self._browse_playlist_file)
        top_bar.finalize()
        root.addWidget(top_bar)

        # ── URL Fetch Bar ────────────────────────────────────────────────────
        url_box = QGroupBox("Fetch from URL  (Spotify playlist · YouTube playlist · YouTube Music playlist)")
        url_box.setStyleSheet("QGroupBox { font-weight: 600; }")
        url_layout = QHBoxLayout(url_box)
        url_layout.setSpacing(12)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "Paste Spotify or YouTube playlist URL here - e.g. https://open.spotify.com/playlist/... or https://www.youtube.com/playlist?list=..."
        )
        self.url_input.setMinimumHeight(34)
        self.url_input.returnPressed.connect(self._fetch_from_url)
        url_layout.addWidget(self.url_input, stretch=1)

        self.fetch_btn = QPushButton("Fetch Playlist")
        self.fetch_btn.setToolTip(get_tooltip_for("Fetch Playlist"))
        self.fetch_btn.setStyleSheet("font-weight: 700; padding: 6px 16px;")
        self.fetch_btn.clicked.connect(self._fetch_from_url)
        url_layout.addWidget(self.fetch_btn)

        self.fetch_progress = QProgressBar()
        self.fetch_progress.setVisible(False)
        self.fetch_progress.setMaximumWidth(200)
        self.fetch_progress.setTextVisible(True)
        url_layout.addWidget(self.fetch_progress)

        self.fetch_status = QLabel("")
        self.fetch_status.setStyleSheet(f"color: {resolved_palette(self.settings)['muted']}; min-width: 160px;")
        url_layout.addWidget(self.fetch_status)

        root.addWidget(url_box)

        creds_box = QGroupBox("Spotify login")
        creds_box.setStyleSheet("QGroupBox { font-weight: 600; }")
        creds_layout = QVBoxLayout(creds_box)

        creds_row = QHBoxLayout()
        creds_row.setSpacing(12)
        self.spotify_client_id_input = QLineEdit()
        self.spotify_client_id_input.setPlaceholderText("Spotify Client ID")
        self.spotify_client_id_input.setText(self.settings.value("spotify/client_id", ""))
        creds_row.addWidget(self.spotify_client_id_input, stretch=1)

        save_creds_btn = QPushButton("Save Client ID")
        save_creds_btn.setToolTip(get_tooltip_for("Save Spotify credentials"))
        save_creds_btn.clicked.connect(self._save_spotify_credentials)
        creds_row.addWidget(save_creds_btn)

        login_btn = QPushButton("Log in with Spotify")
        login_btn.setToolTip(get_tooltip_for("Log in with Spotify"))
        login_btn.clicked.connect(self._login_to_spotify)
        creds_row.addWidget(login_btn)

        help_btn = QPushButton("See step-by-step instructions")
        help_btn.setToolTip(get_tooltip_for("How to set up Spotify API"))
        help_btn.clicked.connect(self._show_spotify_setup_help)
        creds_row.addWidget(help_btn)

        creds_layout.addLayout(creds_row)
        root.addWidget(creds_box)

        yt_creds_box = QGroupBox("YouTube login (for creating a real YouTube playlist)")
        yt_creds_box.setStyleSheet("QGroupBox { font-weight: 600; }")
        yt_creds_layout = QVBoxLayout(yt_creds_box)

        yt_creds_row = QHBoxLayout()
        yt_creds_row.setSpacing(12)
        self.youtube_client_id_input = QLineEdit()
        self.youtube_client_id_input.setPlaceholderText("Google OAuth Client ID")
        self.youtube_client_id_input.setText(self.settings.value("youtube/client_id", ""))
        yt_creds_row.addWidget(self.youtube_client_id_input, stretch=1)

        self.youtube_client_secret_input = QLineEdit()
        self.youtube_client_secret_input.setPlaceholderText("Google OAuth Client Secret")
        self.youtube_client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.youtube_client_secret_input.setText(self.settings.value("youtube/client_secret", ""))
        yt_creds_row.addWidget(self.youtube_client_secret_input, stretch=1)

        save_yt_creds_btn = QPushButton("Save credentials")
        save_yt_creds_btn.setToolTip(get_tooltip_for("Save YouTube credentials"))
        save_yt_creds_btn.clicked.connect(self._save_youtube_credentials)
        yt_creds_row.addWidget(save_yt_creds_btn)

        yt_login_btn = QPushButton("Log in with YouTube")
        yt_login_btn.setToolTip(get_tooltip_for("Log in with YouTube"))
        yt_login_btn.clicked.connect(self._login_to_youtube)
        yt_creds_row.addWidget(yt_login_btn)

        yt_help_btn = QPushButton("See step-by-step instructions")
        yt_help_btn.setToolTip(get_tooltip_for("How to set up YouTube API"))
        yt_help_btn.clicked.connect(self._show_youtube_setup_help)
        yt_creds_row.addWidget(yt_help_btn)

        yt_creds_layout.addLayout(yt_creds_row)
        root.addWidget(yt_creds_box)

        # ── Splitter: Input text on left, mapped tracklist on right ──────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Manual / pasted text input
        left_box = QGroupBox("Or Paste Tracklist Text  (Artist - Song, numbered lists, CSV rows)")
        left_layout = QVBoxLayout(left_box)
        left_layout.setSpacing(10)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Direction:"))
        self.direction_combo = QComboBox()
        self.direction_combo.setToolTip(get_tooltip_for("Playlist Conversion Direction"))
        self.direction_combo.addItems([
            "Spotify -> YouTube & YouTube Music",
            "YouTube -> Spotify",
        ])
        mode_row.addWidget(self.direction_combo, stretch=1)
        left_layout.addLayout(mode_row)

        self.input_editor = QTextEdit()
        self.input_editor.setPlaceholderText("Paste tracklist lines here...")
        self.input_editor.setFont(QFont("Segoe UI", scaled_font_size(10)))
        left_layout.addWidget(self.input_editor)

        btn_row = AppToolBar(self.settings, "playlist_convert_toolbar")
        btn_row.add_action("Convert && Map Tracks", self._convert_from_text)
        btn_row.add_action("Clear", self.input_editor.clear)
        btn_row.finalize()
        left_layout.addWidget(btn_row)

        splitter.addWidget(left_box)

        # Right: Converted Playlist Output
        right_box = QGroupBox("Mapped Tracklist && Output")
        right_layout = QVBoxLayout(right_box)
        right_layout.setSpacing(10)

        self.status_label = QLabel("No tracks loaded yet. Paste a URL above or enter tracks on the left.")
        self.status_label.setStyleSheet(f"color: {resolved_palette(self.settings)['muted']}; font-weight: 500;")
        self.status_label.setWordWrap(True)
        right_layout.addWidget(self.status_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "Title", "Artist", "Duration", "Open Links"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        right_layout.addWidget(self.table)

        # Export row
        export_row = AppToolBar(self.settings, "playlist_export_toolbar")
        export_row.add_action("Export M3U8", self._export_m3u8)
        export_row.add_action("Export CSV", self._export_csv)
        export_row.add_action("Copy Tracklist", self._copy_tracklist)
        export_row.add_action("Open First 5 in Browser", self._open_top_browser)
        export_row.add_action("Create YouTube Playlist...", self._create_youtube_playlist)
        export_row.finalize()
        right_layout.addWidget(export_row)

        self.youtube_create_progress = QProgressBar()
        self.youtube_create_progress.setVisible(False)
        right_layout.addWidget(self.youtube_create_progress)

        splitter.addWidget(right_box)
        splitter.setSizes([420, 580])
        root.addWidget(splitter, stretch=1)

    def _show_spotify_setup_help(self) -> None:
        html: str = (
            "<ol>"
            "<li>Open the <a href=\"https://developer.spotify.com/dashboard\">Spotify Developer Dashboard</a> "
            "and create an app.</li>"
            "<li>Name it anything, e.g. <i>FOSSEverything</i>.</li>"
            "<li>In the app's settings, add this exact redirect URI: "
            "<code>http://127.0.0.1:8888/callback</code></li>"
            "<li>Copy the <b>Client ID</b> (no Client Secret is needed &mdash; this app uses the "
            "secretless PKCE login flow).</li>"
            "<li>Paste it into the Client ID field above and click <b>Save Client ID</b>.</li>"
            "<li>Click <b>Log in with Spotify</b> and approve access in the browser that opens.</li>"
            "</ol>"
            "<p><b>Requirements:</b> the signed-in Spotify account must be listed under "
            "<i>Settings &gt; Users Management</i> on that app while it's in Development Mode. "
            "Spotify requires <code>127.0.0.1</code>, not <code>localhost</code>, in the redirect URI.</p>"
        )
        _show_setup_instructions(self, "Spotify API setup", html)

    def _save_spotify_credentials(self) -> None:
        client_id: str = self.spotify_client_id_input.text().strip()

        if client_id:
            self.settings.setValue("spotify/client_id", client_id)
            playlist_ops._clear_spotify_user_token_cache()
            QMessageBox.information(self, "Spotify Client ID saved", "Client ID saved. A fresh Spotify user login is required before playlist imports can proceed.")
        else:
            self.settings.remove("spotify/client_id")
            playlist_ops._clear_spotify_user_token_cache()
            QMessageBox.information(self, "Spotify Client ID cleared", "The Spotify Client ID was cleared. You must enter it again before using Spotify playlist imports.")

    def _login_to_spotify(self) -> None:
        try:
            access_token: Optional[str] = playlist_ops.start_spotify_user_login()
            if access_token:
                QMessageBox.information(
                    self,
                    "Spotify login complete",
                    "Spotify login succeeded. Your user access token is cached and will be used for playlist reads that require user permissions.",
                )
            else:
                QMessageBox.warning(self, "Spotify login failed", "No access token was returned.")
        except Exception as exc:
            QMessageBox.critical(self, "Spotify login failed", str(exc))

    def _show_youtube_setup_help(self) -> None:
        html: str = (
            "<ol>"
            "<li>Open the <a href=\"https://console.cloud.google.com\">Google Cloud Console</a> "
            "and create (or pick) a project.</li>"
            "<li>Go to <b>APIs &amp; Services &gt; Library</b> and enable "
            "<a href=\"https://console.cloud.google.com/apis/library/youtube.googleapis.com\">YouTube Data API v3</a>.</li>"
            "<li>Go to <a href=\"https://console.cloud.google.com/apis/credentials/consent\">OAuth consent screen</a> "
            "and set User Type to <b>External</b>, then add your Google account under <i>Test users</i> "
            "while the app is unverified.</li>"
            "<li>Go to <a href=\"https://console.cloud.google.com/apis/credentials\">Credentials</a> &gt; "
            "Create Credentials &gt; OAuth client ID, and choose <b>Desktop app</b>.</li>"
            "<li>Copy the Client ID and Client Secret into the fields above and click <b>Save credentials</b>.</li>"
            "<li>Click <b>Log in with YouTube</b> and approve access in the browser that opens.</li>"
            "</ol>"
            "<p><b>Quota:</b> YouTube's free API quota is 10,000 units/day; each track costs about 150 units, "
            "so roughly 60 tracks/day is the practical ceiling on the default quota.</p>"
        )
        _show_setup_instructions(self, "YouTube API setup", html)

    def _save_youtube_credentials(self) -> None:
        client_id: str = self.youtube_client_id_input.text().strip()
        client_secret: str = self.youtube_client_secret_input.text().strip()

        if client_id and client_secret:
            self.settings.setValue("youtube/client_id", client_id)
            self.settings.setValue("youtube/client_secret", client_secret)
            youtube_ops.clear_youtube_token_cache()
            QMessageBox.information(self, "YouTube credentials saved", "Credentials saved. A fresh YouTube login is required before playlists can be created.")
        elif not client_id and not client_secret:
            self.settings.remove("youtube/client_id")
            self.settings.remove("youtube/client_secret")
            youtube_ops.clear_youtube_token_cache()
            QMessageBox.information(self, "YouTube credentials cleared", "YouTube API credentials were cleared. You must enter both values again before creating YouTube playlists.")
        else:
            QMessageBox.warning(self, "Incomplete credentials", "Enter both a Client ID and Client Secret.")

    def _login_to_youtube(self) -> None:
        try:
            success = youtube_ops.start_youtube_login()
            if success:
                QMessageBox.information(
                    self,
                    "YouTube login complete",
                    "YouTube login succeeded. Your access token is cached for creating playlists.",
                )
            else:
                QMessageBox.warning(self, "YouTube login failed", "No access token was returned.")
        except Exception as exc:
            QMessageBox.critical(self, "YouTube login failed", str(exc))

    # ── YouTube Playlist Creation ────────────────────────────────────────────

    def _create_youtube_playlist(self) -> None:
        if not self.tracks:
            QMessageBox.warning(self, "No Tracks", "Load or convert a playlist first.")
            return

        client_id = self.settings.value("youtube/client_id", "")
        client_secret = self.settings.value("youtube/client_secret", "")
        if not client_id or not client_secret:
            QMessageBox.warning(
                self,
                "YouTube login required",
                "Creating a YouTube playlist requires a Google OAuth Client ID and Secret, plus a "
                "logged-in Google account. Enter the values above and click 'Log in with YouTube' first."
            )
            return
        if not youtube_ops.has_youtube_login():
            QMessageBox.warning(
                self,
                "YouTube login required",
                "You must log in with YouTube before creating a playlist. Click 'Log in with YouTube' first."
            )
            return

        title, ok = QInputDialog.getText(
            self, "Playlist name", "Name for the new YouTube playlist:",
            text="Imported with FOSSEverything",
        )
        if not ok or not title.strip():
            return

        title = title.strip()
        resumable = youtube_ops.get_resumable_import(self.tracks, title)
        already_done = resumable[0] if resumable else 0
        remaining = len(self.tracks) - already_done

        if remaining > 50:
            resume_note = f"{already_done} track(s) were already added in a previous run. " if already_done else ""
            proceed = QMessageBox.question(
                self,
                "Large playlist",
                f"{resume_note}{remaining} track(s) remain. YouTube's free API quota "
                "typically allows only about 60 tracks/day, so this may run out of quota partway "
                "through and leave the playlist incomplete (you can run this again later to keep "
                "adding the rest). Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return

        self.youtube_create_progress.setVisible(True)
        self.youtube_create_progress.setRange(0, len(self.tracks))
        self.youtube_create_progress.setValue(already_done)
        self.status_label.setText(f"Creating YouTube playlist '{title}'...")

        self._youtube_worker = _YouTubePlaylistWorker(self.tracks, title, "private", parent=self)
        self._youtube_worker.progress.connect(self._on_youtube_create_progress)
        self._youtube_worker.finished_ok.connect(self._on_youtube_create_done)
        self._youtube_worker.error.connect(self._on_youtube_create_error)
        self._youtube_worker.start()

    def _on_youtube_create_progress(self, current: int, total: int, track_name: str) -> None:
        self.youtube_create_progress.setValue(current)
        self.status_label.setText(f"Adding track {current}/{total}: {track_name[:40]}")

    def _on_youtube_create_done(self, result: youtube_ops.YouTubePlaylistResult) -> None:
        self.youtube_create_progress.setVisible(False)
        summary = f"Created YouTube playlist with {result.matched}/{len(self.tracks)} tracks matched."
        if result.unmatched:
            preview = "\n".join(f"  - {name}" for name in result.unmatched[:10])
            more = f"\n  ...and {len(result.unmatched) - 10} more" if len(result.unmatched) > 10 else ""
            summary += f"\n\n{len(result.unmatched)} track(s) could not be matched on YouTube:\n{preview}{more}"
        self.status_label.setText(f"YouTube playlist created: {result.playlist_url}")

        msg = QMessageBox(self)
        msg.setWindowTitle("YouTube playlist created")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(summary)
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        open_btn = msg.addButton("Open playlist", QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Ok)
        msg.exec()
        if msg.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl(result.playlist_url))

    def _on_youtube_create_error(self, error_msg: str) -> None:
        self.youtube_create_progress.setVisible(False)
        self.status_label.setText("YouTube playlist creation failed.")
        QMessageBox.critical(self, "YouTube Playlist Error", error_msg)

    # ── URL Fetching ──────────────────────────────────────────────────────────

    def _fetch_from_url(self) -> None:
        url: str = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "No URL", "Please paste a Spotify or YouTube playlist URL first.")
            return

        platform = playlist_ops.detect_url_platform(url)
        if not platform:
            QMessageBox.warning(
                self, "Unrecognized URL",
                "URL not recognized as Spotify or YouTube.\n\n"
                "Supported:\n"
                "  - https://open.spotify.com/playlist/...\n"
                "  - https://www.youtube.com/playlistlist=...\n"
                "  - https://music.youtube.com/browse/..."
            )
            return

        if platform == "spotify":
            client_id = self.settings.value("spotify/client_id", "")
            if not client_id:
                QMessageBox.warning(
                    self,
                    "Spotify login required",
                    "Spotify playlist imports require a valid Client ID, plus a logged-in Spotify account. "
                    "Enter the Client ID above and click 'Log in with Spotify' before fetching the playlist."
                )
                return
            if not playlist_ops.get_spotify_user_token():
                QMessageBox.warning(
                    self,
                    "Spotify login required",
                    "You must log in to Spotify before importing a Spotify playlist. Click 'Log in with Spotify' first."
                )
                return

        platform_label = "Spotify" if platform == "spotify" else "YouTube"
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("Fetching...")
        self.fetch_progress.setVisible(True)
        self.fetch_progress.setRange(0, 0)   # indeterminate spinner
        mode_text = "public mode" if platform == "spotify" else "playlist mode"
        self.fetch_status.setText(f"Connecting to {platform_label}... ({mode_text})")
        self.status_label.setText(f"⏳ Fetching playlist from {platform_label}...")

        self._fetch_worker = _FetchWorker(url, parent=self)
        self._fetch_worker.progress.connect(self._on_fetch_progress)
        self._fetch_worker.finished.connect(self._on_fetch_done)
        self._fetch_worker.error.connect(self._on_fetch_error)
        self._fetch_worker.start()

    def _on_fetch_progress(self, current: int, total: int, track_name: str) -> None:
        if total > 0:
            self.fetch_progress.setRange(0, total)
            self.fetch_progress.setValue(current)
        self.fetch_status.setText(f"Track {current}/{total}: {track_name[:30]}...")

    def _on_fetch_done(self, tracks: list) -> None:
        self.tracks = tracks
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("  Fetch Playlist")
        self.fetch_progress.setVisible(False)
        self.fetch_status.setText(f" {len(tracks)} tracks fetched!")
        self._populate_table(tracks)

    def _on_fetch_error(self, error_msg: str) -> None:
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("  Fetch Playlist")
        self.fetch_progress.setVisible(False)
        self.fetch_status.setText(" Fetch failed")
        self.status_label.setText(" Could not fetch playlist.")
        QMessageBox.critical(self, "Fetch Error", error_msg)

    # ── Manual Text Conversion ────────────────────────────────────────────────

    def _browse_playlist_file(self) -> None:
        path: str
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Playlist File", "",
            "Playlist & Text Files (*.txt *.csv *.m3u8 *.m3u *.json);;All Files (*.*)"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    self.input_editor.setPlainText(f.read())
                self._convert_from_text()
            except Exception as exc:
                QMessageBox.critical(self, "Read Error", f"Could not read file: {exc}")

    def _convert_from_text(self) -> None:
        text: str = self.input_editor.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "No Input", "Please enter or paste playlist tracks first.")
            return
        self.tracks = playlist_ops.parse_tracklist_text(text)
        self._populate_table(self.tracks)

    # ── Table ─────────────────────────────────────────────────────────────────

    def _populate_table(self, tracks: list) -> None:
        self.status_label.setText(f" {len(tracks)} tracks mapped - click YT / YTM / Spotify to search each one.")
        self.table.setRowCount(len(tracks))
        for r, tr in enumerate(tracks):
            self.table.setItem(r, 0, QTableWidgetItem(str(r + 1)))
            self.table.setItem(r, 1, QTableWidgetItem(tr.title))
            self.table.setItem(r, 2, QTableWidgetItem(tr.artist))
            self.table.setItem(r, 3, QTableWidgetItem(tr.duration_str))

            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(2, 2, 2, 2)
            act_layout.setSpacing(4)

            yt_btn = QPushButton("YT")
            yt_btn.setToolTip(get_tooltip_for("Search on YouTube"))
            yt_btn.setFixedWidth(36)
            yt_btn.clicked.connect(lambda _, u=tr.youtube_url: QDesktopServices.openUrl(QUrl(u)))
            act_layout.addWidget(yt_btn)
            ytm_btn = QPushButton("YTM")
            ytm_btn.setToolTip(get_tooltip_for("Search on YouTube Music"))
            ytm_btn.setFixedWidth(40)
            ytm_btn.clicked.connect(lambda _, u=tr.youtube_music_url: QDesktopServices.openUrl(QUrl(u)))
            act_layout.addWidget(ytm_btn)
            sp_btn = QPushButton("Spotify")
            sp_btn.setToolTip(get_tooltip_for("Search on Spotify"))
            sp_btn.setFixedWidth(55)
            sp_btn.clicked.connect(lambda _, u=tr.spotify_url: QDesktopServices.openUrl(QUrl(u)))
            act_layout.addWidget(sp_btn)
            self.table.setCellWidget(r, 4, act_widget)

    # ── Exports ───────────────────────────────────────────────────────────────

    def _export_m3u8(self) -> None:
        if not self.tracks:
            QMessageBox.warning(self, "No Tracks", "Load or convert a playlist first.")
            return
        path: str
        path, _ = QFileDialog.getSaveFileName(self, "Save M3U8 Playlist", "playlist.m3u8", "M3U8 Playlist (*.m3u8);;All Files (*.*)")
        if path:
            try:
                playlist_ops.export_m3u8_playlist(self.tracks, path)
                QMessageBox.information(self, "Exported", f"M3U8 playlist saved to {path}")
            except Exception as exc:
                QMessageBox.critical(self, "Export Error", str(exc))

    def _export_csv(self) -> None:
        if not self.tracks:
            QMessageBox.warning(self, "No Tracks", "Load or convert a playlist first.")
            return
        path: str
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV Playlist", "playlist.csv", "CSV Spreadsheet (*.csv);;All Files (*.*)")
        if path:
            try:
                playlist_ops.export_csv_playlist(self.tracks, path)
                QMessageBox.information(self, "Exported", f"CSV playlist saved to {path}")
            except Exception as exc:
                QMessageBox.critical(self, "Export Error", str(exc))

    def _copy_tracklist(self) -> None:
        if not self.tracks:
            return
        lines: list[str] = [f"{tr.artist} - {tr.title}" if tr.artist else tr.title for tr in self.tracks]
        QGuiApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Copied", f"Copied {len(lines)} tracks to clipboard!")

    def _open_top_browser(self) -> None:
        if not self.tracks:
            return
        for tr in self.tracks[:5]:
            url: str = tr.youtube_music_url if "YouTube" in self.direction_combo.currentText() else tr.spotify_url
            QDesktopServices.openUrl(QUrl(url))
