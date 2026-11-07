# UX Audit and Polish Report: Document Suite (ai/ux-docs)

## Scope
Tools audited, polished, and verified:
- PDF Tools (`app/web/js/tools/pdf.js`)
- OCR Studio (`app/web/js/tools/ocr.js`)
- Markdown Studio (`app/web/js/tools/markdown.js`)
- Resume Studio (`app/web/js/tools/resume.js`)
- File Format Converter (`app/web/js/tools/converter.js`)
- File Compressor (`app/web/js/tools/compressor.js`)
- Metadata Tools (`app/web/js/tools/metadata.js`)
- Styling enhancements in `app/web/css/tools.css` under respective tool blocks.

## Issues Found and Fixed
1. Converter:
   - Inline styles across table columns, header rows, and stage wrappers violated Section 0 hard invariants and caused rigid column sizing.
   - Refactored all inline styles into responsive utility classes in `tools.css` (`.converter-table-fixed`, `.converter-col-file`, `.converter-col-meta`, `.converter-card-bound`, `.converter-full-width`).
2. Compressor:
   - Fixed table layout clipping and removed inline styles from queue items, action buttons, and size badges. Added `.compressor-col-file`, `.compressor-col-orig`, `.compressor-col-comp`, `.compressor-col-saved`, and `.compressor-ellipsis`.
3. PDF Studio:
   - Replaced inline styles across page number stamp controls, header rows, thumbnail boxes, and protect/unlock split layout with dedicated `.pdf-*` classes.
   - Hidden elements use CSS `.hidden` rather than inline `display: none`.
4. OCR Studio:
   - Added user warning when Tesseract OCR binary or language models are not installed.
   - Replaced table inline styles with `.ocr-col-num` and `.ocr-col-action`.
5. Markdown Studio:
   - Replaced hard-coded inline styles in the live preview document template with `.empty-preview-note`.
6. Resume Studio:
   - Eliminated extensive inline styles across editor content cards, contact details, date and degree inputs, and bullet rows. Introduced reusable classes in `tools.css`.
7. Metadata Tools:
   - Replaced inline styles in tag tables, scrub configuration boxes, and batch tables with dedicated `.metadata-*` classes.

## Verification
- Linter and static invariant verification:
  `uv run --no-project --python .venv/bin/python python -m pytest tests/test_api_contract.py tests/test_web_static.py tests/test_parity_ops.py` (14/14 passed)
- Scenario walkthrough tests:
  `uv run --no-project --python .venv/bin/python python -m pytest tests/ui/scenarios/test_pdf_walkthrough.py tests/ui/scenarios/test_ocr_walkthrough.py tests/ui/scenarios/test_markdown_walkthrough.py tests/ui/scenarios/test_resume_walkthrough.py tests/ui/scenarios/test_compressor_walkthrough.py tests/ui/scenarios/test_metadata_walkthrough.py` (6/6 passed)
- Custom audits:
  Zero non-ASCII bytes, zero forbidden direct style assignments, comments within 2 lines limit.
- Screenshots saved under `docs/ai-notes/ai/ux-docs/screens/` across desktop (1280x800), mobile/tiny (800x600), and large (3840x2160) viewports.

## Shared Files Touched
- None outside the assigned scope. All modifications were confined to `app/web/js/tools/`, `app/web/css/tools.css`, `app/core/tooltips.py`, and `docs/ai-notes/ai/ux-docs/`.

## Items Needing Owner Decision
- None. All improvements preserve existing functionality and comply strictly with design tokens and contract invariants.
