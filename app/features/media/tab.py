"""Media Studio workspace: trim, transcode, compress, extract audio, and capture video frames."""
from __future__ import annotations

import os
from typing import Any, Callable, Optional

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QGuiApplication, QFont, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QPushButton, QLabel, QFileDialog, QMessageBox, QGroupBox, QTabWidget,
    QProgressBar, QSlider, QSplitter, QFrame,
    QStyle, QSizePolicy, QInputDialog, QListWidget, QListWidgetItem,
    QAbstractItemView, QStackedWidget
)

from app.core.spinbox import NoScrollDoubleSpinBox, NoScrollSpinBox
from app.features.media import ops as media_ops
from app.core.theme import resolved_palette, theme_signals
from app.ui.ui_scaling import scaled_font_pt
from app.core.tooltips import get_tooltip_for
from app.system.workers import WorkerThread

try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput  # noqa: 22
    from PyQt6.QtMultimediaWidgets import QVideoWidget  # noqa: 22
    MULTIMEDIA_AVAILABLE = True
except ImportError:
    MULTIMEDIA_AVAILABLE = False


class MediaTab(QWidget):
    """Modern, intuitive Media Studio workspace."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.current_path: str | None = None
        self.media_info: dict | None = None
        self.duration_ms: int = 0
        self._worker: WorkerThread | None = None
        self.batch_items: list[media_ops.BatchMediaItem] = []
        self.batch_output_dir: str | None = None
        self.last_transcription: dict | None = None
        self.timeline_clips: list[dict] = []
        self.timeline_audio_tracks: list[dict] = []

        self._init_player()
        self._build_ui()
        theme_signals.changed.connect(self._refresh_theme_colors)

    def _refresh_theme_colors(self) -> None:
        palette = resolved_palette()
        if self.video_widget:
            self.video_widget.setStyleSheet(f"background-color: {palette['background']}; border-radius: 4px;")
        self.range_summary_lbl.setStyleSheet(
            f"color: {palette['accent']}; font-weight: 600; font-size: {scaled_font_pt(11)};"
        )

    def _init_player(self) -> None:
        if MULTIMEDIA_AVAILABLE:
            self.player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.player.setAudioOutput(self.audio_output)
            self.video_widget = QVideoWidget(self)
            self.player.setVideoOutput(self.video_widget)

            self.player.positionChanged.connect(self._on_player_position_changed)
            self.player.durationChanged.connect(self._on_player_duration_changed)
        else:
            self.player = None
            self.audio_output = None
            self.video_widget = None

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Media Studio")
        title.setStyleSheet("font-weight: 700;")
        sub = QLabel("Trim, convert, compress, extract audio, and capture frames from video and audio offline.")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box, stretch=1)
        root.addLayout(header)

        outer_tabs = QTabWidget()
        outer_tabs.addTab(self._build_single_file_tab(), "Single File")
        outer_tabs.addTab(self._build_batch_tab(), "Batch Processing")
        root.addWidget(outer_tabs, stretch=1)

    def _build_single_file_tab(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        # Top file bar
        file_row = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select any video or audio file (MP4, MOV, MKV, MP3, WAV, AAC, etc.)...")
        self.file_path_edit.setReadOnly(True)
        browse_btn = QPushButton("Open Media File...")
        browse_btn.setToolTip(get_tooltip_for("Open Media File"))
        browse_btn.setStyleSheet("font-weight: 600; padding: 6px 14px;")
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(self.file_path_edit, stretch=1)
        file_row.addWidget(browse_btn)
        root.addLayout(file_row)

        # Main splitter (Left: Player & Info, Right: Tool Controls)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Column: Player & Metadata Chip Card
        left_box = QWidget()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(14)

        # Player area
        player_group = QGroupBox("Playback && Preview")
        player_group.setMinimumHeight(340)
        player_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        player_layout = QVBoxLayout(player_group)
        player_layout.setContentsMargins(8, 8, 8, 8)
        player_layout.setSpacing(10)

        if self.video_widget:
            self.video_widget.setMinimumHeight(260)
            self.video_widget.setStyleSheet(f"background-color: {resolved_palette()['background']}; border-radius: 4px;")
            player_layout.addWidget(self.video_widget, stretch=1)
        else:
            no_player_lbl = QLabel("QtMultimedia video playback not available on this platform.")
            no_player_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_player_lbl.setMinimumHeight(260)
            player_layout.addWidget(no_player_lbl)

        # Seek Slider & Time
        seek_row = QHBoxLayout()
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.sliderMoved.connect(self._on_seek_moved)
        self.time_label = QLabel("00:00:00.0 / 00:00:00.0")
        self.time_label.setStyleSheet(f"font-family: monospace; font-size: {scaled_font_pt(11)};")
        seek_row.addWidget(self.seek_slider, stretch=1)
        seek_row.addWidget(self.time_label)
        player_layout.addLayout(seek_row)

        # Transport controls
        controls_row = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setToolTip(get_tooltip_for("Play"))
        self.play_btn.clicked.connect(self._toggle_playback)
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setToolTip(get_tooltip_for("Stop"))
        self.stop_btn.clicked.connect(self._stop_playback)

        controls_row.addWidget(self.play_btn)
        controls_row.addWidget(self.stop_btn)

        vol_lbl = QLabel("volume")
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setMaximumWidth(100)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)
        controls_row.addStretch(1)
        controls_row.addWidget(vol_lbl)
        controls_row.addWidget(self.vol_slider)
        player_layout.addLayout(controls_row)

        left_layout.addWidget(player_group, stretch=1)

        # Info Chips
        self.info_card = QGroupBox("Media Details")
        self.info_card.setMinimumHeight(170)
        self.info_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        info_layout = QFormLayout(self.info_card)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setVerticalSpacing(8)
        self.info_res_lbl = QLabel("--")
        self.info_dur_lbl = QLabel("--")
        self.info_codec_lbl = QLabel("--")
        self.info_size_lbl = QLabel("--")
        info_layout.addRow("Duration:", self.info_dur_lbl)
        info_layout.addRow("Resolution && FPS:", self.info_res_lbl)
        info_layout.addRow("Codecs && Streams:", self.info_codec_lbl)
        info_layout.addRow("File Size:", self.info_size_lbl)
        left_layout.addWidget(self.info_card)

        splitter.addWidget(left_box)

        # Right Column: Tool Tabs
        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(14)

        # Trimming Timeline Box (Always visible at top of tool panel)
        trim_box = QGroupBox("Range && Trim Points")
        trim_layout = QVBoxLayout(trim_box)
        trim_layout.setContentsMargins(10, 10, 10, 10)
        trim_layout.setSpacing(12)

        pts_row = QHBoxLayout()
        pts_row.addWidget(QLabel("Start Time (s):"))
        self.start_spin = NoScrollDoubleSpinBox()
        self.start_spin.setToolTip(get_tooltip_for("Start Time"))
        self.start_spin.setRange(0, 999999)
        self.start_spin.setSingleStep(1.0)
        self.start_spin.valueChanged.connect(self._update_range_label)
        pts_row.addWidget(self.start_spin)

        mark_in_btn = QPushButton("Mark Start")
        mark_in_btn.setToolTip(get_tooltip_for("Mark Start"))
        mark_in_btn.clicked.connect(self._mark_in)
        pts_row.addWidget(mark_in_btn)

        pts_row.addSpacing(15)

        pts_row.addWidget(QLabel("End Time (s):"))
        self.end_spin = NoScrollDoubleSpinBox()
        self.end_spin.setToolTip(get_tooltip_for("End Time"))
        self.end_spin.setRange(0, 999999)
        self.end_spin.setSingleStep(1.0)
        self.end_spin.valueChanged.connect(self._update_range_label)
        pts_row.addWidget(self.end_spin)

        mark_out_btn = QPushButton("Mark End")
        mark_out_btn.setToolTip(get_tooltip_for("Mark End"))
        mark_out_btn.clicked.connect(self._mark_out)
        pts_row.addWidget(mark_out_btn)

        trim_layout.addLayout(pts_row)

        self.range_summary_lbl = QLabel("Selection duration: 0.000s")
        self.range_summary_lbl.setStyleSheet(f"color: {resolved_palette()['accent']}; font-weight: 600; font-size: {scaled_font_pt(11)};")
        trim_layout.addWidget(self.range_summary_lbl)

        right_layout.addWidget(trim_box)

        # Tabbed Tool Actions
        tool_tabs = QTabWidget()

        # Tab 1: Trim / Cut
        tool_tabs.addTab(self._build_trim_tab(), "Trim / Cut")
        # Tab 2: Extract Audio
        tool_tabs.addTab(self._build_audio_tab(), "Extract Audio")
        # Tab 3: Convert & Transcode
        tool_tabs.addTab(self._build_convert_tab(), "Convert")
        # Tab 4: Compress & Resize
        tool_tabs.addTab(self._build_compress_tab(), "Compress")
        # Tab 5: Frame Grabber & Mute
        tool_tabs.addTab(self._build_extras_tab(), "Frame / Mute")
        # Tab 6: Timeline Composer
        tool_tabs.addTab(self._build_timeline_tab(), "Timeline Composer")

        right_layout.addWidget(tool_tabs, stretch=1)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate pulse
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)

        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([760, 640])

        root.addWidget(splitter, stretch=1)
        return w

    # ─── Tool Sub-Tabs ───────────────────────────────────────────────────────
    def _build_trim_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(16)

        layout.addWidget(QLabel("Cut a section from the file using the Start and End markers defined above."))

        form = QFormLayout()
        self.trim_mode_combo = QComboBox()
        self.trim_mode_combo.setToolTip(get_tooltip_for("Cut Engine"))
        self.trim_mode_combo.addItem("High Precision (Re-encode) -- Frame accurate cuts", False)
        self.trim_mode_combo.addItem("Fast Stream Copy -- Lossless & instantaneous (keyframe aligned)", True)
        form.addRow("Cut Engine:", self.trim_mode_combo)
        layout.addLayout(form)

        run_trim_btn = QPushButton("Export Trimmed Media...")
        run_trim_btn.setToolTip(get_tooltip_for("Export Trimmed Media"))
        run_trim_btn.setStyleSheet(f"font-weight: 700; padding: 9px 18px; font-size: {scaled_font_pt(13)};")
        run_trim_btn.clicked.connect(self._run_trim)
        layout.addWidget(run_trim_btn)
        layout.addStretch()
        return w

    def _build_audio_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(16)

        layout.addWidget(QLabel("Extract the sound track from the video and save it as an audio file."))

        form = QFormLayout()
        self.audio_fmt_combo = QComboBox()
        self.audio_fmt_combo.setToolTip(get_tooltip_for("Audio Format"))
        self.audio_fmt_combo.addItems(["MP3 (.mp3)", "WAV (.wav)", "AAC (.aac)", "FLAC (.flac)", "M4A (.m4a)", "OGG (.ogg)"])
        form.addRow("Audio Format:", self.audio_fmt_combo)

        self.audio_br_combo = QComboBox()
        self.audio_br_combo.setToolTip(get_tooltip_for("Audio Bitrate"))
        self.audio_br_combo.addItems(["320 kbps (High Quality)", "256 kbps (Very Good)", "192 kbps (Standard)", "128 kbps (Compact)"])
        self.audio_br_combo.setCurrentIndex(2)
        form.addRow("Audio Bitrate:", self.audio_br_combo)
        layout.addLayout(form)

        run_audio_btn = QPushButton("Extract Audio Track...")
        run_audio_btn.setToolTip(get_tooltip_for("Extract Audio Track"))
        run_audio_btn.setStyleSheet(f"font-weight: 700; padding: 9px 18px; font-size: {scaled_font_pt(13)};")
        run_audio_btn.clicked.connect(self._run_extract_audio)
        layout.addWidget(run_audio_btn)
        layout.addStretch()
        return w

    def _build_convert_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(16)

        layout.addWidget(QLabel("Transcode media to another container or format."))

        form = QFormLayout()
        self.convert_fmt_combo = QComboBox()
        self.convert_fmt_combo.setToolTip(get_tooltip_for("Target Format"))
        self.convert_fmt_combo.addItems(["MP4 (.mp4)", "MKV (.mkv)", "MOV (.mov)", "WEBM (.webm)", "AVI (.avi)", "MP3 (.mp3)", "WAV (.wav)"])
        form.addRow("Target Format:", self.convert_fmt_combo)

        self.convert_crf_combo = QComboBox()
        self.convert_crf_combo.setToolTip(get_tooltip_for("Video Quality"))
        self.convert_crf_combo.addItem("High Quality (CRF 18)", 18)
        self.convert_crf_combo.addItem("Balanced (CRF 23) - Recommended", 23)
        self.convert_crf_combo.addItem("Smaller File (CRF 28)", 28)
        self.convert_crf_combo.setCurrentIndex(1)
        form.addRow("Video Quality:", self.convert_crf_combo)
        layout.addLayout(form)

        run_convert_btn = QPushButton("Convert Media...")
        run_convert_btn.setToolTip(get_tooltip_for("Convert Media"))
        run_convert_btn.setStyleSheet(f"font-weight: 700; padding: 9px 18px; font-size: {scaled_font_pt(13)};")
        run_convert_btn.clicked.connect(self._run_convert)
        layout.addWidget(run_convert_btn)
        layout.addStretch()
        return w

    def _build_compress_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(16)

        layout.addWidget(QLabel("Shrink video file size for sharing on Discord, email, or web."))

        form = QFormLayout()
        self.compress_preset_combo = QComboBox()
        self.compress_preset_combo.setToolTip(get_tooltip_for("Compression Preset"))
        self.compress_preset_combo.addItem("Discord / Email Target (8MB limit, 480p / CRF 28)", ("discord", "480p"))
        self.compress_preset_combo.addItem("Balanced Web (720p / CRF 24)", ("balanced", "720p"))
        self.compress_preset_combo.addItem("High Quality (1080p / CRF 20)", ("quality", "1080p"))
        form.addRow("Compression Preset:", self.compress_preset_combo)
        layout.addLayout(form)

        run_compress_btn = QPushButton("Compress Video...")
        run_compress_btn.setToolTip(get_tooltip_for("Compress Video"))
        run_compress_btn.setStyleSheet(f"font-weight: 700; padding: 9px 18px; font-size: {scaled_font_pt(13)};")
        run_compress_btn.clicked.connect(self._run_compress)
        layout.addWidget(run_compress_btn)
        layout.addStretch()
        return w

    def _build_extras_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(16)

        layout.addWidget(QLabel("Quick frame snapshot, subtitle generation, audio overlays, and audio removal tools:"))

        frame_btn = QPushButton("Capture Frame at Current Playhead...")
        frame_btn.setToolTip(get_tooltip_for("Capture Frame"))
        frame_btn.setStyleSheet("font-weight: 600; padding: 8px 12px;")
        frame_btn.clicked.connect(self._run_capture_frame)
        layout.addWidget(frame_btn)

        transcribe_btn = QPushButton("Transcribe Audio (Local Whisper)...")
        transcribe_btn.setToolTip(get_tooltip_for("Transcribe Audio"))
        transcribe_btn.setStyleSheet("font-weight: 600; padding: 8px 12px;")
        transcribe_btn.clicked.connect(self._run_transcription)
        layout.addWidget(transcribe_btn)

        self.transcription_status_label = QLabel("No transcription yet.")
        self.transcription_status_label.setWordWrap(True)
        layout.addWidget(self.transcription_status_label)

        subtitle_btn = QPushButton("Generate Subtitle File...")
        subtitle_btn.setToolTip(get_tooltip_for("Generate Subtitles"))
        subtitle_btn.setStyleSheet("font-weight: 600; padding: 8px 12px;")
        subtitle_btn.clicked.connect(self._generate_subtitles)
        layout.addWidget(subtitle_btn)

        mix_btn = QPushButton("Mix Audio onto Video...")
        mix_btn.setToolTip(get_tooltip_for("Mix Audio onto Video"))
        mix_btn.setStyleSheet("font-weight: 600; padding: 8px 12px;")
        mix_btn.clicked.connect(self._mix_audio_with_video)
        layout.addWidget(mix_btn)

        mute_btn = QPushButton("Export Muted Video (Strip Audio)...")
        mute_btn.setToolTip(get_tooltip_for("Mute Audio"))
        mute_btn.setStyleSheet("font-weight: 600; padding: 8px 12px;")
        mute_btn.clicked.connect(self._run_mute)
        layout.addWidget(mute_btn)

        layout.addStretch()
        return w

    # ─── Timeline Composer Tab ───────────────────────────────────────────────
    def _build_timeline_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Concatenate trimmed/cropped clips into one video or GIF, with optional fades and a mixed-in audio track."))

        row = QHBoxLayout()
        self.timeline_list = QListWidget()
        row.addWidget(self.timeline_list, stretch=1)

        btn_col = QVBoxLayout()
        add_clip_btn = QPushButton("Add Clip...")
        add_clip_btn.setToolTip(get_tooltip_for("Add Clip"))
        add_clip_btn.clicked.connect(self._timeline_add_clip)
        edit_clip_btn = QPushButton("Edit Selected...")
        edit_clip_btn.setToolTip(get_tooltip_for("Edit Timeline Clip"))
        edit_clip_btn.clicked.connect(self._timeline_edit_clip)
        remove_clip_btn = QPushButton("Remove Selected")
        remove_clip_btn.setToolTip(get_tooltip_for("Remove Timeline Clip"))
        remove_clip_btn.clicked.connect(self._timeline_remove_clip)
        move_up_btn = QPushButton("Move Up")
        move_up_btn.setToolTip(get_tooltip_for("Move Clip Up"))
        move_up_btn.clicked.connect(lambda: self._timeline_move_clip(-1))
        move_down_btn = QPushButton("Move Down")
        move_down_btn.setToolTip(get_tooltip_for("Move Clip Down"))
        move_down_btn.clicked.connect(lambda: self._timeline_move_clip(1))
        for btn in (add_clip_btn, edit_clip_btn, remove_clip_btn, move_up_btn, move_down_btn):
            btn_col.addWidget(btn)
        btn_col.addStretch()
        row.addLayout(btn_col)
        layout.addLayout(row, stretch=1)

        export_form = QFormLayout()
        self.timeline_format_combo = QComboBox()
        self.timeline_format_combo.setToolTip(get_tooltip_for("Timeline Export Format"))
        self.timeline_format_combo.addItems(["mp4", "gif"])
        export_form.addRow("Export Format:", self.timeline_format_combo)

        size_row = QHBoxLayout()
        self.timeline_width_spin = NoScrollSpinBox()
        self.timeline_width_spin.setToolTip(get_tooltip_for("Target Width"))
        self.timeline_width_spin.setRange(0, 7680)
        self.timeline_width_spin.setValue(1280)
        self.timeline_height_spin = NoScrollSpinBox()
        self.timeline_height_spin.setToolTip(get_tooltip_for("Target Height"))
        self.timeline_height_spin.setRange(0, 4320)
        self.timeline_height_spin.setValue(720)
        size_row.addWidget(QLabel("Width:"))
        size_row.addWidget(self.timeline_width_spin)
        size_row.addWidget(QLabel("Height:"))
        size_row.addWidget(self.timeline_height_spin)
        export_form.addRow("Target Size:", size_row)

        self.timeline_fps_spin = NoScrollSpinBox()
        self.timeline_fps_spin.setToolTip(get_tooltip_for("Frame Rate"))
        self.timeline_fps_spin.setRange(1, 60)
        self.timeline_fps_spin.setValue(24)
        export_form.addRow("Frame Rate:", self.timeline_fps_spin)

        self.timeline_crossfade_spin = NoScrollDoubleSpinBox()
        self.timeline_crossfade_spin.setToolTip(get_tooltip_for("Crossfade Duration"))
        self.timeline_crossfade_spin.setRange(0.0, 10.0)
        self.timeline_crossfade_spin.setSingleStep(0.1)
        self.timeline_crossfade_spin.setValue(0.0)
        export_form.addRow("Crossfade Between Clips (s, 0 = hard cut):", self.timeline_crossfade_spin)
        layout.addLayout(export_form)

        layout.addWidget(QLabel("Audio Overlay Tracks (optional, mixed together over the whole timeline):"))
        audio_row = QHBoxLayout()
        self.timeline_audio_list = QListWidget()
        audio_row.addWidget(self.timeline_audio_list, stretch=1)

        audio_btn_col = QVBoxLayout()
        add_audio_btn = QPushButton("Add Track...")
        add_audio_btn.setToolTip(get_tooltip_for("Add Audio Track"))
        add_audio_btn.clicked.connect(self._timeline_add_audio_track)
        edit_audio_btn = QPushButton("Edit Selected...")
        edit_audio_btn.setToolTip(get_tooltip_for("Edit Audio Track"))
        edit_audio_btn.clicked.connect(self._timeline_edit_audio_track)
        remove_audio_btn = QPushButton("Remove Selected")
        remove_audio_btn.setToolTip(get_tooltip_for("Remove Audio Track"))
        remove_audio_btn.clicked.connect(self._timeline_remove_audio_track)
        for btn in (add_audio_btn, edit_audio_btn, remove_audio_btn):
            audio_btn_col.addWidget(btn)
        audio_btn_col.addStretch()
        audio_row.addLayout(audio_btn_col)
        layout.addLayout(audio_row)

        compose_btn = QPushButton("Compose Timeline...")
        compose_btn.setToolTip(get_tooltip_for("Compose Timeline"))
        compose_btn.setStyleSheet("font-weight: 700; padding: 8px 16px;")
        compose_btn.clicked.connect(self._run_compose_timeline)
        layout.addWidget(compose_btn)
        return w

    def _timeline_add_clip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Add Clip to Timeline", "", "Video Files (*.mp4 *.mov *.mkv *.avi *.webm)")
        if not path:
            return
        info = media_ops.get_media_info(path)
        clip = {"input": path, "trim_start": 0.0, "trim_end": info["duration_sec"], "crop": None, "fade_in": 0.0, "fade_out": 0.0}
        self.timeline_clips.append(clip)
        self._refresh_timeline_list()

    def _refresh_timeline_list(self) -> None:
        self.timeline_list.clear()
        for clip in self.timeline_clips:
            crop_note = f", crop={clip['crop']}" if clip["crop"] else ""
            self.timeline_list.addItem(
                f"{os.path.basename(clip['input'])} [{clip['trim_start']:.2f}s -> {clip['trim_end']:.2f}s]{crop_note}"
            )

    def _timeline_edit_clip(self) -> None:
        row = self.timeline_list.currentRow()
        if row < 0:
            return
        clip = self.timeline_clips[row]

        start, ok = QInputDialog.getDouble(self, "Trim Start", "Start (seconds):", clip["trim_start"], 0.0, 100000.0, 2)
        if not ok:
            return
        end, ok = QInputDialog.getDouble(self, "Trim End", "End (seconds):", clip["trim_end"], 0.0, 100000.0, 2)
        if not ok:
            return
        fade_in, ok = QInputDialog.getDouble(self, "Fade In", "Fade in duration (seconds, 0 = none):", clip["fade_in"], 0.0, 30.0, 2)
        if not ok:
            return
        fade_out, ok = QInputDialog.getDouble(self, "Fade Out", "Fade out duration (seconds, 0 = none):", clip["fade_out"], 0.0, 30.0, 2)
        if not ok:
            return
        crop_text, ok = QInputDialog.getText(
            self, "Crop", "Crop as x,y,width,height (blank = no crop):",
            text=",".join(str(v) for v in clip["crop"]) if clip["crop"] else "",
        )
        if not ok:
            return

        clip["trim_start"] = start
        clip["trim_end"] = end
        clip["fade_in"] = fade_in
        clip["fade_out"] = fade_out
        crop_text = crop_text.strip()
        if crop_text:
            try:
                x, y, cw, ch = (int(v.strip()) for v in crop_text.split(","))
                clip["crop"] = (x, y, cw, ch)
            except ValueError:
                QMessageBox.warning(self, "Invalid Crop", "Crop must be four comma-separated integers: x,y,width,height")
        else:
            clip["crop"] = None
        self._refresh_timeline_list()

    def _timeline_remove_clip(self) -> None:
        row = self.timeline_list.currentRow()
        if row >= 0:
            del self.timeline_clips[row]
            self._refresh_timeline_list()

    def _timeline_move_clip(self, direction: int) -> None:
        row = self.timeline_list.currentRow()
        new_row = row + direction
        if row < 0 or not (0 <= new_row < len(self.timeline_clips)):
            return
        self.timeline_clips[row], self.timeline_clips[new_row] = self.timeline_clips[new_row], self.timeline_clips[row]
        self._refresh_timeline_list()
        self.timeline_list.setCurrentRow(new_row)

    def _refresh_timeline_audio_list(self) -> None:
        self.timeline_audio_list.clear()
        for track in self.timeline_audio_tracks:
            self.timeline_audio_list.addItem(
                f"{os.path.basename(track['path'])} [vol={track['volume']:.2f}, "
                f"fade_in={track['fade_in']:.1f}s, fade_out={track['fade_out']:.1f}s, "
                f"offset={track['start_offset']:.1f}s]"
            )

    def _timeline_add_audio_track(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Add Audio Track", "", "Audio Files (*.mp3 *.wav *.aac *.flac *.ogg *.m4a)")
        if not path:
            return
        self.timeline_audio_tracks.append(
            {"path": path, "volume": 1.0, "fade_in": 0.0, "fade_out": 0.0, "start_offset": 0.0}
        )
        self._refresh_timeline_audio_list()

    def _timeline_edit_audio_track(self) -> None:
        row = self.timeline_audio_list.currentRow()
        if row < 0:
            return
        track = self.timeline_audio_tracks[row]

        volume, ok = QInputDialog.getDouble(self, "Volume", "Volume (0.0 - 3.0):", track["volume"], 0.0, 3.0, 2)
        if not ok:
            return
        fade_in, ok = QInputDialog.getDouble(self, "Fade In", "Fade in duration (seconds, 0 = none):", track["fade_in"], 0.0, 30.0, 2)
        if not ok:
            return
        fade_out, ok = QInputDialog.getDouble(self, "Fade Out", "Fade out duration (seconds, 0 = none):", track["fade_out"], 0.0, 30.0, 2)
        if not ok:
            return
        start_offset, ok = QInputDialog.getDouble(
            self, "Start Offset", "Delay before this track starts playing (seconds):", track["start_offset"], 0.0, 100000.0, 2
        )
        if not ok:
            return

        track["volume"] = volume
        track["fade_in"] = fade_in
        track["fade_out"] = fade_out
        track["start_offset"] = start_offset
        self._refresh_timeline_audio_list()

    def _timeline_remove_audio_track(self) -> None:
        row = self.timeline_audio_list.currentRow()
        if row >= 0:
            del self.timeline_audio_tracks[row]
            self._refresh_timeline_audio_list()

    def _run_compose_timeline(self) -> None:
        if not self.timeline_clips:
            QMessageBox.warning(self, "No Clips", "Add at least one clip to the timeline first.")
            return
        export_format = self.timeline_format_combo.currentText()
        out, _ = QFileDialog.getSaveFileName(
            self, "Save Composed Timeline", f"timeline.{export_format}", f"{export_format.upper()} File (*.{export_format})"
        )
        if not out:
            return

        width = int(self.timeline_width_spin.value()) or None
        height = int(self.timeline_height_spin.value()) or None

        self._run_worker(
            media_ops.compose_timeline, list(self.timeline_clips), out,
            export_format=export_format, target_width=width, target_height=height,
            fps=int(self.timeline_fps_spin.value()),
            crossfade_duration=self.timeline_crossfade_spin.value(),
            audio_tracks=list(self.timeline_audio_tracks) or None,
        )

    # ─── Batch Processing Tab ────────────────────────────────────────────────
    def _build_batch_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Run one operation across multiple video/audio files and save the results to a folder."))

        queue_row = QHBoxLayout()
        self.batch_list = QListWidget()
        self.batch_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        queue_row.addWidget(self.batch_list, stretch=1)

        queue_btns = QVBoxLayout()
        add_btn = QPushButton("Add Files...")
        add_btn.setToolTip(get_tooltip_for("Add Files"))
        add_btn.clicked.connect(self._batch_add_files)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setToolTip(get_tooltip_for("Remove Selected"))
        remove_btn.clicked.connect(self._batch_remove_selected)
        clear_btn = QPushButton("Clear")
        clear_btn.setToolTip(get_tooltip_for("Clear Queue"))
        clear_btn.clicked.connect(self._batch_clear)
        queue_btns.addWidget(add_btn)
        queue_btns.addWidget(remove_btn)
        queue_btns.addWidget(clear_btn)
        queue_btns.addStretch()
        queue_row.addLayout(queue_btns)
        layout.addLayout(queue_row, stretch=1)

        form = QFormLayout()
        self.batch_mode_combo = QComboBox()
        self.batch_mode_combo.setToolTip(get_tooltip_for("Batch Operation"))
        self.batch_mode_combo.addItems(["Convert", "Compress", "Extract Audio"])
        self.batch_mode_combo.currentIndexChanged.connect(self._on_batch_mode_changed)
        form.addRow("Operation:", self.batch_mode_combo)
        layout.addLayout(form)

        self.batch_options_stack = QStackedWidget()
        self.batch_options_stack.addWidget(self._build_batch_convert_options())
        self.batch_options_stack.addWidget(self._build_batch_compress_options())
        self.batch_options_stack.addWidget(self._build_batch_extract_audio_options())
        layout.addWidget(self.batch_options_stack)

        out_row = QHBoxLayout()
        self.batch_output_edit = QLineEdit()
        self.batch_output_edit.setReadOnly(True)
        self.batch_output_edit.setPlaceholderText("Choose an output folder...")
        out_browse_btn = QPushButton("Browse...")
        out_browse_btn.setToolTip(get_tooltip_for("Choose Batch Output Folder"))
        out_browse_btn.clicked.connect(self._batch_choose_output_dir)
        out_row.addWidget(self.batch_output_edit, stretch=1)
        out_row.addWidget(out_browse_btn)
        layout.addLayout(out_row)

        self.batch_progress = QProgressBar()
        self.batch_progress.setValue(0)
        layout.addWidget(self.batch_progress)

        self.start_batch_btn = QPushButton("Start Batch")
        self.start_batch_btn.setToolTip(get_tooltip_for("Start Batch"))
        self.start_batch_btn.setStyleSheet(f"font-weight: 700; padding: 9px 18px; font-size: {scaled_font_pt(13)};")
        self.start_batch_btn.clicked.connect(self._start_batch)
        layout.addWidget(self.start_batch_btn)

        return w

    def _build_batch_convert_options(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.batch_convert_fmt_combo = QComboBox()
        self.batch_convert_fmt_combo.setToolTip(get_tooltip_for("Batch Target Format"))
        self.batch_convert_fmt_combo.addItems(["MP4", "MKV", "MOV", "WEBM", "AVI", "MP3", "WAV"])
        form.addRow("Target Format:", self.batch_convert_fmt_combo)
        self.batch_convert_crf_combo = QComboBox()
        self.batch_convert_crf_combo.setToolTip(get_tooltip_for("Batch Video Quality"))
        self.batch_convert_crf_combo.addItem("High Quality (CRF 18)", 18)
        self.batch_convert_crf_combo.addItem("Balanced (CRF 23) - Recommended", 23)
        self.batch_convert_crf_combo.addItem("Smaller File (CRF 28)", 28)
        self.batch_convert_crf_combo.setCurrentIndex(1)
        form.addRow("Video Quality:", self.batch_convert_crf_combo)
        return w

    def _build_batch_compress_options(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.batch_compress_preset_combo = QComboBox()
        self.batch_compress_preset_combo.setToolTip(get_tooltip_for("Batch Compression Preset"))
        self.batch_compress_preset_combo.addItem("Discord / Email Target (small, CRF 28)", "discord")
        self.batch_compress_preset_combo.addItem("Balanced (CRF 24)", "balanced")
        self.batch_compress_preset_combo.addItem("High Quality (CRF 20)", "quality")
        form.addRow("Compression Preset:", self.batch_compress_preset_combo)
        return w

    def _build_batch_extract_audio_options(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.batch_audio_fmt_combo = QComboBox()
        self.batch_audio_fmt_combo.setToolTip(get_tooltip_for("Batch Audio Format"))
        self.batch_audio_fmt_combo.addItems(["MP3", "WAV", "AAC", "FLAC", "M4A", "OGG"])
        form.addRow("Audio Format:", self.batch_audio_fmt_combo)
        self.batch_audio_br_combo = QComboBox()
        self.batch_audio_br_combo.setToolTip(get_tooltip_for("Batch Audio Bitrate"))
        self.batch_audio_br_combo.addItems(["320k", "256k", "192k", "128k"])
        self.batch_audio_br_combo.setCurrentIndex(2)
        form.addRow("Audio Bitrate:", self.batch_audio_br_combo)
        return w

    def _on_batch_mode_changed(self, index: int) -> None:
        self.batch_options_stack.setCurrentIndex(index)

    def _batch_add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Choose media files for batch processing",
            "",
            "Media Files (*.mp4 *.mov *.mkv *.avi *.webm *.mp3 *.wav *.aac *.flac *.ogg *.m4a);;All Files (*.*)",
        )
        if not paths:
            return
        for path in paths:
            self.batch_items.append(media_ops.BatchMediaItem(input_path=path))
        self._refresh_batch_list()

    def _batch_remove_selected(self) -> None:
        rows = sorted((index.row() for index in self.batch_list.selectedIndexes()), reverse=True)
        for row in rows:
            del self.batch_items[row]
        self._refresh_batch_list()

    def _batch_clear(self) -> None:
        self.batch_items.clear()
        self.batch_progress.setValue(0)
        self._refresh_batch_list()

    def _refresh_batch_list(self) -> None:
        self.batch_list.clear()
        for item in self.batch_items:
            label = os.path.basename(item.input_path)
            if item.status == "done":
                label += "  [done]"
            elif item.status == "failed":
                label += f"  [failed: {item.error}]"
            list_item = QListWidgetItem(label)
            list_item.setToolTip(item.input_path)
            self.batch_list.addItem(list_item)

    def _batch_choose_output_dir(self) -> None:
        out = QFileDialog.getExistingDirectory(self, "Choose Batch Output Folder")
        if out:
            self.batch_output_dir = out
            self.batch_output_edit.setText(out)

    def _start_batch(self) -> None:
        if not self.batch_items:
            QMessageBox.warning(self, "No files", "Add files to the batch queue first.")
            return
        if not self.batch_output_dir:
            QMessageBox.warning(self, "No output folder", "Choose an output folder first.")
            return

        self.batch_progress.setMaximum(len(self.batch_items))
        self.batch_progress.setValue(0)
        self.start_batch_btn.setEnabled(False)

        def _progress(done: int, total: int, filename: str) -> None:
            self.batch_progress.setValue(done)
            self._refresh_batch_list()

        mode = self.batch_mode_combo.currentText()
        if mode == "Convert":
            fmt = self.batch_convert_fmt_combo.currentText().lower()
            crf = self.batch_convert_crf_combo.currentData()
            self._worker = WorkerThread(
                media_ops.batch_convert_media, self.batch_items, self.batch_output_dir,
                target_format=fmt, crf=crf, progress_cb=_progress,
            )
        elif mode == "Compress":
            preset = self.batch_compress_preset_combo.currentData()
            self._worker = WorkerThread(
                media_ops.batch_compress_media, self.batch_items, self.batch_output_dir,
                preset=preset, progress_cb=_progress,
            )
        else:
            fmt = self.batch_audio_fmt_combo.currentText().lower()
            bitrate = self.batch_audio_br_combo.currentText()
            self._worker = WorkerThread(
                media_ops.batch_extract_audio, self.batch_items, self.batch_output_dir,
                audio_format=fmt, bitrate=bitrate, progress_cb=_progress,
            )

        self._worker.finished_ok.connect(self._on_batch_ok)
        self._worker.failed.connect(self._on_batch_failed)
        self._worker.start()

    def _on_batch_ok(self, results: list) -> None:
        self.start_batch_btn.setEnabled(True)
        self._refresh_batch_list()
        done_count = sum(1 for item in results if item.status == "done")
        QMessageBox.information(self, "Batch Complete", f"Successfully processed {done_count} of {len(results)} file(s).")

    def _on_batch_failed(self, error: str) -> None:
        self.start_batch_btn.setEnabled(True)
        QMessageBox.critical(self, "Batch Error", f"Batch processing error: {error}")

    # ─── File Loading & Info ─────────────────────────────────────────────────
    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Media File",
            "",
            "Media Files (*.mp4 *.mov *.mkv *.avi *.webm *.mp3 *.wav *.aac *.flac *.ogg *.m4a);;All Files (*.*)"
        )
        if path:
            self.load_file(path)

    def load_file(self, path: str) -> None:
        if not os.path.exists(path):
            return
        self.current_path = path
        self.file_path_edit.setText(path)

        try:
            self.media_info = media_ops.get_media_info(path)
            dur_sec = self.media_info.get("duration_sec", 0.0)
            self.duration_ms = int(dur_sec * 1000)

            # Update info card
            res_txt = "Audio file (no video stream)"
            if self.media_info.get("has_video"):
                w = self.media_info.get("width", "")
                h = self.media_info.get("height", "")
                fps = self.media_info.get("fps", "")
                res_txt = f"{w} × {h} @ {fps} fps"
            self.info_res_lbl.setText(res_txt)
            self.info_dur_lbl.setText(f"{self.media_info.get('duration_str')} ({dur_sec:.1f}s)")

            vcodec = self.media_info.get("video_codec") or "None"
            acodec = self.media_info.get("audio_codec") or "None"
            self.info_codec_lbl.setText(f"Video: {vcodec} | Audio: {acodec}")

            sz_mb = self.media_info.get("size_bytes", 0) / (1024 * 1024)
            self.info_size_lbl.setText(f"{sz_mb:.2f} MB")

            # Setup trim spins
            self.start_spin.setValue(0.0)
            self.end_spin.setValue(dur_sec)
            self._update_range_label()

            # Load into player
            if self.player:
                self.player.setSource(QUrl.fromLocalFile(path))
                self.time_label.setText(f"00:00:00.0 / {self.media_info.get('duration_str')}")
        except Exception as exc:
            QMessageBox.critical(self, "Media Error", f"Could not parse media file:\n{exc}")

    # ─── Player Controls ─────────────────────────────────────────────────────
    def _toggle_playback(self) -> None:
        if not self.player or not self.current_path:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_btn.setText("▶ Play")
        else:
            self.player.play()
            self.play_btn.setText("⏸ Pause")

    def _stop_playback(self) -> None:
        if self.player:
            self.player.stop()
            self.play_btn.setText("▶ Play")

    def _on_player_position_changed(self, pos_ms: int) -> None:
        if self.duration_ms > 0:
            val = int((pos_ms / self.duration_ms) * 1000)
            self.seek_slider.setValue(val)
        curr_str = media_ops.format_timestamp(pos_ms / 1000.0)
        tot_str = media_ops.format_timestamp(self.duration_ms / 1000.0)
        self.time_label.setText(f"{curr_str} / {tot_str}")

    def _on_player_duration_changed(self, dur_ms: int) -> None:
        if dur_ms > 0:
            self.duration_ms = dur_ms

    def _on_seek_moved(self, val: int) -> None:
        if self.player and self.duration_ms > 0:
            target_ms = int((val / 1000.0) * self.duration_ms)
            self.player.setPosition(target_ms)

    def _on_volume_changed(self, val: int) -> None:
        if self.audio_output:
            self.audio_output.setVolume(val / 100.0)

    # ─── Trim Markers ────────────────────────────────────────────────────────
    def _mark_in(self) -> None:
        if self.player:
            sec = self.player.position() / 1000.0
            self.start_spin.setValue(sec)

    def _mark_out(self) -> None:
        if self.player:
            sec = self.player.position() / 1000.0
            self.end_spin.setValue(sec)

    def _update_range_label(self) -> None:
        start = self.start_spin.value()
        end = self.end_spin.value()
        dur = max(0.0, end - start)
        self.range_summary_lbl.setText(f"Selection duration: {media_ops.format_timestamp(dur)} ({dur:.3f}s)")

    # ─── Background Operations ───────────────────────────────────────────────
    def _run_worker(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        self.progress_bar.setVisible(True)

        self._worker = WorkerThread(fn, *args, **kwargs)
        self._worker.finished_ok.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_error)
        self._worker.start()

    def _on_worker_finished(self, output_path: Any) -> None:
        self._cleanup_worker()
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Success", f"Operation completed successfully!\nOutput saved to:\n{output_path}")

    def _on_worker_error(self, err_msg: str) -> None:
        self._cleanup_worker()
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Operation Failed", f"FFmpeg processing failed:\n{err_msg}")

    def _cleanup_worker(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait()
        self._worker = None

    # ─── Actions ─────────────────────────────────────────────────────────────
    def _run_trim(self) -> None:
        if not self.current_path:
            return
        ext = os.path.splitext(self.current_path)[1]
        base = os.path.splitext(os.path.basename(self.current_path))[0]
        out, _ = QFileDialog.getSaveFileName(self, "Save Trimmed Media", f"{base}_trimmed{ext}")
        if not out:
            return

        fast_copy = self.trim_mode_combo.currentData()
        start_sec = self.start_spin.value()
        end_sec = self.end_spin.value()

        self._run_worker(
            media_ops.trim_media,
            self.current_path,
            out,
            start_time_sec=start_sec,
            end_time_sec=end_sec,
            fast_copy=fast_copy,
        )

    def _run_extract_audio(self) -> None:
        if not self.current_path:
            return
        fmt = self.audio_fmt_combo.currentText().split()[0].lower()
        br = self.audio_br_combo.currentText().split()[0] + "k"
        base = os.path.splitext(os.path.basename(self.current_path))[0]
        out, _ = QFileDialog.getSaveFileName(self, "Save Extracted Audio", f"{base}_audio.{fmt}")
        if not out:
            return

        self._run_worker(
            media_ops.extract_audio,
            self.current_path,
            out,
            audio_format=fmt,
            bitrate=br,
        )

    def _run_convert(self) -> None:
        if not self.current_path:
            return
        fmt = self.convert_fmt_combo.currentText().split()[0].lower()
        crf = self.convert_crf_combo.currentData()
        base = os.path.splitext(os.path.basename(self.current_path))[0]
        out, _ = QFileDialog.getSaveFileName(self, "Save Converted Media", f"{base}_converted.{fmt}")
        if not out:
            return

        self._run_worker(
            media_ops.convert_media,
            self.current_path,
            out,
            target_format=fmt,
            crf=crf,
        )

    def _run_compress(self) -> None:
        if not self.current_path:
            return
        preset, target_res = self.compress_preset_combo.currentData()
        ext = os.path.splitext(self.current_path)[1]
        base = os.path.splitext(os.path.basename(self.current_path))[0]
        out, _ = QFileDialog.getSaveFileName(self, "Save Compressed Video", f"{base}_compressed{ext}")
        if not out:
            return

        self._run_worker(
            media_ops.compress_video,
            self.current_path,
            out,
            preset=preset,
            target_resolution=target_res,
        )

    def _run_mute(self) -> None:
        if not self.current_path:
            return
        ext = os.path.splitext(self.current_path)[1]
        base = os.path.splitext(os.path.basename(self.current_path))[0]
        out, _ = QFileDialog.getSaveFileName(self, "Save Muted Video", f"{base}_muted{ext}")
        if not out:
            return

        self._run_worker(
            media_ops.mute_video,
            self.current_path,
            out,
        )

    def _run_capture_frame(self) -> None:
        if not self.current_path:
            return
        pos_sec = (self.player.position() / 1000.0) if self.player else 0.0
        base = os.path.splitext(os.path.basename(self.current_path))[0]
        out, _ = QFileDialog.getSaveFileName(self, "Save Video Frame", f"{base}_frame_{int(pos_sec)}s.png", "Images (*.png *.jpg)")
        if not out:
            return

        try:
            media_ops.extract_frame(self.current_path, out, timestamp_sec=pos_sec)
            QMessageBox.information(self, "Frame Captured", f"Video frame exported to:\n{out}")
        except Exception as exc:
            QMessageBox.critical(self, "Capture Failed", str(exc))

    def _run_transcription(self) -> None:
        if not self.current_path:
            return
        language, ok = QInputDialog.getText(self, "Transcribe Audio", "Language code (e.g. en, es, fr):", text="en")
        if not ok:
            return

        self.transcription_status_label.setText("Transcribing locally... this may take a while.")
        self.progress_bar.setVisible(True)
        self._worker = WorkerThread(media_ops.transcribe_audio, self.current_path, language.strip() or "en")
        self._worker.finished_ok.connect(self._on_transcription_finished)
        self._worker.failed.connect(self._on_transcription_failed)
        self._worker.start()

    def _on_transcription_finished(self, result: dict) -> None:
        self._cleanup_worker()
        self.progress_bar.setVisible(False)
        if result.get("status") != "success":
            self.last_transcription = None
            self.transcription_status_label.setText(result.get("warning", "Transcription unavailable."))
            return
        self.last_transcription = result
        self.transcription_status_label.setText(
            f"Transcribed {len(result['segments'])} segment(s). Use 'Generate Subtitle File...' to export with real timing."
        )

    def _on_transcription_failed(self, err_msg: str) -> None:
        self._cleanup_worker()
        self.progress_bar.setVisible(False)
        self.transcription_status_label.setText(f"Transcription failed: {err_msg}")

    def _generate_subtitles(self) -> None:
        if not self.current_path:
            return

        base = os.path.splitext(os.path.basename(self.current_path))[0]
        out, _ = QFileDialog.getSaveFileName(
            self,
            "Save Subtitle File",
            f"{base}_captions.srt",
            "Subtitle Files (*.srt *.vtt)",
        )
        if not out:
            return
        subtitle_format = os.path.splitext(out)[1].lower().lstrip(".") or "srt"

        if self.last_transcription and self.last_transcription.get("segments"):
            use_transcript = QMessageBox.question(
                self, "Use Transcription Timing",
                f"Use the {len(self.last_transcription['segments'])} timed segment(s) from the last transcription instead of typing cues manually?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if use_transcript == QMessageBox.StandardButton.Yes:
                self._run_worker(
                    media_ops.generate_subtitles_from_transcription, self.last_transcription, out, subtitle_format=subtitle_format
                )
                return

        text, ok = QInputDialog.getMultiLineText(
            self,
            "Subtitle Cues",
            "Enter subtitle timings and text. Example:\n00:00:00,000 --> 00:00:02,000\nHello world\n\n00:00:02,000 --> 00:00:04,000\nSecond cue",
            "",
        )
        if not ok or not text.strip():
            return

        cue_list = media_ops.parse_subtitle_cues(text)
        if not cue_list:
            QMessageBox.critical(
                self,
                "Invalid Subtitle Input",
                "No valid subtitle cues were found. Use timecoded entries like '00:00:00,000 --> 00:00:02,000'.",
            )
            return

        self._run_worker(media_ops.generate_subtitle_file, text, out, subtitle_format=subtitle_format)

    def _mix_audio_with_video(self) -> None:
        if not self.current_path:
            return

        audio_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select audio track to mix into the current video",
            "",
            "Audio Files (*.mp3 *.wav *.aac *.flac *.ogg *.m4a);;All Files (*.*)",
        )
        if not audio_path:
            return

        base = os.path.splitext(os.path.basename(self.current_path))[0]
        out, _ = QFileDialog.getSaveFileName(
            self,
            "Save Mixed Video",
            f"{base}_mixed.mp4",
            "Video Files (*.mp4 *.mkv *.mov *.avi *.webm)",
        )
        if not out:
            return

        volume, ok = QInputDialog.getDouble(
            self,
            "Mix Volume",
            "Set the audio level for the overlay (0.0 to 3.0):",
            1.0,
            0.0,
            3.0,
            2,
        )
        if not ok:
            return

        fade_in, ok = QInputDialog.getDouble(
            self,
            "Fade In",
            "Fade in duration in seconds:",
            0.0,
            0.0,
            60.0,
            2,
        )
        if not ok:
            return

        fade_out, ok = QInputDialog.getDouble(
            self,
            "Fade Out",
            "Fade out duration in seconds:",
            0.0,
            0.0,
            60.0,
            2,
        )
        if not ok:
            return

        self._run_worker(
            media_ops.compose_media_with_audio,
            self.current_path,
            out,
            audio_path,
            volume=volume,
            fade_in=fade_in,
            fade_out=fade_out,
        )

