import inspect
import json
import time
from pathlib import Path
from typing import Any


from app.web.api import (
    BaseApi,
    ArchiveApiMixin,
    CollageApiMixin,
    CompressorApiMixin,
    ConverterApiMixin,
    DataApiMixin,
    EncodingApiMixin,
    ImagesApiMixin,
    MarkdownApiMixin,
    MediaApiMixin,
    MetadataApiMixin,
    Model3dApiMixin,
    NetworkMonitorApiMixin,
    OcrApiMixin,
    PaletteApiMixin,
    PdfApiMixin,
    PlaylistApiMixin,
    QrApiMixin,
    RenamerApiMixin,
    ResumeApiMixin,
    TextToolsApiMixin,
    UnitConverterApiMixin,
    WebApi,
    WordCounterApiMixin,
)
from tests.fixtures import make_fixtures


ALL_MIXINS = [
    BaseApi,
    ArchiveApiMixin,
    CollageApiMixin,
    CompressorApiMixin,
    ConverterApiMixin,
    DataApiMixin,
    EncodingApiMixin,
    ImagesApiMixin,
    MarkdownApiMixin,
    MediaApiMixin,
    MetadataApiMixin,
    Model3dApiMixin,
    NetworkMonitorApiMixin,
    OcrApiMixin,
    PaletteApiMixin,
    PdfApiMixin,
    PlaylistApiMixin,
    QrApiMixin,
    RenamerApiMixin,
    ResumeApiMixin,
    TextToolsApiMixin,
    UnitConverterApiMixin,
    WordCounterApiMixin,
]


def test_public_method_signatures() -> None:
    # Assert every public method has (self, params: dict[str, Any]) -> dict[str, Any].
    api = WebApi()
    mismatches: list[str] = []

    for name in dir(api):
        if name.startswith("_"):
            continue
        method_obj = getattr(api, name)
        if not callable(method_obj):
            continue
        sig = inspect.signature(method_obj)
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

    assert not mismatches, "Non-conforming API methods:\n" + "\n".join(mismatches[:30])


def test_no_duplicate_mixin_methods() -> None:
    # Assert no two mixins declare the same public method name.
    method_sources: dict[str, str] = {}
    duplicates: list[str] = []

    for cls in ALL_MIXINS:
        for attr, method_func in cls.__dict__.items():
            if attr.startswith("_") or not callable(method_func):
                continue
            if attr in method_sources:
                duplicates.append(f"{attr} defined in both {method_sources[attr]} and {cls.__name__}")
            else:
                method_sources[attr] = cls.__name__

    assert not duplicates, "Duplicate method definitions found:\n" + "\n".join(duplicates)


def test_empty_params_never_raises() -> None:
    # Assert calling any public method with empty params never raises unhandled exception.
    api = WebApi()
    failures: list[str] = []

    for name in dir(api):
        if name.startswith("_"):
            continue
        method_obj = getattr(api, name)
        if not callable(method_obj):
            continue
        try:
            res = method_obj({})
            if not isinstance(res, dict):
                failures.append(f"{name}: did not return dict: {type(res)}")
        except Exception as exc:
            failures.append(f"{name}: raised unhandled {type(exc).__name__}: {exc}")

    assert not failures, "Methods failed on empty params:\n" + "\n".join(failures[:20])


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
        ("metadata_inspect", {"file_path": fixtures["sample.png"]}),
        ("renamer_preview", {"file_paths": [fixtures["sample.txt"]], "template": "doc_{n}"}),
        ("archive_list", {"archive_path": fixtures["sample.zip"]}),
        ("converter_available_targets", {"file_path": fixtures["sample.docx"]}),
        ("metadata_inspect", {"file_path": fixtures["sample.docx"]}),
        ("converter_available_targets", {"file_path": fixtures["sample.txt"]}),
        ("collage_presets", {}),
        ("palette_contrast", {"color1": "#000000", "color2": "#ffffff"}),
        ("qr_generate", {"payload": "https://example.com"}),
        ("images_load_data", {"file_path": fixtures["sample.png"]}),
        ("pdf_open_doc", {"file_path": fixtures["sample.pdf"]}),
        ("ocr_languages", {}),
        ("ocr_scan_inputs", {"paths": []}),
        ("media_get_info", {"file_path": fixtures["tone.wav"]}),
        ("playlist_parse_text", {"text": "Artist - Title"}),
        ("network_stats", {}),
        ("model3d_info", {"file_path": fixtures["cube.stl"]}),
        ("resume_sample", {}),
        ("units_catalog", {}),
        ("images_models_status", {}),
        ("ocr_inspect_file", {"file_path": fixtures["sample.pdf"]}),
        ("qr_label_presets", {}),
        ("converter_scan_inputs", {"paths": [fixtures["sample.txt"]]}),
        ("compressor_scan_inputs", {"paths": [fixtures["sample.txt"]]}),
        ("renamer_scan_inputs", {"paths": [fixtures["sample.txt"]]}),
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


def test_mixin_helper_methods_and_error_free_execution(tmp_path: Path) -> None:
    # Verify helper methods exist on WebApi and calling endpoints never causes NameError or AttributeError.
    api = WebApi()
    assert hasattr(api, "_get_monitor"), "WebApi is missing _get_monitor helper"
    assert hasattr(WebApi, "_get_monitor"), "WebApi class is missing _get_monitor descriptor"

    # All callable members of ALL_MIXINS must be accessible on WebApi.
    missing_from_webapi: list[str] = []
    for cls in ALL_MIXINS:
        for attr, fn in cls.__dict__.items():
            if attr.startswith("__"):
                continue
            if callable(fn) and not hasattr(api, attr):
                missing_from_webapi.append(f"{cls.__name__}.{attr}")

    assert not missing_from_webapi, "Mixins declare methods missing from WebApi:\n" + "\n".join(missing_from_webapi)

    # Use an isolated temporary file to avoid touching tests/test_data
    scratch_file = tmp_path / "scratch.txt"
    scratch_file.write_text("sample content", encoding="utf-8")

    sample_params = {
        "file_path": str(scratch_file),
        "path": str(scratch_file),
        "paths": [str(scratch_file)],
        "output_path": str(tmp_path / "out.txt"),
        "content": '{"key": "value"}',
        "text": "sample text",
        "markdown": "# Header\nContent",
        "expression": "*/5 * * * *",
        "source_format": "json",
        "target_format": "yaml",
        "language": "json",
        "format": "json",
        "operation": "reverse_words",
        "category": "hex",
        "metadata": {"title": "Test"},
        "style": "apa",
        "entries": [{"title": "Test"}],
        "pattern": "foo",
        "replacement": "bar",
        "value": 1.0,
        "from_unit": "m",
        "to_unit": "km",
        "source_unit": "m",
        "target_unit": "km",
        "title": "Title",
        "start_time": "2026-01-01T00:00:00",
        "destination": "8.8.8.8",
        "process_name": "python",
        "trust_level": "trusted",
        "page_number": 0,
    }

    bugs: list[str] = []
    for name in dir(api):
        if name.startswith("_"):
            continue
        method = getattr(api, name)
        if not callable(method):
            continue
        try:
            res = method(sample_params)
            if isinstance(res, dict) and not res.get("ok"):
                code = res.get("code", "")
                err = res.get("error", "")
                if code in ("NameError", "AttributeError", "UnboundLocalError"):
                    bugs.append(f"{name}: {code} - {err}")
        except (NameError, AttributeError, UnboundLocalError) as exc:
            bugs.append(f"{name} raised unhandled {type(exc).__name__}: {exc}")
        except Exception:
            pass

    assert not bugs, "Internal name resolution or attribute errors detected:\n" + "\n".join(bugs)
