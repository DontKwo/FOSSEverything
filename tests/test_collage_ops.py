"""Unit tests for photo collage composer operations."""
import os
import tempfile
import unittest
from PIL import Image
from app.features.collage import ops as collage_ops


class CollageOpsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_files = []
        for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]:
            f = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            img = Image.new("RGB", (60, 60), color)
            img.save(f.name)
            f.close()
            self.tmp_files.append(f.name)

    def tearDown(self) -> None:
        for p in self.tmp_files:
            if os.path.exists(p):
                os.remove(p)

    def test_make_2x2_collage(self) -> None:
        config = collage_ops.CollageConfig(
            cols=2, thumb_width=100, thumb_height=100, padding=10, fit_mode="cover"
        )
        result = collage_ops.make_collage(self.tmp_files, config=config)
        expected_w = 2 * 100 + 3 * 10  # 230
        expected_h = 2 * 100 + 3 * 10  # 230
        self.assertEqual(result.size, (expected_w, expected_h))

    def test_make_collage_with_captions(self) -> None:
        config = collage_ops.CollageConfig(
            cols=2, thumb_width=100, thumb_height=100, padding=10, fit_mode="contain"
        )
        captions = ["Red", "Green", "Blue", "Yellow"]
        result = collage_ops.make_collage(self.tmp_files, config=config, captions=captions)
        self.assertGreater(result.height, 200)

    def test_fit_cell_modes(self) -> None:
        sample = Image.new("RGB", (100, 50), (100, 100, 100))
        cover = collage_ops._fit_cell(sample, 80, 80, "cover")
        self.assertEqual(cover.size, (80, 80))
        contain = collage_ops._fit_cell(sample, 80, 80, "contain")
        self.assertEqual(contain.size, (80, 80))
        stretch = collage_ops._fit_cell(sample, 80, 80, "stretch")
        self.assertEqual(stretch.size, (80, 80))

    def test_make_collage_with_round_corners_and_cell_backgrounds(self) -> None:
        config = collage_ops.CollageConfig(
            cols=2,
            thumb_width=80,
            thumb_height=80,
            padding=10,
            bg_color=(30, 30, 30),
            cell_backgrounds=[(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)],
            corner_radius=12,
        )
        result = collage_ops.make_collage(self.tmp_files, config=config)
        self.assertEqual(result.size, (2 * 80 + 3 * 10, 2 * 80 + 3 * 10))
        self.assertEqual(result.mode, "RGB")

    def test_make_collage_with_round_corners_without_cell_backgrounds(self) -> None:
        config = collage_ops.CollageConfig(
            cols=1, thumb_width=60, thumb_height=60, padding=10, bg_color=(0, 255, 0), corner_radius=15
        )
        result = collage_ops.make_collage(self.tmp_files[:1], config=config)
        self.assertEqual(result.getpixel((10, 10)), (0, 255, 0))

    def test_collage_presets_reorder_and_watermark(self) -> None:
        reordered = collage_ops.reorder_image_paths(self.tmp_files, [2, 0, 3, 1])
        self.assertEqual(reordered[0], self.tmp_files[2])

        preset = collage_ops.LAYOUT_PRESETS["Triptych"]
        self.assertEqual(preset["cols"], 3)

        result = collage_ops.make_collage(self.tmp_files, layout_name="Side-by-side 2-up", watermark_text="Draft")
        self.assertEqual(result.mode, "RGB")
        self.assertGreater(result.width, 0)

        watermarked = collage_ops.add_watermark_to_image(Image.new("RGB", (200, 200), "white"), "Demo", opacity=0.5, position="center")
        self.assertEqual(watermarked.mode, "RGBA")


if __name__ == "__main__":
    unittest.main()
