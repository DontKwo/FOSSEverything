"""Unit tests for screenshot capture operations."""
import os
import tempfile
import unittest
from PIL import Image
from app.features.screenshot import ops as screenshot_ops


class ScreenshotOpsTests(unittest.TestCase):
    def test_save_screenshot(self) -> None:
        img = Image.new("RGB", (120, 80), (100, 150, 200))
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "screenshot.png")
            screenshot_ops.save_screenshot(img, file_path, "PNG")
            self.assertTrue(os.path.exists(file_path))
            with Image.open(file_path) as loaded:
                self.assertEqual(loaded.size, (120, 80))

    def test_region_validation(self) -> None:
        with self.assertRaises(ValueError):
            screenshot_ops.capture_screen_region(0, 0, 0, 0)


if __name__ == "__main__":
    unittest.main()
