"""Unit tests for PDF watermark, text extraction, and page numbering."""
import os
import tempfile
import unittest
import pymupdf as fitz
from app.features.pdf import ops as pdf_ops


class PdfOpsExtendedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.pdf_path = os.path.join(self.tmp_dir.name, "sample.pdf")
        doc = fitz.open()
        for i in range(3):
            page = doc.new_page(width=300, height=400)
            page.insert_text((50, 100), f"Sample content on page {i + 1}", fontsize=14)
        doc.save(self.pdf_path)
        doc.close()

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_extract_pdf_text(self) -> None:
        text = pdf_ops.extract_pdf_text(self.pdf_path, mode="plain", page_separator=True)
        self.assertIn("Sample content on page 1", text)
        self.assertIn("--- Page 2 ---", text)

    def test_add_pdf_watermark(self) -> None:
        out = os.path.join(self.tmp_dir.name, "watermarked.pdf")
        pdf_ops.add_pdf_watermark(self.pdf_path, out, text="TOP SECRET", opacity=0.3)
        self.assertTrue(os.path.exists(out))
        extracted = pdf_ops.extract_pdf_text(out)
        self.assertIn("TOP SECRET", extracted)

    def test_add_page_numbers(self) -> None:
        out = os.path.join(self.tmp_dir.name, "numbered.pdf")
        pdf_ops.add_page_numbers(
            self.pdf_path, out,
            format_str="Page {n} of {total}",
            position="bottom_center",
            font_size=10,
        )
        self.assertTrue(os.path.exists(out))
        extracted = pdf_ops.extract_pdf_text(out)
        self.assertIn("Page 1 of 3", extracted)
        self.assertIn("Page 3 of 3", extracted)

    def test_fill_pdf_form_fields(self) -> None:
        form_path = os.path.join(self.tmp_dir.name, "form.pdf")
        form_doc = fitz.open()
        page = form_doc.new_page(width=300, height=200)
        widget = fitz.Widget()
        widget.rect = fitz.Rect(40, 60, 220, 90)
        widget.field_name = "customer_name"
        widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT  # noqa: 21 (pymupdf Widget attribute, read internally by the library)
        widget.field_value = ""
        page.add_widget(widget)
        widget.update()
        form_doc.save(form_path)
        form_doc.close()

        fields = pdf_ops.list_pdf_form_fields(form_path)
        self.assertEqual(fields[0]["field_name"], "customer_name")

        out_path = os.path.join(self.tmp_dir.name, "filled_form.pdf")
        pdf_ops.fill_pdf_form(form_path, out_path, {"customer_name": "Ada"})
        filled_fields = pdf_ops.list_pdf_form_fields(out_path)
        self.assertEqual(filled_fields[0]["field_value"], "Ada")


if __name__ == "__main__":
    unittest.main()
