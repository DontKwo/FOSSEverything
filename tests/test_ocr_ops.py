"""Unit tests for ocr_ops module."""
import os
import unittest
from PIL import Image, ImageDraw
import pymupdf as fitz
from app.features.ocr import ops as ocr_ops
from tests.test_support import TempDirTestCase


class TestOcrOps(TempDirTestCase):
    def _create_sample_image(self, text: str = "INVOICE #9982 - $120.00") -> str:
        """Create a synthetic high-contrast image with clear text for OCR."""
        img = Image.new("RGB", (600, 150), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((30, 50), text, fill="black")
        path = os.path.join(self.work_dir, "sample.png")
        img.save(path)
        return path

    def _create_sample_pdf(self, text: str = "CONFIDENTIAL REPORT 2026") -> str:
        """Create a PDF with text rendered as page images (scanned PDF simulation)."""
        img_path = self._create_sample_image(text)
        doc = fitz.open(img_path)
        pdf_bytes = doc.convert_to_pdf()
        doc.close()

        pdf_path = os.path.join(self.work_dir, "scanned_doc.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        return pdf_path

    def test_get_supported_languages(self) -> None:
        langs = ocr_ops.get_supported_languages()
        self.assertIsInstance(langs, dict)
        self.assertIn("eng", langs)
        self.assertIn("spa", langs)
        self.assertIn("fra", langs)
        self.assertIn("deu", langs)
        self.assertEqual(langs["eng"], "English")

    def test_ocr_image_path(self) -> None:
        img_path = self._create_sample_image("Hello World 123")
        res = ocr_ops.ocr_image(img_path, language="eng", dpi=200)
        self.assertIn("text", res)
        self.assertIn("words", res)
        self.assertIn("blocks", res)
        self.assertIn("Hello", res["text"])
        self.assertIn("World", res["text"])
        self.assertGreaterEqual(len(res["words"]), 2)

    def test_ocr_image_pil_object(self) -> None:
        img = Image.new("RGB", (500, 120), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 40), "Direct PIL OCR Test", fill="black")
        res = ocr_ops.ocr_image(img, language="eng", dpi=200)
        self.assertIn("Direct", res["text"])

    def test_ocr_pdf_document(self) -> None:
        pdf_path = self._create_sample_pdf("Page One Scanned Content")
        res = ocr_ops.ocr_pdf(pdf_path, language="eng", dpi=150)
        self.assertEqual(res["page_count"], 1)
        self.assertIn("Page", res["text"])
        self.assertIn("Scanned", res["text"])
        self.assertEqual(len(res["page_texts"]), 1)

    def test_ocr_file_universal_dispatcher(self) -> None:
        img_path = self._create_sample_image("Universal Dispatcher Test")
        res_img = ocr_ops.ocr_file(img_path, language="eng")
        self.assertIn("Dispatcher", res_img["text"])

        pdf_path = self._create_sample_pdf("PDF Dispatcher Test")
        res_pdf = ocr_ops.ocr_file(pdf_path, language="eng")
        self.assertIn("PDF", res_pdf["text"])

    def test_create_searchable_pdf_from_image(self) -> None:
        img_path = self._create_sample_image("Searchable Image Text 2026")
        out_pdf = os.path.join(self.work_dir, "searchable_from_img.pdf")
        ocr_ops.create_searchable_pdf(img_path, out_pdf, language="eng")

        self.assertTrue(os.path.exists(out_pdf))
        # Verify text can be extracted via standard (non-OCR) fitz reader
        with fitz.open(out_pdf) as doc:
            self.assertEqual(len(doc), 1)
            txt = doc[0].get_text()
            self.assertIn("Searchable", txt)

    def test_create_searchable_pdf_from_scanned_pdf(self) -> None:
        scanned_pdf = self._create_sample_pdf("Scanned PDF to Searchable PDF")
        out_pdf = os.path.join(self.work_dir, "searchable_from_pdf.pdf")
        ocr_ops.create_searchable_pdf(scanned_pdf, out_pdf, language="eng")

        self.assertTrue(os.path.exists(out_pdf))
        with fitz.open(out_pdf) as doc:
            txt = doc[0].get_text()
            self.assertIn("Searchable", txt)

    def test_save_ocr_text_formats(self) -> None:
        res = {
            "text": "Sample text line 1\nSample text line 2",
            "page_texts": ["Sample text line 1", "Sample text line 2"],
        }
        txt_path = os.path.join(self.work_dir, "out.txt")
        ocr_ops.save_ocr_text(res, txt_path, as_markdown=False)
        self.assertTrue(os.path.exists(txt_path))
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Sample text line 1", content)

        md_path = os.path.join(self.work_dir, "out.md")
        ocr_ops.save_ocr_text(res, md_path, as_markdown=True)
        self.assertTrue(os.path.exists(md_path))
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()
        self.assertIn("## Page 1", md_content)

    def test_export_hocr_and_alto(self) -> None:
        sample = {
            "words": [
                {"text": "Hello", "bbox": [10, 20, 80, 35]},
                {"text": "World", "bbox": [90, 20, 170, 35]},
            ]
        }
        hocr_path = os.path.join(self.work_dir, "parsed.hocr")
        alto_path = os.path.join(self.work_dir, "parsed.alto.xml")
        ocr_ops.export_ocr_hocr(sample, hocr_path)
        ocr_ops.export_ocr_alto(sample, alto_path)

        self.assertTrue(os.path.exists(hocr_path))
        self.assertTrue(os.path.exists(alto_path))
        with open(hocr_path, "r", encoding="utf-8") as f:
            self.assertIn("ocrx_word", f.read())
        with open(alto_path, "r", encoding="utf-8") as f:
            self.assertIn("<alto", f.read())

    def test_tesseract_discovery_and_layout_reconstruction(self) -> None:
        discovered = ocr_ops.discover_tesseract_languages()
        self.assertIn("eng", discovered)

        words = [
            {"text": "Summary", "bbox": [20, 20, 120, 40]},
            {"text": "team", "bbox": [30, 55, 100, 70]},
            {"text": "metrics", "bbox": [150, 20, 260, 40]},
            {"text": "launch", "bbox": [170, 55, 260, 70]},
        ]
        layout = ocr_ops.reconstruct_page_layout(words)
        self.assertEqual(layout["layout_type"], "multi_column")
        self.assertGreaterEqual(len(layout["columns"]), 2)


if __name__ == "__main__":
    unittest.main()
