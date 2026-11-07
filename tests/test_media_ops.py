"""Unit tests for media_ops module."""
import os
import subprocess
import unittest
from app.features.media import ops as media_ops
from tests.test_support import TempDirTestCase


class TestMediaOps(TempDirTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.ffmpeg = media_ops.get_ffmpeg_path()

        # Generate a synthetic 2-second test video with audio track
        self.test_video = os.path.join(self.work_dir, "test_source.mp4")
        cmd = [
            self.ffmpeg, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:v", "libx264", "-c:a", "aac",
            self.test_video
        ]
        subprocess.run(cmd, capture_output=True, check=True)

    def test_get_media_info(self) -> None:
        info = media_ops.get_media_info(self.test_video)
        self.assertTrue(info["has_video"])
        self.assertTrue(info["has_audio"])
        self.assertAlmostEqual(info["duration_sec"], 2.0, places=1)
        self.assertEqual(info["width"], 320)
        self.assertEqual(info["height"], 240)

    def test_trim_media(self) -> None:
        out = os.path.join(self.work_dir, "trimmed.mp4")
        media_ops.trim_media(self.test_video, out, start_time_sec=0.5, end_time_sec=1.5)
        self.assertTrue(os.path.exists(out))
        info = media_ops.get_media_info(out)
        self.assertAlmostEqual(info["duration_sec"], 1.0, places=1)

    def test_extract_audio(self) -> None:
        out = os.path.join(self.work_dir, "audio.mp3")
        media_ops.extract_audio(self.test_video, out, audio_format="mp3")
        self.assertTrue(os.path.exists(out))
        info = media_ops.get_media_info(out)
        self.assertTrue(info["has_audio"])
        self.assertFalse(info["has_video"])

    def test_convert_media(self) -> None:
        out = os.path.join(self.work_dir, "converted.mkv")
        media_ops.convert_media(self.test_video, out, target_format="mkv")
        self.assertTrue(os.path.exists(out))
        info = media_ops.get_media_info(out)
        self.assertTrue(info["has_video"])

    def test_mute_video(self) -> None:
        out = os.path.join(self.work_dir, "muted.mp4")
        media_ops.mute_video(self.test_video, out)
        self.assertTrue(os.path.exists(out))
        info = media_ops.get_media_info(out)
        self.assertTrue(info["has_video"])
        self.assertFalse(info["has_audio"])

    def test_extract_frame(self) -> None:
        out = os.path.join(self.work_dir, "frame.png")
        media_ops.extract_frame(self.test_video, out, timestamp_sec=0.5)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 0)

    def test_compress_video(self) -> None:
        out = os.path.join(self.work_dir, "compressed.mp4")
        media_ops.compress_video(self.test_video, out, preset="discord", target_resolution="480p")
        self.assertTrue(os.path.exists(out))

    def test_extract_and_burn_subtitles(self) -> None:
        subtitle_path = os.path.join(self.work_dir, "captions.srt")
        with open(subtitle_path, "w", encoding="utf-8") as f:
            f.write("1\n00:00:00,000 --> 00:00:01,000\nHello world\n")

        video_with_subs = os.path.join(self.work_dir, "with_subs.mp4")
        ffmpeg = media_ops.get_ffmpeg_path()
        cmd = [
            ffmpeg, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-f", "srt", "-i", subtitle_path,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-c:s", "mov_text",
            video_with_subs,
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        extracted_sub = os.path.join(self.work_dir, "extracted.srt")
        media_ops.extract_subtitles(video_with_subs, extracted_sub)
        self.assertTrue(os.path.exists(extracted_sub))

        burned = os.path.join(self.work_dir, "burned.mp4")
        media_ops.burn_subtitles(video_with_subs, burned, subtitle_path)
        self.assertTrue(os.path.exists(burned))

    def test_generate_subtitle_file_rejects_empty_cues(self) -> None:
        out = os.path.join(self.work_dir, "invalid_subtitles.srt")
        with self.assertRaisesRegex(ValueError, "No valid subtitle cues"):
            media_ops.generate_subtitle_file("hello world without timing", out)
        self.assertFalse(os.path.exists(out))

    def test_transcribe_audio_reports_local_backend_status(self) -> None:
        result = media_ops.transcribe_audio(self.test_video, language="en")
        self.assertIn("status", result)
        self.assertIn("language", result)
        self.assertIn(result["status"], {"success", "error", "not_available"})


if __name__ == "__main__":
    unittest.main()
