"""Tests for local archive creation and extraction utilities."""
import os
import tempfile
import unittest

from app.features.archive import ops as archive_ops


class ArchiveOpsTests(unittest.TestCase):
    def test_create_and_extract_zip_archive(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source_dir = os.path.join(td, "src")
            os.makedirs(source_dir, exist_ok=True)
            with open(os.path.join(source_dir, "note.txt"), "w", encoding="utf-8") as f:
                f.write("hello archive")

            archive_path = os.path.join(td, "bundle.zip")
            archive_ops.create_archive(source_dir, archive_path)
            self.assertTrue(os.path.exists(archive_path))
            self.assertIn("src/note.txt", archive_ops.list_archive_contents(archive_path))

            extract_dir = os.path.join(td, "out")
            extracted = archive_ops.extract_archive(archive_path, extract_dir)
            self.assertTrue(any(os.path.basename(path) == "note.txt" for path in extracted))
            with open(os.path.join(extract_dir, "src", "note.txt"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "hello archive")

    def test_create_tar_archive(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source_path = os.path.join(td, "payload.txt")
            with open(source_path, "w", encoding="utf-8") as f:
                f.write("payload")

            archive_path = os.path.join(td, "payload.tar.gz")
            archive_ops.create_archive(source_path, archive_path)
            self.assertTrue(os.path.exists(archive_path))
            self.assertIn("payload.txt", archive_ops.list_archive_contents(archive_path))

    def test_incremental_backup(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source_dir = os.path.join(td, "src")
            backup_dir = os.path.join(td, "backup")
            os.makedirs(source_dir, exist_ok=True)
            with open(os.path.join(source_dir, "alpha.txt"), "w", encoding="utf-8") as f:
                f.write("first")

            first = archive_ops.create_incremental_backup(source_dir, backup_dir)
            self.assertTrue(os.path.exists(first["archive_path"]))
            self.assertTrue(os.path.exists(first["manifest_path"]))

            with open(os.path.join(source_dir, "alpha.txt"), "w", encoding="utf-8") as f:
                f.write("second")
            with open(os.path.join(source_dir, "beta.txt"), "w", encoding="utf-8") as f:
                f.write("new")

            second = archive_ops.create_incremental_backup(source_dir, backup_dir)
            self.assertGreater(second["total_files"], 0)
            self.assertIn("alpha.txt", second["files"])
            self.assertIn("beta.txt", second["files"])

    def test_password_protected_bundle_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source_dir = os.path.join(td, "src")
            os.makedirs(source_dir, exist_ok=True)
            payload_path = os.path.join(source_dir, "secret.txt")
            with open(payload_path, "w", encoding="utf-8") as f:
                f.write("team secret")

            bundle_path = os.path.join(td, "bundle.enc")
            archive_ops.create_password_protected_bundle(source_dir, bundle_path, "hunter2")
            self.assertTrue(os.path.exists(bundle_path))
            self.assertGreater(os.path.getsize(bundle_path), 0)

            extracted_dir = os.path.join(td, "out")
            extracted = archive_ops.extract_password_protected_bundle(bundle_path, extracted_dir, "hunter2")
            self.assertTrue(extracted)
            self.assertTrue(any(os.path.basename(path) == "secret.txt" for path in extracted))

    def test_bundle_rotation_and_integrity_verification(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source_dir = os.path.join(td, "src")
            os.makedirs(source_dir, exist_ok=True)
            with open(os.path.join(source_dir, "notes.txt"), "w", encoding="utf-8") as fh:
                fh.write("rotation test")

            bundle_path = os.path.join(td, "bundle.enc")
            archive_ops.create_password_protected_bundle(source_dir, bundle_path, "first-pass")

            rotated = archive_ops.rotate_bundle_key(bundle_path, "first-pass", "second-pass")
            self.assertTrue(os.path.exists(rotated))

            integrity = archive_ops.verify_bundle_integrity(rotated, "second-pass")
            self.assertTrue(integrity["valid"])
            self.assertGreater(len(integrity["entries"]), 0)

    def test_convert_archive_format(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source_dir = os.path.join(td, "src")
            os.makedirs(source_dir, exist_ok=True)
            payload_path = os.path.join(source_dir, "notes.txt")
            with open(payload_path, "w", encoding="utf-8") as fh:
                fh.write("archive conversion test")

            input_zip = os.path.join(td, "src.zip")
            archive_ops.create_archive(source_dir, input_zip)
            converted = os.path.join(td, "src.tar.gz")
            archive_ops.convert_archive_format(input_zip, converted, archive_format="tar.gz")

            self.assertTrue(os.path.exists(converted))
            self.assertIn("src/notes.txt", archive_ops.list_archive_contents(converted))

    def test_test_archive_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            source_dir = os.path.join(td, "src")
            os.makedirs(source_dir, exist_ok=True)
            with open(os.path.join(source_dir, "test.txt"), "w", encoding="utf-8") as f:
                f.write("content")

            zip_path = os.path.join(td, "test.zip")
            archive_ops.create_archive(source_dir, zip_path)
            res_zip = archive_ops.test_archive(zip_path)
            self.assertTrue(res_zip["valid"])

            tar_path = os.path.join(td, "test.tar.gz")
            archive_ops.create_archive(source_dir, tar_path)
            res_tar = archive_ops.test_archive(tar_path)
            self.assertTrue(res_tar["valid"])


if __name__ == "__main__":
    unittest.main()
