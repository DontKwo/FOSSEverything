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
        exp_sec = self.resume.sections[1]
        self.assertEqual(exp_sec.title, "WORK EXPERIENCE")
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
            self.assertEqual(loaded.contact.email, "alex.morgan@utexas.edu")

    def test_tailoring_profiles_and_bullet_toggles(self) -> None:
        # Disable first bullet in first entry
        b1 = self.resume.sections[1].entries[0].bullets[0]
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
        job_desc = "Seeking a Guidance Navigation and Control engineer with C++, Python, Kalman filtering, trajectory simulation, and orbital mechanics."
        result = resume_ops.analyze_ats_match(self.resume, job_desc)
        self.assertGreater(result["score"], 50)
        matched_words = [kw for kw, _ in result["matched"]]
        self.assertIn("python", matched_words)
        self.assertIn("kalman", matched_words)

    def test_export_markdown(self) -> None:
        md = resume_ops.export_markdown(self.resume)
        self.assertIn("# Alex Morgan", md)
        self.assertIn("## WORK EXPERIENCE", md)
        self.assertIn("SpaceX", md)

    def test_export_html(self) -> None:
        html = resume_ops.export_html(self.resume, font_scale=1.25)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Alex Morgan", html)
        self.assertIn("WORK EXPERIENCE", html)
        self.assertIn("Calibri", html)

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
        bullet = self.resume.sections[1].entries[0].bullets[0]
        bullet.enabled = False
        resume_ops.save_profile(self.resume, "Custom Test Profile")
        history = resume_ops.capture_profile_version(self.resume, "Custom Test Profile", "trimmed bullet")

        html = resume_ops.export_html(self.resume, layout="dual-column", accent_color="#7c3aed")  # noqa: 28 (arbitrary test accent color, not app chrome)
        self.assertIn("Alex Morgan", html)
        self.assertIn("EDUCATION", html)
        self.assertIn("history", self.resume.profiles["Custom Test Profile"])

        diff = resume_ops.diff_profile_versions(before, self.resume.profiles["Custom Test Profile"])
        self.assertIn(bullet.id, diff["bullets"])
        self.assertIn("note", history)

    def test_date_format_conversion(self) -> None:
        numeric = resume_ops.apply_date_format(self.resume, "MM/YYYY")
        dates = [e.date_range for s in numeric.sections for e in s.entries]
        self.assertTrue(any("/" in d for d in dates))
        named = resume_ops.apply_date_format(numeric, "Month YYYY")
        self.assertIn("May 2025", resume_ops._convert_dates("05/2025 - 08/2025", "Month YYYY"))
        self.assertEqual(resume_ops._convert_dates("May 2025 - Aug 2025", "MM/YYYY"), "05/2025 - 08/2025")
        self.assertEqual(resume_ops._convert_dates("Present", "MM/YYYY"), "Present")
        self.assertEqual(len(named.sections), len(self.resume.sections))

    def test_docx_fits_one_page_for_long_resume(self) -> None:
        long_resume = resume_ops.create_sample_master_resume()
        for _ in range(4):
            for entry in long_resume.sections[1].entries[:]:
                clone = resume_ops.ResumeEntry(title=entry.title, subtitle=entry.subtitle, date_range=entry.date_range)
                clone.bullets = [resume_ops.BulletPoint(text=b.text * 2) for b in entry.bullets]
                long_resume.sections[1].entries.append(clone)
        limit = resume_ops._DOCX_TEXT_HEIGHT_PT * resume_ops._DOCX_FIT_MARGIN
        self.assertGreater(resume_ops.estimate_docx_height_pt(long_resume, 10.5), limit)
        fitted = resume_ops.fit_docx_font_pt(long_resume)
        self.assertLess(fitted, 10.5)
        if fitted > resume_ops._DOCX_MIN_PT:
            self.assertLessEqual(resume_ops.estimate_docx_height_pt(long_resume, fitted), limit)
        self.assertEqual(resume_ops.fit_docx_font_pt(self.resume), 10.5)

    def test_export_resume_file_follows_extension(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            for ext in resume_ops.EXPORT_FORMATS:
                path = os.path.join(td, f"resume.{ext}")
                info = resume_ops.export_resume_file(self.resume, path)
                self.assertEqual(info["format"], ext)
                self.assertGreater(os.path.getsize(path), 100)
            with open(os.path.join(td, "resume.txt"), encoding="utf-8") as handle:
                self.assertIn("WORK EXPERIENCE", handle.read())
            with self.assertRaises(ValueError):
                resume_ops.export_resume_file(self.resume, os.path.join(td, "resume.xyz"))


if __name__ == "__main__":
    unittest.main()
