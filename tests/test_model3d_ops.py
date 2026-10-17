"""Tests for headless 3D model geometry operations (load, cut, repair, scale, export)."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import trimesh

from app.features.model3d import brep_backend, ops as model3d_ops
from app.features.model3d.ops import Model3D


def _box_stl_path(directory: str, size: float = 10.0) -> str:
    path = os.path.join(directory, "box.stl")
    trimesh.creation.box(extents=(size, size, size)).export(path)
    return path


class Model3DMeshOpsTests(unittest.TestCase):
    def test_load_stl_and_obj(self) -> None:
        with TemporaryDirectory() as directory:
            stl_path = _box_stl_path(directory)
            obj_path = os.path.join(directory, "box.obj")
            trimesh.creation.box(extents=(10, 10, 10)).export(obj_path)

            stl_model = model3d_ops.load(stl_path)
            obj_model = model3d_ops.load(obj_path)
            self.assertEqual(stl_model.backend, "mesh")
            self.assertEqual(obj_model.backend, "mesh")
            self.assertEqual(model3d_ops.info(stl_model)["triangle_count"], 12)

    def test_info_reports_correct_volume_and_bbox(self) -> None:
        with TemporaryDirectory() as directory:
            model = model3d_ops.load(_box_stl_path(directory, size=10.0))
            data = model3d_ops.info(model)
            self.assertTrue(data["watertight"])
            self.assertAlmostEqual(data["volume"], 1000.0, places=3)
            self.assertEqual(data["bbox_min"], [-5.0, -5.0, -5.0])
            self.assertEqual(data["bbox_max"], [5.0, 5.0, 5.0])

    def test_cut_capped_produces_watertight_halves(self) -> None:
        with TemporaryDirectory() as directory:
            model = model3d_ops.load(_box_stl_path(directory))
            piece_a, piece_b = model3d_ops.cut(model, (0, 0, 0), (1, 0, 0), cap=True)
            info_a, info_b = model3d_ops.info(piece_a), model3d_ops.info(piece_b)
            self.assertTrue(info_a["watertight"])
            self.assertTrue(info_b["watertight"])
            self.assertAlmostEqual(info_a["volume"] + info_b["volume"], 1000.0, places=2)

    def test_cut_open_shell_is_not_watertight(self) -> None:
        with TemporaryDirectory() as directory:
            model = model3d_ops.load(_box_stl_path(directory))
            piece_a, _ = model3d_ops.cut(model, (0, 0, 0), (1, 0, 0), cap=False)
            self.assertFalse(model3d_ops.info(piece_a)["watertight"])

    def test_tessellated_preview_shapes_match(self) -> None:
        with TemporaryDirectory() as directory:
            model = model3d_ops.load(_box_stl_path(directory))
            verts, faces = model3d_ops.tessellated_preview(model)
            self.assertEqual(verts.shape, model.mesh.vertices.shape)
            self.assertEqual(faces.shape, model.mesh.faces.shape)

    def test_export_round_trip_stl_obj_ply(self) -> None:
        with TemporaryDirectory() as directory:
            model = model3d_ops.load(_box_stl_path(directory))
            for ext in ("obj", "ply", "stl"):
                out_path = os.path.join(directory, f"out.{ext}")
                model3d_ops.export(model, out_path)
                self.assertTrue(Path(out_path).is_file())

    def test_repair_fills_holes_and_fixes_normals(self) -> None:
        with TemporaryDirectory() as directory:
            model = model3d_ops.load(_box_stl_path(directory))
            repaired = model3d_ops.repair(model)
            self.assertTrue(model3d_ops.info(repaired)["watertight"])

    def test_repair_rejects_brep_models(self) -> None:
        fake_brep = Model3D(backend="brep", shape=object())
        with self.assertRaises(ValueError):
            model3d_ops.repair(fake_brep)

    def test_scale_uniform(self) -> None:
        with TemporaryDirectory() as directory:
            model = model3d_ops.load(_box_stl_path(directory))
            scaled = model3d_ops.scale(model, 2.0)
            self.assertAlmostEqual(model3d_ops.info(scaled)["volume"], 8000.0, places=2)

    def test_measure_distance(self) -> None:
        self.assertAlmostEqual(model3d_ops.measure_distance((0, 0, 0), (3, 4, 0)), 5.0)

    def test_load_rejects_unsupported_extension(self) -> None:
        with self.assertRaises(ValueError):
            model3d_ops.load("model.xyz")

    def test_cut_multi_with_two_planes_produces_four_pieces(self) -> None:
        with TemporaryDirectory() as directory:
            model = model3d_ops.load(_box_stl_path(directory))
            pieces = model3d_ops.cut_multi(model, [((0, 0, 0), (1, 0, 0)), ((0, 0, 0), (0, 1, 0))], cap=True)
            self.assertEqual(len(pieces), 4)
            total_volume = sum(model3d_ops.info(p)["volume"] for p in pieces)
            self.assertAlmostEqual(total_volume, 1000.0, places=2)

    def test_cut_multi_requires_at_least_one_plane(self) -> None:
        with TemporaryDirectory() as directory:
            model = model3d_ops.load(_box_stl_path(directory))
            with self.assertRaises(ValueError):
                model3d_ops.cut_multi(model, [])


@unittest.skipUnless(model3d_ops.brep_backend_available(), "Optional CAD backend (OCP) not installed")
class Model3DBrepOpsTests(unittest.TestCase):
    def _make_step_box(self, directory: str) -> str:
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox  # noqa: 13 (runtime feature-check, class guarded by skipUnless)

        shape = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()
        path = os.path.join(directory, "box.step")
        brep_backend.brep_export_step(shape, path)
        return path

    def test_mesh_to_step_round_trip(self) -> None:
        with TemporaryDirectory() as directory:
            mesh_model = model3d_ops.load(_box_stl_path(directory))
            step_path = os.path.join(directory, "from_mesh.step")
            model3d_ops.export(mesh_model, step_path)
            reloaded = model3d_ops.load(step_path)
            self.assertEqual(reloaded.backend, "brep")
            self.assertTrue(brep_backend.brep_is_valid(reloaded.shape))

    def test_brep_cut_via_generated_step(self) -> None:
        with TemporaryDirectory() as directory:
            step_path = self._make_step_box(directory)
            model = model3d_ops.load(step_path)
            self.assertEqual(model.backend, "brep")

            piece_a, piece_b = model3d_ops.cut(model, (5, 5, 5), (1, 0, 0), cap=True)
            self.assertTrue(brep_backend.brep_is_valid(piece_a.shape))
            self.assertTrue(brep_backend.brep_is_valid(piece_b.shape))
            info_a, info_b = model3d_ops.info(piece_a), model3d_ops.info(piece_b)
            self.assertAlmostEqual(info_a["volume"] + info_b["volume"], 1000.0, places=2)

    def test_step_export_and_tessellation(self) -> None:
        with TemporaryDirectory() as directory:
            step_path = self._make_step_box(directory)
            model = model3d_ops.load(step_path)
            verts, faces = model3d_ops.tessellated_preview(model)
            self.assertGreater(len(verts), 0)
            self.assertGreater(len(faces), 0)
            stl_path = os.path.join(directory, "from_step.stl")
            model3d_ops.export(model, stl_path)
            self.assertTrue(Path(stl_path).is_file())


if __name__ == "__main__":
    unittest.main()
