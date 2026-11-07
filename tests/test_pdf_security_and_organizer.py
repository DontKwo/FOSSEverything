"""Tests for PDF password protection and page organization."""
import unittest
import os
import tempfile
import pikepdf
from app.features.pdf import ops as pdf_ops


class PdfSecurityAndOrganizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.sample_pdf = os.path.join(self.tmp_dir, "sample.pdf")
        pdf = pikepdf.Pdf.new()
        for _ in range(4):
            pdf.add_blank_page(page_size=(100, 100))
        pdf.save(self.sample_pdf)
        pdf.close()

    def test_protect_and_unlock_pdf(self) -> None:
        protected_pdf = os.path.join(self.tmp_dir, "protected.pdf")
        unlocked_pdf = os.path.join(self.tmp_dir, "unlocked.pdf")

        # 1. Protect PDF
        pdf_ops.protect_pdf(self.sample_pdf, protected_pdf, user_password="secret_pass", allow_printing=True)
        self.assertTrue(pdf_ops.is_pdf_encrypted(protected_pdf))

        # 2. Unlock PDF
        pdf_ops.unlock_pdf(protected_pdf, unlocked_pdf, password="secret_pass")
        self.assertFalse(pdf_ops.is_pdf_encrypted(unlocked_pdf))

        # Verify page count is preserved
        with pikepdf.Pdf.open(unlocked_pdf) as pdf:
            self.assertEqual(len(pdf.pages), 4)

    def test_reorganize_pdf_pages(self) -> None:
        organized_pdf = os.path.join(self.tmp_dir, "organized.pdf")
        # Reverse order, rotate first page 90 degrees, duplicate page 2
        ops = [
            {"source_page": 4, "rotation": 90},
            {"source_page": 3, "rotation": 0},
            {"source_page": 2, "rotation": 180},
            {"source_page": 2, "rotation": 0},  # duplicate
        ]
        pdf_ops.reorganize_pdf_pages(self.sample_pdf, organized_pdf, ops)
        with pikepdf.Pdf.open(organized_pdf) as pdf:
            self.assertEqual(len(pdf.pages), 4)
            self.assertEqual(int(pdf.pages[0].get("/Rotate", 0)), 90)
            self.assertEqual(int(pdf.pages[2].get("/Rotate", 0)), 180)


if __name__ == "__main__":
    unittest.main()
