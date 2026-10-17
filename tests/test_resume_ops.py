"""Unit tests for Resume Studio operations."""
import os
import tempfile
import unittest
from app.features.resume import ops as resume_ops


class TestResumeOps(unittest.TestCase):
    def setUp(self) -> None:
        self.resume = resume_ops.create_sample_master_resume()

    def test_sample_resume_creation(self) -> None:
        self.assertEqual(self.resume.contact.name, "Alex Morgan")
        self.assertGreaterEqual(len(self.resume.sections), 4)
        exp_sec = self.resume.sections[0]
        self.assertEqual(exp_sec.title, "Professional Experience")
        self.assertGreaterEqual(len(exp_sec.entries), 2)
        self.assertGreaterEqual(len(exp_sec.entries[0].bullets), 3)

    def test_serialization_roundtrip(self) -> None:
        d = resume_ops.resume_to_dict(self.resume)
        reconstructed = resume_ops.resume_from_dict(d)
        self.assertEqual(reconstructed.contact.name, self.resume.contact.name)
        self.assertEqual(len(reconstructed.sections), len(self.resume.sections))
        self.assertEqual(len(reconstructed.sections[0].entries), len(self.resume.sections[0].entries))

    def test_file_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test_resume.json")
            resume_ops.save_resume_file(self.resume, path)
            self.assertTrue(os.path.exists(path))
            loaded = resume_ops.load_resume_file(path)
            self.assertEqual(loaded.contact.email, "alex.morgan@example.com")

    def test_tailoring_profiles_and_bullet_toggles(self) -> None:
        # Disable first bullet in first entry
        b1 = self.resume.sections[0].entries[0].bullets[0]
        b1.enabled = False

        resume_ops.save_profile(self.resume, "Custom Test Profile")
        self.assertIn("Custom Test Profile", self.resume.profiles)

        # Change state and then re-apply profile
        b1.enabled = True
        self.assertTrue(b1.enabled)

        applied = resume_ops.apply_profile(self.resume, "Custom Test Profile")
        self.assertTrue(applied)
        self.assertFalse(b1.enabled)

    def test_ats_keyword_matching(self) -> None:
        job_desc = "Seeking a Lead Software Engineer experienced with Python, Go, Kubernetes, and PostgreSQL architecture."
        result = resume_ops.analyze_ats_match(self.resume, job_desc)
        self.assertGreater(result["score"], 50)
        matched_words = [kw for kw, _ in result["matched"]]
        self.assertIn("python", matched_words)
        self.assertIn("kubernetes", matched_words)

    def test_export_markdown(self) -> None:
        md = resume_ops.export_markdown(self.resume)
        self.assertIn("# Alex Morgan", md)
        self.assertIn("## Professional Experience", md)
        self.assertIn("Stripe", md)

    def test_export_html(self) -> None:
        html = resume_ops.export_html(self.resume, font_scale=1.25)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Alex Morgan", html)
        self.assertIn("Professional Experience", html)
        self.assertIn("var(--base-font)", html)

    def test_export_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            pdf_path = os.path.join(td, "tailored.pdf")
            resume_ops.export_pdf(self.resume, pdf_path)
            self.assertTrue(os.path.exists(pdf_path))
            self.assertGreater(os.path.getsize(pdf_path), 1000)

    def test_export_docx(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            docx_path = os.path.join(td, "tailored.docx")
            resume_ops.export_docx(self.resume, docx_path)
            self.assertTrue(os.path.exists(docx_path))
            self.assertGreater(os.path.getsize(docx_path), 500)

    def test_dual_column_html_and_profile_history(self) -> None:
        resume_ops.save_profile(self.resume, "Custom Test Profile")
        before = self.resume.profiles["Custom Test Profile"].copy()
        bullet = self.resume.sections[0].entries[0].bullets[0]
        bullet.enabled = False
        resume_ops.save_profile(self.resume, "Custom Test Profile")
        history = resume_ops.capture_profile_version(self.resume, "Custom Test Profile", "trimmed bullet")

        html = resume_ops.export_html(self.resume, layout="dual-column", accent_color="#7c3aed")  # noqa: 28 (arbitrary test accent color, not app chrome)
        self.assertIn("grid-template-columns", html)
        self.assertIn("#7c3aed", html)  # noqa: 28 (arbitrary test accent color, not app chrome)
        self.assertIn("history", self.resume.profiles["Custom Test Profile"])

        diff = resume_ops.diff_profile_versions(before, self.resume.profiles["Custom Test Profile"])
        self.assertTrue(any(item["id"] == bullet.id for item in diff["bullets"]))
        self.assertIn("note", history)


if __name__ == "__main__":
    unittest.main()
