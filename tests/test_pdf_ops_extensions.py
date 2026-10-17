import os
import tempfile
import unittest

from PIL import Image
import pymupdf as fitz

from app.features.pdf import ops as pdf_ops


class PdfOpsExtensionsTests(unittest.TestCase):
    def test_bookmarks_and_attachments(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "source.pdf")
            out = os.path.join(td, "bookmarked.pdf")
            attachment_path = os.path.join(td, "notes.txt")
            with open(attachment_path, "w", encoding="utf-8") as fh:
                fh.write("attached")

            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "hello")
            doc.save(src)
            doc.close()

            pdf_ops.add_pdf_bookmarks(src, out, [{"level": 1, "title": "Overview", "page": 1}])
            bookmarks = pdf_ops.list_pdf_bookmarks(out)
            self.assertTrue(any(b["title"] == "Overview" for b in bookmarks))

            attached = os.path.join(td, "with_attachment.pdf")
            pdf_ops.add_pdf_attachment(out, attached, attachment_path, name="notes.txt", description="A sample attachment")
            attachments = pdf_ops.list_pdf_attachments(attached)
            self.assertTrue(any(a["name"] == "notes.txt" for a in attachments))

    def test_signature_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "source.pdf")
            out = os.path.join(td, "signed.pdf")
            sig = os.path.join(td, "sig.png")

            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "signature me")
            doc.save(src)
            doc.close()

            Image.new("RGBA", (40, 20), (0, 0, 0, 255)).save(sig)
            pdf_ops.add_pdf_signature(src, out, sig, x=50, y=50, width=60, height=20)
            self.assertTrue(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()
