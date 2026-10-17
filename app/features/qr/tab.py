"""QR Codes tab: create, customize, export, scan, and decode QR codes & barcodes."""
from __future__ import annotations

import os
from typing import Any, Optional

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QColor, QImage, QPixmap, QGuiApplication, QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QTextEdit, QPushButton, QLabel, QFileDialog, QMessageBox,
    QColorDialog, QGroupBox, QScrollArea, QFrame, QTabWidget, QListWidget,
    QListWidgetItem, QSplitter, QCheckBox, QInputDialog
)
from PIL import Image
import pymupdf

from app.core.customizable_toolbar import AppToolBar
from app.core.spinbox import NoScrollSpinBox
from app.features.qr import ops as qr_ops
from app.features.data import ops as data_ops
from app.core.theme import resolved_palette, theme_signals
from app.core.tooltips import get_tooltip_for
from app.ui.ui_scaling import scaled_font_pt

BARCODE_SYMBOLOGIES = [
    ("Code 39", "code39"),
    ("Code 128", "code128"),
    ("EAN-13", "ean13"),
    ("EAN-8", "ean8"),
    ("UPC-A", "upca"),
    ("ITF (Interleaved 2 of 5)", "itf"),
]


def _pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    img = pil_img.convert("RGBA")
    raw = img.tobytes("raw", "RGBA")
    qimg = QImage(raw, img.width, img.height, img.width * 4, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


class QrTab(QWidget):
    """Workspace for generating and decoding QR codes & barcodes locally."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.fg_color = QColor(0, 0, 0)
        self.bg_color = QColor(255, 255, 255)
        self.logo_path = None
        self.current_pil_qr = None
        self.current_decoded_items = []

        self._build_ui()
        self._update_qr_preview()
        theme_signals.changed.connect(self._refresh_theme_colors)

    def _refresh_theme_colors(self) -> None:
        border = resolved_palette()["border"]
        self.fg_preview.setStyleSheet(f"background-color: {self.fg_color.name()}; border: 1px solid {border}; border-radius: 3px;")
        self.bg_preview.setStyleSheet(f"background-color: {self.bg_color.name()}; border: 1px solid {border}; border-radius: 3px;")
        self.preview_label.setStyleSheet(f"border: 1px solid {border}; border-radius: 6px;")
        self.scan_img_label.setStyleSheet(f"border: 1px dashed {border}; border-radius: 6px; padding: 20px;")

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        self.sub_tabs = QTabWidget()
        main_layout.addWidget(self.sub_tabs)

        # Tab 1: Generator
        gen_tab = QWidget()
        self._build_generator_ui(gen_tab)
        self.sub_tabs.addTab(gen_tab, "QR Generator")

        # Tab 2: Scanner / Decoder
        scan_tab = QWidget()
        self._build_scanner_ui(scan_tab)
        self.sub_tabs.addTab(scan_tab, "Scan && Decode")

    def _build_generator_ui(self, gen_tab: QWidget) -> None:
        root = QHBoxLayout(gen_tab)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(20)

        left_scroll = QScrollArea(widgetResizable=True, frameShape=QFrame.Shape.NoFrame)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)

        title = QLabel("QR Code Generator")
        title.setStyleSheet("font-weight: 700;")
        left_layout.addWidget(title)
        left_layout.addWidget(QLabel("Generate custom QR codes 100% offline. No internet required."))

        type_group = QGroupBox("Payload Type")
        type_form = QFormLayout(type_group)
        self.type_combo = QComboBox()
        self.type_combo.setToolTip(get_tooltip_for("Payload Type"))
        self.type_combo.addItems([
            "URL / Web Link",
            "Wi-Fi Network",
            "Plain Text",
            "Contact Card (vCard)",
            "Business Card (MeCard)",
            "Email Address",
            "Phone Number",
            "SMS Message",
            "WhatsApp Message",
            "Geo Location",
            "Calendar Event",
            "Asset / Inventory Tag",
            "Barcode",
        ])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_form.addRow("Type:", self.type_combo)
        left_layout.addWidget(type_group)

        # Dynamic fields container
        self.fields_group = QGroupBox("Content Details")
        self.fields_layout = QFormLayout(self.fields_group)
        left_layout.addWidget(self.fields_group)

        # URL
        self.url_input = QLineEdit("https://github.com/fosseverything")
        self.url_input.setPlaceholderText("https://example.com")
        self.url_input.textChanged.connect(self._update_qr_preview)

        # Wi-Fi
        self.wifi_ssid = QLineEdit("MyHomeNetwork")
        self.wifi_pass = QLineEdit()
        self.wifi_pass.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.wifi_sec = QComboBox()
        self.wifi_sec.setToolTip(get_tooltip_for("Wi-Fi Security"))
        self.wifi_sec.addItems(["WPA/WPA2/WPA3", "WEP", "Open (No Password)"])
        self.wifi_ssid.textChanged.connect(self._update_qr_preview)
        self.wifi_pass.textChanged.connect(self._update_qr_preview)
        self.wifi_sec.currentIndexChanged.connect(self._update_qr_preview)

        # Plain Text
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter arbitrary text or notes...")
        self.text_input.textChanged.connect(self._update_qr_preview)

        # vCard
        self.vcard_fn = QLineEdit("Jane Doe")
        self.vcard_org = QLineEdit("Acme Corp")
        self.vcard_tel = QLineEdit("+1 (555) 019-2834")
        self.vcard_email = QLineEdit("jane@example.com")
        self.vcard_url = QLineEdit("https://janedoe.me")
        for w in (self.vcard_fn, self.vcard_org, self.vcard_tel, self.vcard_email, self.vcard_url):
            w.textChanged.connect(self._update_qr_preview)

        # MeCard
        self.mecard_name = QLineEdit("Jane Doe")
        self.mecard_org = QLineEdit("Acme Corp")
        self.mecard_tel = QLineEdit("+1 (555) 019-2834")
        self.mecard_email = QLineEdit("jane@example.com")
        self.mecard_url = QLineEdit("https://janedoe.me")
        self.mecard_address = QLineEdit()
        for w in (self.mecard_name, self.mecard_org, self.mecard_tel, self.mecard_email, self.mecard_url, self.mecard_address):
            w.textChanged.connect(self._update_qr_preview)

        # Email
        self.email_to = QLineEdit("contact@example.com")
        self.email_sub = QLineEdit("Hello")
        self.email_body = QTextEdit()
        self.email_to.textChanged.connect(self._update_qr_preview)
        self.email_sub.textChanged.connect(self._update_qr_preview)
        self.email_body.textChanged.connect(self._update_qr_preview)

        # Phone and SMS
        self.phone_input = QLineEdit("+1-415-555-0100")
        self.phone_input.textChanged.connect(self._update_qr_preview)
        self.sms_number = QLineEdit("+1-415-555-0100")
        self.sms_message = QTextEdit("Meeting at 3pm")
        self.sms_number.textChanged.connect(self._update_qr_preview)
        self.sms_message.textChanged.connect(self._update_qr_preview)

        # WhatsApp
        self.whatsapp_number = QLineEdit("+1-415-555-0100")
        self.whatsapp_message = QTextEdit("Hi, I found you via QR code!")
        self.whatsapp_number.textChanged.connect(self._update_qr_preview)
        self.whatsapp_message.textChanged.connect(self._update_qr_preview)

        # Geo
        self.geo_lat = QLineEdit("40.7128")
        self.geo_lon = QLineEdit("-74.0060")
        self.geo_alt = QLineEdit("0")
        for w in (self.geo_lat, self.geo_lon, self.geo_alt):
            w.textChanged.connect(self._update_qr_preview)

        # Calendar
        self.calendar_summary = QLineEdit("Team sync")
        self.calendar_start = QLineEdit("2026-09-01T10:00:00")
        self.calendar_end = QLineEdit("2026-09-01T10:30:00")
        self.calendar_location = QLineEdit("HQ")
        self.calendar_desc = QTextEdit("Review sprint goals and blockers.")
        for w in (self.calendar_summary, self.calendar_start, self.calendar_end, self.calendar_location):
            w.textChanged.connect(self._update_qr_preview)
        self.calendar_desc.textChanged.connect(self._update_qr_preview)
        self.calendar_ics_btn = QPushButton("Save as .ics File...")
        self.calendar_ics_btn.setToolTip(get_tooltip_for("Save as .ics File"))
        self.calendar_ics_btn.clicked.connect(self._save_calendar_ics)

        # Asset / Inventory Tag
        self.asset_id = QLineEdit("AST-0001")
        self.asset_category = QLineEdit("Laptop")
        self.asset_location = QLineEdit("HQ Rack 3")
        self.asset_owner = QLineEdit("IT Department")
        self.asset_notes = QLineEdit()
        for w in (self.asset_id, self.asset_category, self.asset_location, self.asset_owner, self.asset_notes):
            w.textChanged.connect(self._update_qr_preview)

        self.barcode_value = QLineEdit("ABC123")
        self.barcode_value.setPlaceholderText("ABC123")
        self.barcode_value.textChanged.connect(self._update_qr_preview)
        self.barcode_symbology = QComboBox()
        self.barcode_symbology.setToolTip(get_tooltip_for("Barcode Symbology"))
        for label, code in BARCODE_SYMBOLOGIES:
            self.barcode_symbology.addItem(label, code)
        self.barcode_symbology.currentIndexChanged.connect(self._update_qr_preview)
        self.barcode_label_toggle = QCheckBox("Show value label")
        self.barcode_label_toggle.setToolTip(get_tooltip_for("Show value label"))
        self.barcode_label_toggle.setChecked(True)
        self.barcode_label_toggle.stateChanged.connect(self._update_qr_preview)

        self._rebuild_content_fields(0)

        # Logo embedding
        logo_group = QGroupBox("Center Logo / Icon Embedding")
        logo_form = QFormLayout(logo_group)
        logo_row = QHBoxLayout()
        self.logo_label = QLabel("No logo selected")
        self.logo_label.setStyleSheet("font-style: italic;")
        self.browse_logo_btn = QPushButton("Choose Logo...")
        self.browse_logo_btn.setToolTip(get_tooltip_for("Choose Logo"))
        self.browse_logo_btn.clicked.connect(self._browse_logo)
        self.clear_logo_btn = QPushButton("Clear")
        self.clear_logo_btn.setToolTip(get_tooltip_for("Clear Logo"))
        self.clear_logo_btn.clicked.connect(self._clear_logo)
        self.clear_logo_btn.setEnabled(False)
        logo_row.addWidget(self.browse_logo_btn)
        logo_row.addWidget(self.clear_logo_btn)
        logo_row.addWidget(self.logo_label, 1)
        logo_form.addRow("Logo Image:", logo_row)

        self.logo_scale_spin = NoScrollSpinBox()
        self.logo_scale_spin.setToolTip(get_tooltip_for("Logo Size"))
        self.logo_scale_spin.setRange(10, 35)
        self.logo_scale_spin.setValue(22)
        self.logo_scale_spin.setSuffix("% of QR size")
        self.logo_scale_spin.valueChanged.connect(self._update_qr_preview)
        logo_form.addRow("Logo Size:", self.logo_scale_spin)
        left_layout.addWidget(logo_group)

        # Appearance & Quality
        style_group = QGroupBox("Styling && Resolution")
        style_form = QFormLayout(style_group)

        color_row = QHBoxLayout()
        self.fg_btn = QPushButton("Foreground Color")
        self.fg_btn.setToolTip(get_tooltip_for("Foreground Color"))
        self.fg_btn.clicked.connect(self._choose_fg_color)
        self.fg_preview = QLabel("   ")
        border = resolved_palette()["border"]
        self.fg_preview.setStyleSheet(f"background-color: {self.fg_color.name()}; border: 1px solid {border}; border-radius: 3px;")
        self.bg_btn = QPushButton("Background Color")
        self.bg_btn.setToolTip(get_tooltip_for("Background Color"))
        self.bg_btn.clicked.connect(self._choose_bg_color)
        self.bg_preview = QLabel("   ")
        self.bg_preview.setStyleSheet(f"background-color: {self.bg_color.name()}; border: 1px solid {border}; border-radius: 3px;")
        color_row.addWidget(self.fg_btn)
        color_row.addWidget(self.fg_preview)
        color_row.addSpacing(10)
        color_row.addWidget(self.bg_btn)
        color_row.addWidget(self.bg_preview)
        color_row.addStretch()
        style_form.addRow("Colors:", color_row)

        self.ecc_combo = QComboBox()
        self.ecc_combo.setToolTip(get_tooltip_for("Error Correction"))
        self.ecc_combo.addItem("M - Standard (~15% recovery)", "M")
        self.ecc_combo.addItem("L - Low (~7% recovery)", "L")
        self.ecc_combo.addItem("Q - Medium-High (~25% recovery)", "Q")
        self.ecc_combo.addItem("H - Highest (~30% recovery, best with logos)", "H")
        self.ecc_combo.currentIndexChanged.connect(self._update_qr_preview)
        style_form.addRow("Error Correction:", self.ecc_combo)

        self.size_spin = NoScrollSpinBox()
        self.size_spin.setToolTip(get_tooltip_for("Module Size"))
        self.size_spin.setRange(2, 40)
        self.size_spin.setValue(10)
        self.size_spin.setSuffix(" px/module")
        self.size_spin.valueChanged.connect(self._update_qr_preview)
        style_form.addRow("Module Size:", self.size_spin)
        left_layout.addWidget(style_group)
        left_layout.addStretch()

        left_scroll.setWidget(left_widget)
        root.addWidget(left_scroll, 3)

        # Right side: preview & actions
        right_panel = QVBoxLayout()
        right_panel.setSpacing(14)

        preview_box = QGroupBox("Live Preview")
        preview_box_layout = QVBoxLayout(preview_box)
        preview_box_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(280, 280)
        border = resolved_palette()["border"]
        self.preview_label.setStyleSheet(f"border: 1px solid {border}; border-radius: 6px;")
        preview_box_layout.addWidget(self.preview_label)

        self.info_label = QLabel("Export Size: 330x330 px")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet(f"font-size: {scaled_font_pt(11)};")
        preview_box_layout.addWidget(self.info_label)
        right_panel.addWidget(preview_box)

        btn_box = QGroupBox("Export && Share")
        btn_layout = QVBoxLayout(btn_box)

        copy_btn = QPushButton("Copy Image to Clipboard")
        copy_btn.setToolTip(get_tooltip_for("Copy Image to Clipboard"))
        copy_btn.setStyleSheet("padding: 8px; font-weight: 600;")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(copy_btn)

        save_png_btn = QPushButton("Save Image (PNG / JPEG / WEBP / PDF)...")
        save_png_btn.setToolTip(get_tooltip_for("Save Image"))
        save_png_btn.setStyleSheet("padding: 8px;")
        save_png_btn.clicked.connect(self.save_qr_image)
        btn_layout.addWidget(save_png_btn)

        save_svg_btn = QPushButton("Export Vector SVG (Lossless Print)...")
        save_svg_btn.setToolTip(get_tooltip_for("Export Vector SVG"))
        save_svg_btn.setStyleSheet("padding: 8px;")
        save_svg_btn.clicked.connect(self.export_svg)
        btn_layout.addWidget(save_svg_btn)

        save_label_sheet_btn = QPushButton("Print Label Sheet (PDF)...")
        save_label_sheet_btn.setToolTip(get_tooltip_for("Print Label Sheet"))
        save_label_sheet_btn.setStyleSheet("padding: 8px;")
        save_label_sheet_btn.clicked.connect(self.save_label_sheet)
        btn_layout.addWidget(save_label_sheet_btn)

        right_panel.addWidget(btn_box)
        right_panel.addStretch()

        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        root.addWidget(right_widget, 2)

    def _build_scanner_ui(self, scan_tab: QWidget) -> None:
        layout = QVBoxLayout(scan_tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        top_bar = AppToolBar(None, "qr_scanner_toolbar")
        top_bar.add_action("Open Image or PDF...", self._scan_browse_file, tooltip_key="Open Image or PDF")
        top_bar.add_action("Paste from Clipboard", self._scan_paste_clipboard)
        top_bar.finalize()
        layout.addWidget(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: image preview
        left_box = QGroupBox("Input Image Preview")
        left_layout = QVBoxLayout(left_box)
        self.scan_img_label = QLabel("Open an image/PDF or paste a screenshot to detect QR codes and barcodes.")
        self.scan_img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        border = resolved_palette()["border"]
        self.scan_img_label.setStyleSheet(f"border: 1px dashed {border}; border-radius: 6px; padding: 20px;")
        left_layout.addWidget(self.scan_img_label)
        splitter.addWidget(left_box)

        # Right: decoded results
        right_box = QGroupBox("Decoded Results")
        right_layout = QVBoxLayout(right_box)

        self.scan_results_list = QListWidget()
        self.scan_results_list.currentRowChanged.connect(self._on_scan_result_selected)
        right_layout.addWidget(self.scan_results_list, 1)

        # Result detail card
        self.detail_card = QGroupBox("Payload Details")
        self.detail_layout = QVBoxLayout(self.detail_card)

        self.detail_title = QLabel("No code selected")
        self.detail_title.setStyleSheet(f"font-weight: 700; font-size: {scaled_font_pt(14)};")
        self.detail_layout.addWidget(self.detail_title)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_layout.addWidget(self.detail_text)

        action_toolbar = AppToolBar(None, "qr_scan_result_toolbar")
        action_toolbar.add_action("Copy Text", self._copy_scanned_payload)
        self.open_url_btn = action_toolbar.add_action("Open URL in Browser", self._open_scanned_url)
        self.open_url_btn.setVisible(False)
        self.copy_wifi_btn = action_toolbar.add_action("Copy Wi-Fi Password", self._copy_scanned_wifi_pass)
        self.copy_wifi_btn.setVisible(False)
        action_toolbar.finalize()
        self.detail_layout.addWidget(action_toolbar)

        right_layout.addWidget(self.detail_card, 2)
        splitter.addWidget(right_box)

        layout.addWidget(splitter)

    # ─── Scanner Handlers ────────────────────────────────────────────────────
    def load_file(self, file_path: str) -> None:
        """Load and decode a file directly."""
        self.sub_tabs.setCurrentIndex(1)
        self._decode_file_path(file_path)

    def _scan_browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image or PDF for QR/Barcode Scan", "",
            "All Supported (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.pdf);;Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff);;PDFs (*.pdf)"
        )
        if path:
            self._decode_file_path(path)

    def _scan_paste_clipboard(self) -> None:
        cb = QGuiApplication.clipboard()
        img = cb.image()
        if not img.isNull():
            pixmap = QPixmap.fromImage(img)
            self._display_and_decode_pixmap(pixmap)
        else:
            QMessageBox.information(self, "Clipboard Empty", "No image found on clipboard.")

    def _decode_file_path(self, file_path: str) -> None:
        try:
            if file_path.lower().endswith(".pdf"):
                doc = pymupdf.open(file_path)
                if len(doc) > 0:
                    pix = doc[0].get_pixmap(dpi=150)
                    qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimg)
                    self.scan_img_label.setPixmap(pixmap.scaled(320, 320, Qt.AspectRatioMode.KeepAspectRatio))
            else:
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    self.scan_img_label.setPixmap(pixmap.scaled(320, 320, Qt.AspectRatioMode.KeepAspectRatio))

            results = qr_ops.decode_qr_and_barcodes(file_path)
            self._populate_scan_results(results)
        except Exception as exc:
            QMessageBox.critical(self, "Scan Failed", f"Error scanning file: {exc}")

    def _display_and_decode_pixmap(self, pixmap: QPixmap) -> None:
        self.scan_img_label.setPixmap(pixmap.scaled(320, 320, Qt.AspectRatioMode.KeepAspectRatio))
        # Convert to PIL
        qimg = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        raw = qimg.bits().asstring(qimg.sizeInBytes())
        pil_img = Image.frombuffer("RGBA", (qimg.width(), qimg.height()), raw, "raw", "RGBA", 0, 1)
        try:
            results = qr_ops.decode_qr_and_barcodes(pil_img)
            self._populate_scan_results(results)
        except Exception as exc:
            QMessageBox.critical(self, "Scan Failed", f"Error scanning image: {exc}")

    def _populate_scan_results(self, results: list[dict[str, Any]]) -> None:
        self.current_decoded_items = results
        self.scan_results_list.clear()

        if not results:
            self.scan_results_list.addItem("No QR codes or barcodes detected in image.")
            self.detail_title.setText("None Detected")
            self.detail_text.setPlainText("No scannable QR code or barcode pattern found in this document/image.")
            self.open_url_btn.setVisible(False)
            self.copy_wifi_btn.setVisible(False)
            return

        for idx, item in enumerate(results):
            parsed = item.get("parsed", {})
            title = parsed.get("title", item.get("type", "Code"))
            page_note = f" (Page {item['page']})" if "page" in item else ""
            list_item = QListWidgetItem(f"[{item['type']}] {title}{page_note}")
            self.scan_results_list.addItem(list_item)

        self.scan_results_list.setCurrentRow(0)

    def _on_scan_result_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.current_decoded_items):
            return
        item = self.current_decoded_items[row]
        parsed = item.get("parsed", {})
        ptype = parsed.get("type", "text")
        payload = item.get("payload", "")

        self.detail_title.setText(f"{item['type']}: {parsed.get('title', 'Decoded Content')}")
        self.detail_text.setPlainText(payload)

        # Context action buttons
        self.open_url_btn.setVisible(ptype == "url")
        self.copy_wifi_btn.setVisible(ptype == "wifi")

    def _copy_scanned_payload(self) -> None:
        text = self.detail_text.toPlainText()
        if text:
            QGuiApplication.clipboard().setText(text)
            QMessageBox.information(self, "Copied", "Payload copied to clipboard!")

    def _open_scanned_url(self) -> None:
        url = self.detail_text.toPlainText().strip()
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _copy_scanned_wifi_pass(self) -> None:
        row = self.scan_results_list.currentRow()
        if 0 <= row < len(self.current_decoded_items):
            parsed = self.current_decoded_items[row].get("parsed", {})
            pw = parsed.get("data", {}).get("password", "")
            if pw:
                QGuiApplication.clipboard().setText(pw)
                QMessageBox.information(self, "Copied", "Wi-Fi password copied to clipboard!")
            else:
                QMessageBox.information(self, "No Password", "This Wi-Fi network has no password (Open).")

    # ─── Generator Handlers ──────────────────────────────────────────────────
    def _on_type_changed(self, idx: int) -> None:
        self._rebuild_content_fields(idx)
        self._update_qr_preview()

    def _rebuild_content_fields(self, idx: int) -> None:
        while self.fields_layout.count():
            item = self.fields_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        if idx == 0:  # URL
            self.fields_layout.addRow("Website URL:", self.url_input)
        elif idx == 1:  # Wi-Fi
            self.fields_layout.addRow("Network Name (SSID):", self.wifi_ssid)
            self.fields_layout.addRow("Security Type:", self.wifi_sec)
            self.fields_layout.addRow("Password:", self.wifi_pass)
        elif idx == 2:  # Text
            self.fields_layout.addRow("Message Text:", self.text_input)
        elif idx == 3:  # vCard
            self.fields_layout.addRow("Full Name:", self.vcard_fn)
            self.fields_layout.addRow("Organization:", self.vcard_org)
            self.fields_layout.addRow("Phone:", self.vcard_tel)
            self.fields_layout.addRow("Email:", self.vcard_email)
            self.fields_layout.addRow("Website:", self.vcard_url)
        elif idx == 4:  # MeCard
            self.fields_layout.addRow("Full Name:", self.mecard_name)
            self.fields_layout.addRow("Organization:", self.mecard_org)
            self.fields_layout.addRow("Phone:", self.mecard_tel)
            self.fields_layout.addRow("Email:", self.mecard_email)
            self.fields_layout.addRow("Website:", self.mecard_url)
            self.fields_layout.addRow("Address:", self.mecard_address)
        elif idx == 5:  # Email
            self.fields_layout.addRow("To Email:", self.email_to)
            self.fields_layout.addRow("Subject:", self.email_sub)
            self.fields_layout.addRow("Message Body:", self.email_body)
        elif idx == 6:  # Phone
            self.fields_layout.addRow("Phone Number:", self.phone_input)
        elif idx == 7:  # SMS
            self.fields_layout.addRow("Phone Number:", self.sms_number)
            self.fields_layout.addRow("Message:", self.sms_message)
        elif idx == 8:  # WhatsApp
            self.fields_layout.addRow("Phone Number:", self.whatsapp_number)
            self.fields_layout.addRow("Prefilled Message:", self.whatsapp_message)
        elif idx == 9:  # Geo
            self.fields_layout.addRow("Latitude:", self.geo_lat)
            self.fields_layout.addRow("Longitude:", self.geo_lon)
            self.fields_layout.addRow("Altitude (optional):", self.geo_alt)
        elif idx == 10:  # Calendar
            self.fields_layout.addRow("Summary:", self.calendar_summary)
            self.fields_layout.addRow("Start:", self.calendar_start)
            self.fields_layout.addRow("End:", self.calendar_end)
            self.fields_layout.addRow("Location:", self.calendar_location)
            self.fields_layout.addRow("Description:", self.calendar_desc)
            self.fields_layout.addRow("", self.calendar_ics_btn)
        elif idx == 11:  # Asset tag
            self.fields_layout.addRow("Asset ID:", self.asset_id)
            self.fields_layout.addRow("Category:", self.asset_category)
            self.fields_layout.addRow("Location:", self.asset_location)
            self.fields_layout.addRow("Owner:", self.asset_owner)
            self.fields_layout.addRow("Notes:", self.asset_notes)
        elif idx == 12:  # Barcode
            self.fields_layout.addRow("Symbology:", self.barcode_symbology)
            self.fields_layout.addRow("Barcode Value:", self.barcode_value)
            self.fields_layout.addRow("Display label:", self.barcode_label_toggle)

    def _choose_fg_color(self) -> None:
        col = QColorDialog.getColor(self.fg_color, self, "Select Foreground Color")
        if col.isValid():
            self.fg_color = col
            border = resolved_palette()["border"]
            self.fg_preview.setStyleSheet(f"background-color: {col.name()}; border: 1px solid {border}; border-radius: 3px;")
            self._update_qr_preview()

    def _choose_bg_color(self) -> None:
        col = QColorDialog.getColor(self.bg_color, self, "Select Background Color")
        if col.isValid():
            self.bg_color = col
            border = resolved_palette()["border"]
            self.bg_preview.setStyleSheet(f"background-color: {col.name()}; border: 1px solid {border}; border-radius: 3px;")
            self._update_qr_preview()

    def _browse_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Center Logo Image", "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.svg);;All Files (*.*)"
        )
        if path:
            self.logo_path = path
            self.logo_label.setText(os.path.basename(path))
            self.logo_label.setStyleSheet("font-weight: 500;")
            self.clear_logo_btn.setEnabled(True)
            self._update_qr_preview()

    def _clear_logo(self) -> None:
        self.logo_path = None
        self.logo_label.setText("No logo selected")
        self.logo_label.setStyleSheet("font-style: italic;")
        self.clear_logo_btn.setEnabled(False)
        self._update_qr_preview()

    def _get_payload(self) -> str:
        idx = self.type_combo.currentIndex()
        if idx == 0:
            return self.url_input.text().strip()
        elif idx == 1:
            sec_idx = self.wifi_sec.currentIndex()
            sec_map = {0: "WPA", 1: "WEP", 2: "nopass"}
            return qr_ops.make_wifi_payload(
                ssid=self.wifi_ssid.text().strip(),
                password=self.wifi_pass.text().strip(),
                security=sec_map.get(sec_idx, "WPA"),
                hidden=False,
            )
        elif idx == 2:
            return self.text_input.toPlainText()
        elif idx == 3:
            return qr_ops.make_vcard_payload(
                name=self.vcard_fn.text().strip(),
                org=self.vcard_org.text().strip(),
                phone=self.vcard_tel.text().strip(),
                email=self.vcard_email.text().strip(),
                url=self.vcard_url.text().strip(),
            )
        elif idx == 4:
            return qr_ops.make_mecard_payload(
                name=self.mecard_name.text().strip(),
                org=self.mecard_org.text().strip(),
                phone=self.mecard_tel.text().strip(),
                email=self.mecard_email.text().strip(),
                url=self.mecard_url.text().strip(),
                address=self.mecard_address.text().strip(),
            )
        elif idx == 5:
            return qr_ops.make_email_payload(
                to=self.email_to.text().strip(),
                subject=self.email_sub.text().strip(),
                body=self.email_body.toPlainText(),
            )
        elif idx == 6:
            return qr_ops.make_phone_payload(self.phone_input.text().strip())
        elif idx == 7:
            return qr_ops.make_sms_payload(self.sms_number.text().strip(), self.sms_message.toPlainText())
        elif idx == 8:
            return qr_ops.make_whatsapp_payload(self.whatsapp_number.text().strip(), self.whatsapp_message.toPlainText())
        elif idx == 9:
            return qr_ops.make_geo_payload(
                self.geo_lat.text().strip(),
                self.geo_lon.text().strip(),
                self.geo_alt.text().strip() if self.geo_alt.text().strip() else None,
            )
        elif idx == 10:
            return qr_ops.make_calendar_payload(
                summary=self.calendar_summary.text().strip() or "Untitled event",
                start=self.calendar_start.text().strip(),
                end=self.calendar_end.text().strip(),
                location=self.calendar_location.text().strip(),
                description=self.calendar_desc.toPlainText(),
            )
        elif idx == 11:
            return qr_ops.make_asset_tag_payload(
                asset_id=self.asset_id.text().strip() or "AST-0001",
                category=self.asset_category.text().strip(),
                location=self.asset_location.text().strip(),
                owner=self.asset_owner.text().strip(),
                notes=self.asset_notes.text().strip(),
            )
        elif idx == 12:
            return self.barcode_value.text().strip() or "ABC123"
        return ""

    def _save_calendar_ics(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Calendar Event", "event.ics", "iCalendar File (*.ics)")
        if not path:
            return
        try:
            payload = data_ops.generate_ics([
                {
                    "summary": self.calendar_summary.text().strip() or "Untitled event",
                    "start": self.calendar_start.text().strip(),
                    "end": self.calendar_end.text().strip(),
                    "location": self.calendar_location.text().strip(),
                    "description": self.calendar_desc.toPlainText(),
                }
            ])
            with open(path, "w", encoding="utf-8") as f:
                f.write(payload)
            QMessageBox.information(self, "Saved", f"Calendar event saved to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))

    def _update_qr_preview(self) -> None:
        payload = self._get_payload()
        ecc = self.ecc_combo.currentData() or "M"
        box_size = self.size_spin.value()
        fg = (self.fg_color.red(), self.fg_color.green(), self.fg_color.blue())
        bg = (self.bg_color.red(), self.bg_color.green(), self.bg_color.blue())

        try:
            if self.type_combo.currentIndex() == 12:
                pil_img = qr_ops.generate_barcode(
                    payload,
                    barcode_type=self.barcode_symbology.currentData() or "code39",
                    width=2,
                    height=90,
                    include_label=self.barcode_label_toggle.isChecked(),
                    foreground=fg,
                    background=bg,
                )
            elif self.logo_path:
                scale = self.logo_scale_spin.value() / 100.0
                pil_img = qr_ops.generate_qr_with_logo(
                    payload,
                    logo=self.logo_path,
                    logo_scale=scale,
                    error_correction=ecc,
                    box_size=box_size,
                    fill_color=fg,
                    back_color=bg,
                )
            else:
                pil_img = qr_ops.generate_qr_code(
                    payload, error_correction=ecc, box_size=box_size, fill_color=fg, back_color=bg
                )
            self.current_pil_qr = pil_img
            pixmap = _pil_to_qpixmap(pil_img)
            scaled = pixmap.scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
            self.preview_label.setPixmap(scaled)
            logo_note = " (with logo)" if self.logo_path and self.type_combo.currentIndex() != 12 else ""
            self.info_label.setText(f"Export Size: {pil_img.width}x{pil_img.height} px | Payload: {len(payload)} chars{logo_note}")
        except Exception as exc:
            self.info_label.setText(f"Error: {exc}")

    def copy_to_clipboard(self) -> None:
        if self.current_pil_qr is None:
            return
        pixmap = _pil_to_qpixmap(self.current_pil_qr)
        QGuiApplication.clipboard().setPixmap(pixmap)
        QMessageBox.information(self, "Copied", "QR Code copied to clipboard!")

    def export_svg(self) -> None:
        if self.type_combo.currentIndex() == 12:
            QMessageBox.information(self, "Barcode Export", "Barcode exports are saved as image files rather than SVG; use Save Image (PNG/JPEG/WEBP/PDF).")
            return
        payload = self._get_payload()
        ecc = self.ecc_combo.currentData() or "M"
        box_size = self.size_spin.value()
        fg = self.fg_color.name()
        bg = self.bg_color.name()

        path, _ = QFileDialog.getSaveFileName(
            self, "Export SVG Vector QR Code", "qrcode.svg", "SVG Vector File (*.svg)"
        )
        if not path:
            return
        try:
            qr_ops.save_qr_svg(
                payload, path, error_correction=ecc, box_size=box_size, fill_color=fg, back_color=bg
            )
            QMessageBox.information(self, "SVG Exported", f"Vector QR code saved to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def save_qr_image(self) -> None:
        if self.current_pil_qr is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save QR Code", "qrcode.png",
            "PNG Image (*.png);;SVG Vector (*.svg);;JPEG Image (*.jpg *.jpeg);;WEBP Image (*.webp);;PDF Document (*.pdf)"
        )
        if not path:
            return
        if path.lower().endswith(".svg"):
            self.export_svg()
            return
        ext = path.split(".")[-1].upper() if "." in path else "PNG"
        try:
            qr_ops.save_qr_code(self.current_pil_qr, path, format=ext)
            QMessageBox.information(self, "Saved", f"Saved QR code to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))

    def save_label_sheet(self) -> None:
        if self.current_pil_qr is None:
            return
        preset_names = list(qr_ops.LABEL_SHEET_PRESETS.keys())
        preset_name, ok = QInputDialog.getItem(
            self, "Label Sheet Layout", "Choose a print-ready layout:", preset_names, 0, False
        )
        if not ok or not preset_name:
            return
        count, ok = QInputDialog.getInt(
            self, "Number of Labels", "How many copies of this code to print?", 1, 1, 500
        )
        if not ok:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Label Sheet", "label_sheet.pdf", "PDF Document (*.pdf)"
        )
        if not path:
            return
        try:
            qr_ops.generate_label_sheet([self.current_pil_qr] * count, preset_name, path)
            QMessageBox.information(self, "Saved", f"Label sheet saved to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
