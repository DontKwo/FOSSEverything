import os
import tempfile
import unittest
from pathlib import Path

from app.web.api import WebApi


class TestMatrixDiscoveredRegressions(unittest.TestCase):
    def setUp(self) -> None:
        self.api = WebApi()

    def test_image_resize_never_overwrites_input_without_flag(self) -> None:
        # Verify that images_resize refuses to overwrite source image when overwrite flag is false.
        from PIL import Image

        with tempfile.TemporaryDirectory() as td:
            img_path = os.path.join(td, "test_img.png")
            im = Image.new("RGBA", (32, 32), color=(255, 0, 0, 255))
            im.save(img_path)
            orig_bytes = Path(img_path).read_bytes()

            res = self.api.images_resize({
                "file_path": img_path,
                "output_path": img_path,
                "width": 16,
                "height": 16,
                "overwrite": False,
            })
            self.assertFalse(res["ok"])
            self.assertIn("cannot overwrite input file", res.get("error", ""))
            self.assertEqual(Path(img_path).read_bytes(), orig_bytes)

    def test_metadata_batch_cleanup_avoids_same_directory_corruption(self) -> None:
        # Verify that metadata_batch_cleanup redirects output directory if same as input directory.
        with tempfile.TemporaryDirectory() as td:
            in_dir = os.path.join(td, "docs")
            os.makedirs(in_dir, exist_ok=True)
            txt_p = os.path.join(in_dir, "sample.txt")
            Path(txt_p).write_text("hello", encoding="utf-8")

            res = self.api.metadata_batch_cleanup({
                "input_dir": in_dir,
                "output_dir": in_dir,
            })
            self.assertTrue(res["ok"])
            self.assertTrue(os.path.exists(f"{in_dir}_clean"))


if __name__ == "__main__":
    unittest.main()
