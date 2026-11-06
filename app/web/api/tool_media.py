import base64
import io
import os
from pathlib import Path
from typing import Any

from app.features.media.ops import (
    BatchMediaItem,
    batch_compress_media,
    batch_convert_media,
    batch_extract_audio,
    change_playback_speed,
    compose_media_with_audio,
    compose_timeline,
    compress_media,
    convert_media,
    extract_audio,
    extract_frame,
    format_timestamp,
    generate_subtitles_from_transcription,
    get_media_info,
    mute_video,
    parse_subtitle_cues,
    reverse_media,
    transcribe_audio,
    trim_media,
    video_to_gif,
)
from app.features.media.stream_server import MEDIA_EXTENSIONS, register_media_file
from app.web.api.result import api_method, fail, ok, require


class MediaApiMixin:
    @api_method
    def media_get_info(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract audio and video stream container metadata and duration.
        require(params, "file_path")
        file_path = str(params["file_path"])
        info = get_media_info(file_path)
        dur = float(info.get("duration_sec", info.get("duration", 0.0)))
        formatted_dur = format_timestamp(dur)
        return ok(info=info, duration_formatted=formatted_dur, duration_sec=dur, file_path=file_path)

    @api_method
    def media_info(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for querying media info.
        return self.media_get_info(params)

    @api_method
    def media_get_file_url(self, params: dict[str, Any]) -> dict[str, Any]:
        # Register a local media file and return its loopback HTTP streaming URL.
        require(params, "file_path")
        file_path = Path(str(params["file_path"])).resolve()
        if not file_path.is_file():
            return fail(f"Media file not found: {file_path}", code="FileNotFound")
        if file_path.suffix.lower() not in MEDIA_EXTENSIONS:
            return fail(f"Unsupported media type: {file_path.suffix or 'none'}", code="UnsupportedType")
        return ok(url=register_media_file(str(file_path)), file_path=str(file_path))

    @api_method
    def media_trim(self, params: dict[str, Any]) -> dict[str, Any]:
        # Trim audio or video between start and end timestamps.
        require(params, "input_path", "output_path", "start_time", "end_time")
        in_p = str(params["input_path"])
        out_p = str(params["output_path"])
        start = float(params["start_time"])
        end = float(params["end_time"])
        fast = bool(params.get("fast_copy", True))
        res_p = trim_media(in_p, out_p, start_time_sec=start, end_time_sec=end, fast_copy=fast)
        return ok(output_path=res_p)

    @api_method
    def media_extract_audio(self, params: dict[str, Any]) -> dict[str, Any]:
        # Demux and export audio track from video file.
        require(params, "input_path", "output_path")
        in_p = str(params["input_path"])
        out_p = str(params["output_path"])
        bitrate = str(params.get("bitrate", "192k"))
        fmt = str(params.get("audio_format", "mp3"))
        res_p = extract_audio(in_p, out_p, audio_format=fmt, bitrate=bitrate)
        return ok(output_path=res_p)

    @api_method
    def media_convert(self, params: dict[str, Any]) -> dict[str, Any]:
        # Transcode video or audio to target container format.
        require(params, "input_path", "output_path")
        in_p = str(params["input_path"])
        out_p = str(params["output_path"])
        vcodec = params.get("video_codec")
        acodec = params.get("audio_codec")
        res_p = convert_media(in_p, out_p, video_codec=vcodec, audio_codec=acodec)
        return ok(output_path=res_p)

    @api_method
    def media_compress(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compress video to meet target file size limit.
        in_p = str(params.get("input_path") or params.get("file_path") or "")
        if not in_p:
            raise ValueError("Parameter input_path or file_path is required")
        out_p = str(params.get("output_path") or Path(in_p).with_stem(Path(in_p).stem + "_compressed"))
        raw_preset = str(params.get("preset", "balanced")).lower()
        if raw_preset in ("high", "high_quality", "best", "light"):
            preset = "high_quality"
        elif raw_preset in ("low", "small_file", "maximum", "small"):
            preset = "small_file"
        else:
            preset = "balanced"
        original_bytes = os.path.getsize(in_p) if os.path.exists(in_p) else 0
        res_p = compress_media(in_p, out_p, preset=preset)
        compressed_bytes = os.path.getsize(res_p) if os.path.exists(res_p) else 0
        return ok(output_path=res_p, original_bytes=original_bytes, compressed_bytes=compressed_bytes)

    @api_method
    def media_mute_video(self, params: dict[str, Any]) -> dict[str, Any]:
        # Strip audio stream from video container without re-encoding video track.
        require(params, "input_path", "output_path")
        in_p = str(params["input_path"])
        out_p = str(params["output_path"])
        res_p = mute_video(in_p, out_p)
        return ok(output_path=res_p)

    @api_method
    def media_mute(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for muting video track.
        return self.media_mute_video(params)

    @api_method
    def media_extract_frame(self, params: dict[str, Any]) -> dict[str, Any]:
        # Capture single still video frame at timestamp as image.
        require(params, "input_path", "timestamp")
        in_p = str(params["input_path"])
        ts = float(params["timestamp"])
        out_p = params.get("output_path")
        if not out_p:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                out_p = temp_file.name
        res_p = extract_frame(in_p, str(out_p), timestamp_sec=ts)
        from PIL import Image
        with Image.open(res_p) as img:
            width, height = img.size
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
        data_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return ok(data_url=f"data:image/jpeg;base64,{data_b64}", width=width, height=height, output_path=res_p)

    @api_method
    def media_capture_frame(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for frame capture.
        return self.media_extract_frame(params)

    @api_method
    def media_speed_reverse(self, params: dict[str, Any]) -> dict[str, Any]:
        # Change playback speed or reverse audio/video.
        require(params, "input_path", "output_path")
        in_p = str(params["input_path"])
        out_p = str(params["output_path"])
        speed = float(params.get("speed_factor", 1.0))
        do_reverse = bool(params.get("reverse", False))

        if do_reverse:
            if speed != 1.0:
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=Path(out_p).suffix, delete=False) as temp_file:
                    tmp_p = temp_file.name
                try:
                    change_playback_speed(in_p, tmp_p, speed_factor=speed)
                    res_p = reverse_media(tmp_p, out_p)
                finally:
                    if os.path.exists(tmp_p):
                        os.remove(tmp_p)
            else:
                res_p = reverse_media(in_p, out_p)
        else:
            res_p = change_playback_speed(in_p, out_p, speed_factor=speed)

        return ok(output_path=res_p)

    @api_method
    def media_video_to_gif(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert video clip segment to optimized animated GIF.
        require(params, "input_path", "output_path")
        in_p = str(params["input_path"])
        out_p = str(params["output_path"])
        start = float(params.get("start_time", 0.0))
        dur_val = params.get("duration")
        dur = float(dur_val) if dur_val is not None else None
        fps = int(params.get("fps", 15))
        width = int(params.get("width", 480))
        res_p = video_to_gif(in_p, out_p, start_time=start, duration=dur, fps=fps, width=width)
        return ok(output_path=res_p)

    @api_method
    def media_transcribe(self, params: dict[str, Any]) -> dict[str, Any]:
        # Transcribe audio track speech to subtitle file (SRT or VTT).
        require(params, "input_path")
        in_p = str(params["input_path"])
        lang = str(params.get("language", "en"))
        res_dict = transcribe_audio(in_p, language=lang)
        segments = res_dict.get("segments", [])
        out_p = params.get("output_path")
        if out_p:
            fmt = str(params.get("subtitle_format", "srt")).lower()
            if fmt == "txt" or str(out_p).lower().endswith(".txt"):
                os.makedirs(os.path.dirname(os.path.abspath(str(out_p))), exist_ok=True)
                with open(str(out_p), "w", encoding="utf-8") as f:
                    f.write(res_dict.get("text", ""))
            elif segments:
                generate_subtitles_from_transcription(res_dict, str(out_p), subtitle_format=fmt)
        parsed = parse_subtitle_cues(res_dict.get("text", "")) if not segments else segments
        return ok(
            text=res_dict.get("text", ""),
            segments=segments,
            count=len(segments),
            cues=parsed,
            status=res_dict.get("status", "success"),
            warning=res_dict.get("warning", ""),
            output_path=out_p,
        )

    @api_method
    def media_compose_audio(self, params: dict[str, Any]) -> dict[str, Any]:
        # Combine video stream with external audio track.
        require(params, "video_path", "audio_path", "output_path")
        v_p = str(params["video_path"])
        a_p = str(params["audio_path"])
        out_p = str(params["output_path"])
        res_p = compose_media_with_audio(video_input=v_p, output_path=out_p, audio_input=a_p)
        return ok(output_path=res_p)

    @api_method
    def media_compose_timeline(self, params: dict[str, Any]) -> dict[str, Any]:
        # Compose multi-clip sequence timeline into single output file.
        require(params, "clips", "output_path")
        clips = list(params["clips"])
        out_p = str(params["output_path"])
        res_p = compose_timeline(clips, out_p)
        return ok(output_path=res_p)

    @api_method
    def media_batch_operations(self, params: dict[str, Any]) -> dict[str, Any]:
        # Batch transcode, compress, or extract audio from media files.
        require(params, "items", "operation", "output_dir")
        op = str(params["operation"]).lower()
        out_dir = str(params["output_dir"])
        raw_items = list(params["items"])
        items = [
            BatchMediaItem(
                input_path=str(it.get("input_path") or it.get("source_path") or it),
            )
            for it in raw_items
        ]
        if op == "convert":
            tgt = str(params.get("target_format", "mp4"))
            crf = int(params.get("crf", 23))
            results = batch_convert_media(items, out_dir, target_format=tgt, crf=crf)
        elif op == "compress":
            preset = str(params.get("preset", "balanced"))
            results = batch_compress_media(items, out_dir, preset=preset)
        elif op == "extract_audio":
            fmt = str(params.get("audio_format", "mp3"))
            bitrate = str(params.get("bitrate", "192k"))
            results = batch_extract_audio(items, out_dir, audio_format=fmt, bitrate=bitrate)
        else:
            return fail(f"Unsupported media batch op: {op}", code="InvalidOperation")
        res_dicts = [
            {"input_path": it.input_path, "status": it.status, "output_path": it.output_path, "error": it.error}
            for it in results
        ]
        return ok(results=res_dicts)
