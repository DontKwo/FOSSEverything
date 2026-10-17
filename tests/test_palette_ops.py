"""Unit tests for color palette extraction operations."""
import unittest
from PIL import Image
from app.features.palette import ops as palette_ops


class PaletteOpsTests(unittest.TestCase):
    def setUp(self) -> None:
        # Create a test image with 2 distinct colors (red half, blue half)
        self.img = Image.new("RGB", (100, 100), (255, 0, 0))
        for x in range(50, 100):
            for y in range(100):
                self.img.putpixel((x, y), (0, 0, 255))

    def test_extract_palette(self) -> None:
        swatches = palette_ops.extract_palette(self.img, n_colors=4)
        self.assertGreaterEqual(len(swatches), 2)
        hexes = [s.hex_code.upper() for s in swatches]
        # Should contain red (#FF0000) and blue (#0000FF)
        self.assertTrue(any("FF0000" in h for h in hexes))
        self.assertTrue(any("0000FF" in h for h in hexes))

    def test_palette_strip_generation(self) -> None:
        swatches = palette_ops.extract_palette(self.img, n_colors=4)
        strip = palette_ops.generate_palette_strip(swatches, width=200, height=40)
        self.assertEqual(strip.size, (200, 40))

    def test_sample_pixel_color(self) -> None:
        swatch_red = palette_ops.sample_pixel_color(self.img, 10, 10)
        self.assertEqual(swatch_red.rgb, (255, 0, 0))
        self.assertEqual(swatch_red.hex_code.upper(), "#FF0000")  # noqa: 28 (expected pixel-sampled color value, not app chrome)

        swatch_blue = palette_ops.sample_pixel_color(self.img, 75, 50)
        self.assertEqual(swatch_blue.rgb, (0, 0, 255))
        self.assertEqual(swatch_blue.hex_code.upper(), "#0000FF")  # noqa: 28 (expected pixel-sampled color value, not app chrome)

    def test_named_color_and_contrast(self) -> None:
        self.assertEqual(palette_ops.nearest_named_color((255, 0, 0)), "red")
        self.assertEqual(palette_ops.nearest_named_color((0, 0, 255)), "blue")
        self.assertGreater(palette_ops.contrast_ratio((255, 255, 255), (0, 0, 0)), 20)

    def test_kmeans_palette_mode(self) -> None:
        swatches = palette_ops.extract_palette(self.img, n_colors=3, method="kmeans")
        self.assertEqual(len(swatches), 3)
        self.assertTrue(all(s.name for s in swatches))


if __name__ == "__main__":
    unittest.main()
