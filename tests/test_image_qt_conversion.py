"""Regression tests for safe Pillow-to-Qt image rendering."""
import unittest

from PIL import Image

from app.features.image.tab import _pil_to_qimage


class ImageQtConversionTests(unittest.TestCase):
    def test_rgb_image_becomes_a_detached_qimage(self) -> None:
        image = Image.new("RGB", (1920, 1920), "white")
        qimage = _pil_to_qimage(image)
        image.close()
        self.assertFalse(qimage.isNull())
        self.assertEqual((qimage.width(), qimage.height()), (1920, 1920))

    def test_rgba_image_keeps_alpha_format(self) -> None:
        qimage = _pil_to_qimage(Image.new("RGBA", (2, 3), (0, 0, 0, 0)))
        self.assertEqual(qimage.format(), qimage.Format.Format_RGBA8888)  # noqa: 16


if __name__ == "__main__":
    unittest.main()
