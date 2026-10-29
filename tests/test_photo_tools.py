"""Tests for comprehensive photo editing operations."""
import unittest
from PIL import Image
from app.features.image import ops as image_ops
from app.ui.canvas import Tool, ResizableArrowItem
from PyQt6.QtCore import QPointF

class PhotoToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.test_img = Image.new("RGB", (100, 80), color=(120, 80, 60))

    def test_auto_enhance(self) -> None:
        res = image_ops.auto_enhance(self.test_img)
        self.assertEqual(res.size, (100, 80))

    def test_filter_presets(self) -> None:
        for preset in image_ops.FILTER_PRESETS:
            res = image_ops.apply_filter_preset(self.test_img, preset)
            self.assertEqual(res.size, (100, 80))

    def test_adjust_image_with_warmth(self) -> None:
        warm = image_ops.adjust_image(self.test_img, image_ops.ImageAdjustments(warmth=50))
        self.assertEqual(warm.size, (100, 80))
        cool = image_ops.adjust_image(self.test_img, image_ops.ImageAdjustments(warmth=-50))
        self.assertEqual(cool.size, (100, 80))

    def test_aspect_ratio_crop_box(self) -> None:
        box = image_ops.aspect_ratio_crop_box(100, 50, 1, 1)
        self.assertEqual(box, (25, 0, 75, 50))
        box_16_9 = image_ops.aspect_ratio_crop_box(160, 90, 16, 9)
        self.assertEqual(box_16_9, (0, 0, 160, 90))

    def test_circle_crop(self) -> None:
        res = image_ops.circle_crop_image(self.test_img)
        self.assertEqual(res.size, (80, 80))
        self.assertEqual(res.mode, "RGBA")

    def test_border_addition(self) -> None:
        res = image_ops.add_border(self.test_img, border_size=10, color=(255, 255, 255), polaroid=False)
        self.assertEqual(res.size, (120, 100))
        polaroid_res = image_ops.add_border(self.test_img, border_size=10, color=(255, 255, 255), polaroid=True)
        self.assertEqual(polaroid_res.size, (120, 130))

    def test_region_blur_and_pixelate(self) -> None:
        blurred = image_ops.blur_region(self.test_img, (10, 10, 50, 50), radius=5)
        self.assertEqual(blurred.size, (100, 80))
        pixelated = image_ops.pixelate_region(self.test_img, (10, 10, 50, 50), pixel_size=5)
        self.assertEqual(pixelated.size, (100, 80))

    def test_replace_background_color(self) -> None:
        cutout = Image.new("RGBA", (50, 50), (255, 0, 0, 128))
        res = image_ops.replace_background_color(cutout, color=(0, 255, 0, 255))
        self.assertEqual(res.size, (50, 50))

    def test_arrow_tool_item(self) -> None:
        arrow = ResizableArrowItem(QPointF(10, 10), QPointF(50, 50))
        d = arrow.to_dict()
        self.assertEqual(d["type"], "arrow")
        self.assertEqual(d["start"], (10, 10))
        self.assertEqual(d["end"], (50, 50))

if __name__ == "__main__":
    unittest.main()
