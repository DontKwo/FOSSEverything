"""Resume Studio workspace: master resume management, granular per-job tailoring, and ATS optimization."""
from __future__ import annotations

import os
from typing import Optional, Any
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QPushButton, QLabel, QFileDialog, QMessageBox, QGroupBox, QTabWidget,
    QProgressBar, QScrollArea, QFrame, QTextEdit, QCheckBox, QSplitter,
    QInputDialog, QSizePolicy
)

from app.core.customizable_toolbar import AppToolBar
from app.features.resume import ops as resume_ops
from app.core.theme import resolved_palette, theme_signals
from app.core.tooltips import get_tooltip_for
from app.ui.ui_scaling import scaled_font_pt, scaled_font_size


def _apply_delete_button_style(button: QPushButton, *, bold: bool = False) -> None:
    weight = " font-weight: bold;" if bold else ""
    button.setStyleSheet(f"color: {resolved_palette()['accent']};{weight}")


class BulletRowWidget(QFrame):
    """Row representing a single bullet point with check-to-include and inline edit."""
    changed = pyqtSignal()
    delete_requested = pyqtSignal(str)
    move_up_requested = pyqtSignal(str)
    move_down_requested = pyqtSignal(str)

    def __init__(self, bullet: resume_ops.BulletPoint, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.bullet = bullet
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._refresh_frame_colors()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        self.check = QCheckBox()
        self.check.setChecked(bullet.enabled)
        self.check.setToolTip(get_tooltip_for("Include bullet"))
        self.check.toggled.connect(self._on_toggled)
        layout.addWidget(self.check)

        self.edit = QLineEdit(bullet.text)
        self.edit.setPlaceholderText("Bullet text (e.g. Achieved 40% performance gain by...)")
        self.edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.edit, stretch=1)

        up_btn = QPushButton("▲")
        up_btn.setFixedSize(22, 22)
        up_btn.setToolTip(get_tooltip_for("Move bullet up"))
        up_btn.clicked.connect(lambda: self.move_up_requested.emit(self.bullet.id))
        layout.addWidget(up_btn)

        down_btn = QPushButton("▼")
        down_btn.setFixedSize(22, 22)
        down_btn.setToolTip(get_tooltip_for("Move bullet down"))
        down_btn.clicked.connect(lambda: self.move_down_requested.emit(self.bullet.id))
        layout.addWidget(down_btn)

        self.del_btn = QPushButton("x")
        self.del_btn.setFixedSize(22, 22)
        _apply_delete_button_style(self.del_btn, bold=True)
        self.del_btn.setToolTip(get_tooltip_for("Delete bullet"))
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self.bullet.id))
        layout.addWidget(self.del_btn)

        theme_signals.changed.connect(self._refresh_theme_colors)

    def _refresh_frame_colors(self) -> None:
        palette = resolved_palette()
        self.setStyleSheet(
            f"QFrame {{ background: {palette['panel']}; "
            f"border: 1px solid {palette['border']}; border-radius: 4px; padding: 2px; }}"
        )

    def _refresh_theme_colors(self) -> None:
        _apply_delete_button_style(self.del_btn, bold=True)
        self._refresh_frame_colors()

    def _on_toggled(self, checked: bool) -> None:
        self.bullet.enabled = checked
        self.changed.emit()

    def _on_text_changed(self, text: str) -> None:
        self.bullet.text = text
        self.changed.emit()


class EntryWidget(QGroupBox):
    """Card representing an individual job role, project, or degree entry."""
    changed = pyqtSignal()
    delete_requested = pyqtSignal(str)
    move_up_requested = pyqtSignal(str)
    move_down_requested = pyqtSignal(str)

    def __init__(self, entry: resume_ops.ResumeEntry, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.entry = entry
        self.setTitle(f"{entry.title or 'Entry'}")
        self.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; border: 1px solid {resolved_palette()['border']}; "
            f"border-radius: 6px; margin-top: 6px; padding-top: 10px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Header controls
        hdr_row = QHBoxLayout()
        self.check = QCheckBox("Enable Entry")
        self.check.setChecked(entry.enabled)
        self.check.setToolTip(get_tooltip_for("Enable Entry"))
        self.check.toggled.connect(self._on_toggled)
        hdr_row.addWidget(self.check)
        hdr_row.addStretch()

        up_btn = QPushButton("▲ Move Up")
        up_btn.setToolTip(get_tooltip_for("Move section up"))
        up_btn.clicked.connect(lambda: self.move_up_requested.emit(self.entry.id))
        hdr_row.addWidget(up_btn)

        down_btn = QPushButton("▼ Move Down")
        down_btn.setToolTip(get_tooltip_for("Move section down"))
        down_btn.clicked.connect(lambda: self.move_down_requested.emit(self.entry.id))
        hdr_row.addWidget(down_btn)

        self.del_btn = QPushButton("Delete Entry")
        self.del_btn.setToolTip(get_tooltip_for("Delete section"))
        _apply_delete_button_style(self.del_btn)
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self.entry.id))
        hdr_row.addWidget(self.del_btn)
        layout.addLayout(hdr_row)

        theme_signals.changed.connect(self._refresh_theme_colors)

        # Entry fields
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        self.title_edit = QLineEdit(entry.title)
        self.title_edit.setPlaceholderText("Job Title / Degree / Project Name")
        self.title_edit.textChanged.connect(self._on_title_changed)
        form.addRow("Title / Role:", self.title_edit)

        sub_row = QHBoxLayout()
        self.sub_edit = QLineEdit(entry.subtitle)
        self.sub_edit.setPlaceholderText("Company / Institution / Tech")
        self.sub_edit.textChanged.connect(self._on_sub_changed)
        sub_row.addWidget(self.sub_edit, stretch=2)

        self.date_edit = QLineEdit(entry.date_range)
        self.date_edit.setPlaceholderText("Dates (e.g. 2022 - Present)")
        self.date_edit.textChanged.connect(self._on_date_changed)
        sub_row.addWidget(self.date_edit, stretch=1)

        self.loc_edit = QLineEdit(entry.location)
        self.loc_edit.setPlaceholderText("Location (e.g. San Francisco, CA)")
        self.loc_edit.textChanged.connect(self._on_loc_changed)
        sub_row.addWidget(self.loc_edit, stretch=1)
        form.addRow("Details:", sub_row)
        layout.addLayout(form)

        # Bullets container
        b_label_row = QHBoxLayout()
        b_label_row.addWidget(QLabel("Bullet Points (Check to include in tailored resume):"))
        b_label_row.addStretch()
        add_b_btn = QPushButton("Add Bullet")
        add_b_btn.setToolTip(get_tooltip_for("Add Bullet"))
        add_b_btn.clicked.connect(self._add_bullet)
        b_label_row.addWidget(add_b_btn)
        layout.addLayout(b_label_row)

        self.bullets_vbox = QVBoxLayout()
        self.bullets_vbox.setSpacing(8)
        layout.addLayout(self.bullets_vbox)

        self._render_bullets()

    def _refresh_theme_colors(self) -> None:
        _apply_delete_button_style(self.del_btn)
        self.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; border: 1px solid {resolved_palette()['border']}; "
            f"border-radius: 6px; margin-top: 6px; padding-top: 10px; }}"
        )

    def _render_bullets(self) -> None:
        while self.bullets_vbox.count():
            item = self.bullets_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for b in self.entry.bullets:
            row = BulletRowWidget(b, self)
            row.changed.connect(self.changed.emit)
            row.delete_requested.connect(self._delete_bullet)
            row.move_up_requested.connect(self._move_bullet_up)
            row.move_down_requested.connect(self._move_bullet_down)
            self.bullets_vbox.addWidget(row)

    def _on_toggled(self, checked: bool) -> None:
        self.entry.enabled = checked
        self.changed.emit()

    def _on_title_changed(self, text: str) -> None:
        self.entry.title = text
        self.setTitle(f"{text or 'Entry'}")
        self.changed.emit()

    def _on_sub_changed(self, text: str) -> None:
        self.entry.subtitle = text
        self.changed.emit()

    def _on_date_changed(self, text: str) -> None:
        self.entry.date_range = text
        self.changed.emit()

    def _on_loc_changed(self, text: str) -> None:
        self.entry.location = text
        self.changed.emit()

    def _add_bullet(self) -> None:
        b = resume_ops.BulletPoint(text="", enabled=True)
        self.entry.bullets.append(b)
        self._render_bullets()
        self.changed.emit()

    def _delete_bullet(self, bullet_id: str) -> None:
        self.entry.bullets = [b for b in self.entry.bullets if b.id != bullet_id]
        self._render_bullets()
        self.changed.emit()

    def _move_bullet_up(self, bullet_id: str) -> None:
        idx = next((i for i, b in enumerate(self.entry.bullets) if b.id == bullet_id), -1)
        if idx > 0:
            self.entry.bullets[idx - 1], self.entry.bullets[idx] = self.entry.bullets[idx], self.entry.bullets[idx - 1]
            self._render_bullets()
            self.changed.emit()

    def _move_bullet_down(self, bullet_id: str) -> None:
        idx = next((i for i, b in enumerate(self.entry.bullets) if b.id == bullet_id), -1)
        if idx >= 0 and idx < len(self.entry.bullets) - 1:
            self.entry.bullets[idx + 1], self.entry.bullets[idx] = self.entry.bullets[idx], self.entry.bullets[idx + 1]
            self._render_bullets()
            self.changed.emit()


class SectionWidget(QFrame):
    """Container for an entire section with retitling and entry list."""
    changed = pyqtSignal()
    delete_requested = pyqtSignal(str)
    move_up_requested = pyqtSignal(str)
    move_down_requested = pyqtSignal(str)

    def __init__(self, section: resume_ops.ResumeSection, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.section = section
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._refresh_frame_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header bar
        hdr_row = QHBoxLayout()
        self.check = QCheckBox()
        self.check.setChecked(section.enabled)
        self.check.setToolTip(get_tooltip_for("Enable Section"))
        self.check.toggled.connect(self._on_toggled)
        hdr_row.addWidget(self.check)

        hdr_row.addWidget(QLabel("Section Title:"))
        self.title_edit = QLineEdit(section.title)
        self.title_edit.setPlaceholderText("Section title")
        self.title_edit.setStyleSheet(f"font-weight: 700; font-size: {scaled_font_pt(13)};")
        self.title_edit.textChanged.connect(self._on_title_changed)
        hdr_row.addWidget(self.title_edit, stretch=1)

        up_btn = QPushButton("▲")
        up_btn.setToolTip(get_tooltip_for("Move section up"))
        up_btn.clicked.connect(lambda: self.move_up_requested.emit(self.section.id))
        hdr_row.addWidget(up_btn)

        down_btn = QPushButton("▼")
        down_btn.setToolTip(get_tooltip_for("Move section down"))
        down_btn.clicked.connect(lambda: self.move_down_requested.emit(self.section.id))
        hdr_row.addWidget(down_btn)

        self.del_btn = QPushButton("Delete Section")
        self.del_btn.setToolTip(get_tooltip_for("Delete Section"))
        _apply_delete_button_style(self.del_btn)
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self.section.id))
        hdr_row.addWidget(self.del_btn)
        layout.addLayout(hdr_row)

        theme_signals.changed.connect(self._refresh_theme_colors)

        # Entries container
        self.entries_vbox = QVBoxLayout()
        self.entries_vbox.setSpacing(8)
        layout.addLayout(self.entries_vbox)

        add_entry_btn = QPushButton("Add Role / Item to Section")
        add_entry_btn.setToolTip(get_tooltip_for("Add Role / Item to Section"))
        add_entry_btn.setStyleSheet("font-weight: 600; padding: 4px;")
        add_entry_btn.clicked.connect(self._add_entry)
        layout.addWidget(add_entry_btn)

        self._render_entries()

    def _refresh_frame_colors(self) -> None:
        palette = resolved_palette()
        self.setStyleSheet(
            f"SectionWidget {{ background: {palette['panel']}; "
            f"border: 2px solid {palette['border']}; border-radius: 8px; margin-bottom: 8px; }}"
        )

    def _refresh_theme_colors(self) -> None:
        _apply_delete_button_style(self.del_btn)
        self._refresh_frame_colors()

    def _render_entries(self) -> None:
        while self.entries_vbox.count():
            item = self.entries_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for entry in self.section.entries:
            w = EntryWidget(entry, self)
            w.changed.connect(self.changed.emit)
            w.delete_requested.connect(self._delete_entry)
            w.move_up_requested.connect(self._move_entry_up)
            w.move_down_requested.connect(self._move_entry_down)
            self.entries_vbox.addWidget(w)

    def _on_toggled(self, checked: bool) -> None:
        self.section.enabled = checked
        self.changed.emit()

    def _on_title_changed(self, text: str) -> None:
        self.section.title = text
        self.changed.emit()

    def _add_entry(self) -> None:
        e = resume_ops.ResumeEntry(
            title="",
            subtitle="",
            date_range="",
            location="",
            bullets=[resume_ops.BulletPoint(text="", enabled=True)],
            enabled=True,
        )
        self.section.entries.append(e)
        self._render_entries()
        self.changed.emit()

    def _delete_entry(self, entry_id: str) -> None:
        self.section.entries = [e for e in self.section.entries if e.id != entry_id]
        self._render_entries()
        self.changed.emit()

    def _move_entry_up(self, entry_id: str) -> None:
        idx = next((i for i, e in enumerate(self.section.entries) if e.id == entry_id), -1)
        if idx > 0:
            self.section.entries[idx - 1], self.section.entries[idx] = self.section.entries[idx], self.section.entries[idx - 1]
            self._render_entries()
            self.changed.emit()

    def _move_entry_down(self, entry_id: str) -> None:
        idx = next((i for i, e in enumerate(self.section.entries) if e.id == entry_id), -1)
        if idx >= 0 and idx < len(self.section.entries) - 1:
            self.section.entries[idx + 1], self.section.entries[idx] = self.section.entries[idx], self.section.entries[idx + 1]
            self._render_entries()
            self.changed.emit()


class ResumeTab(QWidget):
    """Master Resume & 1-Click Per-Job Tailoring Studio."""

    def _blank_resume(self) -> resume_ops.MasterResume:
        return resume_ops.MasterResume(
            contact=resume_ops.ContactInfo(name="", title="", email="", phone="", location="", linkedin="", github="", website=""),
            summary="",
            summary_enabled=True,
            sections=[],
            profiles={},
        )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.resume: resume_ops.MasterResume = self._blank_resume()
        self._build_ui()
        self._load_resume_to_ui()
        theme_signals.changed.connect(self._refresh_theme_colors)

    def _refresh_theme_colors(self) -> None:
        palette = resolved_palette()
        self.header_sub_label.setStyleSheet(f"font-size: {scaled_font_pt(12)}; color: {palette['muted']};")
        self.stats_lbl.setStyleSheet(f"color: {palette['accent']}; font-weight: 600;")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Header bar & Preset Profile Selector
        title = QLabel("Resume Studio")
        title.setStyleSheet(f"font-size: {scaled_font_pt(24)}; font-weight: 700;")
        self.header_sub_label = QLabel("Build a comprehensive master resume, then check/uncheck bullets and reorder sections to tailor per job.")
        self.header_sub_label.setStyleSheet(f"font-size: {scaled_font_pt(12)}; color: {resolved_palette()['muted']};")
        root.addWidget(title)
        root.addWidget(self.header_sub_label)

        top_bar = AppToolBar(None, "resume_toolbar")
        top_bar.add_action("New", self._new_resume)
        top_bar.add_action("Open...", self._open_resume)
        top_bar.add_action("Save Master...", self._save_resume)
        top_bar.addSeparator()

        top_bar.addWidget(QLabel("Job Tailoring Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setToolTip(get_tooltip_for("Job Tailoring Profile"))
        self.profile_combo.addItem("Full Master Resume (Default)", None)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        top_bar.addWidget(self.profile_combo)
        top_bar.add_action("Save Tailoring Preset...", self._save_preset)
        top_bar.finalize()
        root.addWidget(top_bar)

        # Main Splitter (Left: Master Editor, Right: Live Preview & ATS Matcher)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: Master Editor Scroll Area ──────────────────────────────────
        left_scroll = QScrollArea(widgetResizable=True, frameShape=QFrame.Shape.NoFrame)
        left_container = QWidget()
        self.left_vbox = QVBoxLayout(left_container)
        self.left_vbox.setContentsMargins(0, 0, 8, 0)
        self.left_vbox.setSpacing(10)

        # Contact info card
        contact_group = QGroupBox("Personal && Contact Details")
        c_form = QFormLayout(contact_group)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Your name")
        self.name_edit.textChanged.connect(self._on_contact_changed)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Professional title")
        self.title_edit.textChanged.connect(self._on_contact_changed)
        c_form.addRow("Full Name:", self.name_edit)
        c_form.addRow("Professional Title:", self.title_edit)

        c_row1 = QHBoxLayout()
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Email")
        self.email_edit.textChanged.connect(self._on_contact_changed)
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("Phone")
        self.phone_edit.textChanged.connect(self._on_contact_changed)
        c_row1.addWidget(self.email_edit)
        c_row1.addWidget(self.phone_edit)
        c_form.addRow("Email && Phone:", c_row1)

        c_row2 = QHBoxLayout()
        self.loc_edit = QLineEdit()
        self.loc_edit.setPlaceholderText("Location")
        self.loc_edit.textChanged.connect(self._on_contact_changed)
        self.web_edit = QLineEdit()
        self.web_edit.setPlaceholderText("Portfolio / website")
        self.web_edit.textChanged.connect(self._on_contact_changed)
        c_row2.addWidget(self.loc_edit)
        c_row2.addWidget(self.web_edit)
        c_form.addRow("Location && Portfolio:", c_row2)

        c_row3 = QHBoxLayout()
        self.li_edit = QLineEdit()
        self.li_edit.setPlaceholderText("LinkedIn")
        self.li_edit.textChanged.connect(self._on_contact_changed)
        self.gh_edit = QLineEdit()
        self.gh_edit.setPlaceholderText("GitHub")
        self.gh_edit.textChanged.connect(self._on_contact_changed)
        c_row3.addWidget(self.li_edit)
        c_row3.addWidget(self.gh_edit)
        c_form.addRow("LinkedIn && GitHub:", c_row3)

        self.left_vbox.addWidget(contact_group)

        # Summary card
        summary_group = QGroupBox("Executive Summary / Objective")
        s_layout = QVBoxLayout(summary_group)
        self.summary_check = QCheckBox("Include Summary in Tailored Resume")
        self.summary_check.setToolTip(get_tooltip_for("Include Summary in Tailored Resume"))
        self.summary_check.toggled.connect(self._on_summary_toggled)
        s_layout.addWidget(self.summary_check)

        self.summary_text = QTextEdit()
        self.summary_text.setPlaceholderText("Write a short profile summary for this resume...")
        self.summary_text.setMaximumHeight(100)
        self.summary_text.setStyleSheet(f"font-size: {scaled_font_pt(12)};")
        self.summary_text.textChanged.connect(self._on_summary_changed)
        s_layout.addWidget(self.summary_text)
        self.left_vbox.addWidget(summary_group)

        # Sections Container
        self.sections_vbox = QVBoxLayout()
        self.sections_vbox.setSpacing(10)
        self.left_vbox.addLayout(self.sections_vbox)

        # Add section button
        add_sec_btn = QPushButton("Add New Section (Experience, Projects, Skills, Education, Custom)...")
        add_sec_btn.setToolTip(get_tooltip_for("Add New Section"))
        add_sec_btn.setStyleSheet("font-weight: 700; padding: 8px;")
        add_sec_btn.clicked.connect(self._add_section_dialog)
        self.left_vbox.addWidget(add_sec_btn)

        left_scroll.setWidget(left_container)
        splitter.addWidget(left_scroll)

        # ── Right: Preview, Export & ATS Analyzer ────────────────────────────
        right_box = QWidget()
        right_vbox = QVBoxLayout(right_box)
        right_vbox.setContentsMargins(8, 0, 0, 0)
        right_vbox.setSpacing(8)

        self.right_tabs = QTabWidget()

        # Tab 1: Live Document Preview
        preview_widget = QWidget()
        p_layout = QVBoxLayout(preview_widget)
        p_layout.setContentsMargins(8, 8, 8, 8)
        p_layout.setSpacing(8)

        # Stats bar
        self.stats_lbl = QLabel("Sections: 0 | Entries: 0 | Bullets: 0")
        self.stats_lbl.setStyleSheet(f"color: {resolved_palette()['accent']}; font-weight: 600;")
        p_layout.addWidget(self.stats_lbl)

        self.preview_doc = QTextEdit()
        self.preview_doc.setReadOnly(True)
        self.preview_doc.setStyleSheet(f"font-size: {scaled_font_pt(10)};")
        self.preview_doc.setFont(QFont("Monospace", scaled_font_size(9)))
        p_layout.addWidget(self.preview_doc, stretch=1)

        # Export row
        exp_row = AppToolBar(None, "resume_export_toolbar")
        exp_row.add_action("Export PDF...", self._export_pdf)
        exp_row.add_action("Export Markdown...", self._export_md)
        exp_row.add_action("Export HTML...", self._export_html)
        exp_row.add_action("Copy Text", self._copy_text)
        exp_row.finalize()
        p_layout.addWidget(exp_row)

        self.right_tabs.addTab(preview_widget, "Live Preview && Export")

        # Tab 2: ATS Keyword Matcher
        ats_widget = QWidget()
        ats_layout = QVBoxLayout(ats_widget)
        ats_layout.setContentsMargins(8, 8, 8, 8)
        ats_layout.setSpacing(8)

        ats_layout.addWidget(QLabel("Paste Target Job Description:"))
        self.job_desc_input = QTextEdit()
        self.job_desc_input.setPlaceholderText("Paste job posting requirements, skills, and qualifications here...")
        ats_layout.addWidget(self.job_desc_input, stretch=1)

        analyze_btn = QPushButton("Analyze ATS Match Score && Missing Keywords")
        analyze_btn.setToolTip(get_tooltip_for("Analyze ATS Match Score"))
        analyze_btn.setStyleSheet("font-weight: 700; padding: 6px;")
        analyze_btn.clicked.connect(self._analyze_ats)
        ats_layout.addWidget(analyze_btn)

        self.ats_score_bar = QProgressBar()
        self.ats_score_bar.setRange(0, 100)
        self.ats_score_bar.setValue(0)
        ats_layout.addWidget(self.ats_score_bar)

        self.ats_results = QTextEdit()
        self.ats_results.setReadOnly(True)
        ats_layout.addWidget(self.ats_results, stretch=1)


        right_vbox.addWidget(self.right_tabs)
        splitter.addWidget(right_box)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)
        root.addWidget(splitter, stretch=1)

    # ─── Data Binding & Rendering ────────────────────────────────────────────
    def _load_resume_to_ui(self) -> None:
        c = self.resume.contact
        self.name_edit.setText(c.name)
        self.title_edit.setText(c.title)
        self.email_edit.setText(c.email)
        self.phone_edit.setText(c.phone)
        self.loc_edit.setText(c.location)
        self.web_edit.setText(c.website)
        self.li_edit.setText(c.linkedin)
        self.gh_edit.setText(c.github)

        self.summary_check.setChecked(self.resume.summary_enabled)
        self.summary_text.setText(self.resume.summary)

        # Profile combo
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem("Full Master Resume (Default)", None)
        for prof_name in self.resume.profiles.keys():
            self.profile_combo.addItem(f"Preset: {prof_name}", prof_name)
        self.profile_combo.blockSignals(False)

        self._render_sections()
        self._update_preview()

    def _render_sections(self) -> None:
        while self.sections_vbox.count():
            item = self.sections_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for sec in self.resume.sections:
            w = SectionWidget(sec, self)
            w.changed.connect(self._update_preview)
            w.delete_requested.connect(self._delete_section)
            w.move_up_requested.connect(self._move_section_up)
            w.move_down_requested.connect(self._move_section_down)
            self.sections_vbox.addWidget(w)

    def _update_preview(self) -> None:
        md = resume_ops.export_markdown(self.resume)
        self.preview_doc.setText(md)

        # Stats
        active_secs = sum(1 for s in self.resume.sections if s.enabled)
        active_entries = sum(sum(1 for e in s.entries if e.enabled) for s in self.resume.sections if s.enabled)
        active_bullets = sum(sum(sum(1 for b in e.bullets if b.enabled) for e in s.entries if e.enabled) for s in self.resume.sections if s.enabled)
        total_bullets = sum(sum(len(e.bullets) for e in s.entries) for s in self.resume.sections)
        self.stats_lbl.setText(f"Active Sections: {active_secs}/{len(self.resume.sections)} | Active Roles: {active_entries} | Active Bullets: {active_bullets}/{total_bullets}")

    # ─── Contact & Summary Listeners ─────────────────────────────────────────
    def _on_contact_changed(self) -> None:
        self.resume.contact.name = self.name_edit.text()
        self.resume.contact.title = self.title_edit.text()
        self.resume.contact.email = self.email_edit.text()
        self.resume.contact.phone = self.phone_edit.text()
        self.resume.contact.location = self.loc_edit.text()
        self.resume.contact.website = self.web_edit.text()
        self.resume.contact.linkedin = self.li_edit.text()
        self.resume.contact.github = self.gh_edit.text()
        self._update_preview()

    def _on_summary_toggled(self, checked: bool) -> None:
        self.resume.summary_enabled = checked
        self._update_preview()

    def _on_summary_changed(self) -> None:
        self.resume.summary = self.summary_text.toPlainText()
        self._update_preview()

    # ─── Section Operations ──────────────────────────────────────────────────
    def _add_section_dialog(self) -> None:
        types = ["Professional Experience", "Featured Projects", "Technical Skills", "Education", "Certifications", "Awards", "Custom Section"]
        title, ok = QInputDialog.getItem(self, "Add Resume Section", "Select section template or enter title:", types, 0, True)
        if ok and title:
            sec = resume_ops.ResumeSection(
                title=title,
                type="custom",
                entries=[resume_ops.ResumeEntry(title="New Entry", bullets=[resume_ops.BulletPoint(text="Key detail...")])],
                enabled=True,
            )
            self.resume.sections.append(sec)
            self._render_sections()
            self._update_preview()

    def _delete_section(self, section_id: str) -> None:
        self.resume.sections = [s for s in self.resume.sections if s.id != section_id]
        self._render_sections()
        self._update_preview()

    def _move_section_up(self, section_id: str) -> None:
        idx = next((i for i, s in enumerate(self.resume.sections) if s.id == section_id), -1)
        if idx > 0:
            self.resume.sections[idx - 1], self.resume.sections[idx] = self.resume.sections[idx], self.resume.sections[idx - 1]
            self._render_sections()
            self._update_preview()

    def _move_section_down(self, section_id: str) -> None:
        idx = next((i for i, s in enumerate(self.resume.sections) if s.id == section_id), -1)
        if idx >= 0 and idx < len(self.resume.sections) - 1:
            self.resume.sections[idx + 1], self.resume.sections[idx] = self.resume.sections[idx], self.resume.sections[idx + 1]
            self._render_sections()
            self._update_preview()

    # ─── Tailoring Presets ───────────────────────────────────────────────────
    def _save_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Tailoring Preset", "Enter name for this tailored job profile (e.g. Backend Lead):")
        if ok and name.strip():
            prof_name = name.strip()
            resume_ops.save_profile(self.resume, prof_name)
            self.profile_combo.addItem(f"Preset: {prof_name}", prof_name)
            self.profile_combo.setCurrentIndex(self.profile_combo.count() - 1)
            QMessageBox.information(self, "Preset Saved", f"Tailoring preset '{prof_name}' saved to your master resume!")

    def _on_profile_selected(self, index: int) -> None:
        prof_name = self.profile_combo.currentData()
        if prof_name:
            resume_ops.apply_profile(self.resume, prof_name)
        else:
            # Enable all
            self.resume.summary_enabled = True
            for s in self.resume.sections:
                s.enabled = True
                for e in s.entries:
                    e.enabled = True
                    for b in e.bullets:
                        b.enabled = True
        self._load_resume_to_ui()

    # ─── File Persistence ────────────────────────────────────────────────────
    def _new_resume(self) -> None:
        res = QMessageBox.question(self, "New Resume", "Create a blank master resume? Any unsaved changes will be cleared.")
        if res == QMessageBox.StandardButton.Yes:
            self.resume = self._blank_resume()
            self._load_resume_to_ui()

    def _open_resume(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Master Resume", "", "Master Resume JSON (*.json);;All Files (*.*)")
        if path:
            try:
                self.resume = resume_ops.load_resume_file(path)
                self._load_resume_to_ui()
                QMessageBox.information(self, "Opened", f"Loaded master resume from:\n{path}")
            except Exception as exc:
                QMessageBox.critical(self, "Error Opening", str(exc))

    def _save_resume(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Master Resume", "master_resume.json", "Master Resume JSON (*.json)")
        if path:
            try:
                resume_ops.save_resume_file(self.resume, path)
                QMessageBox.information(self, "Saved", f"Master resume saved to:\n{path}")
            except Exception as exc:
                QMessageBox.critical(self, "Error Saving", str(exc))

    # ─── ATS Analyzer ────────────────────────────────────────────────────────
    def _analyze_ats(self) -> None:
        job_desc = self.job_desc_input.toPlainText().strip()
        if not job_desc:
            QMessageBox.warning(self, "No Job Description", "Paste a job description to analyze.")
            return

        res = resume_ops.analyze_ats_match(self.resume, job_desc)
        score = res["score"]
        self.ats_score_bar.setValue(score)

        report = [f"=== ATS KEYWORD MATCH SCORE: {score}% ===", ""]
        report.append(f"Matched Keywords ({len(res['matched'])}):")
        if res["matched"]:
            report.append(", ".join(f"{kw} ({cnt}x)" for kw, cnt in res["matched"][:25]))
        else:
            report.append("None found.")
        report.append("")

        report.append(f"Missing Key Terms ({len(res['missing'])}):")
        if res["missing"]:
            report.append(", ".join(f"{kw} ({cnt}x)" for kw, cnt in res["missing"][:25]))
            report.append("\nTip: Enable matching bullets in your master resume or incorporate these terms into your summary/experience.")
        else:
            report.append("Great job! All top keywords are present in your active resume.")

        self.ats_results.setText("\n".join(report))

    # ─── Export Actions ──────────────────────────────────────────────────────
    def _export_pdf(self) -> None:
        out, _ = QFileDialog.getSaveFileName(self, "Export Tailored Resume PDF", "resume.pdf", "PDF Documents (*.pdf)")
        if out:
            try:
                resume_ops.export_pdf(self.resume, out)
                QMessageBox.information(self, "Exported", f"Tailored PDF successfully exported to:\n{out}")
            except Exception as exc:
                QMessageBox.critical(self, "Export Failed", str(exc))

    def _export_md(self) -> None:
        out, _ = QFileDialog.getSaveFileName(self, "Export Tailored Resume Markdown", "resume.md", "Markdown Documents (*.md)")
        if out:
            try:
                md = resume_ops.export_markdown(self.resume)
                with open(out, "w", encoding="utf-8") as f:
                    f.write(md)
                QMessageBox.information(self, "Exported", f"Tailored Markdown successfully exported to:\n{out}")
            except Exception as exc:
                QMessageBox.critical(self, "Export Failed", str(exc))

    def _export_html(self) -> None:
        out, _ = QFileDialog.getSaveFileName(self, "Export Tailored Resume HTML", "resume.html", "HTML Documents (*.html)")
        if out:
            try:
                html = resume_ops.export_html(self.resume)
                with open(out, "w", encoding="utf-8") as f:
                    f.write(html)
                QMessageBox.information(self, "Exported", f"Tailored HTML successfully exported to:\n{out}")
            except Exception as exc:
                QMessageBox.critical(self, "Export Failed", str(exc))

    def _copy_text(self) -> None:
        md = resume_ops.export_markdown(self.resume)
        QGuiApplication.clipboard().setText(md)
        QMessageBox.information(self, "Copied", "Tailored resume text copied to clipboard!")
