"""Unit tests validating non-destructive file handling, collision guards, and integrity."""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from app.core.file_safety import (
    check_write_safety,
    compute_path_sha256,
    generate_safe_output_path,
)


class FileSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path("tests/_tmp_safety_test")
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.sample_file = self.tmp_dir / "document.txt"
        self.sample_file.write_text("Original content untouched", encoding="utf-8")
        self.original_hash = compute_path_sha256(str(self.sample_file))

    def tearDown(self) -> None:
        if self.tmp_dir.exists():
            import shutil
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_original_hash_integrity(self) -> None:
        current_hash = compute_path_sha256(str(self.sample_file))
        self.assertEqual(current_hash, self.original_hash)

    def test_generate_safe_output_path_increments(self) -> None:
        p1 = generate_safe_output_path(str(self.sample_file), suffix="_converted")
        Path(p1).write_text("first", encoding="utf-8")

        p2 = generate_safe_output_path(str(self.sample_file), suffix="_converted")
        self.assertNotEqual(p1, p2)
        self.assertTrue(p2.endswith("_converted_1.txt"))

    def test_check_write_safety_collision_blocked(self) -> None:
        with self.assertRaises(ValueError):
            check_write_safety(str(self.sample_file), source_path=str(self.sample_file), overwrite=False)

    def test_check_write_safety_overwrite_allowed(self) -> None:
        # Should not raise when overwrite is True
        check_write_safety(str(self.sample_file), source_path=str(self.sample_file), overwrite=True)

    def test_check_write_safety_existing_file_without_overwrite(self) -> None:
        other_file = self.tmp_dir / "target.txt"
        other_file.write_text("existing", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            check_write_safety(str(other_file), overwrite=False)


if __name__ == "__main__":
    unittest.main()
