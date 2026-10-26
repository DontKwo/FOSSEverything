"""Regression tests for local image and PDF metadata handling."""
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pymupdf as fitz
from PIL import Image

from app.features.media import ops as media_ops
from app.features.metadata import ops as metadata_ops


class MetadataOperationsTests(unittest.TestCase):
    def test_edit_and_strip_image_exif(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.jpg"
            exif = Image.Exif()
            exif[315] = "Original artist"  # Artist
            Image.new("RGB", (4, 4), "red").save(source, exif=exif.tobytes())

            edited = Path(directory) / "edited.jpg"
            metadata_ops.save_edited_metadata(str(source), str(edited), {"Artist": "FOSSEverything user"})
            self.assertEqual(metadata_ops.inspect_metadata(str(edited))["Artist"], "FOSSEverything user")

            clean = Path(directory) / "clean.jpg"
            metadata_ops.strip_metadata(str(edited), str(clean))
            self.assertNotIn("Artist", metadata_ops.inspect_metadata(str(clean)))

    def test_edit_and_strip_pdf_metadata(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            document = fitz.open()
            document.new_page()
            document.set_metadata({"title": "Original title", "author": "Original author"})
            document.save(source)
            document.close()

            edited = Path(directory) / "edited.pdf"
            metadata_ops.save_edited_metadata(str(source), str(edited), {"title": "Changed title"})
            self.assertEqual(metadata_ops.inspect_metadata(str(edited))["title"], "Changed title")

            clean = Path(directory) / "clean.pdf"
            metadata_ops.strip_metadata(str(edited), str(clean))
            self.assertEqual(metadata_ops.inspect_metadata(str(clean))["title"], "")

    def test_edit_and_strip_audio_metadata(self) -> None:
        with TemporaryDirectory() as directory:
            ffmpeg = media_ops.get_ffmpeg_path()
            source = Path(directory) / "source.mp3"
            subprocess.run([
                ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-c:a", "libmp3lame", str(source)
            ], capture_output=True, check=True)

            edited = Path(directory) / "edited.mp3"
            metadata_ops.save_edited_metadata(str(source), str(edited), {"title": "Song Title", "artist": "Band Name"})
            meta = metadata_ops.inspect_metadata(str(edited))
            self.assertIn("Title", meta)
            self.assertEqual(meta["Title"], "Song Title")

            clean = Path(directory) / "clean.mp3"
            metadata_ops.strip_metadata(str(edited), str(clean))
            meta_clean = metadata_ops.inspect_metadata(str(clean))
            self.assertNotIn("Title", meta_clean)

    def test_inspect_video_metadata(self) -> None:
        with TemporaryDirectory() as directory:
            ffmpeg = media_ops.get_ffmpeg_path()
            source = Path(directory) / "source.mp4"
            subprocess.run([
                ffmpeg, "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=10",
                "-c:v", "libx264", str(source)
            ], capture_output=True, check=True)

            meta = metadata_ops.inspect_metadata(str(source))
            self.assertEqual(meta["Kind"], "Video")
            self.assertEqual(meta["Video dimensions"], "320 × 240")

    def test_bulk_metadata_updates_and_diff_report(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            document = fitz.open()
            document.new_page()
            document.set_metadata({"title": "Original title", "author": "Original author"})
            document.save(source)
            document.close()

            updated = Path(directory) / "updated.pdf"
            metadata_ops.bulk_update_metadata(str(source), str(updated), {"title": "Changed title", "author": "New author"})
            diff = metadata_ops.compare_metadata(str(source), str(updated))
            self.assertTrue(diff["changed"])
            self.assertEqual(metadata_ops.inspect_metadata(str(updated))["title"], "Changed title")
            self.assertIn("title", metadata_ops.metadata_support_report(str(updated))["editable_fields"])

    def test_gps_preview_and_camera_presets(self) -> None:
        preview = metadata_ops.gps_preview_for_metadata({
            "GPSLatitude": "52.52",
            "GPSLatitudeRef": "N",
            "GPSLongitude": "13.405",
            "GPSLongitudeRef": "E",
        })
        self.assertIsNotNone(preview)
        self.assertIn("maps_url", preview)
        self.assertIn("travel", metadata_ops.camera_field_presets())

    def test_remove_selected_field_and_support_matrix(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.jpg"
            exif = Image.Exif()
            exif[315] = "Author Name"
            Image.new("RGB", (8, 8), "blue").save(source, exif=exif.tobytes())

            output = Path(directory) / "selected_remove.jpg"
            metadata_ops.remove_metadata_fields(str(source), str(output), ["Artist"])
            meta = metadata_ops.inspect_metadata(str(output))
            self.assertEqual(meta.get("Artist", ""), "")

            support = metadata_ops.metadata_support_report(str(source))
            self.assertTrue(support["supported"])
            self.assertTrue(support["removal_caveats"])

    def test_export_metadata_to_json(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            document = fitz.open()
            document.new_page()
            document.set_metadata({"title": "Export Test", "author": "Tester"})
            document.save(source)
            document.close()

            out_json = Path(directory) / "meta.json"
            metadata_ops.export_metadata(str(source), str(out_json))
            self.assertTrue(out_json.exists())
            with open(out_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data.get("title"), "Export Test")


if __name__ == "__main__":
    unittest.main()

