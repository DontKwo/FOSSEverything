"""Interactive screenshot dialog and region snipping overlay."""
from __future__ import annotations

import time
from typing import Optional
from PyQt6.QtCore import Qt, QPoint, QRect, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QGuiApplication, QMouseEvent, QPaintEvent, QKeyEvent
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QRadioButton, QButtonGroup, QWidget, QFrame, QMessageBox
)
from PIL import Image
from app.features.screenshot import ops as screenshot_ops
from app.core.spinbox import NoScrollSpinBox
from app.core.tooltips import get_tooltip_for


class SnippingOverlay(QWidget):
    """Fullscreen semi-transparent overlay to select a screen region."""

    snippet_captured = pyqtSignal(object)  # PIL.Image

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._start_pos: QPoint | None = None
        self._curr_pos: QPoint | None = None
        self._is_selecting = False

        # Grab full screen before showing
        screen = QGuiApplication.primaryScreen()
        self._bg_pixmap = screen.grabWindow(0) if screen else None
        if screen:
            self.setGeometry(screen.geometry())

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: 21 (Qt virtual override, invoked by the framework)
        painter = QPainter(self)
        if self._bg_pixmap:
            painter.drawPixmap(0, 0, self._bg_pixmap)

        overlay = self.palette().color(self.palette().ColorRole.Window)
        overlay.setAlpha(100)
        painter.fillRect(self.rect(), overlay)

        if self._start_pos and self._curr_pos:
            rect = QRect(self._start_pos, self._curr_pos).normalized()
            if self._bg_pixmap:
                painter.drawPixmap(rect, self._bg_pixmap, rect)
            accent = self.palette().color(self.palette().ColorRole.Highlight)
            pen = QPen(accent, 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

            dim_text = f"{rect.width()} × {rect.height()}"
            tooltip_fill = self.palette().color(self.palette().ColorRole.WindowText)
            tooltip_fill.setAlpha(180)
            painter.fillRect(rect.x(), max(0, rect.y() - 22), 100, 20, tooltip_fill)
            painter.setPen(self.palette().color(self.palette().ColorRole.Base))
            painter.drawText(rect.x() + 6, max(14, rect.y() - 8), dim_text)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.pos()
            self._curr_pos = event.pos()
            self._is_selecting = True
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_selecting:
            self._curr_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            if self._start_pos and self._curr_pos:
                rect = QRect(self._start_pos, self._curr_pos).normalized()
                self.hide()
                if rect.width() > 4 and rect.height() > 4:
                    try:
                        img = screenshot_ops.capture_screen_region(
                            rect.x(), rect.y(), rect.width(), rect.height()
                        )
                        self.snippet_captured.emit(img)
                    except Exception:
                        self.snippet_captured.emit(None)
                else:
                    self.snippet_captured.emit(None)
                self.deleteLater()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.snippet_captured.emit(None)
            self.deleteLater()


class ScreenshotDialog(QDialog):
    """Configure and trigger screen capture."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Take Screenshot")
        self.resize(360, 240)
        self.captured_image: Image.Image | None = None
        self._overlay: Optional[SnippingOverlay] = None
        self._countdown_remaining = 0
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._tick_countdown)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Capture desktop screen or select a custom area."))

        self.full_radio = QRadioButton("Full Screen")
        self.full_radio.setToolTip(get_tooltip_for("Full Screen"))
        self.full_radio.setChecked(True)
        self.region_radio = QRadioButton("Select Region / Snip (interactive)")
        self.region_radio.setToolTip(get_tooltip_for("Select Region / Snip"))
        layout.addWidget(self.full_radio)
        layout.addWidget(self.region_radio)

        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("Delay countdown:"))
        self.delay_spin = NoScrollSpinBox()
        self.delay_spin.setToolTip(get_tooltip_for("Delay countdown"))
        self.delay_spin.setRange(0, 10)
        self.delay_spin.setValue(0)
        self.delay_spin.setSuffix(" seconds")
        delay_row.addWidget(self.delay_spin)
        delay_row.addStretch()
        layout.addLayout(delay_row)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {self.palette().color(self.palette().ColorRole.Highlight).name()}; font-weight: 700;")
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.snap_btn = QPushButton("Capture")
        self.snap_btn.setToolTip(get_tooltip_for("Capture"))
        self.snap_btn.setStyleSheet("font-weight: 700; padding: 6px 14px;")
        self.snap_btn.clicked.connect(self._start_capture)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setToolTip(get_tooltip_for("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.snap_btn)
        layout.addLayout(btn_row)

    def _start_capture(self) -> None:
        delay = self.delay_spin.value()
        self.snap_btn.setEnabled(False)
        if delay > 0:
            self._countdown_remaining = delay
            self.status_label.setText(f"Capturing in {self._countdown_remaining}s...")
            self._countdown_timer.start(1000)
        else:
            self.hide()
            QTimer.singleShot(100, self._do_capture)

    def _tick_countdown(self) -> None:
        self._countdown_remaining -= 1
        if self._countdown_remaining > 0:
            self.status_label.setText(f"Capturing in {self._countdown_remaining}s...")
            return
        self._countdown_timer.stop()
        self.status_label.setText("Capturing...")
        self.hide()
        QTimer.singleShot(150, self._do_capture)

    def _do_capture(self) -> None:
        if self.region_radio.isChecked():
            self._overlay = SnippingOverlay()
            self._overlay.snippet_captured.connect(self._on_snippet_captured)
            self._overlay.showFullScreen()
        else:
            try:
                self.captured_image = screenshot_ops.capture_full_screen()
                self.accept()
            except Exception as exc:
                QMessageBox.critical(self, "Screenshot Failed", f"Could not capture the screen:\n{exc}")
                self.reject()

    def _on_snippet_captured(self, img: Image.Image | None) -> None:
        if img is not None:
            self.captured_image = img
            self.accept()
        else:
            self.reject()
