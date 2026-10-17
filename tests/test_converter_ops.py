"""Tests for the installed local format-conversion capabilities."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image
import pymupdf as fitz

from app.features.converter import ops as converter_ops


class ConverterOperationsTests(unittest.TestCase):
    def test_image_to_pdf(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            Image.new("RGBA", (8, 6), (0, 0, 0, 0)).save(source)
            outputs = converter_ops.convert_file(str(source), directory, "PDF")
            self.assertEqual(outputs, [str(Path(directory) / "source.pdf")])
            self.assertTrue(Path(outputs[0]).is_file())

    def test_pdf_exports_each_page_to_images(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "pages.pdf"
            document = fitz.open()
            document.new_page()
            document.new_page()
            document.save(source)
            document.close()
            outputs = converter_ops.convert_file(str(source), directory, "PNG", dpi=72)
            self.assertEqual(len(outputs), 2)
            self.assertTrue(all(os.path.isfile(output) for output in outputs))

    def test_converter_does_not_advertise_unknown_file_types(self) -> None:
        self.assertEqual(converter_ops.available_targets("notes.unknown_xyz"), [])
        self.assertEqual(converter_ops.available_targets("notes.docx"), ["PDF", "TXT", "MD"])

    def test_model3d_source_and_targets(self) -> None:
        self.assertEqual(converter_ops.source_family("part.stl"), "Model3D")
        self.assertEqual(converter_ops.source_family("part.step"), "Model3D")
        targets = converter_ops.available_targets("part.stl")
        self.assertIn("STL", targets)
        self.assertIn("OBJ", targets)
        from app.features.model3d import ops as model3d_ops  # noqa: 13 (deferred: only needed for this test, avoids slow optional-CAD-backend import for the whole file)
        if model3d_ops.brep_backend_available():
            self.assertIn("STEP", targets)
        else:
            self.assertNotIn("STEP", targets)

    def test_model3d_convert_stl_to_obj(self) -> None:
        import trimesh  # noqa: 13 (deferred: only needed for this test, avoids slow mesh-library import for the whole file)
        with TemporaryDirectory() as directory:
            source = Path(directory) / "box.stl"
            trimesh.creation.box(extents=(10, 10, 10)).export(source)
            outputs = converter_ops.convert_file(str(source), directory, "OBJ")
            self.assertEqual(outputs, [str(Path(directory) / "box.obj")])
            self.assertTrue(Path(outputs[0]).is_file())

    def test_batch_convert_files(self) -> None:
        with TemporaryDirectory() as directory:
            src1 = Path(directory) / "img1.png"
            src2 = Path(directory) / "img2.jpg"
            Image.new("RGB", (10, 10), (255, 0, 0)).save(src1)
            Image.new("RGB", (10, 10), (0, 255, 0)).save(src2)

            out_dir = Path(directory) / "outputs"
            items = [
                converter_ops.BatchConversionItem(input_path=str(src1), target_format="WEBP"),
                converter_ops.BatchConversionItem(input_path=str(src2), target_format="PNG"),
            ]
            results = converter_ops.batch_convert_files(items, str(out_dir))
            self.assertEqual(len(results), 2)
            self.assertTrue(all(item.status == "done" for item in results))
            self.assertTrue(all(len(item.output_paths) > 0 for item in results))


if __name__ == "__main__":
    unittest.main()

