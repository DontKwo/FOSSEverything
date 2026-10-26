import base64
import io
from pathlib import Path
from typing import Any

from app.features.media.ops import (
    BatchMediaItem,
    batch_compress_media,
    batch_convert_media,
    batch_extract_audio,
    compose_media_with_audio,
    compose_timeline,
    compress_media,
    compress_video,
    convert_media,
    extract_audio,
    extract_frame,
    format_timestamp,
    generate_subtitle_file,
    generate_subtitles_from_transcription,
    get_media_info,
    mute_video,
    parse_subtitle_cues,
    transcribe_audio,
    trim_media,
)
from app.web.api.result import api_method, fail, ok, require


class MediaApiMixin:
    @api_method
    def media_get_info(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract audio and video stream container metadata and duration.
        require(params, "file_path")
        file_path = str(params["file_path"])
        info = get_media_info(file_path)
        dur = float(info.get("duration", 0.0))
        formatted_dur = format_timestamp(dur)
        return ok(info=info, duration_formatted=formatted_dur, file_path=file_path)

    @api_method
    def media_info(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for querying media info.
        return self.media_get_info(params)

    @api_method
    def media_get_file_url(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return local file:// URL scheme string for HTML5 media elements.
        require(params, "file_path")
        file_path = Path(str(params["file_path"])).resolve()
        return ok(url=file_path.as_uri(), file_path=str(file_path))

    @api_method
    def media_trim(self, params: dict[str, Any]) -> dict[str, Any]:
        # Trim audio or video between start and end timestamps.
        require(params, "input_path", "output_path", "start_time", "end_time")
        in_p = str(params["input_path"])
        out_p = str(params["output_path"])
        start = float(params["start_time"])
        end = float(params["end_time"])
        res_p = trim_media(in_p, out_p, start, end)
        return ok(output_path=res_p)

    @api_method
    def media_extract_audio(self, params: dict[str, Any]) -> dict[str, Any]:
        # Demux and export audio track from video file.
        require(params, "input_path", "output_path")
        in_p = str(params["input_path"])
        out_p = str(params["output_path"])
        bitrate = str(params.get("bitrate", "192k"))
        res_p = extract_audio(in_p, out_p, audio_bitrate=bitrate)
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
        # Two-pass compress video to meet target file size limit.
        require(params, "input_path", "output_path")
        in_p = str(params["input_path"])
        out_p = str(params["output_path"])
        mb = float(params.get("target_size_mb", 25.0))
        res_p = compress_video(in_p, out_p, target_size_mb=mb)
        res_fallback = compress_media(in_p, out_p, target_size_mb=mb)
        return ok(output_path=res_p or res_fallback)

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
        img = extract_frame(in_p, ts, output_path=str(out_p) if out_p else None)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        data_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return ok(data_url=f"data:image/jpeg;base64,{data_b64}", width=img.width, height=img.height, output_path=out_p)

    @api_method
    def media_capture_frame(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for frame capture.
        return self.media_extract_frame(params)

    @api_method
    def media_transcribe(self, params: dict[str, Any]) -> dict[str, Any]:
        # Transcribe audio track speech to subtitle file (SRT or VTT).
        require(params, "input_path")
        in_p = str(params["input_path"])
        lang = params.get("language")
        cues = transcribe_audio(in_p, language=lang)
        out_p = params.get("output_path")
        if out_p:
            generate_subtitle_file(cues, str(out_p))
        srt_text = generate_subtitles_from_transcription(cues)
        parsed = parse_subtitle_cues(srt_text)
        return ok(cues=parsed, srt=srt_text, count=len(parsed), output_path=out_p)

    @api_method
    def media_compose_audio(self, params: dict[str, Any]) -> dict[str, Any]:
        # Combine video stream with external audio track.
        require(params, "video_path", "audio_path", "output_path")
        v_p = str(params["video_path"])
        a_p = str(params["audio_path"])
        out_p = str(params["output_path"])
        res_p = compose_media_with_audio(v_p, a_p, out_p)
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
        require(params, "items", "operation")
        op = str(params["operation"]).lower()
        raw_items = list(params["items"])
        items = [
            BatchMediaItem(
                source_path=str(it["source_path"]),
                output_path=it.get("output_path"),
                options=it.get("options", {}),
            )
            for it in raw_items
        ]
        if op == "convert":
            results = batch_convert_media(items)
        elif op == "compress":
            results = batch_compress_media(items)
        elif op == "extract_audio":
            results = batch_extract_audio(items)
        else:
            return fail(f"Unsupported media batch op: {op}", code="InvalidOperation")
        return ok(results=results)
