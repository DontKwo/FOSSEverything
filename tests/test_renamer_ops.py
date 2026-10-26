"""Tests for batch renamer operations and collision detection."""
import unittest
import os
import tempfile
from app.features.renamer import ops as renamer_ops


class RenamerOpsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.files = []
        for name in ["IMG_001.JPG", "IMG_002.JPG", "document_report.txt"]:
            p = os.path.join(self.tmp_dir, name)
            with open(p, "w") as f:
                f.write("content")
            self.files.append(p)

    def test_find_and_replace(self) -> None:
        plans = renamer_ops.preview_renames(
            self.files,
            mode="find_replace",
            params={"find": "IMG_", "replace": "Photo_", "use_regex": False, "case_sensitive": True},
        )
        self.assertEqual(plans[0].new_name, "Photo_001.JPG")
        self.assertEqual(plans[1].new_name, "Photo_002.JPG")
        self.assertEqual(plans[2].new_name, "document_report.txt")

    def test_regex_renaming(self) -> None:
        plans = renamer_ops.preview_renames(
            self.files,
            mode="find_replace",
            params={"find": r"IMG_(\d+)", "replace": r"Vacation_\1", "use_regex": True},
        )
        self.assertEqual(plans[0].new_name, "Vacation_001.JPG")
        self.assertEqual(plans[1].new_name, "Vacation_002.JPG")

    def test_numbering_sequence(self) -> None:
        plans = renamer_ops.preview_renames(
            self.files,
            mode="numbering",
            params={"prefix": "Item_", "suffix": "", "start": 10, "step": 1, "padding": 3, "keep_name": False},
        )
        self.assertEqual(plans[0].new_name, "Item_010.JPG")
        self.assertEqual(plans[1].new_name, "Item_011.JPG")
        self.assertEqual(plans[2].new_name, "Item_012.txt")

    def test_case_transform(self) -> None:
        plans = renamer_ops.preview_renames(
            self.files,
            mode="change_case",
            params={"case_type": "lower", "affect_ext": True},
        )
        self.assertEqual(plans[0].new_name, "img_001.jpg")
        self.assertEqual(plans[1].new_name, "img_002.jpg")

    def test_numbering_styles(self) -> None:
        plans_prefix = renamer_ops.preview_renames(
            self.files[:1],
            mode="numbering",
            params={"num_style": "prefix", "start": 5, "padding": 3},
        )
        self.assertEqual(plans_prefix[0].new_name, "005_IMG_001.JPG")

        plans_suffix = renamer_ops.preview_renames(
            self.files[:1],
            mode="numbering",
            params={"num_style": "suffix", "start": 5, "padding": 3},
        )
        self.assertEqual(plans_suffix[0].new_name, "IMG_001_005.JPG")

    def test_extended_case_transforms(self) -> None:
        self.assertEqual(renamer_ops.apply_case_transform("hello_world_test", "camel"), "helloWorldTest")
        self.assertEqual(renamer_ops.apply_case_transform("helloWorldTest", "snake"), "hello_world_test")
        self.assertEqual(renamer_ops.apply_case_transform("hello_world_test", "kebab"), "hello-world-test")

    def test_execute_renames(self) -> None:
        plans = renamer_ops.preview_renames(
            self.files,
            mode="find_replace",
            params={"find": "IMG_", "replace": "TestPhoto_", "use_regex": False},
        )
        results = renamer_ops.execute_renames(plans)
        self.assertTrue(all(r.success for r in results))
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "TestPhoto_001.JPG")))

    def test_preset_and_undo_helpers(self) -> None:
        preset = renamer_ops.save_preset("vacation", "find_replace", {"find": "IMG_", "replace": "Trip_"})
        self.assertEqual(preset["name"], "vacation")
        self.assertEqual(preset["mode"], "find_replace")
        self.assertEqual(preset["params"]["replace"], "Trip_")

        original = [("/tmp/a.txt", "/tmp/b.txt"), ("/tmp/c.txt", "/tmp/d.txt")]
        self.assertEqual(renamer_ops.undo_renames(original), [("/tmp/b.txt", "/tmp/a.txt"), ("/tmp/d.txt", "/tmp/c.txt")])

    def test_template_rename_metadata_tokens(self) -> None:
        template = "{date}_{camera}_{artist}"
        file_path = os.path.join(self.tmp_dir, "sample.jpg")
        with open(file_path, "wb") as fh:
            fh.write(b"fake jpg")

        metadata = renamer_ops.extract_rename_metadata(file_path)
        self.assertIn("date", metadata)
        self.assertIn("camera", metadata)

        rendered = renamer_ops.render_rename_template(file_path, template, {"artist": "josh", "camera": "sony"})
        self.assertIn("josh", rendered)
        self.assertIn("sony", rendered)

        plans = renamer_ops.preview_renames([file_path], mode="template", params={"template": "{date}_{camera}_{artist}"})
        self.assertTrue(plans)
        self.assertTrue(plans[0].new_name.endswith(".jpg"))
        self.assertIn("202", plans[0].new_name)


if __name__ == "__main__":
    unittest.main()
