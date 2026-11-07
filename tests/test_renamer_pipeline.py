from __future__ import annotations

import os
import shutil
import tempfile
import unittest

from app.features.renamer import ops as renamer_ops
from app.web.api import WebApi


class RenamerPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.api = WebApi()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_file(self, name: str) -> str:
        path = os.path.join(self.tmp_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("content")
        return path

    def test_replace_text_literal_and_scopes(self) -> None:
        # Verify replace_text treats regex symbols literally across all scopes.
        p1 = self._create_file("report (1) [final].$txt")
        steps = [
            {
                "type": "replace_text",
                "enabled": True,
                "find_text": "(1) [final]",
                "replace_with": "v2",
                "match_case": False,
                "scope": "all",
            }
        ]
        plans = renamer_ops.preview_step_pipeline([p1], steps)
        self.assertEqual(plans[0].new_name, "report v2.$txt")

    def test_replace_text_first_and_last_scope(self) -> None:
        # Verify first and last scope matching.
        p = self._create_file("item_item_item.txt")
        plans_first = renamer_ops.preview_step_pipeline(
            [p],
            [{"type": "replace_text", "enabled": True, "find_text": "item", "replace_with": "part", "scope": "first"}]
        )
        self.assertEqual(plans_first[0].new_name, "part_item_item.txt")

        plans_last = renamer_ops.preview_step_pipeline(
            [p],
            [{"type": "replace_text", "enabled": True, "find_text": "item", "replace_with": "part", "scope": "last"}]
        )
        self.assertEqual(plans_last[0].new_name, "item_item_part.txt")

    def test_add_text_and_change_extension(self) -> None:
        # Verify prefix, suffix, and extension updates.
        p = self._create_file("document.txt")
        steps = [
            {"type": "add_text", "enabled": True, "prefix": "Draft - ", "suffix": " - reviewed"},
            {"type": "change_extension", "enabled": True, "extension": "md"},
        ]
        plans = renamer_ops.preview_step_pipeline([p], steps)
        self.assertEqual(plans[0].new_name, "Draft - document - reviewed.md")

    def test_number_sequence_and_natural_sort(self) -> None:
        # Verify natural sort ordering and number sequence generation.
        p1 = self._create_file("file10.jpg")
        p2 = self._create_file("file2.jpg")
        p3 = self._create_file("file1.jpg")
        steps = [
            {
                "type": "number_sequence",
                "enabled": True,
                "mode": "replace_name",
                "base_name": "Photo",
                "start_at": 1,
                "increment": 1,
                "padding": 3,
                "separator": " - ",
            }
        ]
        plans = renamer_ops.preview_step_pipeline([p1, p2, p3], steps, sort_by="name_asc")
        # In natural sort: file1, file2, file10
        self.assertEqual(os.path.basename(plans[0].old_path), "file1.jpg")
        self.assertEqual(plans[0].new_name, "Photo - 001.jpg")
        self.assertEqual(os.path.basename(plans[1].old_path), "file2.jpg")
        self.assertEqual(plans[1].new_name, "Photo - 002.jpg")
        self.assertEqual(os.path.basename(plans[2].old_path), "file10.jpg")
        self.assertEqual(plans[2].new_name, "Photo - 003.jpg")

    def test_clean_name_and_case(self) -> None:
        # Verify bracket removal, character cleaning, and case transformations.
        p = self._create_file("my cool   (download) [2026] {rip}! file.txt")
        steps = [
            {
                "type": "clean_name",
                "enabled": True,
                "spaces": "collapse",
                "remove_brackets": True,
                "remove_punctuation": True,
            },
            {
                "type": "change_case",
                "enabled": True,
                "case_mode": "title",
            },
        ]
        plans = renamer_ops.preview_step_pipeline([p], steps)
        self.assertEqual(plans[0].new_name, "My Cool File.txt")

    def test_conflict_auto_resolution(self) -> None:
        # Verify duplicate names in batch are auto-resolved with (2), (3).
        p1 = self._create_file("alpha.txt")
        p2 = self._create_file("beta.txt")
        steps = [
            {"type": "replace_text", "enabled": True, "find_text": "beta", "replace_with": "alpha"}
        ]
        plans = renamer_ops.preview_step_pipeline([p1, p2], steps, auto_resolve_conflicts=True)
        self.assertEqual(plans[0].new_name, "alpha.txt")
        self.assertEqual(plans[1].new_name, "alpha (2).txt")
        self.assertFalse(plans[1].has_collision)

    def test_api_renamer_preview_and_execute_undo(self) -> None:
        # Verify WebApi renamer preview, execute, and undo cycle.
        p1 = self._create_file("test_undo_01.txt")
        p2 = self._create_file("test_undo_02.txt")
        steps = [
            {"type": "add_text", "enabled": True, "prefix": "NEW_"}
        ]
        prev_res = self.api.renamer_preview({
            "file_paths": [p1, p2],
            "steps": steps,
        })
        self.assertTrue(prev_res.get("ok"))
        self.assertEqual(len(prev_res.get("entries", [])), 2)
        self.assertEqual(prev_res["entries"][0]["new_name"], "NEW_test_undo_01.txt")

        exec_res = self.api.renamer_execute({
            "file_paths": [p1, p2],
            "steps": steps,
        })
        self.assertTrue(exec_res.get("ok"))
        self.assertEqual(exec_res.get("renamed_count"), 2)
        self.assertTrue(exec_res.get("undo_available"))

        new_p1 = os.path.join(self.tmp_dir, "NEW_test_undo_01.txt")
        self.assertTrue(os.path.exists(new_p1))

        undo_res = self.api.renamer_undo({})
        self.assertTrue(undo_res.get("ok"))
        self.assertEqual(undo_res.get("restored_count"), 2)
        self.assertTrue(os.path.exists(p1))
        self.assertFalse(os.path.exists(new_p1))

    def test_api_recipes_presets(self) -> None:
        # Verify listing starter recipes, saving a user recipe, and deleting it.
        list_res = self.api.renamer_presets({"action": "list"})
        self.assertTrue(list_res.get("ok"))
        self.assertGreaterEqual(len(list_res.get("starter_recipes", [])), 5)

        save_res = self.api.renamer_presets({
            "action": "save",
            "recipe": {
                "name": "Custom Test Recipe",
                "steps": [{"type": "change_case", "enabled": True, "case_mode": "upper"}]
            }
        })
        self.assertTrue(save_res.get("ok"))

        del_res = self.api.renamer_presets({
            "action": "delete",
            "name": "Custom Test Recipe"
        })
        self.assertTrue(del_res.get("ok"))
