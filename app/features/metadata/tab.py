"""Metadata Tools workspace for local inspection, edits, and stripping."""
import os
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QProgressDialog, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.core.customizable_toolbar import AppToolBar
from app.features.metadata import ops as metadata_ops
from app.core.tooltips import get_tooltip_for
from app.system.workers import WorkerThread


class BatchCleanupDialog(QDialog):
    """Pick an input folder, output folder, and recursion for a batch metadata wipe."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Batch Remove Metadata")
        self.resize(420, 200)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Strips metadata from every supported file in a folder. Outputs are written to a separate folder; originals are untouched."))

        form = QFormLayout()
        input_row = QHBoxLayout()
        self.input_edit = QLineEdit()
        input_browse = QPushButton("Browse...")
        input_browse.setToolTip(get_tooltip_for("Browse for input folder"))
        input_browse.clicked.connect(self._browse_input)
        input_row.addWidget(self.input_edit)
        input_row.addWidget(input_browse)
        form.addRow("Input folder:", input_row)

        output_row = QHBoxLayout()
        self.output_edit = QLineEdit()
        output_browse = QPushButton("Browse...")
        output_browse.setToolTip(get_tooltip_for("Browse for output folder"))
        output_browse.clicked.connect(self._browse_output)
        output_row.addWidget(self.output_edit)
        output_row.addWidget(output_browse)
        form.addRow("Output folder:", output_row)
        layout.addLayout(form)

        self.recursive_check = QCheckBox("Include subfolders")
        self.recursive_check.setChecked(True)
        self.recursive_check.setToolTip(get_tooltip_for("Include subfolders"))
        layout.addWidget(self.recursive_check)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_input(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose input folder")
        if path:
            self.input_edit.setText(path)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if path:
            self.output_edit.setText(path)

    def get_options(self) -> dict[str, object]:
        return {
            "input_dir": self.input_edit.text().strip(),
            "output_dir": self.output_edit.text().strip(),
            "recursive": self.recursive_check.isChecked(),
        }


class MetadataTab(QWidget):
    """Expose metadata before modifying it; outputs never overwrite inputs."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.input_path: Optional[str] = None
        layout = QVBoxLayout(self)
        heading = QLabel("Metadata Tools")
        heading.setStyleSheet("font-weight: 700;")
        layout.addWidget(heading)
        notice = QLabel(
            "Inspect a file before sharing it. Edit supported fields or write a clean copy. "
            "Outputs never overwrite the original."
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)

        file_row = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        choose_button = QPushButton("Choose file...")
        choose_button.setToolTip(get_tooltip_for("Choose file"))
        choose_button.clicked.connect(self.choose_file)
        file_row.addWidget(self.file_label, stretch=1)
        file_row.addWidget(choose_button)
        layout.addLayout(file_row)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Metadata field", "Value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
        layout.addWidget(self.table, stretch=1)

        self.status = QLabel("PDF, image, audio, and video files are supported locally.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        actions = AppToolBar(None, "metadata_actions_toolbar")
        actions.add_action("Save edited metadata as...", self.save_edits, tooltip_key="Save edited metadata as")
        actions.add_action("Remove metadata and save as...", self.strip_metadata, tooltip_key="Remove metadata and save as")
        actions.add_action("Batch remove metadata...", self.batch_cleanup, tooltip_key="Batch remove metadata")
        actions.finalize()
        layout.addWidget(actions)

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a file", "",
            "Supported files (*.pdf *.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.gif *.docx *.pptx *.xlsx *.odt *.ods *.odp *.mp3 *.wav *.flac *.aac *.m4a *.ogg *.wma *.mp4 *.mov *.mkv *.avi *.webm);;Office Documents (*.docx *.pptx *.xlsx *.odt *.ods *.odp);;Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff);;PDFs (*.pdf);;Audio & Video (*.mp3 *.wav *.flac *.mp4 *.mov *.mkv);;All Files (*.*)"
        )
        if path:
            self.load_file(path)

    def load_file(self, path: str) -> None:
        try:
            metadata = metadata_ops.inspect_metadata(path)
        except Exception as exc:  # surface file-specific parser errors in the UI
            QMessageBox.critical(self, "Could not read metadata", str(exc))
            return
        self.input_path = path
        self.file_label.setText(os.path.basename(path))
        self.file_label.setToolTip(path)
        editable = metadata_ops.editable_keys(path)
        self.table.setRowCount(0)
        for key, value in metadata.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            key_item = QTableWidgetItem(key)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            value_item = QTableWidgetItem(value)
            if key not in editable:
                value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, value_item)
        self.status.setText(
            "Double-click supported values to edit them. Removing metadata strips standard image/PDF metadata; "
            "it does not remove PDF attachments, annotations, or document content."
        )

    def _output_path(self, title: str, suffix: str) -> Optional[str]:
        base, extension = os.path.splitext(self.input_path)
        default_path = f"{base}_{suffix}{extension}"
        path, _ = QFileDialog.getSaveFileName(self, title, default_path)
        if path and not os.path.splitext(path)[1]:
            return f"{path}{extension}"
        return path

    def _require_file(self) -> bool:
        if self.input_path is None:
            QMessageBox.warning(self, "No file", "Choose a file first.")
            return False
        return True

    def _edits(self) -> dict[str, str]:
        editable = metadata_ops.editable_keys(self.input_path)
        return {
            self.table.item(row, 0).text(): self.table.item(row, 1).text()
            for row in range(self.table.rowCount())
            if self.table.item(row, 0).text() in editable
        }

    def save_edits(self) -> None:
        if not self._require_file():
            return
        output_path = self._output_path("Save edited metadata as", "metadata")
        if not output_path:
            return
        try:
            metadata_ops.save_edited_metadata(self.input_path, output_path, self._edits())
            QMessageBox.information(self, "Saved", f"Saved to {output_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Could not save metadata", str(exc))

    def strip_metadata(self) -> None:
        if not self._require_file():
            return
        output_path = self._output_path("Save clean copy as", "clean")
        if not output_path:
            return
        try:
            metadata_ops.strip_metadata(self.input_path, output_path)
            QMessageBox.information(self, "Clean copy saved", f"Saved to {output_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Could not remove metadata", str(exc))

    def batch_cleanup(self) -> None:
        dialog = BatchCleanupDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        options = dialog.get_options()
        if not options["input_dir"] or not options["output_dir"]:
            QMessageBox.warning(self, "Missing folder", "Choose both an input and output folder.")
            return

        self._batch_progress = QProgressDialog("Cleaning metadata...", None, 0, 0, self)
        self._batch_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._batch_progress.setMinimumDuration(0)
        self._batch_progress.setCancelButton(None)
        self._batch_progress.show()

        self._batch_worker = WorkerThread(
            metadata_ops.batch_metadata_cleanup,
            options["input_dir"],
            options["output_dir"],
            recursive=options["recursive"],
        )
        self._batch_worker.progress.connect(self._update_batch_progress)
        self._batch_worker.finished_ok.connect(self._on_batch_cleanup_done)
        self._batch_worker.failed.connect(self._on_batch_cleanup_failed)
        self._batch_worker.start()

    def _update_batch_progress(self, index: int, total: int, filename: str) -> None:
        self._batch_progress.setMaximum(total)
        self._batch_progress.setValue(index)

    def _on_batch_cleanup_done(self, results: dict) -> None:
        self._batch_progress.close()
        QMessageBox.information(
            self, "Batch cleanup complete",
            f"Processed: {results['processed']}  Skipped: {results['skipped']}  Errors: {results['errors']}",
        )

    def _on_batch_cleanup_failed(self, message: str) -> None:
        self._batch_progress.close()
        QMessageBox.critical(self, "Batch cleanup failed", message)
