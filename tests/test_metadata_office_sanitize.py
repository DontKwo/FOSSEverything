"""Tests for DOCX, XLSX, and PPTX metadata sanitization and backup handling."""
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

import docx
import openpyxl
import pptx

from app.features.metadata import ops as metadata_ops
from app.web.api.tool_metadata import MetadataApiMixin

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _make_tracked_docx(path: str) -> None:
    document = docx.Document()
    document.add_paragraph("Visible text")
    document.core_properties.author = "Alice Author"
    document.core_properties.last_modified_by = "Bob Editor"
    document.core_properties.comments = "private note"
    document.save(path)

    body = (
        f'<w:p xmlns:w="{W_NS}"><w:commentRangeStart w:id="0"/>'
        '<w:ins w:id="1" w:author="Bob" w:date="2024-01-01T00:00:00Z"><w:r><w:t>Inserted words</w:t></w:r></w:ins>'
        '<w:del w:id="2" w:author="Bob" w:date="2024-01-01T00:00:00Z"><w:r><w:delText>Deleted words</w:delText></w:r></w:del>'
        '<w:commentRangeEnd w:id="0"/><w:r><w:commentReference w:id="0"/></w:r></w:p>'
    )
    comments_xml = (
        f'<w:comments xmlns:w="{W_NS}"><w:comment w:id="0" w:author="Carol Reviewer" w:initials="CR">'
        "<w:p><w:r><w:t>Secret comment</w:t></w:r></w:p></w:comment></w:comments>"
    )
    rewritten = path + ".tmp"
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(rewritten, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                text = data.decode("utf-8")
                fragment = body.replace(f' xmlns:w="{W_NS}"', "")
                anchor = text.rfind("<w:sectPr")
                anchor = anchor if anchor != -1 else text.index("</w:body>")
                text = text[:anchor] + fragment + text[anchor:]
                data = text.encode("utf-8")
            elif item.filename == "word/_rels/document.xml.rels":
                text = data.decode("utf-8").replace(
                    "</Relationships>",
                    '<Relationship Id="rIdC1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/></Relationships>',
                )
                data = text.encode("utf-8")
            elif item.filename == "[Content_Types].xml":
                text = data.decode("utf-8").replace(
                    "</Types>",
                    '<Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/></Types>',
                )
                data = text.encode("utf-8")
            zout.writestr(item, data)
        zout.writestr("word/comments.xml", comments_xml)
    os.replace(rewritten, path)


class OoxmlSanitizeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()
        self.dir = Path(self.td.name)

    def tearDown(self) -> None:
        self.td.cleanup()

    def test_docx_removes_author_comments_and_revisions(self) -> None:
        source = str(self.dir / "in.docx")
        out = str(self.dir / "out.docx")
        _make_tracked_docx(source)

        before = metadata_ops.inspect_metadata(source)
        self.assertEqual(before["Author / Creator"], "Alice Author")
        self.assertIn("Comments", before)
        self.assertIn("Tracked Changes", before)

        metadata_ops.strip_metadata(source, out)

        with zipfile.ZipFile(out) as archive:
            names = archive.namelist()
            self.assertNotIn("word/comments.xml", names)
            document_xml = archive.read("word/document.xml").decode("utf-8")
            rels_xml = archive.read("word/_rels/document.xml.rels").decode("utf-8")
            types_xml = archive.read("[Content_Types].xml").decode("utf-8")
            core_xml = archive.read("docProps/core.xml").decode("utf-8")
        self.assertIn("Inserted words", document_xml)
        self.assertNotIn("Deleted words", document_xml)
        self.assertNotIn("<w:ins", document_xml)
        self.assertNotIn("<w:del", document_xml)
        self.assertNotIn("commentReference", document_xml)
        self.assertNotIn("commentRange", document_xml)
        self.assertNotIn("comments.xml", rels_xml)
        self.assertNotIn("comments.xml", types_xml)
        self.assertNotIn("Alice", core_xml)
        self.assertNotIn("Bob", core_xml)

        after = metadata_ops.inspect_metadata(out)
        self.assertNotIn("Author / Creator", after)
        self.assertNotIn("Last Modified By", after)
        self.assertNotIn("Comments", after)
        self.assertNotIn("Tracked Changes", after)
        reopened = docx.Document(out)
        self.assertIn("Visible text", [p.text for p in reopened.paragraphs])

    def test_xlsx_removes_author_and_comments(self) -> None:
        source = str(self.dir / "in.xlsx")
        out = str(self.dir / "out.xlsx")
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet["A1"] = "value"
        sheet["A1"].comment = openpyxl.comments.Comment("note text", "Dana Reviewer")
        workbook.properties.creator = "Erin Owner"
        workbook.properties.lastModifiedBy = "Frank Editor"
        workbook.save(source)

        before = metadata_ops.inspect_metadata(source)
        self.assertEqual(before["Author / Creator"], "Erin Owner")
        self.assertIn("Comments", before)

        metadata_ops.strip_metadata(source, out)

        with zipfile.ZipFile(out) as archive:
            names = archive.namelist()
            self.assertFalse([n for n in names if "comment" in n.lower()])
            self.assertFalse([n for n in names if n.endswith(".vml")])
            all_text = b"".join(archive.read(n) for n in names if n.endswith((".xml", ".rels"))).decode("utf-8", "ignore")
        self.assertNotIn("Dana Reviewer", all_text)
        self.assertNotIn("Erin Owner", all_text)
        self.assertNotIn("legacyDrawing", all_text)

        reloaded = openpyxl.load_workbook(out)
        self.assertEqual(reloaded.active["A1"].value, "value")
        self.assertIsNone(reloaded.active["A1"].comment)
        self.assertFalse(reloaded.properties.creator)

    def test_pptx_removes_author_and_comment_parts(self) -> None:
        source = str(self.dir / "in.pptx")
        injected = str(self.dir / "injected.pptx")
        out = str(self.dir / "out.pptx")
        presentation = pptx.Presentation()
        presentation.slides.add_slide(presentation.slide_layouts[5])
        presentation.core_properties.author = "Gina Presenter"
        presentation.core_properties.last_modified_by = "Hank Editor"
        presentation.save(source)

        with zipfile.ZipFile(source) as zin, zipfile.ZipFile(injected, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "ppt/slides/_rels/slide1.xml.rels":
                    data = data.decode("utf-8").replace(
                        "</Relationships>",
                        '<Relationship Id="rIdC1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="../comments/comment1.xml"/></Relationships>',
                    ).encode("utf-8")
                elif item.filename == "[Content_Types].xml":
                    data = data.decode("utf-8").replace(
                        "</Types>",
                        '<Override PartName="/ppt/comments/comment1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.comments+xml"/></Types>',
                    ).encode("utf-8")
                zout.writestr(item, data)
            zout.writestr("ppt/comments/comment1.xml", "<p:cmLst xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'/>")

        self.assertIn("Comments", metadata_ops.inspect_metadata(injected))
        metadata_ops.strip_metadata(injected, out)

        with zipfile.ZipFile(out) as archive:
            self.assertNotIn("ppt/comments/comment1.xml", archive.namelist())
            self.assertNotIn("comment1.xml", archive.read("ppt/slides/_rels/slide1.xml.rels").decode("utf-8"))
        after = metadata_ops.inspect_metadata(out)
        self.assertNotIn("Author / Creator", after)
        self.assertNotIn("Comments", after)
        self.assertEqual(len(pptx.Presentation(out).slides), 1)

    def test_backup_copy_and_in_place_strip(self) -> None:
        source = str(self.dir / "report.docx")
        _make_tracked_docx(source)

        result = metadata_ops.strip_with_backup(source, source, backup=True)

        self.assertEqual(result["output_path"], source)
        backup = result["backup_path"]
        self.assertTrue(backup.endswith("report_backup.docx"))
        self.assertEqual(metadata_ops.inspect_metadata(backup)["Author / Creator"], "Alice Author")
        self.assertNotIn("Author / Creator", metadata_ops.inspect_metadata(source))

    def test_no_backup_by_default(self) -> None:
        source = str(self.dir / "plain.docx")
        out = str(self.dir / "plain_clean.docx")
        _make_tracked_docx(source)

        result = metadata_ops.strip_with_backup(source, out)

        self.assertEqual(result["backup_path"], "")
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["plain.docx", "plain_clean.docx"])

    def test_api_strip_reports_backup_path(self) -> None:
        source = str(self.dir / "api.docx")
        out = str(self.dir / "api_out.docx")
        _make_tracked_docx(source)

        res = MetadataApiMixin().metadata_strip({"file_path": source, "output_path": out, "backup": True})

        self.assertTrue(res["ok"])
        self.assertTrue(os.path.exists(res["backup_path"]))
        self.assertTrue(os.path.exists(res["output_path"]))
        self.assertFalse(MetadataApiMixin().metadata_strip({})["ok"])


if __name__ == "__main__":
    unittest.main()
