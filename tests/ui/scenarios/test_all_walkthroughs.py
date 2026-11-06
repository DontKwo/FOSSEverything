from pathlib import Path
from typing import Any
from playwright.sync_api import Page

from tests.ui.scenarios.test_archive_walkthrough import test_archive_walkthrough
from tests.ui.scenarios.test_collage_walkthrough import test_collage_walkthrough
from tests.ui.scenarios.test_compressor_walkthrough import test_compressor_walkthrough
from tests.ui.scenarios.test_data_walkthrough import test_data_walkthrough
from tests.ui.scenarios.test_encoding_walkthrough import test_encoding_walkthrough
from tests.ui.scenarios.test_markdown_walkthrough import test_markdown_walkthrough
from tests.ui.scenarios.test_media_walkthrough import test_media_walkthrough
from tests.ui.scenarios.test_metadata_walkthrough import test_metadata_walkthrough
from tests.ui.scenarios.test_model3d_walkthrough import test_model3d_walkthrough
from tests.ui.scenarios.test_network_monitor_walkthrough import test_network_monitor_walkthrough
from tests.ui.scenarios.test_ocr_walkthrough import test_ocr_walkthrough
from tests.ui.scenarios.test_pdf_walkthrough import test_pdf_walkthrough
from tests.ui.scenarios.test_playlist_walkthrough import test_playlist_walkthrough
from tests.ui.scenarios.test_renamer_walkthrough import test_renamer_walkthrough
from tests.ui.scenarios.test_resume_walkthrough import test_resume_walkthrough
from tests.ui.scenarios.test_text_tools_walkthrough import test_text_tools_walkthrough
from tests.ui.scenarios.test_unit_converter_walkthrough import test_unit_converter_walkthrough

from tests.ui.scenarios.converter import SCENARIOS as CONVERTER_SCENARIOS
from tests.ui.scenarios.images import SCENARIOS as IMAGES_SCENARIOS
from tests.ui.scenarios.palette import SCENARIOS as PALETTE_SCENARIOS
from tests.ui.scenarios.qr import SCENARIOS as QR_SCENARIOS


def test_full_application_walkthrough(page: Page, api: Any, tmp_path: Path) -> None:
    # Complete automated Playwright test exercising all 21 canonical tools sequentially.
    fixtures: dict[str, str] = {
        "sample.pdf": str(Path("tests/ui/_fixtures/sample.pdf")),
        "sample.png": str(Path("tests/ui/_fixtures/sample.png")),
        "sample2.png": str(Path("tests/ui/_fixtures/sample.png")),
    }

    # 1. PDF
    test_pdf_walkthrough(page, api, tmp_path)

    # 2. OCR
    test_ocr_walkthrough(page, api, tmp_path)

    # 3. Markdown
    test_markdown_walkthrough(page, api, tmp_path)

    # 4. Resume
    test_resume_walkthrough(page, api, tmp_path)

    # 5. Images
    for _, sc in IMAGES_SCENARIOS:
        sc(page, fixtures, api)

    # 6. Collage
    test_collage_walkthrough(page, api, tmp_path)

    # 7. Palette
    for _, sc in PALETTE_SCENARIOS:
        sc(page, fixtures, api)

    # 8. Model3D
    test_model3d_walkthrough(page, api, tmp_path)

    # 9. Media
    test_media_walkthrough(page, api, tmp_path)

    # 10. Playlist
    test_playlist_walkthrough(page, api, tmp_path)

    # 11. Converter
    for _, sc in CONVERTER_SCENARIOS:
        sc(page, fixtures, api)

    # 12. Compressor
    test_compressor_walkthrough(page, api, tmp_path)

    # 13. Archive
    test_archive_walkthrough(page, api, tmp_path)

    # 14. Renamer
    test_renamer_walkthrough(page, api, tmp_path)

    # 15. Metadata
    test_metadata_walkthrough(page, api, tmp_path)

    # 16. QR
    for _, sc in QR_SCENARIOS:
        sc(page, fixtures, api)

    # 17. Network Monitor
    test_network_monitor_walkthrough(page, api, tmp_path)

    # 18. Unit Converter
    test_unit_converter_walkthrough(page, api, tmp_path)

    # 19. Data Studio
    test_data_walkthrough(page, api, tmp_path)

    # 20. Text Tools
    test_text_tools_walkthrough(page, api, tmp_path)

    # 21. Encoding
    test_encoding_walkthrough(page, api, tmp_path)
