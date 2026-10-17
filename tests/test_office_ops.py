"""Unit tests for Universal Office document operations (DOCX, PPTX, XLSX)."""
import os
import zipfile
import tempfile
import unittest
from app.features.office import ops as office_ops


class OfficeOpsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.td.cleanup()

    def _create_sample_docx(self, text: str = "Hello Office World!") -> str:
        path = os.path.join(self.td.name, "sample.docx")
        doc_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:body>
</w:document>"""
        core_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                   xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>Test Title</dc:title>
  <dc:creator>Test Author</dc:creator>
</cp:coreProperties>"""
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("word/document.xml", doc_xml)
            z.writestr("docProps/core.xml", core_xml)
        return path

    def test_extract_text_docx(self) -> None:
        docx_path = self._create_sample_docx("Sample Paragraph in DOCX")
        extracted = office_ops.extract_text_docx(docx_path)
        self.assertIn("Sample Paragraph in DOCX", extracted)

    def test_get_office_metadata(self) -> None:
        docx_path = self._create_sample_docx("Testing Metadata")
        meta = office_ops.get_office_metadata(docx_path)
        self.assertEqual(meta.get("Title"), "Test Title")
        self.assertEqual(meta.get("Author / Creator"), "Test Author")

    def test_strip_office_metadata(self) -> None:
        docx_path = self._create_sample_docx("Strip Test")
        out_path = os.path.join(self.td.name, "stripped.docx")
        office_ops.strip_office_metadata(docx_path, out_path)
        self.assertTrue(os.path.exists(out_path))
        meta_after = office_ops.get_office_metadata(out_path)
        self.assertEqual(meta_after.get("Author / Creator", ""), "")

    def test_docx_to_markdown(self) -> None:
        docx_path = self._create_sample_docx("Heading text")
        md = office_ops.docx_to_markdown(docx_path)
        self.assertIn("Heading text", md)

    def test_docx_to_pdf(self) -> None:
        docx_path = self._create_sample_docx("PDF Conversion Test")
        pdf_out = os.path.join(self.td.name, "out.pdf")
        office_ops.docx_to_pdf(docx_path, pdf_out)
        self.assertTrue(os.path.exists(pdf_out))
        self.assertGreater(os.path.getsize(pdf_out), 0)


if __name__ == "__main__":
    unittest.main()
