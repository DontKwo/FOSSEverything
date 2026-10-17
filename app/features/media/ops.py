"""Core audio and video processing operations.

Powered by an offline, self-contained local FFmpeg engine via imageio-ffmpeg
and pure Python metadata libraries.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable

from PIL import Image
import imageio_ffmpeg
from tinytag import TinyTag

from app.features.image import ops as image_ops


def get_ffmpeg_path() -> str:
    """Return the path to the local FFmpeg binary."""
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    if exe and os.path.exists(exe):
        return exe

    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    raise RuntimeError("FFmpeg executable not found. Please install imageio-ffmpeg or add ffmpeg to PATH.")


def format_timestamp(seconds: float) -> str:
    """Convert float seconds into HH:MM:SS.mmm formatted string."""
    if seconds < 0:
        seconds = 0.0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"


def get_media_info(path: str) -> dict:
    """Extract comprehensive technical information and metadata from any media file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Media file not found: {path}")

    info = {
        "path": path,
        "filename": os.path.basename(path),
        "size_bytes": os.path.getsize(path),
        "duration_sec": 0.0,
        "duration_str": "00:00:00.000",
        "bitrate_kbps": 0,
        "format": os.path.splitext(path)[1].lower().lstrip("."),
        "has_video": False,
        "has_audio": False,
        "video_codec": None,
        "width": None,
        "height": None,
        "fps": None,
        "audio_codec": None,
        "sample_rate": None,
        "channels": None,
        "tags": {},
    }

    try:
        tag = TinyTag.get(path)
    except Exception:  # noqa: 10 (unsupported container for tinytag; ffmpeg probe below still runs)
        tag = None
    if tag is not None:
        if tag.duration:
            info["duration_sec"] = float(tag.duration)
            info["duration_str"] = format_timestamp(tag.duration)
        if tag.bitrate:
            info["bitrate_kbps"] = int(tag.bitrate)
        if tag.samplerate:
            info["sample_rate"] = int(tag.samplerate)
        if tag.channels:
            info["channels"] = int(tag.channels)
        if tag.title: info["tags"]["title"] = tag.title
        if tag.artist: info["tags"]["artist"] = tag.artist
        if tag.album: info["tags"]["album"] = tag.album
        if tag.year: info["tags"]["year"] = str(tag.year)
        if tag.genre: info["tags"]["genre"] = tag.genre

    # Use FFmpeg to get exact stream details
    try:
        ffmpeg = get_ffmpeg_path()
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", path],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stderr = proc.stderr

        # Duration match: Duration: 00:01:23.45, start: 0.000000, bitrate: 128 kb/s
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d*)", stderr)
        if dur_match and info["duration_sec"] == 0.0:
            h, m, s = float(dur_match.group(1)), float(dur_match.group(2)), float(dur_match.group(3))
            tot_sec = h * 3600 + m * 60 + s
            info["duration_sec"] = tot_sec
            info["duration_str"] = format_timestamp(tot_sec)

        br_match = re.search(r"bitrate:\s*(\d+)\s*kb/s", stderr)
        if br_match and info["bitrate_kbps"] == 0:
            info["bitrate_kbps"] = int(br_match.group(1))

        # Stream matches
        # Video: h264 (High), yuv420p, 1920x1080 [SAR 1:1 DAR 16:9], 29.97 fps
        for line in stderr.splitlines():
            if "Stream #" in line:
                if "Video:" in line:
                    info["has_video"] = True
                    # Codec
                    v_match = re.search(r"Video:\s*([a-zA-Z0-9_\-]+)", line)
                    if v_match:
                        info["video_codec"] = v_match.group(1)
                    # Resolution
                    res_match = re.search(r"(\d{2,5})x(\d{2,5})", line)
                    if res_match:
                        info["width"] = int(res_match.group(1))
                        info["height"] = int(res_match.group(2))
                    # FPS
                    fps_match = re.search(r"(\d+\.\d*)\s*fps", line)
                    if fps_match:
                        info["fps"] = float(fps_match.group(1))
                elif "Audio:" in line:
                    info["has_audio"] = True
                    a_match = re.search(r"Audio:\s*([a-zA-Z0-9_\-]+)", line)
                    if a_match:
                        info["audio_codec"] = a_match.group(1)
                    sr_match = re.search(r"(\d+)\s*Hz", line)
                    if sr_match and not info["sample_rate"]:
                        info["sample_rate"] = int(sr_match.group(1))
                    if "stereo" in line:
                        info["channels"] = 2
                    elif "mono" in line:
                        info["channels"] = 1
                    elif "5.1" in line:
                        info["channels"] = 6
    except Exception:  # noqa: 10 (keep tinytag-derived info on ffmpeg probe failure)
        pass

    return info


def transcribe_audio(input_path: str, language: str = "en", model: str = "tiny", progress_callback: Callable[[int, int], None] | None = None) -> dict:
    """Attempt offline transcription using a local Whisper backend when available.

    This keeps the feature local-first: if no Whisper runtime is installed, the
    function returns a structured status describing the missing offline model.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Media file not found: {input_path}")

    backends = []
    cli_candidates = ["whisper", "faster-whisper"]
    for candidate in cli_candidates:
        if shutil.which(candidate):
            backends.append(candidate)

    try:
        for module_name in ("whisper", "faster_whisper"):
            if importlib.util.find_spec(module_name):
                backends.append(module_name)
    except Exception:  # noqa: 10 (module detection failure should not block CLI-backend fallback)
        pass

    if not backends:
        return {
            "status": "not_available",
            "text": "",
            "segments": [],
            "language": language,
            "model": model,
            "warning": "No local Whisper runtime is installed; install a local whisper/faster-whisper backend to enable on-device speech transcription.",
            "available_backends": [],
        }

    temp_dir = os.path.join(os.path.dirname(os.path.abspath(input_path)), ".fosse_transcribe_tmp")
    os.makedirs(temp_dir, exist_ok=True)
    output_dir = os.path.join(temp_dir, "out")
    os.makedirs(output_dir, exist_ok=True)
    try:
        cmd = [shutil.which("whisper") or shutil.which("faster-whisper"), input_path, "--language", language, "--output_dir", output_dir, "--output_format", "json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)
        json_out = os.path.join(output_dir, os.path.splitext(os.path.basename(input_path))[0] + ".json")
        if os.path.exists(json_out):
            with open(json_out, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            text = str(payload.get("text", "")).strip()
            segments = [
                {"start": float(seg.get("start", 0.0)), "end": float(seg.get("end", 0.0)), "text": str(seg.get("text", "")).strip()}
                for seg in payload.get("segments", [])
            ]
            return {
                "status": "success",
                "text": text,
                "segments": segments,
                "language": language,
                "model": model,
                "available_backends": backends,
            }
        stderr = (proc.stderr or "").strip()
        return {
            "status": "error",
            "text": "",
            "segments": [],
            "language": language,
            "model": model,
            "warning": stderr or "Transcription backend returned no output.",
            "available_backends": backends,
        }
    finally:
        if os.path.isdir(temp_dir):
            for root, _, files in os.walk(temp_dir, topdown=False):
                for name in files:
                    try:
                        os.remove(os.path.join(root, name))
                    except OSError:  # noqa: 10 (cleanup best-effort; must not override a successful result)
                        pass
                try:
                    os.rmdir(root)
                except OSError:  # noqa: 10 (cleanup best-effort; must not override a successful result)
                    pass


def trim_media(
    input_path: str,
    output_path: str,
    start_time_sec: float = 0.0,
    end_time_sec: float | None = None,
    duration_sec: float | None = None,
    fast_copy: bool = False,
    progress_cb: Callable[[float], None] | None = None,
) -> str:
    """Trim audio/video with optional keyframe-copy (fast) or re-encode (accurate) mode."""
    ffmpeg = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    cmd = [ffmpeg, "-y", "-ss", f"{start_time_sec:.3f}"]

    if end_time_sec is not None and end_time_sec > start_time_sec:
        dur = end_time_sec - start_time_sec
        cmd.extend(["-t", f"{dur:.3f}"])
    elif duration_sec is not None and duration_sec > 0:
        cmd.extend(["-t", f"{duration_sec:.3f}"])

    cmd.extend(["-i", input_path])

    if fast_copy:
        cmd.extend(["-c", "copy"])
    else:
        # Re-encode for precise cuts
        ext = os.path.splitext(output_path)[1].lower()
        if ext in (".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"):
            cmd.extend(["-vn"])
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "22", "-c:a", "aac", "-b:a", "192k"])

    cmd.append(output_path)

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg trim failed:\n{res.stderr}")
    return output_path


def extract_audio(
    input_path: str,
    output_path: str,
    audio_format: str = "mp3",
    bitrate: str = "192k",
) -> str:
    """Extract the audio stream from a video into a standalone audio file."""
    ffmpeg = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    fmt = audio_format.lower().lstrip(".")
    cmd = [ffmpeg, "-y", "-i", input_path, "-vn"]

    if fmt == "mp3":
        cmd.extend(["-c:a", "libmp3lame", "-b:a", bitrate])
    elif fmt == "wav":
        cmd.extend(["-c:a", "pcm_s16le"])
    elif fmt in ("aac", "m4a"):
        cmd.extend(["-c:a", "aac", "-b:a", bitrate])
    elif fmt == "flac":
        cmd.extend(["-c:a", "flac"])
    elif fmt == "ogg":
        cmd.extend(["-c:a", "libvorbis", "-b:a", bitrate])
    else:
        cmd.extend(["-b:a", bitrate])

    cmd.append(output_path)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed:\n{res.stderr}")
    return output_path


def convert_media(
    input_path: str,
    output_path: str,
    target_format: str | None = None,
    crf: int = 23,
    scale: tuple[int, int] | None = None,
    mute: bool = False,
    video_codec: str | None = None,
    audio_codec: str | None = None,
) -> str:
    """Transcode a video or audio file to another format, container, or resolution."""
    ffmpeg = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    ext = os.path.splitext(output_path)[1].lower() if not target_format else f".{target_format.lower().lstrip('.')}"
    is_audio_target = ext in (".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a")

    cmd = [ffmpeg, "-y", "-i", input_path]

    if is_audio_target:
        cmd.append("-vn")
        if ext == ".mp3":
            cmd.extend(["-c:a", "libmp3lame", "-b:a", "192k"])
        elif ext == ".wav":
            cmd.extend(["-c:a", "pcm_s16le"])
        elif ext == ".flac":
            cmd.extend(["-c:a", "flac"])
        else:
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])
    else:
        # Video target
        v_codec = video_codec or "libx264"
        cmd.extend(["-c:v", v_codec, "-preset", "fast", "-crf", str(crf)])

        if scale is not None and len(scale) == 2:
            w, h = scale
            # Maintain aspect ratio with -2 for odd dimensions
            cmd.extend(["-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"])

        if mute:
            cmd.append("-an")
        else:
            a_codec = audio_codec or "aac"
            cmd.extend(["-c:a", a_codec, "-b:a", "192k"])

    cmd.append(output_path)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg conversion failed:\n{res.stderr}")
    return output_path


def mute_video(input_path: str, output_path: str) -> str:
    """Create a copy of the video with all audio tracks stripped."""
    ffmpeg = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    cmd = [ffmpeg, "-y", "-i", input_path, "-c:v", "copy", "-an", output_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        # Fallback to re-encoding if copy failed
        cmd = [ffmpeg, "-y", "-i", input_path, "-an", output_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg mute failed:\n{res.stderr}")
    return output_path


def extract_frame(
    input_path: str,
    output_path: str,
    timestamp_sec: float = 0.0,
) -> str:
    """Extract a single video frame at the specified timestamp as a PNG/JPG image."""
    ffmpeg = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    cmd = [
        ffmpeg, "-y",
        "-ss", f"{timestamp_sec:.3f}",
        "-i", input_path,
        "-vframes", "1",
        "-q:v", "2",
        output_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg frame extraction failed:\n{res.stderr}")
    return output_path


def compress_video(
    input_path: str,
    output_path: str,
    preset: str = "balanced",
    target_resolution: str | None = None,
) -> str:
    """Compress video using presets (discord/email 8MB, balanced 720p, high quality 1080p)."""
    crf_map = {
        "discord": 28,
        "small": 28,
        "balanced": 24,
        "quality": 20,
        "high": 18,
    }
    crf = crf_map.get(preset.lower(), 24)

    scale = None
    if target_resolution == "1080p":
        scale = (1920, 1080)
    elif target_resolution == "720p":
        scale = (1280, 720)
    elif target_resolution == "480p":
        scale = (854, 480)
    elif target_resolution == "360p":
        scale = (640, 360)

    return convert_media(input_path, output_path, crf=crf, scale=scale)


def compress_audio(
    input_path: str,
    output_path: str,
    bitrate: str = "128k",
) -> str:
    """Compress audio to a target bitrate (e.g. 128k, 96k, 64k)."""
    return extract_audio(input_path, output_path, audio_format="mp3", bitrate=bitrate)


def compress_media(
    input_path: str,
    output_path: str,
    preset: str = "balanced",
    kind: str | None = None,
    quality: int = 80,
    max_width: int | None = None,
    max_height: int | None = None,
    audio_bitrate: str = "128k",
) -> str:
    """Compress audio, video, or image media with a single local preset interface."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Media file not found: {input_path}")
    ext = os.path.splitext(input_path)[1].lower()
    detected_kind = kind.lower() if kind else ""
    if not detected_kind:
        if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff",
                   ".heic", ".heif", ".avif", ".svg", ".psd",
                   ".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw"):
            detected_kind = "image"
        elif ext in (".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"):
            detected_kind = "audio"
        else:
            detected_kind = "video"

    if detected_kind == "image":
        image = image_ops.load_image(input_path)
        if image.mode in ("RGBA", "LA", "P"):
            rgb = image.convert("RGB")
        else:
            rgb = image.copy()
        if max_width and max_height:
            rgb.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        out_ext = os.path.splitext(output_path)[1].lower() or ".jpg"
        if out_ext in (".png", ".bmp"):
            rgb.save(output_path, format=out_ext[1:].upper(), compress_well=True)
        else:
            rgb.save(output_path, format="JPEG", quality=max(1, min(100, quality)), compress_well=True)
        return output_path

    if detected_kind == "audio":
        return compress_audio(input_path, output_path, bitrate=audio_bitrate)

    return compress_video(input_path, output_path, preset=preset, target_resolution=None)


@dataclass
class BatchMediaItem:
    """Tracks one file's progress through a batch media operation."""
    input_path: str
    status: str = "pending"  # "pending", "done", "failed"
    error: str | None = None
    output_path: str | None = None


def _unique_output_path(output_dir: str, stem: str, ext: str) -> str:
    """Return a collision-free `output_dir/stem+ext` path, appending `_1`, `_2`, etc. if needed."""
    candidate = os.path.join(output_dir, f"{stem}{ext}")
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(output_dir, f"{stem}_{counter}{ext}")
        counter += 1
    return candidate


def _run_batch_media_op(
    items: list[BatchMediaItem],
    output_dir: str,
    ext_for: Callable[[str], str],
    op: Callable[[str, str], None],
    progress_cb: Callable[[int, int, str], None] | None,
) -> list[BatchMediaItem]:
    """Run `op(input_path, output_path)` for every item, recording per-item success/failure."""
    os.makedirs(output_dir, exist_ok=True)
    total = len(items)
    for idx, item in enumerate(items):
        filename = os.path.basename(item.input_path)
        try:
            stem = os.path.splitext(filename)[0]
            out_path = _unique_output_path(output_dir, stem, ext_for(item.input_path))
            op(item.input_path, out_path)
            item.status = "done"
            item.output_path = out_path
            item.error = None
        except Exception as exc:
            item.status = "failed"
            item.error = str(exc)
            item.output_path = None
        if progress_cb:
            progress_cb(idx + 1, total, filename)
    return items


def batch_convert_media(
    items: list[BatchMediaItem],
    output_dir: str,
    target_format: str,
    crf: int = 23,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> list[BatchMediaItem]:
    """Transcode multiple audio/video files to `target_format`, tracking per-item status."""
    ext = f".{target_format.lower().lstrip('.')}"
    return _run_batch_media_op(
        items, output_dir, lambda _path: ext,
        lambda inp, outp: convert_media(inp, outp, target_format=target_format, crf=crf),
        progress_cb,
    )


def batch_compress_media(
    items: list[BatchMediaItem],
    output_dir: str,
    preset: str = "balanced",
    audio_bitrate: str = "128k",
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> list[BatchMediaItem]:
    """Compress multiple audio/video files with a shared preset, tracking per-item status."""
    return _run_batch_media_op(
        items, output_dir, lambda path: os.path.splitext(path)[1].lower(),
        lambda inp, outp: compress_media(inp, outp, preset=preset, audio_bitrate=audio_bitrate),
        progress_cb,
    )


def batch_extract_audio(
    items: list[BatchMediaItem],
    output_dir: str,
    audio_format: str = "mp3",
    bitrate: str = "192k",
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> list[BatchMediaItem]:
    """Extract the audio track from multiple video files, tracking per-item status."""
    ext = f".{audio_format.lower().lstrip('.')}"
    return _run_batch_media_op(
        items, output_dir, lambda _path: ext,
        lambda inp, outp: extract_audio(inp, outp, audio_format=audio_format, bitrate=bitrate),
        progress_cb,
    )


def parse_subtitle_cues(raw_text: str) -> list[dict]:
    """Parse a transcript or cue list into start/end/text entries."""
    text = (raw_text or "").strip()
    if not text:
        return []
    cues = []
    for block in re.split(r"\n\s*\n+", text):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        if "-->" in lines[0]:
            # Format: 00:00:00,000 --> 00:00:03,000
            timing = lines[0]
            body = " ".join(lines[1:])
            left, right = [part.strip() for part in timing.split("-->", 1)]
            if body:
                cues.append({"start": left, "end": right, "text": body})
            continue
        if len(lines) >= 2 and "|" in lines[0]:
            timing = lines[0]
            body = lines[1]
            left, right = [part.strip() for part in timing.split("|", 1)]
            cues.append({"start": left, "end": right, "text": body})
            continue
        if len(lines) >= 2:
            timing = lines[0]
            body = " ".join(lines[1:])
            if "-" in timing:
                left, right = [part.strip() for part in timing.split("-", 1)]
                cues.append({"start": left, "end": right, "text": body})
    return cues


def generate_subtitle_file(cues: list[dict] | str, output_path: str, subtitle_format: str = "srt") -> str:
    """Write a local .srt or .vtt subtitle file from cue dictionaries or raw transcript text."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    fmt = (subtitle_format or "srt").lower().lstrip(".")
    if isinstance(cues, str):
        cue_list = parse_subtitle_cues(cues)
    else:
        cue_list = list(cues or [])

    if not cue_list:
        raise ValueError("No valid subtitle cues were found. Use timecoded entries like '00:00:00,000 --> 00:00:02,000'.")

    if fmt == "vtt":
        lines = ["WEBVTT", ""]
        for idx, cue in enumerate(cue_list, start=1):
            start = cue.get("start", "00:00:00.000")
            end = cue.get("end", "00:00:00.000")
            start = start.replace(",", ".")
            end = end.replace(",", ".")
            if "-->" not in start and "-->" not in end:
                lines.append(f"{idx}")
                lines.append(f"{start} --> {end}")
                lines.append(str(cue.get("text", "")).strip())
                lines.append("")
            else:
                lines.append(str(cue.get("text", "")).strip())
                lines.append("")
        output = "\n".join(lines).strip() + "\n"
    else:
        blocks = []
        for idx, cue in enumerate(cue_list, start=1):
            start = str(cue.get("start", "00:00:00,000"))
            end = str(cue.get("end", "00:00:00,000"))
            start = start.replace(".", ",")
            end = end.replace(".", ",")
            text = str(cue.get("text", "")).strip()
            blocks.append(f"{idx}\n{start} --> {end}\n{text}")
        output = "\n\n".join(blocks) + "\n"

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(output)
    return output_path


def generate_subtitles_from_transcription(transcription: dict, output_path: str, subtitle_format: str = "srt") -> str:
    """Write an .srt or .vtt file from transcribe_audio()'s timed segments."""
    segments = transcription.get("segments", [])
    if not segments:
        raise ValueError("This transcription has no timed segments to export as subtitles.")

    cues = []
    for seg in segments:
        start = format_timestamp(float(seg.get("start", 0.0))).replace(".", ",")
        end = format_timestamp(float(seg.get("end", 0.0))).replace(".", ",")
        cues.append({"start": start, "end": end, "text": seg.get("text", "")})

    return generate_subtitle_file(cues, output_path, subtitle_format=subtitle_format)


def compose_media_with_audio(
    video_input: str,
    output_path: str,
    audio_input: str,
    *,
    volume: float = 1.0,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
    trim_start: float = 0.0,
    trim_end: float | None = None,
    scale: tuple[int, int] | None = None,
) -> str:
    """Overlay a source audio track onto a video, with optional fades and simple scaling."""
    if not os.path.exists(video_input):
        raise FileNotFoundError(f"Video file not found: {video_input}")
    if not os.path.exists(audio_input):
        raise FileNotFoundError(f"Audio file not found: {audio_input}")

    ffmpeg = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    temp_video = output_path + ".trim_video.mp4"
    temp_audio = output_path + ".trim_audio.mp3"
    try:
        if trim_start > 0 or trim_end is not None:
            trim_media(video_input, temp_video, start_time_sec=trim_start, end_time_sec=trim_end or get_media_info(video_input)["duration_sec"], fast_copy=False)
            trim_media(audio_input, temp_audio, start_time_sec=trim_start, end_time_sec=trim_end or get_media_info(audio_input)["duration_sec"], fast_copy=False)
        else:
            temp_video = video_input
            temp_audio = audio_input

        cmd = [ffmpeg, "-y", "-i", temp_video, "-i", temp_audio]
        volume_value = max(0.0, min(3.0, volume))
        filter_parts = [f"[1:a]volume={volume_value}" ]
        if fade_in > 0:
            filter_parts.append(f"afade=t=in:st=0:d={fade_in}")
        if fade_out > 0:
            audio_duration = get_media_info(temp_audio).get("duration_sec", 0.0)
            if audio_duration > fade_out:
                filter_parts.append(f"afade=t=out:st={max(0.0, audio_duration - fade_out)}:d={fade_out}")
        filter_expr = ",".join(filter_parts)
        filter_with_label = f"{filter_expr}[aout]"
        cmd += ["-filter_complex", filter_with_label, "-map", "0:v:0", "-map", "[aout]", "-shortest", "-c:v", "libx264", "-c:a", "aac", output_path]
        if scale is not None:
            cmd = [ffmpeg, "-y", "-i", temp_video, "-i", temp_audio, "-filter_complex", f"[0:v]scale={scale[0]}:{scale[1]}[v];[1:a]volume={volume_value}{f',afade=t=in:st=0:d={fade_in}' if fade_in > 0 else ''}{f',afade=t=out:st={max(0.0, get_media_info(temp_audio).get('duration_sec', 0.0) - fade_out)}:d={fade_out}' if fade_out > 0 else ''}[aout]", "-map", "[v]", "-map", "[aout]", "-shortest", "-c:v", "libx264", "-c:a", "aac", output_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg composition failed:\n{res.stderr}")
        return output_path
    finally:
        if os.path.exists(temp_video) and temp_video != video_input:
            os.remove(temp_video)
        if os.path.exists(temp_audio) and temp_audio != audio_input:
            os.remove(temp_audio)


def _mix_audio_tracks(video_input: str, output_path: str, audio_tracks: list[dict]) -> str:
    """Mix one or more audio overlay tracks onto a video's own audio via ffmpeg's amix filter.

    Each track dict is {"path": str, "volume": float, "fade_in": float, "fade_out": float,
    "start_offset": float}. Tracks are individually volume/fade-adjusted and delayed to their
    start_offset (via adelay) before being combined into a single mixed-down audio stream.
    """
    ffmpeg = get_ffmpeg_path()
    for track in audio_tracks:
        if not os.path.exists(track["path"]):
            raise FileNotFoundError(f"Audio track not found: {track['path']}")

    cmd = [ffmpeg, "-y", "-i", video_input]
    for track in audio_tracks:
        cmd += ["-i", track["path"]]

    filter_parts = []
    mix_inputs = []
    if get_media_info(video_input).get("has_audio", False):
        mix_inputs.append("[0:a]")

    for idx, track in enumerate(audio_tracks, start=1):
        volume = max(0.0, min(3.0, float(track.get("volume", 1.0))))
        fade_in = float(track.get("fade_in", 0.0))
        fade_out = float(track.get("fade_out", 0.0))
        offset = max(0.0, float(track.get("start_offset", 0.0)))
        chain = [f"volume={volume}"]
        if fade_in > 0:
            chain.append(f"afade=t=in:st=0:d={fade_in}")
        if fade_out > 0:
            track_duration = get_media_info(track["path"]).get("duration_sec", 0.0)
            if track_duration > fade_out:
                chain.append(f"afade=t=out:st={max(0.0, track_duration - fade_out)}:d={fade_out}")
        if offset > 0:
            delay_ms = int(offset * 1000)
            chain.append(f"adelay={delay_ms}|{delay_ms}")
        label = f"a{idx}"
        filter_parts.append(f"[{idx}:a]" + ",".join(chain) + f"[{label}]")
        mix_inputs.append(f"[{label}]")

    filter_parts.append("".join(mix_inputs) + f"amix=inputs={len(mix_inputs)}:duration=longest:dropout_transition=0[aout]")
    filter_complex = ";".join(filter_parts)

    cmd += ["-filter_complex", filter_complex, "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", output_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg multi-track audio mix failed:\n{res.stderr}")
    return output_path


def compose_timeline(
    clips: list[dict],
    output_path: str,
    *,
    export_format: str = "mp4",
    target_width: int | None = None,
    target_height: int | None = None,
    fps: int | None = None,
    crossfade_duration: float = 0.0,
    audio_tracks: list[dict] | None = None,
) -> str:
    """Concatenate an ordered sequence of trimmed/cropped/faded clips into one MP4 or GIF export.

    Each clip is a dict: {"input": path, "trim_start": float, "trim_end": float|None,
    "crop": (x, y, w, h)|None, "fade_in": float, "fade_out": float}. If crossfade_duration > 0,
    consecutive clips are xfade-joined (chained pairwise) instead of hard-cut concatenated.
    `audio_tracks` is a list of dicts accepted by `_mix_audio_tracks` for multi-track mixing.
    """
    if not clips:
        raise ValueError("compose_timeline requires at least one clip.")
    ffmpeg = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    inputs: list[str] = []
    filter_segments: list[str] = []
    concat_labels: list[str] = []
    clip_durations: list[float] = []

    for idx, clip in enumerate(clips):
        clip_input = clip["input"]
        if not os.path.exists(clip_input):
            raise FileNotFoundError(f"Clip not found: {clip_input}")
        inputs += ["-i", clip_input]

        trim_start = float(clip.get("trim_start", 0.0))
        trim_end = clip.get("trim_end")
        if trim_end is None:
            trim_end = get_media_info(clip_input)["duration_sec"]
        trim_end = float(trim_end)
        clip_duration = max(0.0, trim_end - trim_start)
        clip_durations.append(clip_duration)

        parts = [f"trim=start={trim_start}:end={trim_end}", "setpts=PTS-STARTPTS"]

        crop = clip.get("crop")
        if crop:
            cx, cy, cw, ch = crop
            parts.append(f"crop={cw}:{ch}:{cx}:{cy}")

        if target_width and target_height:
            parts.append(f"scale={target_width}:{target_height}")
        parts.append("setsar=1")
        parts.append(f"fps={fps or 24}")

        fade_in = float(clip.get("fade_in", 0.0))
        if fade_in > 0:
            parts.append(f"fade=t=in:st=0:d={fade_in}")

        fade_out = float(clip.get("fade_out", 0.0))
        if fade_out > 0 and clip_duration > fade_out:
            parts.append(f"fade=t=out:st={clip_duration - fade_out}:d={fade_out}")

        label = f"v{idx}"
        filter_segments.append(f"[{idx}:v]" + ",".join(parts) + f"[{label}]")
        concat_labels.append(f"[{label}]")

    if crossfade_duration > 0 and len(clips) > 1:
        cum_duration = clip_durations[0]
        current_label = "v0"
        for idx in range(1, len(clips)):
            xf_duration = min(crossfade_duration, clip_durations[idx - 1], clip_durations[idx])
            offset = max(0.0, cum_duration - xf_duration)
            out_label = f"xf{idx}"
            filter_segments.append(
                f"[{current_label}][v{idx}]xfade=transition=fade:duration={xf_duration}:offset={offset}[{out_label}]"
            )
            cum_duration = cum_duration + clip_durations[idx] - xf_duration
            current_label = out_label
        final_label = current_label
    else:
        concat_expr = "".join(concat_labels) + f"concat=n={len(clips)}:v=1:a=0[vout]"
        filter_segments.append(concat_expr)
        final_label = "vout"

    filter_complex = ";".join(filter_segments)

    is_gif = export_format.lower().lstrip(".") == "gif"
    concat_output = output_path + ".timeline.mp4" if is_gif else output_path

    cmd = [ffmpeg, "-y", *inputs, "-filter_complex", filter_complex, "-map", f"[{final_label}]"]
    if fps:
        cmd += ["-r", str(fps)]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", concat_output]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg timeline composition failed:\n{res.stderr}")

    tracks = audio_tracks or []

    try:
        if is_gif:
            gif_fps = fps or 12
            palette = concat_output + ".palette.png"
            try:
                gen_cmd = [ffmpeg, "-y", "-i", concat_output, "-vf", f"fps={gif_fps},split[a][b];[a]palettegen[p];[b][p]paletteuse", output_path]
                res2 = subprocess.run(gen_cmd, capture_output=True, text=True)
                if res2.returncode != 0:
                    raise RuntimeError(f"FFmpeg GIF export failed:\n{res2.stderr}")
            finally:
                if os.path.exists(palette):
                    os.remove(palette)
        elif tracks:
            temp_video_out = output_path + ".novideoaudio.mp4"
            os.replace(output_path, temp_video_out)
            _mix_audio_tracks(temp_video_out, output_path, tracks)
    finally:
        if is_gif and os.path.exists(concat_output):
            os.remove(concat_output)
        if not is_gif and tracks:
            temp_video_out = output_path + ".novideoaudio.mp4"
            if os.path.exists(temp_video_out):
                os.remove(temp_video_out)

    return output_path


def extract_subtitles(input_path: str, output_path: str, stream_index: int = 0) -> str:
    """Extract the first subtitle stream from a video file into an SRT file."""
    ffmpeg = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cmd = [ffmpeg, "-y", "-i", input_path, "-map", f"0:s:{stream_index}", "-c:s", "srt", output_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg subtitle extraction failed:\n{res.stderr}")
    return output_path


def burn_subtitles(input_path: str, output_path: str, subtitle_file: str, font_size: int = 24) -> str:
    """Render a subtitle file onto a video using FFmpeg's subtitles filter."""
    ffmpeg = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    subtitle_arg = subtitle_file.replace("\\", "/")
    if len(subtitle_arg) >= 2 and subtitle_arg[1] == ":":
        subtitle_arg = subtitle_arg[:1] + "\\:" + subtitle_arg[2:]

    filter_expr = f"subtitles='{subtitle_arg}'"

    cmd = [ffmpeg, "-y", "-i", input_path, "-vf", filter_expr, output_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg subtitle burn-in failed:\n{res.stderr}")
    return output_path
