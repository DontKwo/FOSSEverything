"""Unit tests for hash and checksum operations."""
import os
import tempfile
import unittest
from app.features.hash import ops as hash_ops


class HashOpsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, mode="wb")
        self.test_bytes = b"Hello, FOSSEverything Checksum Test!"
        self.tmp_file.write(self.test_bytes)
        self.tmp_file.close()

    def tearDown(self) -> None:
        if os.path.exists(self.tmp_file.name):
            os.remove(self.tmp_file.name)

    def test_hash_text(self) -> None:
        sha256 = hash_ops.hash_text("Hello World", "sha256")
        self.assertEqual(len(sha256), 64)
        md5 = hash_ops.hash_text("Hello World", "md5")
        self.assertEqual(len(md5), 32)

    def test_hash_file_sha256(self) -> None:
        digest = hash_ops.hash_file(self.tmp_file.name, "sha256")
        self.assertEqual(len(digest), 64)

    def test_verify_hash(self) -> None:
        actual_sha256 = hash_ops.hash_file(self.tmp_file.name, "sha256")
        self.assertTrue(hash_ops.verify_hash(self.tmp_file.name, actual_sha256, "sha256"))
        self.assertTrue(hash_ops.verify_hash(self.tmp_file.name, actual_sha256.upper(), "sha256"))
        self.assertFalse(hash_ops.verify_hash(self.tmp_file.name, "0000000000", "sha256"))

    def test_multi_hash_file(self) -> None:
        res = hash_ops.multi_hash_file(self.tmp_file.name, ["md5", "sha1", "sha256", "sha512"])
        self.assertIn("md5", res)
        self.assertIn("sha1", res)
        self.assertIn("sha256", res)
        self.assertIn("sha512", res)
        self.assertEqual(len(res["md5"]), 32)
        self.assertEqual(len(res["sha1"]), 40)
        self.assertEqual(len(res["sha256"]), 64)
        self.assertEqual(len(res["sha512"]), 128)

    def test_directory_hashing_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f1 = os.path.join(td, "a.txt")
            f2 = os.path.join(td, "sub", "b.txt")
            os.makedirs(os.path.dirname(f2), exist_ok=True)
            with open(f1, "w") as f:
                f.write("Alpha file content")
            with open(f2, "w") as f:
                f.write("Beta file content")

            # Hash tree
            res = hash_ops.hash_directory_tree(td, "sha256")
            self.assertEqual(res["total_files"], 2)
            self.assertEqual(len(res["files"]), 2)

            # Generate manifest
            manifest_path = os.path.join(td, "manifest.sha256")
            hash_ops.generate_checksum_manifest(td, manifest_path, "sha256")
            self.assertTrue(os.path.exists(manifest_path))

            # Verify manifest
            rep = hash_ops.verify_checksum_manifest(manifest_path, td)
            self.assertEqual(rep["total"], 2)
            self.assertEqual(rep["passed"], 2)
            self.assertEqual(rep["failed"], 0)
            self.assertEqual(rep["missing"], 0)

    def test_compare_files_and_hmac(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as other:
            other.write(b"Different payload")
            other_path = other.name

        try:
            self.assertTrue(hash_ops.compare_files(self.tmp_file.name, self.tmp_file.name, "sha256"))
            self.assertFalse(hash_ops.compare_files(self.tmp_file.name, other_path, "sha256"))

            digest = hash_ops.hmac_digest("Hello, FOSSEverything", "super-secret-key", "sha256")
            self.assertEqual(len(digest), 64)
            self.assertTrue(hash_ops.verify_hmac("Hello, FOSSEverything", "super-secret-key", digest, "sha256"))
            self.assertFalse(hash_ops.verify_hmac("Hello, FOSSEverything", "wrong-key", digest, "sha256"))
        finally:
            if os.path.exists(other_path):
                os.remove(other_path)


if __name__ == "__main__":
    unittest.main()
