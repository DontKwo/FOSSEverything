from __future__ import annotations

from pathlib import Path

from app.web.api import WebApi


def test_estimate_savings_scales_with_profile(tmp_path: Path) -> None:
    # Higher profiles estimate larger savings for the same file.
    api = WebApi()
    sample = tmp_path / "notes.txt"
    sample.write_text("lorem ipsum " * 400, encoding="utf-8")
    saved = []
    for preset in ("light", "balanced", "aggressive"):
        res = api.compressor_estimate_savings({"items": [{"path": str(sample)}], "preset": preset})
        assert res["ok"] is True
        assert res["total_original_bytes"] == sample.stat().st_size
        assert res["total_estimated_bytes"] + res["total_saved_bytes"] == res["total_original_bytes"]
        saved.append(res["total_saved_bytes"])
    assert saved[0] < saved[1] < saved[2]


def test_scan_reports_output_extension_and_zip_fallback(tmp_path: Path) -> None:
    # Non-media general files are written as ZIP, PDFs keep their extension.
    api = WebApi()
    txt = tmp_path / "a.txt"
    txt.write_text("a", encoding="utf-8")
    pdf = tmp_path / "b.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    res = api.compressor_scan_inputs({"paths": [str(txt), str(pdf)]})
    by_name = {item["name"]: item["output_ext"] for item in res["items"]}
    assert by_name == {"a.txt": ".zip", "b.pdf": ".pdf"}

    out = api.compressor_compress_items({"items": [{"path": str(txt)}]})
    assert out["ok"] is True
    assert Path(out["results"][0]["output_path"]).suffix == ".zip"


def test_estimate_without_params_does_not_raise() -> None:
    # Empty params return a failure payload instead of raising.
    assert WebApi().compressor_estimate_savings({})["ok"] is False
