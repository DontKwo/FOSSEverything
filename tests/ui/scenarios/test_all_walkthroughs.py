from pathlib import Path
from typing import Any
from playwright.sync_api import Page, expect


def test_full_application_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    # Complete automated Playwright test exercising all 21 canonical tools sequentially.
    fixtures_dir = Path("tests/ui/_fixtures")
    sample_pdf = str(fixtures_dir / "sample.pdf")
    sample_png = str(fixtures_dir / "sample.png")
    sample_docx = str(fixtures_dir / "sample.docx")
    cube_stl = str(fixtures_dir / "cube.stl")
    clip_mp4 = str(fixtures_dir / "clip.mp4")
    playlist_m3u8 = str(fixtures_dir / "playlist.m3u8")

    # 1. PDF Tools
    pdf_out = str(tmp_path / "out_pdf_merged.pdf")
    api._dialog_answers.extend([[sample_pdf], pdf_out])
    page.evaluate("window.FOSS.router.open('pdf', 'merge')")
    page.locator("[data-testid='pdf-merge-add-btn'], [data-testid='pdf-add-files-btn']").first.click()
    page.wait_for_timeout(150)
    page.click("[data-testid='pdf-merge-save-btn']")
    page.wait_for_timeout(250)
    assert Path(pdf_out).exists()

    # 2. OCR Studio
    ocr_out = str(tmp_path / "out_ocr.pdf")
    api._dialog_answers.extend([sample_png, ocr_out])
    page.evaluate("window.FOSS.router.open('ocr', 'document')")
    page.click("[data-testid='ocr-choose-file']")
    page.fill("[data-testid='ocr-page-range']", "1")
    page.click("[data-testid='ocr-run-btn']")
    page.wait_for_timeout(300)
    page.click("[data-testid='ocr-export-pdf-btn']")
    page.wait_for_timeout(250)
    assert Path(ocr_out).exists()

    # 3. Markdown Studio
    md_out = str(tmp_path / "out_markdown.html")
    api._dialog_answers.append(md_out)
    page.evaluate("window.FOSS.router.open('markdown', 'editor')")
    page.select_option("[data-testid='markdown-flavor-select']", "gfm")
    page.click("[data-testid='markdown-export-html-btn']")
    page.wait_for_timeout(200)
    assert Path(md_out).exists()

    # 4. Resume Studio
    docx_out = str(tmp_path / "out_resume.docx")
    api._dialog_answers.append(docx_out)
    page.evaluate("window.FOSS.router.open('resume', 'preview')")
    page.click("[data-testid='resume-export-docx-btn']")
    page.wait_for_timeout(250)
    assert Path(docx_out).exists()

    # 5. Image Studio
    img_out = str(tmp_path / "out_img.webp")
    api._dialog_answers.extend([sample_png, img_out])
    page.evaluate("window.FOSS.router.open('images', 'transform')")
    page.click("[data-testid='images-choose-file']")
    page.click("[data-testid='images-save-btn']")
    page.wait_for_timeout(250)
    assert Path(img_out).exists()

    # 6. Photo Collage
    col_out = str(tmp_path / "out_collage.png")
    api._dialog_answers.extend([[sample_png], col_out])
    page.evaluate("window.FOSS.router.open('collage', 'freeform')")
    page.click("[data-testid='collage-add-images-btn']")
    page.click("[data-testid='collage-export-btn']")
    page.wait_for_timeout(250)
    assert Path(col_out).exists()

    # 7. Color Palette
    api._dialog_answers.append(sample_png)
    page.evaluate("window.FOSS.router.open('palette', 'extract')")
    page.click("[data-testid='palette-choose-file']")
    page.wait_for_timeout(250)
    expect(page.locator("[data-testid='palette-swatch-grid']")).to_be_visible()

    # 8. 3D Model Studio
    api._dialog_answers.append(cube_stl)
    page.evaluate("window.FOSS.router.open('model3d', 'inspector')")
    page.click("[data-testid='model3d-load-file']")
    page.wait_for_timeout(250)
    expect(page.locator("[data-testid='model3d-sidebar']")).to_be_visible()

    # 9. Audio & Video Studio
    media_out = str(tmp_path / "out_audio.mp3")
    api._dialog_answers.extend([clip_mp4, media_out])
    page.evaluate("window.FOSS.router.open('media', 'audio')")
    page.click("[data-testid='media-choose-file']")
    page.click("[data-testid='media-extract-audio-btn']")
    page.wait_for_timeout(250)
    assert Path(media_out).exists()

    # 10. Playlist Porter
    pl_out = str(tmp_path / "out_pl.csv")
    api._dialog_answers.extend([playlist_m3u8, pl_out])
    page.evaluate("window.FOSS.router.open('playlist', 'import')")
    page.click("[data-testid='playlist-choose-file']")
    page.click("[data-testid='playlist-export-csv-btn']")
    page.wait_for_timeout(200)
    assert Path(pl_out).exists()

    # 11. Universal Converter
    conv_out = str(tmp_path / "out_conv.jpg")
    api._dialog_answers.extend([sample_png, conv_out])
    page.evaluate("window.FOSS.router.open('converter', 'single')")
    page.click("[data-testid='converter-choose-file']")
    page.click("[data-testid='converter-convert-btn']")
    page.wait_for_timeout(250)
    assert Path(conv_out).exists()

    # 12. File Compressor
    comp_out = str(tmp_path / "out_comp.pdf")
    api._dialog_answers.extend([sample_pdf, comp_out])
    page.evaluate("window.FOSS.router.open('compressor', 'single')")
    page.click("[data-testid='compressor-choose-file']")
    page.click("[data-testid='compressor-run-btn']")
    page.wait_for_timeout(250)
    assert Path(comp_out).exists()

    # 13. Archive Studio
    arc_out = str(tmp_path / "out_arc.zip")
    api._dialog_answers.extend([[sample_png], arc_out])
    page.evaluate("window.FOSS.router.open('archive', 'create')")
    page.click("[data-testid='archive-add-files-btn']")
    page.click("[data-testid='archive-create-btn']")
    page.wait_for_timeout(250)
    assert Path(arc_out).exists()

    # 14. Batch Renamer
    target_f = tmp_path / "rename_me.png"
    target_f.write_bytes(Path(sample_png).read_bytes())
    api._dialog_answers.append(str(target_f))
    page.evaluate("window.FOSS.router.open('renamer', 'rules')")
    page.click("[data-testid='renamer-add-files-btn']")
    page.click("[data-testid='renamer-apply-btn']")
    page.wait_for_timeout(200)

    # 15. Metadata Stripper
    meta_out = str(tmp_path / "out_meta.docx")
    api._dialog_answers.extend([sample_docx, meta_out])
    page.evaluate("window.FOSS.router.open('metadata', 'strip')")
    page.click("[data-testid='metadata-choose-file']")
    page.click("[data-testid='metadata-strip-btn']")
    page.wait_for_timeout(200)
    assert Path(meta_out).exists()

    # 16. QR and Barcodes
    qr_out = str(tmp_path / "out_qr.png")
    api._dialog_answers.append(qr_out)
    page.evaluate("window.FOSS.router.open('qr', 'generate')")
    page.fill("[data-testid='qr-text-input']", "https://foss.example.com")
    page.click("[data-testid='qr-save-png-btn']")
    page.wait_for_timeout(200)
    assert Path(qr_out).exists()

    # 17. Network Traffic Monitor
    page.evaluate("window.FOSS.router.open('network_monitor', 'live')")
    page.wait_for_timeout(200)
    expect(page.locator("text=Source Identity").first).to_be_visible()

    # 18. Unit Converter
    page.evaluate("window.FOSS.router.open('unit_converter', 'standard')")
    expect(page.locator("[data-testid='unit_converter-primary-card']")).to_be_visible()

    # 19. Data Studio
    data_out = str(tmp_path / "out_data.yaml")
    api._dialog_answers.append(data_out)
    page.evaluate("window.FOSS.router.open('data', 'format')")
    page.click("[data-testid='data-save-btn']")
    page.wait_for_timeout(200)
    assert Path(data_out).exists()

    # 20. Text Tools
    page.evaluate("window.FOSS.router.open('text_tools', 'case')")
    expect(page.locator("[data-testid='text_tools-pascal-btn']")).to_be_visible()

    # 21. Encoding / Decoding
    page.evaluate("window.FOSS.router.open('encoding', 'base64')")
    expect(page.locator("[data-testid='encoding-encode-btn']")).to_be_visible()

