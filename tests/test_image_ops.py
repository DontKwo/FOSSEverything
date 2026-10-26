"""Tests for image operations that do not require a real model download."""
import os
import tempfile
import unittest
from typing import Any
from unittest.mock import patch

from PIL import Image

from app.features.image import ops as image_ops


class ImageOperationsTests(unittest.TestCase):
    def test_remove_background_uses_local_rembg_and_converts_to_rgba(self) -> None:
        received = []
        sessions = []

        def fake_remove(image: Any, session: Any) -> Any:
            received.append((image.mode, session))
            return image

        def fake_new_session(name: str) -> str:
            sessions.append(name)
            return f"session:{name}"

        with patch("rembg.remove", fake_remove), patch("rembg.new_session", fake_new_session):
            result = image_ops.remove_background(Image.new("RGB", (3, 2), "white"), "u2netp")

        self.assertEqual(sessions, ["u2netp"])
        self.assertEqual(received, [("RGBA", "session:u2netp")])
        self.assertEqual(result.mode, "RGBA")

    def test_remove_background_defaults_to_supported_model(self) -> None:
        def fake_new_session(name: str) -> str:
            return f"session:{name}"

        with patch("rembg.remove", lambda image, session: image), patch("rembg.new_session", fake_new_session):
            result = image_ops.remove_background(Image.new("RGB", (4, 4), "white"))

        self.assertEqual(result.mode, "RGBA")

    def test_normalize_model_name_maps_balanced_to_working_default(self) -> None:
        self.assertEqual(image_ops._normalize_model_name("Balanced"), "bria-rmbg")
        self.assertEqual(image_ops._normalize_model_name("u2net"), "u2net")

    def test_perspective_crop_image(self) -> None:
        img = Image.new("RGBA", (200, 120), (0, 0, 0, 255))
        for x in range(20, 180, 20):
            for y in range(20, 100, 20):
                img.putpixel((x, y), (255, 0, 0, 255))

        corners = [(20, 20), (180, 10), (190, 110), (10, 100)]
        result = image_ops.perspective_crop_image(img, corners, output_size=(120, 80))
        self.assertEqual(result.size, (120, 80))
        self.assertEqual(result.mode, "RGBA")

    def test_batch_remove_background(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = os.path.join(tmp, "inputs")
            output_dir = os.path.join(tmp, "outputs")
            os.makedirs(input_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)
            p1 = os.path.join(input_dir, "one.png")
            p2 = os.path.join(input_dir, "two.png")
            Image.new("RGB", (10, 10), "red").save(p1)
            Image.new("RGB", (10, 10), "blue").save(p2)

            with patch("app.features.image.ops.remove_background", side_effect=lambda img, model_name="u2net": img.convert("RGBA")):
                outputs = image_ops.batch_remove_background([p1, p2], output_dir=output_dir, model_name="u2net")

            self.assertEqual(len(outputs), 2)
            self.assertTrue(all(os.path.exists(path) for path in outputs))

    def test_color_balance_and_curves_presets(self) -> None:
        img = Image.new("RGB", (20, 20), "black")
        balanced = image_ops.apply_color_balance(img, red_shift=20)
        self.assertEqual(balanced.mode, "RGB")
        curved = image_ops.apply_curves(img, red_points=[(0, 0), (128, 100), (255, 255)])
        self.assertEqual(curved.mode, "RGB")
        preset = image_ops.build_annotation_preset("callout-badge")
        self.assertIn("style", preset)

    def test_non_destructive_layer_masks(self) -> None:
        img = Image.new("RGBA", (8, 8), (255, 0, 0, 255))
        mask = image_ops.build_layer_mask((8, 8), box=(2, 2, 6, 6), invert=False)
        masked = image_ops.apply_non_destructive_mask(img, mask)
        self.assertEqual(masked.mode, "RGBA")
        self.assertEqual(masked.getpixel((0, 0))[3], 0)
        self.assertEqual(masked.getpixel((4, 4))[3], 255)


if __name__ == "__main__":
    unittest.main()
