"""Regression tests for multi-image canvas composition."""
import os
import unittest

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage
from PIL import Image

from app.features.image.tab import ImageTab, _pil_to_qimage
from app.features.image import ops as image_ops
from app.ui.canvas import AnnotationCanvas

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class ImageLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls: type['ImageLayerTests']) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_image_layer_order_does_not_pollute_annotations(self) -> None:
        canvas = AnnotationCanvas()
        canvas.set_image(QImage(30, 30, QImage.Format.Format_RGBA8888))
        first = canvas.add_image_layer(QImage(10, 10, QImage.Format.Format_RGBA8888))
        second = canvas.add_image_layer(QImage(10, 10, QImage.Format.Format_RGBA8888))
        second.setSelected(False)
        first.setSelected(True)
        self.assertTrue(canvas.bring_selected_image_layer_to_front())
        self.assertIs(canvas.image_layers()[-1], first)
        self.assertEqual(canvas.get_annotations(), [])
        first.setSelected(False)
        second.setSelected(True)
        self.assertTrue(canvas.send_selected_image_layer_to_back())
        self.assertIs(canvas.image_layers()[0], second)

    def test_baking_layer_composites_pixels_and_clears_layer_items(self) -> None:
        tab = ImageTab()
        tab.pil_image = Image.new("RGBA", (10, 10), (255, 255, 255, 255))
        tab._refresh_canvas()
        layer = tab.canvas.add_image_layer(_pil_to_qimage(Image.new("RGBA", (2, 2), (255, 0, 0, 255))))
        layer.setPos(3, 4)
        tab._bake_annotations_into_pil()
        self.assertEqual(tab.pil_image.getpixel((3, 4)), (255, 0, 0, 255))
        self.assertEqual(tab.canvas.image_layers(), [])

    def test_per_layer_image_operations_change_only_the_layer_pixels(self) -> None:
        source = Image.new("RGBA", (4, 2), (255, 0, 0, 255))
        source.putpixel((0, 0), (0, 0, 255, 255))
        rotated = image_ops.rotate_image(source, 90)
        self.assertEqual(rotated.size, (2, 4))
        flipped = image_ops.flip_image(source, horizontal=True)
        self.assertEqual(flipped.getpixel((3, 0)), (0, 0, 255, 255))
        adjusted = image_ops.adjust_image(
            source, image_ops.ImageAdjustments(brightness=0, contrast=100, saturation=0, sharpness=100, blur_radius=1, grayscale=True)
        )
        self.assertEqual(adjusted.getpixel((1, 1)), (0, 0, 0, 255))

    def test_composition_undo_restores_layer_position(self) -> None:
        tab = ImageTab()
        tab.pil_image = Image.new("RGBA", (20, 20), "white")
        tab._refresh_canvas()
        tab._reset_edit_history()
        layer = tab.canvas.add_image_layer(_pil_to_qimage(Image.new("RGBA", (2, 2), "red")))
        tab._commit_edit()
        initial_position = layer.pos()
        layer.setPos(9, 8)
        tab.canvas.image_layer_changed.emit()
        tab.undo_edit()
        restored = tab.canvas.image_layers()[0]
        self.assertEqual((restored.pos().x(), restored.pos().y()), (initial_position.x(), initial_position.y()))
        tab.redo_edit()
        redone = tab.canvas.image_layers()[0]
        self.assertEqual((redone.pos().x(), redone.pos().y()), (9, 8))


if __name__ == "__main__":
    unittest.main()
