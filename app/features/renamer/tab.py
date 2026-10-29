"""Batch Renamer workspace: live regex/numbering/case renaming with collision protection."""
from __future__ import annotations

import json
import os
from typing import Optional, Any, Dict, Tuple
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QCheckBox, QPushButton, QLabel, QFileDialog, QMessageBox,
    QInputDialog, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QSplitter
)

from app.features.renamer import ops as renamer_ops
from app.core.customizable_toolbar import AppToolBar
from app.core.spinbox import NoScrollSpinBox
from app.core.tooltips import get_tooltip_for


class RenamerTab(QWidget):
    """Batch file renamer with real-time preview and safe disk operations."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.file_paths: list[str] = []
        self.source_folders: list[str] = []
        self.current_plans: list[renamer_ops.RenamePlan] = []
        self.settings: QSettings = QSettings("FOSSEverything", "FOSSEverything")
        self.last_rename_session: list[Tuple[str, str]] = []
        self._active_plan_key: Optional[str] = None
        self._build_ui()
        self._reload_preset_options()
        self._reload_plan_options()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # Header
        title = QLabel("Batch File Renamer")
        title.setStyleSheet("font-weight: 700;")
        root.addWidget(title)
        root.addWidget(QLabel("Rename groups of files with regex, sequential numbers, prefixes, or case transforms."))

        top_row = AppToolBar(self.settings, "renamer_toolbar")
        top_row.add_action("Add Files...", self._add_files, tooltip_key="Add Files")
        top_row.add_action("Add Folder...", self._add_directory, tooltip_key="Add Folder")
        top_row.add_action("Clear List", self._clear_files, tooltip_key="Clear All")
        top_row.finalize()
        root.addWidget(top_row)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Controls Group
        rules_group = QGroupBox("Renaming Rules")
        rules_layout = QVBoxLayout(rules_group)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Action Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.setToolTip(get_tooltip_for("Action Mode"))
        self.mode_combo.addItems([
            "Find and Replace",
            "Numbering Sequence",
            "Add Prefix / Suffix",
            "Change Letter Case",
            "Change Extension",
        ])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo, stretch=1)
        rules_layout.addLayout(mode_row)

        # Form 1: Find & Replace
        self.fr_widget = QWidget()
        fr_form = QFormLayout(self.fr_widget)
        self.fr_find = QLineEdit()
        self.fr_find.setPlaceholderText("Text or regular expression to find")
        self.fr_find.textChanged.connect(self._update_preview)
        self.fr_replace = QLineEdit()
        self.fr_replace.setPlaceholderText("Replacement text (can use $1 or \1 for regex groups)")
        self.fr_replace.textChanged.connect(self._update_preview)
        self.fr_regex = QCheckBox("Use Regular Expressions (Regex)")
        self.fr_regex.setToolTip(get_tooltip_for("Use Regular Expressions (Regex)"))
        self.fr_regex.toggled.connect(self._update_preview)
        self.fr_case = QCheckBox("Case sensitive")
        self.fr_case.setToolTip(get_tooltip_for("Case sensitive"))
        self.fr_case.setChecked(True)
        self.fr_case.toggled.connect(self._update_preview)
        self.fr_ext = QCheckBox("Include extension in match")
        self.fr_ext.setToolTip(get_tooltip_for("Include extension in match"))
        self.fr_ext.toggled.connect(self._update_preview)

        fr_form.addRow("Find:", self.fr_find)
        fr_form.addRow("Replace with:", self.fr_replace)
        fr_opts = QHBoxLayout()
        fr_opts.addWidget(self.fr_regex)
        fr_opts.addWidget(self.fr_case)
        fr_opts.addWidget(self.fr_ext)
        fr_form.addRow(fr_opts)
        rules_layout.addWidget(self.fr_widget)

        # Form 2: Numbering
        self.num_widget = QWidget()
        num_form = QFormLayout(self.num_widget)
        self.num_prefix = QLineEdit("Photo_")
        self.num_prefix.textChanged.connect(self._update_preview)
        self.num_suffix = QLineEdit()
        self.num_suffix.textChanged.connect(self._update_preview)
        self.num_start = NoScrollSpinBox()
        self.num_start.setToolTip(get_tooltip_for("Start Number"))
        self.num_start.setRange(0, 1000000)
        self.num_start.setValue(1)
        self.num_start.valueChanged.connect(self._update_preview)
        self.num_pad = NoScrollSpinBox()
        self.num_pad.setToolTip(get_tooltip_for("Padding"))
        self.num_pad.setRange(1, 10)
        self.num_pad.setValue(3)
        self.num_pad.setSuffix(" digits (e.g. 001)")
        self.num_pad.valueChanged.connect(self._update_preview)
        self.num_keep = QCheckBox("Append number to original filename (instead of replacing it)")
        self.num_keep.setToolTip(get_tooltip_for("Append number to original filename (instead of replacing it)"))
        self.num_keep.toggled.connect(self._update_preview)

        num_form.addRow("Prefix:", self.num_prefix)
        num_form.addRow("Suffix:", self.num_suffix)
        num_row = QHBoxLayout()
        num_row.addWidget(QLabel("Start Number:"))
        num_row.addWidget(self.num_start)
        num_row.addWidget(QLabel("Padding:"))
        num_row.addWidget(self.num_pad)
        num_form.addRow(num_row)
        num_form.addRow(self.num_keep)
        rules_layout.addWidget(self.num_widget)
        self.num_widget.hide()

        # Form 3: Prefix / Suffix
        self.ps_widget = QWidget()
        ps_form = QFormLayout(self.ps_widget)
        self.ps_prefix = QLineEdit("v1_")
        self.ps_prefix.textChanged.connect(self._update_preview)
        self.ps_suffix = QLineEdit("_final")
        self.ps_suffix.textChanged.connect(self._update_preview)
        ps_form.addRow("Add Prefix:", self.ps_prefix)
        ps_form.addRow("Add Suffix:", self.ps_suffix)
        rules_layout.addWidget(self.ps_widget)
        self.ps_widget.hide()

        # Form 4: Case
        self.case_widget = QWidget()
        case_form = QFormLayout(self.case_widget)
        self.case_combo = QComboBox()
        self.case_combo.setToolTip(get_tooltip_for("Transform to"))
        self.case_combo.addItem("lowercase (e.g. myfile.png)", "lower")
        self.case_combo.addItem("UPPERCASE (e.g. MYFILE.PNG)", "upper")
        self.case_combo.addItem("Title Case (e.g. My File.png)", "title")
        self.case_combo.addItem("Sentence case (e.g. My file.png)", "sentence")
        self.case_combo.currentIndexChanged.connect(self._update_preview)
        self.case_ext = QCheckBox("Apply case change to file extensions too")
        self.case_ext.setToolTip(get_tooltip_for("Apply case change to file extensions too"))
        self.case_ext.toggled.connect(self._update_preview)
        case_form.addRow("Transform to:", self.case_combo)
        case_form.addRow(self.case_ext)
        rules_layout.addWidget(self.case_widget)
        self.case_widget.hide()

        # Form 5: Extension
        self.ext_widget = QWidget()
        ext_form = QFormLayout(self.ext_widget)
        self.ext_edit = QLineEdit("png")
        self.ext_edit.setPlaceholderText("e.g. jpeg, webp, bak")
        self.ext_edit.textChanged.connect(self._update_preview)
        ext_form.addRow("New Extension:", self.ext_edit)
        rules_layout.addWidget(self.ext_widget)
        self.ext_widget.hide()

        splitter.addWidget(rules_group)

        # Cross-Folder / Timeline Options
        cross_group = QGroupBox("Cross-Folder Rename Planning")
        cross_form = QFormLayout(cross_group)

        self.timeline_sort_check = QCheckBox("Order files by capture date/time across all folders (timeline mode)")
        self.timeline_sort_check.setToolTip(get_tooltip_for("Timeline Mode"))
        self.timeline_sort_check.toggled.connect(self._update_preview)
        cross_form.addRow(self.timeline_sort_check)

        consolidate_row = QHBoxLayout()
        self.consolidate_dir_edit = QLineEdit()
        self.consolidate_dir_edit.setPlaceholderText("Optional: consolidate renamed files from every source folder here")
        self.consolidate_dir_edit.textChanged.connect(self._update_preview)
        consolidate_browse = QPushButton("Browse...")
        consolidate_browse.setToolTip(get_tooltip_for("Consolidate Output Folder"))
        consolidate_browse.clicked.connect(self._browse_consolidate_dir)
        consolidate_clear = QPushButton("Clear")
        consolidate_clear.setToolTip(get_tooltip_for("Clear Output Folder"))
        consolidate_clear.clicked.connect(lambda: self.consolidate_dir_edit.setText(""))
        consolidate_row.addWidget(self.consolidate_dir_edit, stretch=1)
        consolidate_row.addWidget(consolidate_browse)
        consolidate_row.addWidget(consolidate_clear)
        cross_form.addRow("Output Folder:", consolidate_row)

        plan_row = QHBoxLayout()
        self.plan_combo = QComboBox()
        self.plan_combo.setToolTip(get_tooltip_for("Saved cross-folder plans"))
        self.plan_combo.setPlaceholderText("Saved cross-folder plans")
        self.plan_combo.setEditable(False)
        self.plan_combo.currentIndexChanged.connect(self._load_selected_plan)
        self.plan_combo.setMinimumWidth(170)
        plan_row.addWidget(self.plan_combo, stretch=1)

        self.save_plan_btn = QPushButton("Save as Cross-Folder Plan...")
        self.save_plan_btn.setToolTip(get_tooltip_for("Save as Cross-Folder Plan..."))
        self.save_plan_btn.clicked.connect(self._save_current_cross_plan)
        plan_row.addWidget(self.save_plan_btn)

        self.rerun_plan_btn = QPushButton("Re-run Plan (New Files Only)")
        self.rerun_plan_btn.setToolTip(get_tooltip_for("Re-run Plan (New Files Only)"))
        self.rerun_plan_btn.clicked.connect(self._rerun_active_plan)
        self.rerun_plan_btn.setEnabled(False)
        plan_row.addWidget(self.rerun_plan_btn)
        cross_form.addRow(plan_row)

        splitter.addWidget(cross_group)

        # Preview Table
        table_group = QGroupBox("Live Preview (Collision-Safe)")
        table_layout = QVBoxLayout(table_group)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Original Name", "New Name", "Status", "Directory"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table_layout.addWidget(self.table)

        splitter.addWidget(table_group)
        root.addWidget(splitter, stretch=1)

        # Bottom actions
        bottom_row = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.setToolTip(get_tooltip_for("Saved presets"))
        self.preset_combo.setPlaceholderText("Saved presets")
        self.preset_combo.setEditable(False)
        self.preset_combo.currentIndexChanged.connect(self._load_selected_preset)
        self.preset_combo.setMinimumWidth(170)
        bottom_row.addWidget(self.preset_combo)

        self.save_preset_btn = QPushButton("Save preset")
        self.save_preset_btn.setToolTip(get_tooltip_for("Save preset"))
        self.save_preset_btn.clicked.connect(self._save_current_preset)
        bottom_row.addWidget(self.save_preset_btn)

        self.undo_btn = QPushButton("Undo last rename")
        self.undo_btn.setToolTip(get_tooltip_for("Undo last rename"))
        self.undo_btn.clicked.connect(self._undo_last_rename)
        self.undo_btn.setEnabled(False)
        bottom_row.addWidget(self.undo_btn)

        self.status_label = QLabel("No files loaded. Click 'Add Files...' or 'Add Folder...'.")
        bottom_row.addWidget(self.status_label, stretch=1)

        self.apply_btn = QPushButton("Apply Renaming Plan")
        self.apply_btn.setToolTip(get_tooltip_for("Apply Renaming Plan"))
        self.apply_btn.setStyleSheet("font-weight: 700; padding: 8px 16px;")
        self.apply_btn.clicked.connect(self._apply_renames)
        bottom_row.addWidget(self.apply_btn)

        root.addLayout(bottom_row)

    def _on_mode_changed(self, index: int) -> None:
        self.fr_widget.setVisible(index == 0)
        self.num_widget.setVisible(index == 1)
        self.ps_widget.setVisible(index == 2)
        self.case_widget.setVisible(index == 3)
        self.ext_widget.setVisible(index == 4)
        self._update_preview()

    def _add_files(self) -> None:
        paths: list[str]
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Files to Rename", "", "All Files (*.*)")
        if paths:
            self.file_paths.extend([p for p in paths if p not in self.file_paths])
            self._update_preview()

    def _add_directory(self) -> None:
        folder: str = QFileDialog.getExistingDirectory(self, "Select Folder to Rename")
        if folder:
            paths: list[str] = []
            for root, _, files in os.walk(folder):
                for f in files:
                    paths.append(os.path.join(root, f))
            self.file_paths.extend([p for p in paths if p not in self.file_paths])
            if folder not in self.source_folders:
                self.source_folders.append(folder)
            self._update_preview()

    def _clear_files(self) -> None:
        self.file_paths.clear()
        self.source_folders.clear()
        self._active_plan_key = None
        self._update_preview()

    def _get_params(self) -> Dict[str, Any]:
        idx = self.mode_combo.currentIndex()
        if idx == 0:
            return {
                "mode": "find_replace",
                "find": self.fr_find.text(),
                "replace": self.fr_replace.text(),
                "use_regex": self.fr_regex.isChecked(),
                "case_sensitive": self.fr_case.isChecked(),
                "include_extension": self.fr_ext.isChecked(),
            }
        elif idx == 1:
            return {
                "mode": "numbering",
                "prefix": self.num_prefix.text(),
                "suffix": self.num_suffix.text(),
                "start": self.num_start.value(),
                "step": 1,
                "padding": self.num_pad.value(),
                "keep_name": self.num_keep.isChecked(),
            }
        elif idx == 2:
            return {
                "mode": "prefix_suffix",
                "prefix": self.ps_prefix.text(),
                "suffix": self.ps_suffix.text(),
            }
        elif idx == 3:
            return {
                "mode": "change_case",
                "case_type": self.case_combo.currentData(),
                "affect_ext": self.case_ext.isChecked(),
            }
        elif idx == 4:
            return {
                "mode": "extension",
                "new_extension": self.ext_edit.text(),
            }
        return {"mode": "find_replace"}

    def _reload_preset_options(self) -> None:
        current: str = self.preset_combo.currentText()
        self.preset_combo.clear()
        self.preset_combo.addItem("Choose preset...")
        for key in sorted(self.settings.allKeys()):
            if key.startswith("renamer/preset/"):
                try:
                    payload: Dict[str, Any] = json.loads(self.settings.value(key))
                    self.preset_combo.addItem(payload.get("name", key.split("/")[-1]), key)
                except Exception:
                    continue
        if current:
            index: int = self.preset_combo.findText(current)
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)

    def _save_current_preset(self) -> None:
        name: str
        ok: bool
        name, ok = QInputDialog.getText(self, "Save renaming preset", "Preset name:")
        if not ok or not name.strip():
            return
        preset: Dict[str, Any] = renamer_ops.save_preset(name.strip(), self.mode_combo.currentText(), self._get_params())
        self.settings.setValue(f"renamer/preset/{preset['name']}", json.dumps(preset))
        self._reload_preset_options()
        self.preset_combo.setCurrentText(preset["name"])

    def _load_selected_preset(self, index: int) -> None:
        if index <= 0:
            return
        key: Optional[str] = self.preset_combo.itemData(index)
        if not key:
            return
        payload: Optional[str] = self.settings.value(key)
        if not payload:
            return
        try:
            preset: Dict[str, Any] = json.loads(payload)
        except (TypeError, ValueError):
            return
        self._apply_mode_and_params(preset.get("mode", "Find and Replace"), preset.get("params", {}))

    def _apply_mode_and_params(self, mode_name: str, params: Dict[str, Any]) -> None:
        mode_map: Dict[str, int] = {
            "Find and Replace": 0,
            "Numbering Sequence": 1,
            "Add Prefix / Suffix": 2,
            "Change Letter Case": 3,
            "Change Extension": 4,
        }
        self.mode_combo.setCurrentIndex(mode_map.get(mode_name, 0))
        if params.get("mode") == "find_replace":
            self.fr_find.setText(params.get("find", ""))
            self.fr_replace.setText(params.get("replace", ""))
            self.fr_regex.setChecked(params.get("use_regex", False))
            self.fr_case.setChecked(params.get("case_sensitive", True))
            self.fr_ext.setChecked(params.get("include_extension", False))
        elif params.get("mode") == "numbering":
            self.num_prefix.setText(params.get("prefix", ""))
            self.num_suffix.setText(params.get("suffix", ""))
            self.num_start.setValue(int(params.get("start", 1)))
            self.num_pad.setValue(int(params.get("padding", 3)))
            self.num_keep.setChecked(params.get("keep_name", False))
        elif params.get("mode") == "prefix_suffix":
            self.ps_prefix.setText(params.get("prefix", ""))
            self.ps_suffix.setText(params.get("suffix", ""))
        elif params.get("mode") == "change_case":
            self.case_combo.setCurrentIndex(0)
            for i in range(self.case_combo.count()):
                if self.case_combo.itemData(i) == params.get("case_type", "lower"):
                    self.case_combo.setCurrentIndex(i)
                    break
            self.case_ext.setChecked(params.get("affect_ext", False))
        elif params.get("mode") == "extension":
            self.ext_edit.setText(params.get("new_extension", ""))
        self._update_preview()

    def _reload_plan_options(self) -> None:
        current: str = self.plan_combo.currentText()
        self.plan_combo.clear()
        self.plan_combo.addItem("Choose cross-folder plan...")
        for key in sorted(self.settings.allKeys()):
            if key.startswith("renamer/crossplan/"):
                try:
                    payload: Dict[str, Any] = json.loads(self.settings.value(key))
                    self.plan_combo.addItem(payload.get("name", key.split("/")[-1]), key)
                except Exception:
                    continue
        if current:
            index: int = self.plan_combo.findText(current)
            if index >= 0:
                self.plan_combo.setCurrentIndex(index)

    def _save_current_cross_plan(self) -> None:
        if not self.source_folders:
            QMessageBox.warning(self, "No source folders", "Add at least one folder with 'Add Folder...' before saving a cross-folder plan.")
            return
        name: str
        ok: bool
        name, ok = QInputDialog.getText(self, "Save cross-folder plan", "Plan name:")
        if not ok or not name.strip():
            return
        target_dir = self.consolidate_dir_edit.text().strip() or None
        config = renamer_ops.CrossFolderPlanConfig(
            name=name.strip(),
            source_folders=self.source_folders,
            mode=self.mode_combo.currentText(),
            params=self._get_params(),
            target_dir=target_dir,
        )
        plan: Dict[str, Any] = renamer_ops.save_cross_folder_plan(config)
        key = f"renamer/crossplan/{plan['name']}"
        self.settings.setValue(key, json.dumps(plan))
        self._reload_plan_options()
        self.plan_combo.setCurrentText(plan["name"])

    def _load_selected_plan(self, index: int) -> None:
        if index <= 0:
            self._active_plan_key = None
            self.rerun_plan_btn.setEnabled(False)
            return
        key: Optional[str] = self.plan_combo.itemData(index)
        if not key:
            return
        payload: Optional[str] = self.settings.value(key)
        if not payload:
            return
        try:
            plan: Dict[str, Any] = json.loads(payload)
        except (TypeError, ValueError):
            return
        self._active_plan_key = key
        self.rerun_plan_btn.setEnabled(True)
        if plan.get("target_dir"):
            self.consolidate_dir_edit.setText(plan["target_dir"])
        self._apply_mode_and_params(plan.get("mode", "Find and Replace"), plan.get("params", {}))

    def _rerun_active_plan(self) -> None:
        if not self._active_plan_key:
            return
        payload: Optional[str] = self.settings.value(self._active_plan_key)
        if not payload:
            return
        plan: Dict[str, Any] = json.loads(payload)
        new_files = renamer_ops.find_new_files_for_plan(plan.get("source_folders", []), plan.get("processed_files", []))
        if not new_files:
            QMessageBox.information(self, "No new files", "No new files have appeared in this plan's source folders since it last ran.")
            return
        self.file_paths = new_files
        self.source_folders = list(plan.get("source_folders", []))
        self._apply_mode_and_params(plan.get("mode", "Find and Replace"), plan.get("params", {}))

    def _undo_last_rename(self) -> None:
        if not self.last_rename_session:
            QMessageBox.information(self, "No recent rename", "There is no recent rename session to undo.")
            return
        failed: list[str] = []
        reverted = 0
        for old_path, new_path in renamer_ops.undo_renames(self.last_rename_session):
            try:
                if os.path.exists(new_path) and not os.path.exists(old_path):
                    os.rename(new_path, old_path)
                    reverted += 1
            except Exception as exc:
                failed.append(f"{new_path}: {exc}")
        if failed:
            QMessageBox.warning(
                self,
                "Rename undo incomplete",
                f"Reverted {reverted} file rename(s).\n\nCould not restore {len(failed)} file(s):\n" + "\n".join(failed),
            )
        else:
            QMessageBox.information(self, "Rename undone", f"Reverted {reverted} file rename(s).")
        self.last_rename_session.clear()
        self.undo_btn.setEnabled(False)

    def _browse_consolidate_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder for Consolidated Renames")
        if folder:
            self.consolidate_dir_edit.setText(folder)

    def _update_preview(self) -> None:
        params: Dict[str, Any] = self._get_params()
        mode: str = params.pop("mode")
        ordered_paths = self.file_paths
        if self.timeline_sort_check.isChecked():
            ordered_paths = renamer_ops.sort_files_by_timeline(self.file_paths)
        self.current_plans = renamer_ops.preview_renames(ordered_paths, mode, params)

        target_dir = self.consolidate_dir_edit.text().strip()
        if target_dir:
            self.current_plans = renamer_ops.plan_consolidate_to_folder(self.current_plans, target_dir)

        self.table.setRowCount(len(self.current_plans))
        changed_count: int = 0
        error_count: int = 0

        for row, plan in enumerate(self.current_plans):
            item_old: QTableWidgetItem = QTableWidgetItem(plan.old_name)
            item_new: QTableWidgetItem = QTableWidgetItem(plan.new_name)

            if plan.error:
                item_status: QTableWidgetItem = QTableWidgetItem(f"[ERROR] {plan.error}")
                item_status.setForeground(Qt.GlobalColor.red)
                error_count += 1
            elif plan.old_name != plan.new_name:
                item_status = QTableWidgetItem("[OK] Will Rename")
                item_status.setForeground(Qt.GlobalColor.green)
                changed_count += 1
            else:
                item_status = QTableWidgetItem("- Unchanged")
                item_status.setForeground(Qt.GlobalColor.gray)

            item_dir: QTableWidgetItem = QTableWidgetItem(os.path.dirname(plan.old_path))
            item_dir.setForeground(Qt.GlobalColor.gray)

            self.table.setItem(row, 0, item_old)
            self.table.setItem(row, 1, item_new)
            self.table.setItem(row, 2, item_status)
            self.table.setItem(row, 3, item_dir)

        total = len(self.current_plans)
        self.status_label.setText(
            f"Total Files: {total} | Changes: {changed_count} | Issues: {error_count}"
        )
        self.apply_btn.setEnabled(changed_count > 0 and error_count == 0)

    def _apply_renames(self) -> None:
        if not self.current_plans:
            return
        ans: int = QMessageBox.question(
            self,
            "Confirm Batch Rename",
            f"Are you sure you want to rename {len([p for p in self.current_plans if p.old_name != p.new_name])} file(s)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        results: list = renamer_ops.execute_renames(self.current_plans)
        successes: int = sum(1 for r in results if r.success)
        failures: int = sum(1 for r in results if not r.success)

        self.last_rename_session = [(r.old_path, r.new_path) for r in results if r.success]
        self.undo_btn.setEnabled(bool(self.last_rename_session))

        if self._active_plan_key:
            payload: Optional[str] = self.settings.value(self._active_plan_key)
            if payload:
                plan: Dict[str, Any] = json.loads(payload)
                processed = set(plan.get("processed_files", []))
                processed.update(r.old_path for r in results if r.success)
                plan["processed_files"] = sorted(processed)
                self.settings.setValue(self._active_plan_key, json.dumps(plan))

        # Update file_paths to newly renamed paths
        new_paths: list[str] = [r.new_path for r in results if r.success]
        self.file_paths = new_paths
        self._update_preview()

        if failures == 0:
            QMessageBox.information(self, "Complete", f"Successfully renamed {successes} file(s).")
        else:
            QMessageBox.warning(self, "Completed with Errors", f"Renamed {successes} file(s), {failures} failed.")
