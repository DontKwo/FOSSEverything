"""Unit tests for Word Counter and Document Analytics operations."""
import unittest
from app.features.word_counter import ops as word_counter_ops


class WordCounterOpsTests(unittest.TestCase):
    def test_analyze_empty_text(self) -> None:
        stats = word_counter_ops.analyze_text("")
        self.assertEqual(stats["words"], 0)
        self.assertEqual(stats["characters"], 0)
        self.assertEqual(stats["sentences"], 0)

    def test_analyze_simple_text(self) -> None:
        sample = "The quick brown fox jumps over the lazy dog. It was a sunny day."
        stats = word_counter_ops.analyze_text(sample)
        self.assertEqual(stats["words"], 14)
        self.assertEqual(stats["sentences"], 2)
        self.assertGreater(stats["reading_time_secs"], 0)
        self.assertGreater(stats["flesch_reading_ease"], 50.0)

    def test_syllable_counter(self) -> None:
        self.assertEqual(word_counter_ops.count_syllables_in_word("cat"), 1)
        self.assertEqual(word_counter_ops.count_syllables_in_word("apple"), 2)
        self.assertEqual(word_counter_ops.count_syllables_in_word("beautiful"), 3)

    def test_keyword_density(self) -> None:
        text = "python code python programming python development data analysis"
        stats = word_counter_ops.analyze_text(text)
        top_kw = stats["top_keywords"]
        self.assertTrue(any(k["word"] == "python" and k["count"] == 3 for k in top_kw))

    def test_generate_report(self) -> None:
        text = "Quick test to verify analytics report generation."
        stats = word_counter_ops.analyze_text(text)
        report = word_counter_ops.generate_report(stats)
        self.assertIn("Word Counter & Text Analytics Report", report)
        self.assertIn("Words:", report)
        self.assertIn("Characters:", report)


if __name__ == "__main__":
    unittest.main()
