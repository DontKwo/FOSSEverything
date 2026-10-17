"""3D Model Studio tab: load STL/OBJ/PLY/STEP/IGES, cut with a plane, repair, scale, measure, and export."""
from __future__ import annotations

import os
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QProgressDialog, QPushButton, QScrollArea, QSizePolicy, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from app.core.customizable_toolbar import AppToolBar
from app.core.spinbox import NoScrollDoubleSpinBox
from app.core.tooltips import get_tooltip_for
from app.features.model3d import ops as model3d_ops
from app.features.model3d.viewport import Model3DViewport
from app.system.workers import WorkerThread

_OPEN_FILTER = (
    "All Supported (*.stl *.obj *.ply *.step *.stp *.iges *.igs);;"
    "Mesh (*.stl *.obj *.ply);;CAD (*.step *.stp *.iges *.igs)"
)
_SAVE_FILTER = "STL (*.stl);;OBJ (*.obj);;PLY (*.ply);;STEP (*.step);;IGES (*.iges)"


class Model3DTab(QWidget):
    """Workspace for cutting, repairing, scaling, measuring, and converting 3D models locally."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_model: model3d_ops.Model3D | None = None
        self.pieces: list[model3d_ops.Model3D] = []
        self.planes: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
        self._pick_target: str | None = None
        self._measure_points: dict[str, tuple[float, float, float]] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        toolbar = AppToolBar(None, "model3d_toolbar")
        toolbar.add_action("Open...", self._browse_file)
        toolbar.add_action("Repair Mesh", self._repair_mesh)
        toolbar.add_action("Export...", self._export_current)
        toolbar.finalize()
        layout.addWidget(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.viewport = Model3DViewport()
        self.viewport.on_click = self._on_viewport_click
        self.viewport.setMinimumWidth(400)
        splitter.addWidget(self.viewport)

        self.side_tabs = QTabWidget()
        self.side_tabs.addTab(self._scrollable(self._build_cut_panel()), "Cut Plane")
        self.side_tabs.addTab(self._scrollable(self._build_inspector_panel()), "Inspector")
        self.side_tabs.addTab(self._scrollable(self._build_scale_panel()), "Scale")
        self.side_tabs.addTab(self._scrollable(self._build_measure_panel()), "Measure")
        self.side_tabs.setMinimumWidth(340)
        self.side_tabs.currentChanged.connect(lambda _index: self._update_plane_gizmo())
        splitter.addWidget(self.side_tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        self.status_label = QLabel("Open an STL, OBJ, PLY, STEP, or IGES model to begin.")
        self.status_label.setWordWrap(True)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.status_label)

    # ─── Panels ──────────────────────────────────────────────────────────
    def _scrollable(self, widget: QWidget) -> QScrollArea:
        """Wrap a side panel in a scroll area so a tall panel (many group boxes,
        the pieces list) is never squeezed below its widgets' natural size."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        return scroll

    def _build_cut_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        origin_group = QGroupBox("Plane origin")
        origin_form = QFormLayout(origin_group)
        self.origin_x = self._make_spin("Plane Origin X")
        self.origin_y = self._make_spin("Plane Origin Y")
        self.origin_z = self._make_spin("Plane Origin Z")
        origin_form.addRow("X:", self.origin_x)
        origin_form.addRow("Y:", self.origin_y)
        origin_form.addRow("Z:", self.origin_z)
        layout.addWidget(origin_group)

        normal_group = QGroupBox("Plane normal")
        normal_form = QFormLayout(normal_group)
        self.normal_x = self._make_spin("Plane Normal X")
        self.normal_y = self._make_spin("Plane Normal Y")
        self.normal_z = self._make_spin("Plane Normal Z")
        self.normal_x.setValue(1.0)
        normal_form.addRow("X:", self.normal_x)
        normal_form.addRow("Y:", self.normal_y)
        normal_form.addRow("Z:", self.normal_z)
        layout.addWidget(normal_group)
        for spin in (self.origin_x, self.origin_y, self.origin_z, self.normal_x, self.normal_y, self.normal_z):
            spin.valueChanged.connect(self._update_plane_gizmo)

        drag_hint = QLabel(
            "Drag an arrow in the viewport to move the plane, or drag a curved handle to "
            "rotate it (like a reference plane in SolidWorks). Numbers below stay in sync."
        )
        drag_hint.setWordWrap(True)
        layout.addWidget(drag_hint)

        helper_row = QHBoxLayout()
        use_view_btn = QPushButton("Use Current View Direction")
        use_view_btn.setToolTip(get_tooltip_for("Use Current View Direction"))
        use_view_btn.clicked.connect(self._use_view_direction)
        pick_btn = QPushButton("Pick Point on Model")
        pick_btn.setToolTip(get_tooltip_for("Pick Point on Model"))
        pick_btn.clicked.connect(lambda: self._start_pick("cut_origin"))
        helper_row.addWidget(use_view_btn)
        helper_row.addWidget(pick_btn)
        layout.addLayout(helper_row)

        planes_group = QGroupBox("Cutting planes (add more than one to split into multiple pieces)")
        planes_layout = QVBoxLayout(planes_group)
        self.planes_list = QListWidget()
        self.planes_list.setMaximumHeight(90)
        planes_layout.addWidget(self.planes_list)
        planes_btn_row = QHBoxLayout()
        add_plane_btn = QPushButton("Add Plane")
        add_plane_btn.setToolTip(get_tooltip_for("Add Plane"))
        add_plane_btn.clicked.connect(self._add_plane)
        remove_plane_btn = QPushButton("Remove Selected Plane")
        remove_plane_btn.setToolTip(get_tooltip_for("Remove Selected Plane"))
        remove_plane_btn.clicked.connect(self._remove_plane)
        planes_btn_row.addWidget(add_plane_btn)
        planes_btn_row.addWidget(remove_plane_btn)
        planes_layout.addLayout(planes_btn_row)
        layout.addWidget(planes_group)

        self.cap_checkbox = QCheckBox("Fill cut cross-section (solid)")
        self.cap_checkbox.setToolTip(get_tooltip_for("Fill cut cross-section (solid)"))
        self.cap_checkbox.setChecked(True)
        layout.addWidget(self.cap_checkbox)
        self.brep_cap_note = QLabel("STEP/IGES cuts are always solid; this option only applies to STL/OBJ/PLY.")
        self.brep_cap_note.setWordWrap(True)
        self.brep_cap_note.setVisible(False)
        layout.addWidget(self.brep_cap_note)

        cut_btn = QPushButton("Cut Model")
        cut_btn.setToolTip(get_tooltip_for("Cut Model"))
        cut_btn.setStyleSheet("padding: 8px; font-weight: 600;")
        cut_btn.clicked.connect(self._apply_cut)
        layout.addWidget(cut_btn)

        layout.addWidget(QLabel("Cut pieces (select one to highlight it in the viewport):"))
        self.pieces_list = QListWidget()
        self.pieces_list.setMaximumHeight(90)
        self.pieces_list.currentRowChanged.connect(self._on_piece_selected)
        layout.addWidget(self.pieces_list)

        piece_btn_row = QHBoxLayout()
        export_piece_btn = QPushButton("Export Selected Piece...")
        export_piece_btn.setToolTip(get_tooltip_for("Export Selected Piece..."))
        export_piece_btn.clicked.connect(self._export_selected_piece)
        export_all_btn = QPushButton("Export All Pieces...")
        export_all_btn.setToolTip(get_tooltip_for("Export All Pieces..."))
        export_all_btn.clicked.connect(self._export_all_pieces)
        use_piece_btn = QPushButton("Cut This Piece Again")
        use_piece_btn.setToolTip(get_tooltip_for("Cut This Piece Again"))
        use_piece_btn.clicked.connect(self._recut_selected_piece)
        piece_btn_row.addWidget(export_piece_btn)
        piece_btn_row.addWidget(export_all_btn)
        piece_btn_row.addWidget(use_piece_btn)
        layout.addLayout(piece_btn_row)

        layout.addStretch()
        return panel

    def _build_inspector_panel(self) -> QWidget:
        panel = QWidget()
        layout = QFormLayout(panel)
        self.info_labels: dict[str, QLabel] = {}
        for key, title in (
            ("backend", "Format"),
            ("watertight", "Watertight"),
            ("volume", "Volume"),
            ("surface_area", "Surface area"),
            ("bbox_min", "Bounding box min"),
            ("bbox_max", "Bounding box max"),
            ("triangle_count", "Triangle count"),
            ("vertex_count", "Vertex count"),
        ):
            label = QLabel("-")
            self.info_labels[key] = label
            layout.addRow(f"{title}:", label)
        return panel

    def _build_scale_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        preset_row = QHBoxLayout()
        mm_to_in_btn = QPushButton("mm -> inch")
        mm_to_in_btn.setToolTip(get_tooltip_for("mm -> inch"))
        mm_to_in_btn.clicked.connect(lambda: self._apply_scale_factor(1.0 / 25.4))
        in_to_mm_btn = QPushButton("inch -> mm")
        in_to_mm_btn.setToolTip(get_tooltip_for("inch -> mm"))
        in_to_mm_btn.clicked.connect(lambda: self._apply_scale_factor(25.4))
        preset_row.addWidget(mm_to_in_btn)
        preset_row.addWidget(in_to_mm_btn)
        layout.addLayout(preset_row)

        form = QFormLayout()
        self.scale_factor_spin = self._make_spin("Uniform Scale Factor")
        self.scale_factor_spin.setValue(1.0)
        self.scale_factor_spin.setRange(0.0001, 10000.0)
        form.addRow("Uniform scale factor:", self.scale_factor_spin)
        layout.addLayout(form)

        apply_btn = QPushButton("Apply Scale")
        apply_btn.setToolTip(get_tooltip_for("Apply Scale"))
        apply_btn.clicked.connect(lambda: self._apply_scale_factor(self.scale_factor_spin.value()))
        layout.addWidget(apply_btn)
        layout.addStretch()
        return panel

    def _build_measure_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        pick_a_btn = QPushButton("Pick Point A on Model")
        pick_a_btn.setToolTip(get_tooltip_for("Pick Point A on Model"))
        pick_a_btn.clicked.connect(lambda: self._start_pick("measure_a"))
        pick_b_btn = QPushButton("Pick Point B on Model")
        pick_b_btn.setToolTip(get_tooltip_for("Pick Point B on Model"))
        pick_b_btn.clicked.connect(lambda: self._start_pick("measure_b"))
        layout.addWidget(pick_a_btn)
        layout.addWidget(pick_b_btn)
        self.measure_result_label = QLabel("Pick two points on the model to measure the distance between them.")
        self.measure_result_label.setWordWrap(True)
        layout.addWidget(self.measure_result_label)
        layout.addStretch()
        return panel

    def _make_spin(self, tooltip: str) -> NoScrollDoubleSpinBox:
        spin = NoScrollDoubleSpinBox()
        spin.setToolTip(get_tooltip_for(tooltip))
        spin.setRange(-1_000_000.0, 1_000_000.0)
        spin.setSingleStep(1.0)
        spin.setMinimumWidth(90)
        # Per-keystroke valueChanged rebuilt the plane actor and garbled the spinbox repaint.
        spin.setKeyboardTracking(False)
        return spin

    # ─── File I/O ────────────────────────────────────────────────────────
    def load_file(self, file_path: str) -> None:
        self._progress_dialog = QProgressDialog("Loading model...", None, 0, 0, self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._worker = WorkerThread(model3d_ops.load, file_path)
        self._worker.finished_ok.connect(lambda model: self._on_load_done(model, file_path))
        self._worker.failed.connect(self._on_load_failed)
        self._worker.start()

    def _on_load_done(self, model: model3d_ops.Model3D, file_path: str) -> None:
        self._progress_dialog.close()
        self._set_current_model(model, file_path)

    def _on_load_failed(self, message: str) -> None:
        self._progress_dialog.close()
        if message == model3d_ops.CAD_INSTALL_HINT:
            QMessageBox.warning(self, "CAD Backend Unavailable", message)
        else:
            QMessageBox.critical(self, "Load Failed", f"Could not load 3D model: {message}")

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open 3D Model", "", _OPEN_FILTER)
        if path:
            self.load_file(path)

    def _set_current_model(self, model: model3d_ops.Model3D, source_path: str | None) -> None:
        self.current_model = model
        self.pieces = []
        self.planes = []
        self.planes_list.clear()
        self.pieces_list.clear()
        verts, faces = model3d_ops.tessellated_preview(model)
        self.viewport.set_models([(verts, faces)])
        if len(verts):
            center = (verts.min(axis=0) + verts.max(axis=0)) / 2.0
        else:
            center = (0.0, 0.0, 0.0)
        self.origin_x.setValue(float(center[0]))
        self.origin_y.setValue(float(center[1]))
        self.origin_z.setValue(float(center[2]))
        self._update_plane_gizmo()
        self._refresh_inspector(model)
        self.brep_cap_note.setVisible(model.backend == "brep")
        self.cap_checkbox.setEnabled(model.backend == "mesh")

        name = os.path.basename(source_path) if source_path else "cut piece"
        message = f"Loaded {name} ({model.source_format})."
        if model.warnings:
            message += " " + " ".join(model.warnings)
        self.status_label.setText(message)

    def _refresh_inspector(self, model: model3d_ops.Model3D) -> None:
        data = model3d_ops.info(model)
        for key, label in self.info_labels.items():
            value = data.get(key)
            if value is None:
                label.setText("-")
            elif isinstance(value, float):
                label.setText(f"{value:.3f}")
            elif isinstance(value, list):
                label.setText(", ".join(f"{v:.3f}" for v in value))
            else:
                label.setText(str(value))

    # ─── Cut plane ───────────────────────────────────────────────────────
    def _current_plane(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        origin = (self.origin_x.value(), self.origin_y.value(), self.origin_z.value())
        normal = (self.normal_x.value(), self.normal_y.value(), self.normal_z.value())
        return origin, normal

    def _update_plane_gizmo(self) -> None:
        if self.current_model is None:
            self.viewport.set_cut_planes([])
            self.viewport.disable_plane_widget()
            return
        origin, normal = self._current_plane()
        show_widget = self.side_tabs.currentIndex() == 0
        if show_widget:
            self.viewport.set_cut_planes(self.planes)
            self.viewport.enable_plane_widget(origin, normal, self._on_plane_widget_changed)
        else:
            self.viewport.set_cut_planes(self.planes + [(origin, normal)])
            self.viewport.disable_plane_widget()

    def _on_plane_widget_changed(self, normal: tuple[float, float, float], origin: tuple[float, float, float]) -> None:
        for spin, value in (
            (self.origin_x, origin[0]), (self.origin_y, origin[1]), (self.origin_z, origin[2]),
            (self.normal_x, normal[0]), (self.normal_y, normal[1]), (self.normal_z, normal[2]),
        ):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

    def _use_view_direction(self) -> None:
        fx, fy, fz = self.viewport.camera_forward()
        self.normal_x.setValue(fx)
        self.normal_y.setValue(fy)
        self.normal_z.setValue(fz)

    def _add_plane(self) -> None:
        self.planes.append(self._current_plane())
        self._refresh_planes_list()
        self._update_plane_gizmo()

    def _remove_plane(self) -> None:
        row = self.planes_list.currentRow()
        if 0 <= row < len(self.planes):
            del self.planes[row]
            self._refresh_planes_list()
            self._update_plane_gizmo()

    def _refresh_planes_list(self) -> None:
        self.planes_list.clear()
        for index, (origin, normal) in enumerate(self.planes, start=1):
            ox, oy, oz = origin
            nx, ny, nz = normal
            text = f"Plane {index}: origin ({ox:.2f}, {oy:.2f}, {oz:.2f})  normal ({nx:.2f}, {ny:.2f}, {nz:.2f})"
            self.planes_list.addItem(QListWidgetItem(text))

    def _active_planes(self) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
        """Planes to cut with: the added list, or the single current plane if none were added."""
        return list(self.planes) if self.planes else [self._current_plane()]

    def _show_pieces(self, pieces: list[model3d_ops.Model3D]) -> None:
        self.pieces = pieces
        self.pieces_list.clear()
        for index in range(len(pieces)):
            self.pieces_list.addItem(QListWidgetItem(f"Piece {index + 1}"))
        self.viewport.set_models([model3d_ops.tessellated_preview(piece) for piece in pieces])
        if pieces:
            self.pieces_list.setCurrentRow(0)

    def _apply_cut(self) -> None:
        if self.current_model is None:
            QMessageBox.information(self, "No Model", "Open a 3D model before cutting.")
            return
        cap = self.cap_checkbox.isChecked() and self.current_model.backend == "mesh"
        self._progress_dialog = QProgressDialog("Cutting model...", None, 0, 0, self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._worker = WorkerThread(model3d_ops.cut_multi, self.current_model, self._active_planes(), cap=cap)
        self._worker.finished_ok.connect(self._on_cut_done)
        self._worker.failed.connect(self._on_cut_failed)
        self._worker.start()

    def _on_cut_done(self, pieces: list[model3d_ops.Model3D]) -> None:
        self._progress_dialog.close()
        self._show_pieces(pieces)
        self._update_plane_gizmo()

        warnings = list(dict.fromkeys(warning for piece in pieces for warning in piece.warnings))
        message = f"Model cut into {len(pieces)} piece{'s' if len(pieces) != 1 else ''}."
        if warnings:
            message += " " + " ".join(warnings)
        self.status_label.setText(message)

    def _on_cut_failed(self, message: str) -> None:
        self._progress_dialog.close()
        QMessageBox.critical(self, "Cut Failed", message)

    def _on_piece_selected(self, row: int) -> None:
        self.viewport.highlight_model(row if row >= 0 else None)
        piece = self._piece_for_row(row)
        if piece is not None:
            self._refresh_inspector(piece)

    def _piece_for_row(self, row: int) -> model3d_ops.Model3D | None:
        if 0 <= row < len(self.pieces):
            return self.pieces[row]
        return None

    def _export_selected_piece(self) -> None:
        piece = self._piece_for_row(self.pieces_list.currentRow())
        if piece is None:
            QMessageBox.information(self, "No Piece Selected", "Cut the model first, then select a piece to export.")
            return
        self._export_model(piece)

    def _export_all_pieces(self) -> None:
        if not self.pieces:
            QMessageBox.information(self, "No Pieces", "Cut the model first, then export all pieces.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export All Pieces (base name)", "", _SAVE_FILTER)
        if not path:
            return
        self._progress_dialog = QProgressDialog("Exporting pieces...", None, 0, len(self.pieces), self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._worker = WorkerThread(self._do_export_all_pieces, list(self.pieces), path)
        self._worker.progress.connect(lambda current, total, message: self._progress_dialog.setValue(current))
        self._worker.finished_ok.connect(lambda base: self._on_export_all_done(base))
        self._worker.failed.connect(self._on_export_all_failed)
        self._worker.start()

    @staticmethod
    def _do_export_all_pieces(
        pieces: list[model3d_ops.Model3D], path: str, progress_cb: Optional[Callable[[int, int, str], None]] = None
    ) -> str:
        base, ext = os.path.splitext(path)
        for index, piece in enumerate(pieces, start=1):
            piece_path = f"{base}_{index}{ext}"
            try:
                model3d_ops.export(piece, piece_path)
            except RuntimeError as exc:
                if str(exc) == model3d_ops.CAD_INSTALL_HINT:
                    raise
                raise RuntimeError(f"Failed exporting piece {index}: {exc}") from exc
            except Exception as exc:
                raise RuntimeError(f"Failed exporting piece {index}: {exc}") from exc
            if progress_cb:
                progress_cb(index, len(pieces), piece_path)
        return base

    def _on_export_all_done(self, base: str) -> None:
        self._progress_dialog.close()
        QMessageBox.information(self, "Exported", f"Saved {len(self.pieces)} pieces alongside {base}")

    def _on_export_all_failed(self, message: str) -> None:
        self._progress_dialog.close()
        if message == model3d_ops.CAD_INSTALL_HINT:
            QMessageBox.warning(self, "CAD Backend Unavailable", message)
        else:
            QMessageBox.critical(self, "Export Failed", message)

    def _recut_selected_piece(self) -> None:
        row = self.pieces_list.currentRow()
        piece = self._piece_for_row(row)
        if piece is None:
            QMessageBox.information(self, "No Piece Selected", "Cut the model first, then select a piece to cut again.")
            return
        cap = self.cap_checkbox.isChecked() and piece.backend == "mesh"
        self._progress_dialog = QProgressDialog("Cutting piece...", None, 0, 0, self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._worker = WorkerThread(model3d_ops.cut_multi, piece, self._active_planes(), cap=cap)
        self._worker.finished_ok.connect(lambda new_pieces: self._on_recut_done(row, new_pieces))
        self._worker.failed.connect(self._on_cut_failed)
        self._worker.start()

    def _on_recut_done(self, row: int, new_pieces: list[model3d_ops.Model3D]) -> None:
        self._progress_dialog.close()
        self._show_pieces(self.pieces[:row] + new_pieces + self.pieces[row + 1:])
        self._update_plane_gizmo()
        self.status_label.setText(
            f"Piece {row + 1} cut into {len(new_pieces)} piece{'s' if len(new_pieces) != 1 else ''}; "
            "other pieces kept."
        )

    # ─── Repair / scale / measure ────────────────────────────────────────
    def _repair_mesh(self) -> None:
        if self.current_model is None:
            QMessageBox.information(self, "No Model", "Open a mesh (STL/OBJ/PLY) model to repair.")
            return
        if self.current_model.backend != "mesh":
            QMessageBox.information(self, "Repair Not Available", "Repair is only available for mesh (STL/OBJ/PLY) models.")
            return
        source_path = self.current_model.source_path
        self._progress_dialog = QProgressDialog("Repairing mesh...", None, 0, 0, self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._worker = WorkerThread(model3d_ops.repair, self.current_model)
        self._worker.finished_ok.connect(lambda repaired: self._on_repair_done(repaired, source_path))
        self._worker.failed.connect(self._on_repair_failed)
        self._worker.start()

    def _on_repair_done(self, repaired: model3d_ops.Model3D, source_path: str | None) -> None:
        self._progress_dialog.close()
        self._set_current_model(repaired, source_path)
        self.status_label.setText("Mesh repaired: filled holes, removed duplicate/degenerate faces, fixed normals.")

    def _on_repair_failed(self, message: str) -> None:
        self._progress_dialog.close()
        QMessageBox.critical(self, "Repair Failed", message)

    def _apply_scale_factor(self, factor: float) -> None:
        if self.current_model is None:
            QMessageBox.information(self, "No Model", "Open a 3D model before scaling.")
            return
        try:
            scaled = model3d_ops.scale(self.current_model, factor)
        except Exception as exc:
            QMessageBox.critical(self, "Scale Failed", str(exc))
            return
        source_path = self.current_model.source_path
        self._set_current_model(scaled, source_path)
        self.status_label.setText(f"Model scaled by {factor:.4f}x.")

    def _start_pick(self, target: str) -> None:
        if self.current_model is None:
            QMessageBox.information(self, "No Model", "Open a 3D model first.")
            return
        self._pick_target = target
        self.viewport.disable_plane_widget()
        self.viewport.start_picking()
        self.status_label.setText("Click a point on the model in the viewport...")

    def _on_viewport_click(self, point: tuple[float, float, float] | None) -> None:
        if self._pick_target is None or point is None:
            return
        if self._pick_target == "cut_origin":
            self.origin_x.setValue(point[0])
            self.origin_y.setValue(point[1])
            self.origin_z.setValue(point[2])
        else:
            self._measure_points[self._pick_target] = point
            if "measure_a" in self._measure_points and "measure_b" in self._measure_points:
                distance = model3d_ops.measure_distance(
                    self._measure_points["measure_a"], self._measure_points["measure_b"]
                )
                self.measure_result_label.setText(f"Distance: {distance:.4f} model units")
            else:
                self.measure_result_label.setText(f"Point recorded: {point}. Pick the other point to measure.")
        self._pick_target = None
        self.status_label.setText("Point picked.")
        self._update_plane_gizmo()

    # ─── Export ──────────────────────────────────────────────────────────
    def _export_current(self) -> None:
        if self.current_model is None:
            QMessageBox.information(self, "No Model", "Open a 3D model before exporting.")
            return
        self._export_model(self.current_model)

    def _export_model(self, model: model3d_ops.Model3D) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export 3D Model", "", _SAVE_FILTER)
        if not path:
            return
        self._progress_dialog = QProgressDialog("Exporting model...", None, 0, 0, self)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.show()
        self._worker = WorkerThread(model3d_ops.export, model, path)
        self._worker.finished_ok.connect(self._on_export_model_done)
        self._worker.failed.connect(self._on_export_model_failed)
        self._worker.start()

    def _on_export_model_done(self, path: str) -> None:
        self._progress_dialog.close()
        QMessageBox.information(self, "Exported", f"Saved to {path}")

    def _on_export_model_failed(self, message: str) -> None:
        self._progress_dialog.close()
        if message == model3d_ops.CAD_INSTALL_HINT:
            QMessageBox.warning(self, "CAD Backend Unavailable", message)
        else:
            QMessageBox.critical(self, "Export Failed", message)
