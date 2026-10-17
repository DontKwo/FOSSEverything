"""Smoke tests for the 3D Model Studio Qt tab and its workspace wiring."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import trimesh
from PyQt6.QtWidgets import QApplication

from app.features.model3d.tab import Model3DTab
from app.ui.main_window import MainWindow

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class Model3DTabSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls: type['Model3DTabSmokeTests']) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from app.features.model3d.viewport import _load_vtk_stack
        _load_vtk_stack()

    def _run_worker(self, tab: Model3DTab) -> None:
        """load_file/_apply_cut/_recut_selected_piece run on a WorkerThread; wait for it
        to finish and pump the event loop so its finished_ok/failed slot actually runs."""
        tab._worker.wait()
        if hasattr(tab, "viewport") and not tab.viewport._is_ready():
            tab.viewport._check_engine_ready()
        self.app.processEvents()

    def test_tab_constructs_and_loads_a_model(self) -> None:
        tab = Model3DTab()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "box.stl"
            trimesh.creation.box(extents=(10, 10, 10)).export(path)
            tab.load_file(str(path))
            self._run_worker(tab)
        self.assertIsNotNone(tab.current_model)
        self.assertEqual(tab.current_model.backend, "mesh")

    def test_tab_cut_populates_pieces_list(self) -> None:
        tab = Model3DTab()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "box.stl"
            trimesh.creation.box(extents=(10, 10, 10)).export(path)
            tab.load_file(str(path))
            self._run_worker(tab)
        tab._apply_cut()
        self._run_worker(tab)
        self.assertEqual(len(tab.pieces), 2)
        self.assertEqual(tab.pieces_list.count(), 2)

    def test_recut_keeps_other_pieces(self) -> None:
        tab = Model3DTab()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "box.stl"
            trimesh.creation.box(extents=(10, 10, 10)).export(path)
            tab.load_file(str(path))
            self._run_worker(tab)
        tab._apply_cut()
        self._run_worker(tab)
        tab.pieces_list.setCurrentRow(0)
        tab.origin_x.setValue(2.5)  # piece 0 spans x in [0, 5]; move the plane into its interior
        tab._recut_selected_piece()
        self._run_worker(tab)
        self.assertEqual(len(tab.pieces), 3)
        self.assertEqual(tab.pieces_list.count(), 3)

    def test_multi_plane_cut_produces_four_pieces(self) -> None:
        tab = Model3DTab()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "box.stl"
            trimesh.creation.box(extents=(10, 10, 10)).export(path)
            tab.load_file(str(path))
            self._run_worker(tab)
        tab._add_plane()  # plane 1: normal (1, 0, 0) through the box center
        tab.normal_x.setValue(0.0)
        tab.normal_y.setValue(1.0)
        tab._add_plane()  # plane 2: normal (0, 1, 0) through the box center
        tab._apply_cut()
        self._run_worker(tab)
        self.assertEqual(len(tab.pieces), 4)

    def test_selecting_piece_highlights_it_in_viewport(self) -> None:
        tab = Model3DTab()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "box.stl"
            trimesh.creation.box(extents=(10, 10, 10)).export(path)
            tab.load_file(str(path))
            self._run_worker(tab)
        tab._apply_cut()
        self._run_worker(tab)
        tab.pieces_list.setCurrentRow(1)
        highlighted_color = tuple(tab.viewport._actors[1].prop.color[:3])
        other_color = tuple(tab.viewport._actors[0].prop.color[:3])
        self.assertNotEqual(highlighted_color, other_color)
        for actual, expected in zip(other_color, tab.viewport._actor_colors[0]):
            self.assertAlmostEqual(actual, expected, places=2)

    def test_viewport_renders_without_error(self) -> None:
        tab = Model3DTab()
        tab.resize(400, 300)
        tab.show()
        self.app.processEvents()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "box.stl"
            trimesh.creation.box(extents=(10, 10, 10)).export(path)
            tab.load_file(str(path))
            self._run_worker(tab)
        tab.viewport.plotter.render()
        self.app.processEvents()


class Model3DWorkspaceWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls: type['Model3DWorkspaceWiringTests']) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_workspace_registry_routes_3d_extensions(self) -> None:
        window = MainWindow()
        workspace = window.workspace_registry.find_for_path("part.stl")
        self.assertIsNotNone(workspace)
        self.assertEqual(workspace.id, "model3d")

    def test_open_workspace_switches_to_model3d_tab(self) -> None:
        window = MainWindow()
        window.open_workspace("model3d")
        self.assertIs(window.tabs.currentWidget(), window.model3d_tab)

    def test_model3d_tools_are_registered_for_search(self) -> None:
        window = MainWindow()
        ids = [tool.id for tool in window.tool_registry.all()]
        self.assertIn("model3d._browse_file", ids)
        self.assertIn("model3d._apply_cut", ids)


if __name__ == "__main__":
    unittest.main()
