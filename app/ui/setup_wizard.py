"""First-run (and on-demand) setup wizard: theme, file associations, optional models."""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QLabel, QListWidget, QProgressBar,
    QPushButton, QVBoxLayout, QWidget, QWizard, QWizardPage,
)

from app.core import theme
from app.features.image import ops as image_ops
from app.features.ocr import ops as ocr_ops
from app.system import shell_integration
from app.core.tooltips import get_tooltip_for
from app.system.workers import WorkerThread
from app.ui.file_association_settings import FileAssociationSettings


def _selectable_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


class _WelcomePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Welcome to FOSSEverything")
        layout = QVBoxLayout(self)
        layout.addWidget(_selectable_label(
            "This short setup wizard configures FOSSEverything for your machine: pick a "
            "theme, register file associations, and optionally pre-download background-"
            "removal models so they are ready before you need them. Re-run it anytime from "
            "Settings > Run Setup Wizard."
        ))


class _ThemePage(QWizardPage):
    def __init__(self, settings: QSettings) -> None:
        super().__init__()
        self.settings = settings
        self.setTitle("Choose a theme")
        layout = QVBoxLayout(self)
        layout.addWidget(_selectable_label("Pick a color theme (changeable later in Settings):"))

        self.combo = QComboBox()
        self.combo.setToolTip(get_tooltip_for("Theme"))
        self.combo.addItems([theme.THEME_PRESET_LABELS[name] for name in theme.THEME_PRESET_ORDER])
        current = theme.current_theme_name(settings)
        self.combo.setCurrentIndex(theme.THEME_PRESET_ORDER.index(current))
        self.combo.currentIndexChanged.connect(self._apply)
        layout.addWidget(self.combo)
        layout.addStretch()

    def _apply(self, index: int) -> None:
        self.settings.setValue("app/theme", theme.THEME_PRESET_ORDER[index])
        theme.notify_theme_changed()


class _FileAssociationsPage(QWizardPage):
    def __init__(self, settings: QSettings, main_window: Any) -> None:
        super().__init__()
        self.setTitle("File associations")
        layout = QVBoxLayout(self)

        self.context_menu_check = QCheckBox("Add 'Open in FOSSEverything' to the right-click menu")
        self.context_menu_check.setToolTip(get_tooltip_for("Add 'Open in FOSSEverything' to the right-click menu"))
        self.context_menu_check.setChecked(True)
        layout.addWidget(self.context_menu_check)
        layout.addWidget(FileAssociationSettings(settings, main_window))

    def validatePage(self) -> bool:  # noqa: 21 (Qt virtual override, invoked by the framework)
        if self.context_menu_check.isChecked():
            shell_integration.register_shell_context_menu()
        else:
            shell_integration.unregister_shell_context_menu()
        return True


class _ModelsPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Pre-download optional models")
        layout = QVBoxLayout(self)
        layout.addWidget(_selectable_label(
            "Background-removal models otherwise download on first use, which can pause "
            "the app for a while. Check any you want ready in advance:"
        ))

        self.checks: dict[str, QCheckBox] = {}
        for model_id, (label, description) in image_ops.BACKGROUND_REMOVAL_MODELS.items():
            check = QCheckBox(f"{label} ({model_id})")
            check.setToolTip(description)
            layout.addWidget(check)
            self.checks[model_id] = check

        self.download_btn = QPushButton("Download selected")
        self.download_btn.setToolTip(get_tooltip_for("Download selected models"))
        self.download_btn.clicked.connect(self._download_selected)
        layout.addWidget(self.download_btn)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = _selectable_label("")
        layout.addWidget(self.status_label)

        layout.addWidget(_selectable_label("Detected Tesseract OCR languages:"))
        lang_list = QListWidget()
        lang_list.setMaximumHeight(120)
        detected = set(ocr_ops.discover_tesseract_languages())
        for code, name in sorted(ocr_ops.SUPPORTED_LANGUAGES.items(), key=lambda item: item[1]):
            mark = "available" if code in detected else "not detected"
            lang_list.addItem(f"{name} ({code}) - {mark}")
        layout.addWidget(lang_list)

        self._worker: WorkerThread | None = None

    def _download_selected(self) -> None:
        selected = [model_id for model_id, check in self.checks.items() if check.isChecked()]
        if not selected:
            self.status_label.setText("No models selected.")
            return
        self.download_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, len(selected))
        self._worker = WorkerThread(image_ops.prefetch_background_removal_models, selected)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_download_done)
        self._worker.failed.connect(self._on_download_failed)
        self._worker.start()

    def _on_progress(self, current: int, _total: int, model_name: str) -> None:
        self.progress.setValue(current)
        self.status_label.setText(f"Downloading {model_name}...")

    def _on_download_done(self, fetched: object) -> None:
        self.download_btn.setEnabled(True)
        self.status_label.setText(f"Downloaded: {', '.join(fetched)}")

    def _on_download_failed(self, message: str) -> None:
        self.download_btn.setEnabled(True)
        self.status_label.setText(f"Download failed: {message}")


class _FinishPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("All set")
        layout = QVBoxLayout(self)
        layout.addWidget(_selectable_label(
            "FOSSEverything is configured. Re-run this wizard anytime from Settings > "
            "Run Setup Wizard."
        ))


class SetupWizard(QWizard):
    """First-run (and on-demand) setup wizard for theme, file associations, and models."""

    def __init__(self, settings: QSettings, main_window: Any = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("FOSSEverything Setup")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(640, 560)
        self.addPage(_WelcomePage())
        self.addPage(_ThemePage(settings))
        self.addPage(_FileAssociationsPage(settings, main_window))
        self.addPage(_ModelsPage())
        self.addPage(_FinishPage())
