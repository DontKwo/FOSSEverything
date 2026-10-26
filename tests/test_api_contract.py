import inspect
import json
import time
from pathlib import Path
from typing import Any

import pytest

from app.web.api import (
    BaseApi,
    ArchiveApiMixin,
    CollageApiMixin,
    ConverterApiMixin,
    DataApiMixin,
    EncodingApiMixin,
    HashApiMixin,
    ImagesApiMixin,
    MarkdownApiMixin,
    MediaApiMixin,
    MetadataApiMixin,
    Model3dApiMixin,
    NetworkMonitorApiMixin,
    OcrApiMixin,
    OfficeApiMixin,
    PaletteApiMixin,
    PdfApiMixin,
    PlaylistApiMixin,
    QrApiMixin,
    RenamerApiMixin,
    ResumeApiMixin,
    ScreenshotApiMixin,
    TextToolsApiMixin,
    WebApi,
    WordCounterApiMixin,
)
from tests.fixtures import make_fixtures


ALL_MIXINS = [
    BaseApi,
    ArchiveApiMixin,
    CollageApiMixin,
    ConverterApiMixin,
    DataApiMixin,
    EncodingApiMixin,
    HashApiMixin,
    ImagesApiMixin,
    MarkdownApiMixin,
    MediaApiMixin,
    MetadataApiMixin,
    Model3dApiMixin,
    NetworkMonitorApiMixin,
    OcrApiMixin,
    OfficeApiMixin,
    PaletteApiMixin,
    PdfApiMixin,
    PlaylistApiMixin,
    QrApiMixin,
    RenamerApiMixin,
    ResumeApiMixin,
    ScreenshotApiMixin,
    TextToolsApiMixin,
    WordCounterApiMixin,
]


def test_public_method_signatures() -> None:
    # Assert every public method has (self, params: dict[str, Any]) -> dict[str, Any].
    api = WebApi()
    mismatches: list[str] = []

    for name in dir(api):
        if name.startswith("_"):
            continue
        val = getattr(api, name)
        if not callable(val):
            continue
        sig = inspect.signature(val)
        params = list(sig.parameters.keys())
        if params != ["params"]:
            mismatches.append(f"{name}: params={params} != ['params']")
            continue
        p_ann = str(sig.parameters["params"].annotation)
        r_ann = str(sig.return_annotation)
        if "dict" not in p_ann:
            mismatches.append(f"{name}: param annotation '{p_ann}' does not contain dict")
        if "dict" not in r_ann:
            mismatches.append(f"{name}: return annotation '{r_ann}' does not contain dict")

    assert not mismatches, f"Non-conforming API methods:\n" + "\n".join(mismatches[:30])


def test_no_duplicate_mixin_methods() -> None:
    # Assert no two mixins declare the same public method name.
    method_sources: dict[str, str] = {}
    duplicates: list[str] = []

    for cls in ALL_MIXINS:
        for attr, val in cls.__dict__.items():
            if attr.startswith("_") or not callable(val):
                continue
            if attr in method_sources:
                duplicates.append(f"{attr} defined in both {method_sources[attr]} and {cls.__name__}")
            else:
                method_sources[attr] = cls.__name__

    assert not duplicates, f"Duplicate method definitions found:\n" + "\n".join(duplicates)


def test_empty_params_never_raises() -> None:
    # Assert calling any public method with empty params never raises unhandled exception.
    api = WebApi()
    failures: list[str] = []

    for name in dir(api):
        if name.startswith("_"):
            continue
        val = getattr(api, name)
        if not callable(val):
            continue
        try:
            res = val({})
            if not isinstance(res, dict):
                failures.append(f"{name}: did not return dict: {type(res)}")
        except Exception as exc:
            failures.append(f"{name}: raised unhandled {type(exc).__name__}: {exc}")

    assert not failures, f"Methods failed on empty params:\n" + "\n".join(failures[:20])


def test_read_only_tool_methods(tmp_path: Path) -> None:
    # Verify read-only operations succeed and produce valid JSON serialization.
    fixtures = make_fixtures(tmp_path)
    api = WebApi()

    read_calls: list[tuple[str, dict[str, Any]]] = [
        ("ping", {}),
        ("encoding_base64_encode_text", {"text": "hello"}),
        ("text_tools_case", {"text": "hello", "mode": "upper"}),
        ("word_counter_analyze", {"text": "one two three four"}),
        ("markdown_to_html", {"markdown": "# Heading\ntext"}),
        ("data_validate_syntax", {"content": '{"key": "value"}', "format": "json"}),
        ("hash_text", {"text": "sample"}),
        ("metadata_inspect", {"file_path": fixtures["sample.png"]}),
        ("renamer_preview", {"file_paths": [fixtures["sample.txt"]], "template": "doc_{n}"}),
        ("archive_list", {"archive_path": fixtures["sample.zip"]}),
        ("office_extract", {"file_path": fixtures["sample.docx"]}),
        ("converter_available_targets", {"file_path": fixtures["sample.txt"]}),
        ("collage_presets", {}),
        ("palette_contrast", {"color1": "#000000", "color2": "#ffffff"}),
        ("qr_generate", {"payload": "https://example.com"}),
        ("images_load_data", {"file_path": fixtures["sample.png"]}),
        ("pdf_open_doc", {"file_path": fixtures["sample.pdf"]}),
        ("ocr_languages", {}),
        ("screenshot_capture_region", {"x1": 0, "y1": 0, "x2": 10, "y2": 10}),
        ("media_get_info", {"file_path": fixtures["tone.wav"]}),
        ("playlist_parse_text", {"text": "Artist - Title"}),
        ("network_stats", {}),
        ("model3d_info", {"file_path": fixtures["cube.stl"]}),
        ("resume_sample", {}),
    ]

    for method_name, params in read_calls:
        fn = getattr(api, method_name)
        res = fn(params)
        assert res.get("ok") is True, f"{method_name} returned ok=False: {res}"
        dumped = json.dumps(res)
        assert isinstance(dumped, str)


def test_job_lifecycle() -> None:
    # Assert job_start, job_poll, and job_cancel execute correctly.
    api = WebApi()
    start_res = api.job_start({"method": "ping", "params": {}})
    assert start_res.get("ok") is True
    job_id = start_res["id"]

    for _ in range(50):
        poll_res = api.job_poll({"id": job_id})
        assert poll_res.get("ok") is True
        if poll_res.get("state") in ("done", "failed", "cancelled"):
            break
        time.sleep(0.05)

    assert poll_res.get("state") == "done"
    assert poll_res.get("result", {}).get("pong") is True

    # Test cancel
    start_cancel = api.job_start({"method": "ping", "params": {}})
    cid = start_cancel["id"]
    cancel_res = api.job_cancel({"id": cid})
    assert cancel_res.get("ok") is True
